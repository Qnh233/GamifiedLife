"""
Database models for Gamified Life Engine (MySQL)
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()
Base = db.Model
class ChatLog(Base):
    __tablename__ = 'chat_logs'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    agent = db.Column(db.String(50))  # 记录是哪个agent生成的消息（如reflector、planner等）
    created_at = db.Column(db.DateTime, default=datetime.now)

class User(Base):
    """用户信息表：存储等级、经验值、连续登入天数等核心游戏属性"""

    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    level = db.Column(db.Integer, default=1) # 当前等级
    total_xp = db.Column(db.Integer, default=0) # 总经验
    current_xp = db.Column(db.Integer, default=0) # 当前经验
    xp_to_next_level = db.Column(db.Integer, default=1000) # 升级所需经验
    streak_days = db.Column(db.Integer, default=0) # 连续登入天数
    tasks_completed = db.Column(db.Integer, default=0) # 完成任务次数
    goals_completed = db.Column(db.Integer, default=0) # 完成目标次数
    challenges_completed = db.Column(db.Integer, default=0) # 完成挑战次数
    last_reflection_at = db.Column(db.DateTime, nullable=True) # 上次总结画像时间
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 定义关联关系：方便通过 user.tasks 直接获取该用户的所有任务
    # cascade='all, delete-orphan' 表示删除用户时，关联的任务、成就等也会被自动删除
    chat_logs = db.relationship('ChatLog', backref='user', lazy=True, cascade='all, delete-orphan')  # 关联聊天记录
    goals = db.relationship('Goal', backref='user', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')
    achievements = db.relationship('UserAchievement', backref='user', lazy=True, cascade='all, delete-orphan')
    rewards = db.relationship('UserReward', backref='user', lazy=True, cascade='all, delete-orphan')
    game_events = db.relationship('GameEvent', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'level': self.level,
            'total_xp': self.total_xp,
            'current_xp': self.current_xp,
            'xp_to_next_level': self.xp_to_next_level,
            'streak_days': self.streak_days,
            'tasks_completed': self.tasks_completed,
            'goals_completed': self.goals_completed,
            'challenges_completed': self.challenges_completed,
            'is_active': self.is_active,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Goal(Base):
    """目标表：用户设置的任务目标，如完成100个任务、达成特定成就等"""
    __tablename__ = 'goals'
    
    id = db.Column(db.String(36), primary_key=True)  # 目标ID
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)  # 关联用户ID
    title = db.Column(db.String(200), nullable=False)  # 目标标题
    description = db.Column(db.Text)  # 目标描述
    deadline = db.Column(db.DateTime)  # 目标完成时间
    status = db.Column(db.String(20), default='active')  # 目标状态（如active、completed）
    xp_reward = db.Column(db.Integer, default=100)  # 完成目标后奖励的经验值
    created_at = db.Column(db.DateTime, default=datetime.now) # 目标创建时间
    completed_at = db.Column(db.DateTime)  # 目标完成时间
    
    tasks = db.relationship('Task', backref='goal', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'status': self.status,
            'xp_reward': self.xp_reward,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class Task(Base):
    __tablename__ = 'tasks'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    goal_id = db.Column(db.String(36), db.ForeignKey('goals.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    difficulty = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='pending')
    xp_reward = db.Column(db.Integer, default=100)
    is_challenge = db.Column(db.Boolean, default=False)
    challenge_type = db.Column(db.String(50))
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'goal_id': self.goal_id,
            'title': self.title,
            'description': self.description,
            'difficulty': self.difficulty,
            'status': self.status,
            'xp_reward': self.xp_reward,
            'is_challenge': self.is_challenge,
            'challenge_type': self.challenge_type,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class ScheduledJob(Base):
    """定时任务表：存储用户的定时任务配置"""
    __tablename__ = 'scheduled_jobs'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # 任务显示名称
    job_type = db.Column(db.String(50), nullable=False) # 'reflector' or 'chat'
    cron_expression = db.Column(db.String(100), nullable=False) # e.g. "0 8 * * *"
    message_content = db.Column(db.Text, nullable=True) # For chat jobs
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_run_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'job_type': self.job_type,
            'cron_expression': self.cron_expression,
            'message_content': self.message_content,
            'is_active': self.is_active,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None
        }


class Achievement(Base):
    __tablename__ = 'achievements'
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    target = db.Column(db.Integer, default=1)
    
    user_achievements = db.relationship('UserAchievement', backref='achievement', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'target': self.target
        }


class UserAchievement(Base):
    __tablename__ = 'user_achievements'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.String(50), db.ForeignKey('achievements.id'), nullable=False)
    unlocked = db.Column(db.Boolean, default=False)
    progress = db.Column(db.Integer, default=0)
    unlocked_at = db.Column(db.DateTime)
    
    def to_dict(self):
        achievement = Achievement.query.get(self.achievement_id)
        return {
            'id': self.id,
            'achievement_id': self.achievement_id,
            'name': achievement.name if achievement else '',
            'description': achievement.description if achievement else '',
            'icon': achievement.icon if achievement else '',
            'unlocked': self.unlocked,
            'progress': self.progress,
            'target': achievement.target if achievement else 1,
            'unlocked_at': self.unlocked_at.isoformat() if self.unlocked_at else None
        }


class Reward(Base):
    __tablename__ = 'rewards'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    reward_type = db.Column(db.String(20))
    value = db.Column(db.Integer)
    rarity = db.Column(db.String(20))
    icon = db.Column(db.String(50))
    
    user_rewards = db.relationship('UserReward', backref='reward', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'reward_type': self.reward_type,
            'value': self.value,
            'rarity': self.rarity,
            'icon': self.icon
        }


class UserReward(Base):
    __tablename__ = 'user_rewards'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    reward_id = db.Column(db.String(36), db.ForeignKey('rewards.id'), nullable=False)
    obtained_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        reward = Reward.query.get(self.reward_id)
        return {
            'id': self.id,
            'reward_id': self.reward_id,
            'name': reward.name if reward else '',
            'description': reward.description if reward else '',
            'reward_type': reward.reward_type if reward else '',
            'value': reward.value if reward else 0,
            'rarity': reward.rarity if reward else '',
            'obtained_at': self.obtained_at.isoformat() if self.obtained_at else None
        }


class GameEvent(Base):
    __tablename__ = 'game_events'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    event_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'event_type': self.event_type,
            'description': self.description,
            'event_data': self.event_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


DEFAULT_ACHIEVEMENTS = [
    {'id': 'first_blood', 'name': 'First Blood', 'description': 'Complete your first task', 'icon': '⚔️', 'target': 1},
    {'id': 'on_fire', 'name': 'On Fire', 'description': 'Achieve a 3-day streak', 'icon': '🔥', 'target': 3},
    {'id': 'unstoppable', 'name': 'Unstoppable', 'description': 'Achieve a 7-day streak', 'icon': '💎', 'target': 7},
    {'id': 'master_planner', 'name': 'Master Planner', 'description': 'Complete 10 tasks', 'icon': '📋', 'target': 10},
    {'id': 'goal_crusher', 'name': 'Goal Crusher', 'description': 'Complete 5 goals', 'icon': '🎯', 'target': 5},
    {'id': 'challenge_seeker', 'name': 'Challenge Seeker', 'description': 'Complete 10 challenges', 'icon': '🏆', 'target': 10},
    {'id': 'epic_hero', 'name': 'Epic Hero', 'description': 'Complete an epic task', 'icon': '👑', 'target': 1},
    {'id': 'level_10', 'name': 'Rising Star', 'description': 'Reach level 10', 'icon': '⭐', 'target': 10},
    {'id': 'level_50', 'name': 'Veteran', 'description': 'Reach level 50', 'icon': '🌟', 'target': 50},
    {'id': 'streak_master', 'name': 'Streak Master', 'description': 'Achieve a 30-day streak', 'icon': '⚡', 'target': 30},
]

DEFAULT_REWARDS = [
    {'id': 'xp_boost_common', 'name': 'XP Boost', 'description': 'Increases XP for your next task', 'reward_type': 'xp', 'value': 75, 'rarity': 'common', 'icon': '✨'},
    {'id': 'health_potion', 'name': 'Health Potion', 'description': 'Recover from a failed task', 'reward_type': 'item', 'value': 1, 'rarity': 'common', 'icon': '🧪'},
    {'id': 'mystery_box', 'name': 'Mystery Box', 'description': 'Contains a random reward', 'reward_type': 'item', 'value': 1, 'rarity': 'rare', 'icon': '📦'},
    {'id': 'challenge_shield', 'name': 'Challenge Shield', 'description': 'Skip one challenge task', 'reward_type': 'item', 'value': 1, 'rarity': 'rare', 'icon': '🛡️'},
    {'id': 'legendary_artifact', 'name': 'Legendary Artifact', 'description': 'Double XP for 1 day', 'reward_type': 'item', 'value': 1, 'rarity': 'epic', 'icon': '💍'},
    {'id': 'golden_ticket', 'name': 'Golden Ticket', 'description': 'Auto-complete any task', 'reward_type': 'item', 'value': 1, 'rarity': 'legendary', 'icon': '🎫'},
]


def init_default_data():
    for ach_data in DEFAULT_ACHIEVEMENTS:
        if not Achievement.query.get(ach_data['id']):
            achievement = Achievement(**ach_data)
            db.session.add(achievement)
    
    for reward_data in DEFAULT_REWARDS:
        if not Reward.query.get(reward_data['id']):
            reward = Reward(**reward_data)
            db.session.add(reward)
    
    db.session.commit()


