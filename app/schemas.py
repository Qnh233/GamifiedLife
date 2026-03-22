"""
Pydantic schemas for Gamified Life Engine
"""
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EPIC = "epic"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class UserInput:
    def __init__(self, user_id: str, message: str):
        self.user_id = user_id
        self.message = message


class Goal:
    def __init__(self, id: str, title: str, description: Optional[str] = None,
                 deadline: Optional[datetime] = None, status: str = "active",
                 xp_reward: int = 100):
        self.id = id
        self.title = title
        self.description = description
        self.deadline = deadline
        self.status = status
        self.xp_reward = xp_reward
        self.created_at = datetime.now()


class Task:
    def __init__(self, id: str, goal_id: str, title: str,
                 description: Optional[str] = None, difficulty: str = "medium",
                 status: str = "pending", xp_reward: int = 100,
                 is_challenge: bool = False, challenge_type: Optional[str] = None,
                 due_date: Optional[datetime] = None):
        self.id = id
        self.goal_id = goal_id
        self.title = title
        self.description = description
        self.difficulty = difficulty
        self.status = status
        self.xp_reward = xp_reward
        self.is_challenge = is_challenge
        self.challenge_type = challenge_type
        self.due_date = due_date
        self.created_at = datetime.now()
        self.completed_at = None


class Reward:
    def __init__(self, id: str, name: str, description: str,
                 reward_type: str, value: int, rarity: str, icon: Optional[str] = None):
        self.id = id
        self.name = name
        self.description = description
        self.reward_type = reward_type
        self.value = value
        self.rarity = rarity
        self.icon = icon
        self.obtained_at = None


class Achievement:
    def __init__(self, id: str, name: str, description: str, icon: str,
                 unlocked: bool = False, progress: int = 0, target: int = 1):
        self.id = id
        self.name = name
        self.description = description
        self.icon = icon
        self.unlocked = unlocked
        self.progress = progress
        self.target = target
        self.unlocked_at = None


class UserProfile:
    def __init__(self, user_id: str, username: str, level: int = 1,
                 total_xp: int = 0, current_xp: int = 0,
                 xp_to_next_level: int = 1000, streak_days: int = 0,
                 tasks_completed: int = 0, goals_completed: int = 0,
                 challenges_completed: int = 0):
        self.user_id = user_id
        self.username = username
        self.level = level
        self.total_xp = total_xp
        self.current_xp = current_xp
        self.xp_to_next_level = xp_to_next_level
        self.streak_days = streak_days
        self.tasks_completed = tasks_completed
        self.goals_completed = goals_completed
        self.challenges_completed = challenges_completed
        self.achievements = []
        self.inventory = []
        self.created_at = datetime.now()


class AgentResponse:
    def __init__(self, agent_name: str, success: bool, message: str,
                 data: Optional[dict] = None, next_action: Optional[str] = None):
        self.agent_name = agent_name
        self.success = success
        self.message = message
        self.data = data
        self.next_action = next_action


class GameEvent:
    def __init__(self, event_type: str, description: str,
                 rewards: list = None, metadata: dict = None):
        self.event_type = event_type
        self.description = description
        self.rewards = rewards or []
        self.metadata = metadata or {}
