from typing import List

from pydantic import BaseModel, Field

# 定义一个规范的数据模型 (就像 Java 里的 Entity/DTO)

"""
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
"""

class Goal(BaseModel):
    id: str = Field(description="计划的唯一标识符")
    title: str = Field(description="计划的标题")
    description: str = Field(description="计划的详细描述")
    deadline: str = Field(description="计划的截止日期，格式为YYYY-MM-DD或null")
    xp_reward: int = Field(description="完成计划后获得的经验值奖励")

class Task(BaseModel):
    id: str = Field(description="任务的唯一标识符")
    title: str = Field(description="任务的标题")
    description: str = Field(description="任务的详细描述")
    difficulty: str = Field(description="任务的难度等级，可选值为easy|medium|hard|epic")
    is_challenge: bool = Field(description="是否为挑战任务")
    challenge_type: str = Field(description="挑战类型，可选值为time_challenge|streak_challenge|combo_challenge|hidden_challenge|null")
    due_date: str = Field(description="任务的截止日期，格式为YYYY-MM-DD")
    xp_reward: int = Field(description="完成任务后获得的经验值奖励")

class Tasks(BaseModel):
    tasks: List[Task]

class TaskPlan(BaseModel):
    goal : Goal = Field(description="目标信息")
    tasks : Tasks = Field(description="任务列表")
    reasoning : str = Field(description="对任务分解的解释说明")
