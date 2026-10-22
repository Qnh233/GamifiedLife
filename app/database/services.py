import uuid
from datetime import datetime
import time
from app.database.models import db, User, Goal, Task, UserAchievement, UserReward, GameEvent, ChatLog
from app.config import config

def _save_agent_result_once(user_id, result):
    user = db.session.get(User, user_id)
    if not user:
        return True

    if result.get('final_response'):
        ai_msg = ChatLog(id=str(uuid.uuid4()),user_id=user_id, role='assistant', content=result['final_response'])
        db.session.add(ai_msg)

    if result.get('current_goal'):
        goal_data = result['current_goal']
        existing_goal = db.session.get(Goal, goal_data['id'])
        if not existing_goal:
            deadline = None
            if goal_data.get('deadline'):
                try:
                    deadline = datetime.fromisoformat(goal_data['deadline'])
                except (ValueError, TypeError):
                    pass

            goal = Goal(
                id=goal_data['id'],
                user_id=user_id,
                title=goal_data['title'],
                description=goal_data.get('description'),
                deadline=deadline,
                xp_reward=goal_data.get('xp_reward', 100),
                status=goal_data.get('status', 'active')
            )
            db.session.add(goal)
        else:
            if goal_data.get('status'):
                 existing_goal.status = goal_data['status']
            if goal_data.get('completed_at'):
                 try:
                     existing_goal.completed_at = datetime.fromisoformat(goal_data['completed_at'])
                 except: 
                     pass
    
    if result.get('current_tasks'):
        for task_data in result['current_tasks']:
            existing_task = db.session.get(Task, task_data['id'])
            if not existing_task:
                due_date = None
                if task_data.get('due_date'):
                    try:
                        due_date = datetime.fromisoformat(task_data['due_date'])
                    except: 
                        pass
                
                completed_at = None
                if task_data.get('completed_at'):
                    try:
                         completed_at = datetime.fromisoformat(task_data['completed_at'])
                    except:
                         pass

                task = Task(
                    id=task_data['id'],
                    user_id=user_id,
                    goal_id=result.get('current_goal', {}).get('id'), # associate with current goal if new
                    title=task_data['title'],
                    description=task_data.get('description'),
                    difficulty=task_data.get('difficulty', 'medium'),
                    xp_reward=task_data.get('xp_reward', 100),
                    is_challenge=task_data.get('is_challenge', False),
                    challenge_type=task_data.get('challenge_type'),
                    due_date=due_date,
                    status=task_data.get('status', 'pending'),
                    completed_at=completed_at
                )
                db.session.add(task)
            else:
                if task_data.get('status') and task_data['status'] != existing_task.status:
                    existing_task.status = task_data['status']
                
                if task_data.get('goal_id'):
                    existing_task.goal_id = task_data['goal_id']

                if task_data.get('completed_at'):
                    try:
                        existing_task.completed_at = datetime.fromisoformat(task_data['completed_at'])
                    except (ValueError, TypeError):
                        pass

    if result.get('user_profile'):
        user_data = result['user_profile']
        if 'level' in user_data: user.level = user_data.get('level', user.level)
        if 'total_xp' in user_data: user.total_xp = user_data.get('total_xp', user.total_xp)
        if 'current_xp' in user_data: user.current_xp = user_data.get('current_xp', user.current_xp)
        if 'xp_to_next_level' in user_data: user.xp_to_next_level = user_data.get('xp_to_next_level', user.xp_to_next_level)
        if 'streak_days' in user_data: user.streak_days = user_data.get('streak_days', user.streak_days)
        if 'tasks_completed' in user_data: user.tasks_completed = user_data.get('tasks_completed', user.tasks_completed)
        if 'goals_completed' in user_data: user.goals_completed = user_data.get('goals_completed', user.goals_completed)
        if 'challenges_completed' in user_data: user.challenges_completed = user_data.get('challenges_completed', user.challenges_completed)
    
    if result.get('rewards_earned'):
        for reward_data in result['rewards_earned']:
            if reward_data:
                user_reward = UserReward(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    reward_id=reward_data.get('id', 'xp_boost_common')
                )
                db.session.add(user_reward)
    
    if result.get('game_events'):
        for event_data in result['game_events']:
            event = GameEvent(
                id=str(uuid.uuid4()),
                user_id=user_id,
                event_type=event_data.get('event_type', 'task_completed'),
                description=event_data.get('description', ''),
                event_data=event_data.get('event_data', {})
            )
            db.session.add(event)
        
        for event in result['game_events']:
            if event.get('achievements_unlocked'):
                for ach in event['achievements_unlocked']:
                    user_ach = UserAchievement.query.filter_by(
                        user_id=user_id,
                        achievement_id=ach.get('id')
                    ).first()
                    if user_ach and not user_ach.unlocked:
                        user_ach.unlocked = True
                        user_ach.unlocked_at = datetime.now()
    
    db.session.commit()
    return True

def save_agent_result(user_id, result):
    """
    Persists the result state from the agent workflow into the database.
    Adds rollback + retry for transient DB failures.
    """
    last_error = None
    max_retries = max(1, config.DB_MAX_RETRIES)
    for attempt in range(max_retries):
        try:
            return _save_agent_result_once(user_id, result)
        except Exception as e:
            last_error = e
            db.session.rollback()
            if attempt == max_retries - 1:
                raise
            delay = config.DB_RETRY_BASE_DELAY_SEC * (2 ** attempt)
            time.sleep(delay)
    raise RuntimeError(f"save_agent_result failed after retries: {last_error}")

