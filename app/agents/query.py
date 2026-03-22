"""
Query Agent - User Status and Task Queries
"""
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.agents.state import AgentState
from app.agents.llm_client import llm_client


QUERY_SYSTEM_PROMPT = """You are the Query Agent for the Gamified Life Engine.

Your role is to answer user questions about their status, progress, tasks, and goals.

Respond with a helpful, informative message. You have access to:
- User profile (level, XP, achievements, inventory)
- Current tasks and goals
- Task completion history

Format your response as:
- Current status summary
- Active tasks list
- Progress towards goals
- Any relevant achievements or rewards

Keep responses concise but informative.
"""

async def query_node(state: AgentState, config: RunnableConfig) -> AgentState:
    user_input = state["user_input"]
    profile = state.get("user_profile")
    tasks = state.get("current_tasks", [])
    goal = state.get("current_goal")
    current_user_id = config["configurable"]["user_id"]

    if profile:
        profile_dict = profile if isinstance(profile, dict) else profile.to_dict() if hasattr(profile, 'to_dict') else {}
    else:
        profile_dict = {}
    
    context = f"""
User Query: {user_input}
"""
    # User
    # Profile:
    # - Level: {profile_dict.get('level', 1)}
    # - Total
    # XP: {profile_dict.get('total_xp', 0)}
    # - Current
    # XP: {profile_dict.get('current_xp', 0)}
    # - XP
    # to
    # Next
    # Level: {profile_dict.get('xp_to_next_level', 1000)}
    # - Tasks
    # Completed: {profile_dict.get('tasks_completed', 0)}
    # - Streak
    # Days: {profile_dict.get('streak_days', 0)}
    #
    # Current
    # Goal: {goal.get('title') if goal else "No active goal"}
    # Tasks: {len(tasks)}
    # tasks
    # 2. 将 System Context 和用户的历史消息拼接
    # state["messages"] 包含了从开始到现在的对话历史，甚至包括之前工具的执行结果
    
    # Ensure we don't duplicate the raw input if it's already in state history
    messages_for_prompt = state["messages"]
    if messages_for_prompt and isinstance(messages_for_prompt[-1], HumanMessage) and messages_for_prompt[-1].content == user_input:
        messages_for_prompt = messages_for_prompt[:-1]

    messages = [SystemMessage(content=QUERY_SYSTEM_PROMPT)] + messages_for_prompt + [HumanMessage(content=context)]

    # 3. 异步调用绑定了工具的 LLM
    # 如果 LLM 觉得不需要工具，它返回纯文本的 AIMessage
    # 如果 LLM 觉得需要工具，它返回带有 tool_calls 属性的 AIMessage
    response = await llm_client.llm_with_tools.ainvoke(messages,config={'configurable':{'user_id':current_user_id}})
    # 4. 严格按照 Reducer 规则返回增量数据
    return {
        "messages": [response],
        "workflow_status": "query_responded",
        "final_response": response.content
    }
