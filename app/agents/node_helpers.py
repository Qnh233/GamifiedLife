# python
import inspect
import asyncio
from typing import Callable, Optional, Any
from app.agents.state import AgentState
from functools import wraps
from typing import Callable, Dict, Any
from app.mcp.client import mcp_client
from app.agents.llm_client import llm_client
import json
from app.utils.logging_utils import get_logger, log_event, preview_text

logger = get_logger(__name__)

def tool_aware(node_func: Callable) -> Callable:
    """装饰器：自动处理工具调用和返回"""

    @wraps(node_func)
    async def wrapper(state: AgentState) -> AgentState:
        # 1. 检查是否是工具返回
        if state.get("tool_status") == "completed" and state.get("tool_sender") == node_func.__name__:
            # 处理工具返回结果
            tool_result = state.get("tool_result")
            return handle_tool_return(state, tool_result, node_func.__name__)
        else:
            # 正常流程，执行主逻辑，加入工具调用prompt
            # 加入工具调用prompt
            tools_prompt = await generate_tool_prompt()  # 预生成工具提示，避免每次调用都生成
            state["tools_prompt"] = tools_prompt  # 确保存在

        # 2. 执行节点主逻辑
        result = await node_func(state)

        # 3. 如果节点需要调用工具，装饰器会自动处理
        if result.get("needs_tool_call", False):
            return prepare_tool_call(result, result["tool_name"], result["tool_args"], node_func.__name__)

        return result

    return wrapper
async def generate_tool_prompt() -> str:
    """生成工具调用提示文本"""
    try:
        tools = await mcp_client.list_tools()
    except Exception as e:
        log_event(logger, "agent.node_helpers.list_tools_failed", level="error", error=str(e))
        return None
    if not tools:
        return None
    tools_desc = ["可用工具："]
    for t in tools:
        # Format: - name: description (schema: ...)
        schema_str = json.dumps(t.get("inputSchema", {}))
        tools_desc.append(f"- {t['name']}: {t['description']}\n  Schema: {schema_str}")

    # If no tools are available, return none
    if not tools_desc:
        return None
    log_event(logger, "agent.node_helpers.tools_listed", tools_count=len(tools))
    tools_prompt = "\n".join(tools_desc)

    tools_prompt.join("\n如果需要调用工具，请严格按照以下格式在响应中指定并且只回复工具调用json，其他信息不需要：")
    tools_prompt.join('{"needs_tool_call": True, "tool_name": "tool_name", "tool_args": {"arg1": "value1", ...}}')

    return tools_prompt

def handle_tool_return(state: AgentState, tool_result: Any, source_node: str) -> AgentState:
    """统一处理工具返回"""
    # 清除工具状态
    new_state = {
        **state,
        "tool_status": "idle",
        "tool_result": None,
        "tool_sender": None,
        "tool_name": None,
        "tool_args": None
    }

    # 将工具结果添加到状态中供节点使用
    new_state["tool_result"] = tool_result

    return new_state


def prepare_tool_call(state: AgentState, tool_name: str, tool_args: Dict, source_node: str) -> AgentState:
    """准备工具调用"""
    return {
        **state,
        "tool_status": "pending",
        "tool_name": tool_name,
        "tool_args": tool_args,
        "tool_sender": source_node,
        "needs_tool_call": False  # 清除标记
    }


def set_tool_response(state: AgentState, result: Any, target: str, origin: str = "tools") -> AgentState:
    """
    工具调用完成时由 tools 节点调用，标记返回并指定要激活的目标节点名（与 workflow 中 add_node 使用的 name 对应）。
    """
    state["_tool_response"] = result
    state["_tool_target"] = target
    state["_tool_origin"] = origin
    return state

class BaseAgentNode:
    """
    可选基类：节点可以继承并实现 run 和 on_tool_return。
    workflow 中注册时使用节点实例（可调用）。
    """
    def __call__(self, state: AgentState):
        # 支持同步或异步 run
        result = self.run(state)
        if inspect.isawaitable(result):
            return result
        return result
    async def run(self, state: AgentState) -> AgentState:
        """默认实现，子类可以覆盖"""
        raise NotImplementedError("子类必须实现run方法")

########################
# Tool Selection Logic #
########################

async def analyze_tool_necessity(user_input: str, node_context: str = "") -> dict:
    """
    Analyzes if the user input requires any of the available MCP tools.

    Args:
        user_input: The user's message.
        node_context: Optional context about the current node's role (e.g., "query", "chat").

    Returns:
        dict: {
            "tool": "tool_name" | "none",
            "args": { ... }
        }
    """
    try:
        tools = await mcp_client.list_tools()
    except Exception as e:
        log_event(logger, "agent.node_helpers.list_tools_failed", level="error", error=str(e))
        return {"tool": "none"}

    tools_desc = []
    for t in tools:
        # Format: - name: description (schema: ...)
        schema_str = json.dumps(t.get("inputSchema", {}))
        tools_desc.append(f"- {t['name']}: {t['description']}\n  Schema: {schema_str}")

    # If no tools are available, return none
    if not tools_desc:
        return {"tool": "none"}

    tools_prompt = "\n".join(tools_desc)

    system_prompt = f"""
    You are a smart assistant that decides if external tools are needed to answer the user's request.
    
    Current Node Context: {node_context}
    
    Available Tools:
    {tools_prompt}
    
    - none: If the request can be handled without tools or by the current node's internal knowledge.
    
    Analyze the user input and decide.
    If a tool is needed, return the tool name and arguments that match the tool's schema.
    
    Return JSON format:
    {{
        "tool": "tool_name" | "none",
        "args": {{ "arg_name": "value", ... }}
    }}
    """

    try:
        intent = await llm_client.acomplete_json(system_prompt, user_input)

        # Validate structure
        if "tool" not in intent:
            intent["tool"] = "none"
        if "args" not in intent:
            intent["args"] = {}

        return intent
    except Exception as e:
        log_event(logger, "agent.node_helpers.analysis_failed", level="error", error=str(e))
        return {"tool": "none"}
