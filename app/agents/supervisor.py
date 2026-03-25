"""
Supervisor Agent - Intent Routing and Decision Making

This agent acts as the orchestrator that determines whether to route
the user input to the Planner (for new goals) or to the Reward Agent
(for task completion and gamification).
"""
import json

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.agents.state import AgentState
from app.agents.llm_client import llm_client

from app.common.POJO.supervisor_Decision import Decision
from app.utils.logging_utils import get_logger, log_event, preview_text
logger = get_logger(__name__)

SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor Agent for the Gamified Life Engine.

Your role is to analyze user input and determine the appropriate action:

1. PLANNING: When user wants to create new goals, tasks, or plans
   - Keywords: "我要完成", "想做", "计划", "目标", "要搞定", "需要完成"
   - Examples: "这周我要搞定遥感论文的初稿", "想开始健身"

2. REWARD: When user reports completion, wants rewards, or checks status
   - Keywords: "完成了", "搞定了", "做完了", "打卡", "奖励", "成就"
   - Examples: "我今天完成了健身", "来看看我的成就"

3. QUERY: When user asks questions about their status, tasks, or goals
   - Keywords: "怎么样", "有什么", "查看", "状态", "进度"
   - Examples: "我的任务进度怎样", "今天有什么任务"

4. CHAT: General conversation that doesn't fit the above categories
   - Keywords: Any casual conversation

Respond with a JSON object containing:
- "decision": "PLANNING" | "REWARD" | "QUERY" | "CHAT"
- "reasoning": Brief explanation of your decision
- "confidence": Score from 0 to 1

Example output:
{"decision": "PLANNING", "reasoning": "User wants to create a new goal for their thesis", "confidence": 0.95}
"""

async def supervisor_node(state: AgentState) -> AgentState:
    user_input = state["user_input"]
    # 1. 实例化解析器，绑定你的 Pydantic 模型
    parser = JsonOutputParser(pydantic_object=Decision)
    # format_instructions = parser.get_format_instructions()

    # Ensure we don't duplicate the raw input if it's already in state history
    messages_for_prompt = state["messages"]
    if messages_for_prompt and isinstance(messages_for_prompt[-1], HumanMessage) and messages_for_prompt[-1].content == user_input:
        messages_for_prompt = messages_for_prompt[:-1] # Remove the raw input from history part

    # Construct prompt: System -> History -> Raw Input
    message = [SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT)] + messages_for_prompt + [HumanMessage(content=user_input)]

    # Use JSON mode to avoid provider-specific tool_choice incompatibilities.
    # structured_llm = llm_client.llm(Decision, method="json_mode")

    response = await llm_client.llm.ainvoke(message)
    # response_data = response.model_dump() if hasattr(response, "model_dump") else response
    # 2. 解析 LLM 输出
    content = response.content.strip()
    # 3. 解析 JSON
    try:
        response_data = json.loads(content)
        # 如果你后续严格需要 Pydantic 对象，可以取消下面这行的注释:
        # response_data = Decision(**response_data).model_dump()
    except json.JSONDecodeError:
        log_event(logger, "agent.supervisor.parse_error", level="error", content_preview=preview_text(content))
        # 容错处理：如果解析失败，默认走常规聊天
        response_data = {
            "decision": "CHAT",
            "reasoning": "Fallback routing due to JSON parsing error.",
            "confidence": 0.0
        }
    
    # Return delta update instead of modifying state in-place
    # print(f"Supervisor decided to route to: \-\> {str(response_data.get('decision', 'CHAT')).upper()}")
    # print("=====================================\n")
    log_event(
        logger,
        "agent.supervisor.route_decision",
        user_id=state.get("user_id"),
        decision=str(response_data.get("decision", "CHAT")).upper(),
        confidence=response_data.get("confidence"),
        reasoning=preview_text(response_data.get("reasoning")),
    )

    return {
        "supervisor_decision": response_data,
        "next_agent": str(response_data.get("decision", "CHAT")).upper(),
        "workflow_status": f"routed_to_{str(response_data.get('decision', 'CHAT')).lower()}",
        "messages": [AIMessage(
            role="assistant",
            agent="supervisor",
            content=f"Routed to {response_data.get('decision', 'CHAT')} - {response_data.get('reasoning', '')}"
        )]
    }
