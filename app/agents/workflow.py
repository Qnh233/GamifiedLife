"""
LangGraph workflow - Multi-Agent Orchestration

This module defines the LangGraph workflow that orchestrates
all agents together using state machine patterns.
"""
import time
import asyncio
import importlib
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.agents.state import AgentState, create_initial_state
from app.agents.supervisor import supervisor_node
from app.agents.planner import planner_node
from app.agents.reward import reward_node
from app.agents.query import query_node
from app.agents.chat import chat_node
from app.agents.reflector import reflector_node
from langgraph.graph.state import CompiledStateGraph
from app.mcp.mcp_tools import agent_tools
from app.config import config as app_config
from app.utils.logging_utils import get_logger

# app/agents/workflow.py 顶部
from openinference.instrumentation.langchain import LangChainInstrumentor

# 一键对 LangChain/LangGraph 组件插桩
LangChainInstrumentor().instrument()
logger = get_logger(__name__)

def create_workflow() -> CompiledStateGraph:
    # 优先使用 Redis 持久化 checkpoint；若 Redis/依赖不可用则降级到内存模式。
    checkpointer = MemorySaver()
    # try:
    #     redis_module = importlib.import_module("langgraph.checkpoint.redis")
    #     redis_checkpoint_saver_cls = getattr(redis_module, "RedisSaver", None)
    #     if redis_checkpoint_saver_cls is None:
    #         raise ImportError("RedisSaver not found in langgraph.checkpoint.redis")
    #     redis_saver = redis_checkpoint_saver_cls(
    #             redis_url=app_config.REDIS_URL,
    #             # 关键保护：为 checkpoint Redis 请求设置超时，防止对话链路被无限阻塞。
    #             connection_args={
    #                 "socket_connect_timeout": app_config.REDIS_SOCKET_CONNECT_TIMEOUT_SEC,
    #                 "socket_timeout": app_config.REDIS_SOCKET_TIMEOUT_SEC,
    #                 "retry_on_timeout": True,
    #             },
    #             checkpoint_prefix="workflow_checkpoint",
    #             checkpoint_write_prefix="workflow_checkpoint_write",
    #     )
    #     redis_saver.setup()
    #     checkpointer = redis_saver
    #     logger.info("LangGraph checkpointer initialized with Redis.")
    # except Exception as exc:
    #     logger.warning(
    #         "Redis checkpointer unavailable (requires Redis Stack with RediSearch, e.g. FT._LIST support), fallback to MemorySaver: %s",
    #         exc,
    #     )
    workflow = StateGraph(AgentState)
    # 监督节点
    workflow.add_node("supervisor", supervisor_node)
    # 规划 处理规划任务
    workflow.add_node("planner", planner_node)
    # 奖励节点 处理奖励计算和生成奖励消息
    workflow.add_node("reward",  reward_node)
    # 查询节点 处理用户查询和信息检索
    workflow.add_node("query",  query_node)
    # 聊天节点 处理用户与智能体的直接对话
    workflow.add_node("chat", chat_node)
    # 反思节点 处理用户画像更新
    workflow.add_node("reflector",  reflector_node)
    # 响应节点 统一处理所有路径的最终响应生成
    workflow.add_node("response", lambda state: state)

    def rout_supervisor(state: AgentState) -> str:
        # 监督节点根据状态决定下一步路由
        next_agent = state.get("next_agent","CHAT")
        if next_agent == "REWARD":
            return "reward"
        elif next_agent == "QUERY":
            return "query"
        elif next_agent == "CHAT":
            return "chat"
        elif next_agent == "PLANNING":
            return "planner"  # 默认直接生成响应
        else:
            return "response"
    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        rout_supervisor,
        {
            "reward": "reward",
            "query": "query",
            "chat": "chat",
            "planner": "planner",
        }
    )

    def tools_condition(state: AgentState) -> str:
        # 永远只看状态里 messages 列表的最后一条消息
        last_message = state["messages"][-1]
        # 检查这条消息里有没有大模型生成的 tool_calls 标记
        if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
            return "tools"  # 触发工具节点
        else:
            return "response"  # 或者返回你想去的下一个业务节点
    # 1. 初始化不同的 ToolNode -- 对应赋予使用不同的工具
    query_tools_node = ToolNode(agent_tools)
    planner_tools_node = ToolNode(agent_tools)
    chat_tools_node = ToolNode(agent_tools)

    # 2. 分别添加到图中
    workflow.add_node("query_tools",  query_tools_node)
    workflow.add_node("chat_tools",  chat_tools_node)
    workflow.add_node("planner_tools", planner_tools_node)

    # 3. 各自绑定自己的条件边和返回边 (形成独立的小闭环)
    workflow.add_conditional_edges("query", tools_condition, {"tools": "query_tools", "response": "response"})
    workflow.add_edge("query_tools", "query")  # 精准原路返回

    workflow.add_conditional_edges("planner", tools_condition, {"tools": "planner_tools", "response": "response"})
    workflow.add_edge("planner_tools", "planner")  # 精准原路返回

    workflow.add_conditional_edges("chat", tools_condition, {"tools": "chat_tools", "response": "response"})
    workflow.add_edge("chat_tools", "chat")  # 精准原路返回

    # workflow.add_edge("chat", "response")
    workflow.add_edge("reward", "response")

    # Change flow to include reflection after response
    # workflow.add_edge("response", "reflector")
    workflow.add_edge("response", END)
    
    return workflow.compile(checkpointer=checkpointer)


workflow = create_workflow()


def _build_thread_id(user_id: str, session_id: Optional[str]) -> str:
    # 多会话隔离：同一用户在不同会话下使用独立 thread_id，避免 checkpoint 覆盖。
    safe_session_id = (session_id or "").strip() or "default"
    return f"{user_id}:{safe_session_id}"


async def run_agent_workflow(
    user_id: str,
    user_input: str,
    user_profile=None,
    current_goal=None,
    current_tasks=None,
    session_id: Optional[str] = None,
) -> AgentState:
    initial_state = create_initial_state(user_id, user_input, current_goal, current_tasks)
    if user_profile:
        initial_state["user_profile"] = user_profile
    config = RunnableConfig(
        configurable={"user_id": user_id, "thread_id": _build_thread_id(user_id, session_id)}
    )
    final_state = await asyncio.wait_for(
        workflow.ainvoke(initial_state, config=config),
        timeout=app_config.AGENT_WORKFLOW_TIMEOUT_SEC,
    )
    return final_state

async def stream_agent_workflow(
    user_id: str,
    user_input: str,
    user_profile=None,
    current_goal=None,
    current_tasks=None,
    session_id: Optional[str] = None,
):
    initial_state = create_initial_state(user_id, user_input, current_goal, current_tasks)
    if user_profile:
        initial_state["user_profile"] = user_profile
    config = RunnableConfig(
        configurable={"user_id": user_id, "thread_id": _build_thread_id(user_id, session_id)}
    )
    async for event in workflow.astream(initial_state, stream_mode="updates", config=config):
        yield event

