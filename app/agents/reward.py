"""
Gamification/Reward Agent - Task Completion, Achievements, and Rewards

This agent handles:
1. Processing task completion events
2. Calculating XP gains and level ups
3. Rolling for random loot drops
4. Generating immersive reward messages
5. Checking and unlocking achievements
"""
from langchain_core.messages import SystemMessage, AIMessage
import json

from app.agents.state import AgentState
from app.agents.llm_client import llm_client
from app.config import config
from datetime import datetime
import uuid
from app.utils.logging_utils import get_logger, log_event
from app.evals.core_logic import apply_xp_to_profile, calculate_drop, calculate_xp_reward, safe_json_loads
logger = get_logger(__name__)


REWARD_SYSTEM_PROMPT = """You are the Gamification/Reward Agent for the Gamified Life Engine.

Your role is to create immersive, rewarding experiences when users complete tasks.

When a task is completed, you must:
1. Calculate XP earned (based on task difficulty)
2. Roll for random loot drops (base drop rate: {drop_rate}%)
3. Check for achievement unlocks
4. Generate an immersive, celebratory message
5. Check if user levels up

XP Calculation:
- Easy: {base_xp} * 1.0 = {base_xp} XP
- Medium: {base_xp} * 1.5 = {base_xp * 1.5} XP  
- Hard: {base_xp} * 2.0 = {base_xp * 2} XP
- Epic: {base_xp} * 3.0 = {base_xp * 3} XP
- Challenge Bonus: +50% XP

Drop Rate Modifiers:
- Hard tasks: +5% drop rate
- Epic tasks: +15% drop rate
- Challenge completion: +10% drop rate
- Streak bonus: +2% per streak day

Rarity Rolls:
- Common: 60% of drops
- Rare: 25% of drops  
- Epic: 12% of drops
- Legendary: 3% of drops

Make the message exciting, use game terminology, and celebrate the user's accomplishment!
"""


REWARD_POOL = [
    {"name": "XP Boost", "rarity": "common", "type": "xp", "value": 75, "description": "Increases XP for your next task"},
    {"name": "Health Potion", "rarity": "common", "type": "item", "value": 1, "description": "Recover from a failed task"},
    {"name": "Mystery Box", "rarity": "rare", "type": "item", "value": 1, "description": "Contains a random reward"},
    {"name": "Challenge Shield", "rarity": "rare", "type": "item", "value": 1, "description": "Skip one challenge task"},
    {"name": "Legendary Artifact", "rarity": "epic", "type": "item", "value": 1, "description": "Double XP for 1 day"},
    {"name": "Golden Ticket", "rarity": "legendary", "type": "item", "value": 1, "description": "Auto-complete any task"},
]

TASK_MATCH_PROMPT = """You are helping the Reward Agent identify which task the user completed.

User Input: "{user_input}"

Available Tasks:
{task_list}

Select the task that best matches the user's input.
Return a JSON object:
{{
    "task_id": "id of the matched task, or null if no clear match",
    "confidence": 0.0 to 1.0,
    "reasoning": "why you selected this task"
}}
"""

async def reward_node(state: AgentState) -> AgentState:
    profile = state.get("user_profile")
    tasks = state.get("current_tasks", [])
    user_input = state["user_input"]

    if not profile:
        profile = {"level": 1, "total_xp": 0, "current_xp": 0, "xp_to_next_level": 1000, 
                   "streak_days": 0, "tasks_completed": 0, "goals_completed": 0, "challenges_completed": 0}
    
    profile_dict = profile if isinstance(profile, dict) else profile.to_dict() if hasattr(profile, 'to_dict') else {"level": 1}
    
    completed_task = None
    xp_only_mode = False

    # 1. Check if any task is already marked completed in state (unlikely if coming from pending DB list)
    for task in tasks:
        if isinstance(task, dict) and task.get("status") == "completed":
            completed_task = task
            break
    
    # 2. If no task identified, use LLM to match user input to a task
    if not completed_task and tasks:
        task_list_str = "\n".join([f"- ID: {t['id']}, Title: {t['title']}" for t in tasks if isinstance(t, dict)])

        try:
            match_prompt = TASK_MATCH_PROMPT.format(user_input=user_input, task_list=task_list_str)
            match_response = await llm_client.invoke_with_retry(
                [SystemMessage(content=match_prompt)],
                prefer_tools=False,
            )
            parsed = safe_json_loads(match_response.content, {"task_id": None, "confidence": 0.0, "reasoning": ""})
            task_id = parsed.get("task_id")
            if task_id:
                for t in tasks:
                    if t.get("id") == task_id:
                        completed_task = t
                        # Mark as completed in state (will be saved to DB in main.py)
                        t['status'] = 'completed'
                        t['completed_at'] = datetime.now().isoformat()
                        break
        except Exception as e:
            log_event(logger, "agent.reward.task_match_error", level="error", error=str(e), user_id=state.get("user_id"))
            # Fallback logic: if only 1 task exists and it's a short "done" message, assume it's that one
            if len(tasks) == 1 and len(user_input) < 20:
                completed_task = tasks[0]
                completed_task['status'] = 'completed'
            elif tasks:
                # Layer 3: 奖励节点兜底，最小化处理为“仅XP”
                completed_task = tasks[0]
                completed_task['status'] = 'completed'
                completed_task['completed_at'] = datetime.now().isoformat()
                xp_only_mode = True

    if not completed_task:
        # If still no task identified, ask user to be more specific
        msg = "I'm not sure which task you completed. Could you please specify?"
        # Return delta for failure case
        return {
            "final_response": msg,
            "messages": [AIMessage(agent="reward", content=msg)],
            "workflow_status": "reward_failed_no_task_match",
            "next_agent": "RESPONSE"
        }

    # 奖励节点与 HTTP 完成任务接口复用同一 XP 规则，避免评估时出现双标准。
    xp_earned = calculate_xp_reward(
        completed_task.get("difficulty") if completed_task else "medium",
        bool(completed_task and completed_task.get("is_challenge")),
    )
    profile_dict, level_up = apply_xp_to_profile(profile_dict, xp_earned)
    
    drop = None
    if completed_task and not xp_only_mode:
        drop = calculate_drop(completed_task, profile_dict, REWARD_POOL)
    
    if completed_task:
        profile_dict["tasks_completed"] = profile_dict.get("tasks_completed", 0) + 1
        profile_dict["streak_days"] = profile_dict.get("streak_days", 0) + 1
    
    reward_message = f"🎉 任务完成！你获得了 {xp_earned} XP"
    if level_up:
        reward_message += f" 还升级到了 {profile_dict.get('level')} 级！"
    if drop:
        reward_message += f" 还获得了稀有掉落: {drop['name']} ({drop['rarity']})!"
    
    game_event = {
        "event_type": "task_completed",
        "description": reward_message,
        "rewards": [drop] if drop else [],
        "event_data": {"xp_earned": xp_earned, "level_up": level_up}
    }
    
    # Return delta for messages (reduced) and full lists for others (overwritten)
    return {
        "user_profile": profile_dict,
        "rewards_earned": [drop] if drop else [],
        "game_events": state.get("game_events", []) + [game_event],
        "messages": [AIMessage(agent="reward", content=reward_message)],
        "workflow_status": "reward_degraded_xp_only" if xp_only_mode else "reward_processed",
        "next_agent": "RESPONSE",
        "final_response": reward_message
    }
