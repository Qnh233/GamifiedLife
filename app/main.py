"""
Flask application for Gamified Life Engine
"""
import time
import uuid
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import config
from app.database.models import db, User, Goal, Task, UserAchievement, UserReward, GameEvent, Achievement, Reward, ChatLog, init_default_data, ScheduledJob
from app.agents.workflow import run_agent_workflow
from app.scheduler_service import init_scheduler, add_job_to_scheduler, remove_job_from_scheduler
from app.database.services import save_agent_result
from app.utils.logging_utils import get_logger, setup_logging, log_event
import time
def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    CORS(app, supports_credentials=True)
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()  # 1. 如果表不存在，创建表
        init_default_data() # 2. 确保基础配置数据（如成就列表）已填入
        init_scheduler(app) # 3. Initialize scheduler

    register_routes(app)
    setup_logging()
    return app


def register_routes(app):
    logger = get_logger(__name__)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/status')
    def status():
        return jsonify({
            'name': config.APP_NAME,
            'version': '1.0.0',
            'status': 'running',
            'agents': ['supervisor', 'planner', 'reward', 'query', 'chat']
        })
    
    @app.route('/health')
    def health_check():
        return jsonify({'status': 'healthy'})
    
    @app.route('/api/chat', methods=['POST'])
    def chat():
        start_ts = time.perf_counter()
        data = request.get_json()
        user_id = data.get('user_id')
        message = data.get('message')
        log_event(
            logger,
            "chat.request.received",
            user_id=user_id,
            input_preview=message,
            preview=True,
        )
        
        if not user_id or not message:
            return jsonify({'error': 'user_id and message are required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            user = User(
                id=user_id,
                username=f"User_{user_id[:8]}",
                xp_to_next_level=1000
            )
            db.session.add(user)
            db.session.commit()
            
            for ach in Achievement.query.all():
                user_ach = UserAchievement(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    achievement_id=ach.id,
                    progress=0,
                    unlocked=False
                )
                db.session.add(user_ach)
            db.session.commit()
        
        # 获取当前上下文
        current_goal = Goal.query.filter_by(user_id=user_id, status='active').first()
        current_tasks = Task.query.filter_by(user_id=user_id, status='pending').all()

        goal_dict = current_goal.to_dict() if current_goal else None
        tasks_list = [t.to_dict() for t in current_tasks]

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Save User Message
        user_msg = ChatLog(id=str(uuid.uuid4()), user_id=user_id, role='user', content=message)
        db.session.add(user_msg)
        db.session.commit()
        wf_start = time.perf_counter()
        try:
            result = loop.run_until_complete(
                run_agent_workflow(user_id, message, user.to_dict(), goal_dict, tasks_list)
            )
        finally:
            loop.close()
        log_event(
            logger,
            "chat.workflow.completed",
            user_id=user_id,
            duration_ms=int((time.perf_counter() - wf_start) * 1000),
            next_agent=result.get("next_agent"),
            final_response_preview=result.get("final_response"),
            preview=True,
        )
        db_start = time.perf_counter()
        # Save results to DB
        save_agent_result(user_id, result)
        log_event(
            logger,
            "chat.persistence.completed",
            user_id=user_id,
            duration_ms=int((time.perf_counter() - db_start) * 1000),
        )

        log_event(
            logger,
            "chat.request.completed",
            user_id=user_id,
            total_duration_ms=int((time.perf_counter() - start_ts) * 1000),
        )

        return jsonify({
            'success': True,
            'agent': result.get('next_agent', 'unknown'),
            'message': result.get('final_response', ''),
            'data': {
                'goal': result.get('current_goal'),
                'tasks': result.get('current_tasks'),
                'profile': user.to_dict(),
                'game_events': [e for e in result.get('game_events', [])]
            }
        })
    
    @app.route('/api/tasks/complete/<task_id>', methods=['POST'])
    def complete_task(task_id):
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        task = Task.query.get(task_id)
        if not task or task.user_id != user_id:
            return jsonify({'error': 'Task not found'}), 404
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        task.status = 'completed'
        task.completed_at = datetime.now()
        
        difficulty_mult = config.DIFFICULTY_MULTIPLIER.get(task.difficulty, 1.0)
        xp_earned = int(config.BASE_XP_PER_TASK * difficulty_mult)
        
        if task.is_challenge:
            xp_earned = int(xp_earned * 1.5)
            user.challenges_completed += 1
        
        old_level = user.level
        user.current_xp += xp_earned
        user.total_xp += xp_earned
        user.tasks_completed += 1
        user.streak_days += 1
        
        while user.current_xp >= user.xp_to_next_level:
            user.current_xp -= user.xp_to_next_level
            user.level += 1
            user.xp_to_next_level = int(user.xp_to_next_level * 1.2)
        
        level_up = user.level > old_level
        
        import random
        base_drop_rate = config.DROP_RATE_BASE
        if task.difficulty == 'hard':
            base_drop_rate += 0.05
        elif task.difficulty == 'epic':
            base_drop_rate += 0.15
        if task.is_challenge:
            base_drop_rate += 0.10
        base_drop_rate += user.streak_days * 0.02
        
        drop = None
        if random.random() < base_drop_rate:
            roll = random.random()
            if roll < 0.60:
                rarity = 'common'
            elif roll < 0.85:
                rarity = 'rare'
            elif roll < 0.97:
                rarity = 'epic'
            else:
                rarity = 'legendary'
            
            reward_pool = Reward.query.filter_by(rarity=rarity).all()
            if reward_pool:
                drop_reward = random.choice(reward_pool)
                user_reward = UserReward(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    reward_id=drop_reward.id
                )
                db.session.add(user_reward)
                drop = drop_reward.to_dict()
        
        event_desc = f"Completed task '{task.title}'! +{xp_earned} XP"
        if level_up:
            event_desc += f" Level up to {user.level}!"
        if drop:
            event_desc += f" Got {drop['name']}!"
        
        event = GameEvent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type='task_completed',
            description=event_desc,
            event_data={'xp_earned': xp_earned, 'level_up': level_up, 'drop': drop}
        )
        db.session.add(event)
        
        check_achievements(user, task)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': event_desc,
            'xp_earned': xp_earned,
            'level_up': level_up,
            'new_level': user.level,
            'drop': drop,
            'profile': user.to_dict()
        })
    
    @app.route('/api/profile/<user_id>', methods=['GET'])
    def get_profile(user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'user_id': user_id,
                'exists': False,
                'message': 'Profile not found'
            }), 404
        
        achievements = UserAchievement.query.filter_by(user_id=user_id).all()
        rewards = UserReward.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'exists': True,
            'profile': user.to_dict(),
            'achievements': [a.to_dict() for a in achievements],
            'rewards': [r.to_dict() for r in rewards]
        })
    
    @app.route('/api/goals/<user_id>', methods=['GET'])
    def get_goals(user_id):
        goals = Goal.query.filter_by(user_id=user_id).all()
        return jsonify({
            'goals': [g.to_dict() for g in goals]
        })
    
    @app.route('/api/tasks/<user_id>', methods=['GET'])
    def get_tasks(user_id):
        status = request.args.get('status')
        query = Task.query.filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        tasks = query.all()
        return jsonify({
            'tasks': [t.to_dict() for t in tasks]
        })
    
    @app.route('/api/achievements', methods=['GET'])
    def get_all_achievements():
        achievements = Achievement.query.all()
        return jsonify({
            'achievements': [a.to_dict() for a in achievements]
        })
    
    @app.route('/api/rewards', methods=['GET'])
    def get_all_rewards():
        rewards = Reward.query.all()
        return jsonify({
            'rewards': [r.to_dict() for r in rewards]
        })
    
    @app.route('/api/events/<user_id>', methods=['GET'])
    def get_events(user_id):
        limit = request.args.get('limit', 20, type=int)
        events = GameEvent.query.filter_by(user_id=user_id).order_by(
            GameEvent.created_at.desc()
        ).limit(limit).all()
        return jsonify({
            'events': [e.to_dict() for e in events]
        })

    @app.route('/api/schedules/<user_id>', methods=['GET'])
    def get_schedules(user_id):
        jobs = ScheduledJob.query.filter_by(user_id=user_id).all()
        return jsonify({
            'schedules': [j.to_dict() for j in jobs]
        })

    @app.route('/api/schedules', methods=['POST'])
    def create_schedule():
        data = request.get_json()
        user_id = data.get('user_id')
        cron_expression = data.get('cron_expression') # "m h d M w"
        job_type = data.get('job_type') # 'reflector' or 'chat'
        name = data.get('name')
        
        if not user_id or not cron_expression or not job_type or not name:
             return jsonify({'error': 'Missing required fields'}), 400
             
        job_id = str(uuid.uuid4())
        job = ScheduledJob(
            id=job_id,
            user_id=user_id,
            name=name,
            job_type=job_type,
            cron_expression=cron_expression,
            message_content=data.get('message_content'),
            is_active=True
        )
        db.session.add(job)
        db.session.commit()
        
        try:
            add_job_to_scheduler(job_id, cron_expression, job_type, user_id, data.get('message_content'))
        except Exception as e:
            db.session.delete(job)
            db.session.commit()
            return jsonify({'error': f'Failed to schedule: {str(e)}'}), 500
        
        return jsonify({'success': True, 'job': job.to_dict()})

    @app.route('/api/schedules/<job_id>', methods=['DELETE'])
    def delete_schedule(job_id):
        job = ScheduledJob.query.get(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
            
        db.session.delete(job)
        db.session.commit()
        
        remove_job_from_scheduler(job_id)
        
        return jsonify({'success': True})


def check_achievements(user, task=None):
    achievements_to_check = [
        ('first_blood', user.tasks_completed >= 1),
        ('on_fire', user.streak_days >= 3),
        ('unstoppable', user.streak_days >= 7),
        ('master_planner', user.tasks_completed >= 10),
        ('goal_crusher', user.goals_completed >= 5),
        ('challenge_seeker', user.challenges_completed >= 10),
        ('level_10', user.level >= 10),
        ('level_50', user.level >= 50),
        ('streak_master', user.streak_days >= 30),
    ]
    
    if task and task.difficulty == 'epic':
        achievements_to_check.append(('epic_hero', True))
    
    for ach_id, condition in achievements_to_check:
        if condition:
            user_ach = UserAchievement.query.filter_by(
                user_id=user.id,
                achievement_id=ach_id
            ).first()
            if user_ach and not user_ach.unlocked:
                user_ach.unlocked = True
                user_ach.unlocked_at = datetime.now()


app = create_app()


if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
