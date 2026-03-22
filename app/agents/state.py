"""
Core state definition for LangGraph workflow
"""
from typing import TypedDict, Optional, Annotated
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import add_messages

from app.common.constant import ToolCallState


class AgentState(TypedDict):
    user_id: str
    user_input: str
    user_profile: Optional[dict]
    
    current_goal: Optional[dict]
    current_tasks: list[dict]


    supervisor_decision: Optional[dict]
    planner_output: Optional[dict]
    reward_output: Optional[dict]
    
    game_events: list[dict]
    rewards_earned: list[dict]
    # 核心魔法：add_messages 会自动处理列表的 Append 操作
    # 无论是 HumanMessage, AIMessage(包含 tool_calls), 还是 ToolMessage，都会被安全追加
    messages: Annotated[list[BaseMessage], add_messages]
    
    final_response: Optional[str]
    next_agent: Optional[str]
    workflow_status: str


def create_initial_state(user_id: str, user_input: str, current_goal: Optional[dict] = None, current_tasks: list[dict] = None) -> AgentState:
    return {
        "user_id": user_id,
        "user_input": user_input,
        "user_profile": None,
        "current_goal": current_goal,
        "current_tasks": current_tasks if current_tasks is not None else [],
        "supervisor_decision": None,
        "planner_output": None,
        "reward_output": None,
        "game_events": [],
        "rewards_earned": [],
        "messages": [HumanMessage(content=user_input)],
        "final_response": None,
        "next_agent": None,
        "workflow_status": "started"
    }
