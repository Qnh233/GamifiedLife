"""
Chat Agent - General conversation and assistance

This agent handles casual conversation and queries that don't fit into the
planning, reward, or query categories.
"""
import json

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from app.agents.state import AgentState
from app.agents.llm_client import llm_client
from app.agents.node_helpers import analyze_tool_necessity, tool_aware
from app.common.constant import ToolCallState


CHAT_SYSTEM_PROMPT = """You are a helpful and encouraging Gamified Life Assistant.

Your role is to:
1. Engage in casual conversation with the user (e.g., greet them, ask how they are doing).
2. Provide encouragement and motivation.
3. Answer general questions about productivity and gamification.
4. If the user asks something outside your scope, polite guide them to planning or query features.

Keep your tone friendly, upbeat, and gamified (e.g., use terms like "player", "quest", "level up").
"""

async def chat_node(state: AgentState) -> AgentState:
    user_input = state["user_input"]
    profile = state.get("user_profile", {})
    if profile:
        profile_dict = profile if isinstance(profile, dict) else profile.to_dict() if hasattr(profile, 'to_dict') else {}
        name = profile_dict.get('username', 'Player')
    else:
        name = 'Player'

    user_input = f"User Name: {name}\nUser Input: {user_input}\n"
    
    # Sanitize history: Remove or fix dangling tool calls to prevent validation errors
    clean_history = []
    history = state["messages"]
    for i, msg in enumerate(history):
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            # Check if this tool call is answered by the next message
            is_answered = False
            if i + 1 < len(history):
                next_msg = history[i+1]
                if isinstance(next_msg, ToolMessage):
                    is_answered = True
            
            if not is_answered:
                # Use a plain AIMessage without tool_calls to avoid validation error
                # We preserve content so context is not lost
                clean_history.append(AIMessage(content=msg.content))
                continue
        
        clean_history.append(msg)

    messages = clean_history + [SystemMessage(content=CHAT_SYSTEM_PROMPT),HumanMessage(content=user_input)]

    # Use llm (without tools) to prevent chat agent from generating unhandled tool calls
    response = await llm_client.llm.ainvoke(messages)

    return {
        "messages": [response],
        "workflow_status": "chat_responded",
        "final_response": response.content,
    }
