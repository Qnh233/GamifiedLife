"""
Planner Agent - Goal Decomposition and Task Planning

This agent breaks down high-level goals into specific daily "quest" tasks,
assigns difficulty levels, XP rewards, and calculates random drop rates.
"""
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser

from app.agents.state import AgentState
from app.agents.llm_client import llm_client
from app.common.POJO.TaskPlan import TaskPlan
from app.config import config
from datetime import datetime
import uuid


PLANNER_SYSTEM_PROMPT = """You are the Planner Agent for the Gamified Life Engine.

Your role is to break down user goals into specific, actionable daily tasks (quests).

For each goal, you must:
1. Create a main Goal object with title, description, deadline
2. Break it down into 3-7 daily tasks based on the timeframe
3. Assign difficulty levels (easy, medium, hard, epic) to each task
4. Determine if tasks are "challenges" (special tasks with higher rewards)

Task Difficulty Guidelines:
- EASY: Simple tasks taking < 30 minutes (1.0x XP multiplier)
- MEDIUM: Regular tasks taking 30-60 minutes (1.5x XP multiplier)  
- HARD: Complex tasks taking 1-2 hours (2.0x XP multiplier)
- EPIC: Major milestones or very difficult tasks (3.0x XP multiplier)

Challenge Types:
- "time_challenge": Complete within time limit
- "streak_challenge": Complete multiple days in a row
- "combo_challenge": Complete multiple related tasks
- "hidden_challenge": Rare special tasks

Base XP per task: {base_xp}

Output a JSON object with this structure:
{{
    "goal": {{
        "id": "unique_id",
        "title": "goal title",
        "description": "goal description",
        "deadline": "YYYY-MM-DD or null",
        "xp_reward": total_xp_for_goal
    }},
    "tasks": [
        {{
            "id": "unique_id",
            "title": "task title",
            "description": "task description",
            "difficulty": "easy|medium|hard|epic",
            "is_challenge": true|false,
            "challenge_type": "time_challenge|streak_challenge|combo_challenge|hidden_challenge|null",
            "due_date": "YYYY-MM-DD",
            "xp_reward": calculated_xp
        }}
    ],
    "reasoning": "explanation of how you broke down the goal"
}}

Consider the user's context and preferences when creating tasks.
""".format(base_xp=config.BASE_XP_PER_TASK)


async def planner_node(state: AgentState) -> AgentState:
    user_input = state["user_input"]
    # 1. 实例化解析器，绑定你的 Pydantic 模型
    parser = JsonOutputParser(pydantic_object=TaskPlan)
    # format_instructions = parser.get_format_instructions()
    context = ""
    if state.get("user_profile"):
        profile = state["user_profile"]
        profile_dict = profile if isinstance(profile, dict) else profile.to_dict() if hasattr(profile, 'to_dict') else {}
        context = f"""
User Profile Context:
- Level: {profile_dict.get('level', 1)}
- Total XP: {profile_dict.get('total_xp', 0)}
- Tasks Completed: {profile_dict.get('tasks_completed', 0)}
- Streak Days: {profile_dict.get('streak_days', 0)}
"""
    # Ensure we don't duplicate the raw input if it's already in state history
    messages_for_prompt = state["messages"]
    if messages_for_prompt and isinstance(messages_for_prompt[-1], HumanMessage) and messages_for_prompt[-1].content == user_input:
        messages_for_prompt = messages_for_prompt[:-1]

    message = [SystemMessage(content=PLANNER_SYSTEM_PROMPT)] + messages_for_prompt + [HumanMessage(content=f"{user_input}\n{context}")]

    # Use JSON mode to avoid provider-specific tool_choice incompatibilities.
    response = await llm_client.llm.ainvoke(message)

    # 2. 解析 LLM 输出
    content = response.content.strip()
    # 3. 解析 JSON
    try:
        task_plan = parser.parse(content)
        response_data = task_plan.model_dump() if hasattr(task_plan, "model_dump") else task_plan
    except Exception as e:
        print(f"[Planner Error] Failed to parse JSON: {content}\nError: {e}")
        # 容错处理：如果解析失败，创建一个默认的空任务计划
        response_data = {
            "goal": {
                "id": str(uuid.uuid4()),
                "title": "Default Goal",
                "description": "This is a fallback goal due to parsing error.",
                "deadline": None,
                "xp_reward": 0
            },
            "tasks": []
        }

    goal_data = response_data.get("goal", {})
    tasks_container = response_data.get("tasks", [])
    if isinstance(tasks_container, dict):
        tasks_data = tasks_container.get("tasks", [])
    elif isinstance(tasks_container, list):
        tasks_data = tasks_container
    else:
        tasks_data = []
    
    goal_id = goal_data.get("id", str(uuid.uuid4()))
    
    tasks = []
    for task_data in tasks_data:
        difficulty_str = task_data.get("difficulty", "medium")
        
        xp_multiplier = config.DIFFICULTY_MULTIPLIER.get(difficulty_str, 1.0)
        if task_data.get("is_challenge"):
            xp_multiplier *= 1.5
            
        xp_reward = int(config.BASE_XP_PER_TASK * xp_multiplier)
        
        due_date = None
        if task_data.get("due_date"):
            try:
                due_date = datetime.fromisoformat(task_data["due_date"])
            except:
                pass
        
        task = {
            "id": task_data.get("id", str(uuid.uuid4())),
            "goal_id": goal_id,
            "title": task_data.get("title", ""),
            "description": task_data.get("description"),
            "difficulty": difficulty_str,
            "status": "pending",
            "xp_reward": xp_reward,
            "is_challenge": task_data.get("is_challenge", False),
            "challenge_type": task_data.get("challenge_type"),
            "due_date": task_data.get("due_date")
        }
        tasks.append(task)
    
    goal = {
        "id": goal_id,
        "title": goal_data.get("title", ""),
        "description": goal_data.get("description"),
        "deadline": goal_data.get("deadline"),
        "xp_reward": goal_data.get("xp_reward", config.BASE_XP_PER_TASK * len(tasks_data))
    }
    
    response_msg = f"Created goal '{goal_data['title']}' with {len(tasks)} tasks:\n"
    for t in tasks:
        response_msg += f"- {t['title']} ({t['difficulty']})\n"

    # Return state update dict (delta) instead of modifying in-place
    return {
        "current_goal": goal,
        "current_tasks": tasks,
        "planner_output": response_data,
        "final_response": response_msg,
        "workflow_status": "planning_completed",
        "next_agent": "RESPONSE",
        "messages": [AIMessage(content=response_msg, name="planner")]
    }
