import asyncio
import json
from datetime import datetime
from flask_apscheduler import APScheduler
from app.database.models import db, ScheduledJob, User, Goal, Task, ChatLog
from app.database.services import save_agent_result
from app.agents.reflector import run_reflector
from app.agents.workflow import run_agent_workflow

scheduler = APScheduler()

def init_scheduler(app):
    scheduler.init_app(app)
    scheduler.start()
    
    # Load existing jobs on startup
    with app.app_context():
        jobs = ScheduledJob.query.filter_by(is_active=True).all()
        for job in jobs:
            add_job_to_scheduler(job.id, job.cron_expression, job.job_type, job.user_id, job.message_content)

def add_job_to_scheduler(job_id, cron_expression, job_type, user_id, message_content=None):
    # cron_expression expected as "minute hour day month day_of_week" or simplified
    # APScheduler standard cron trigger uses specific kwargs.
    # Let's assume the user input is a standard cron string "m h dom mon dow".
    # Or we can just support simple "hour:minute" for daily tasks?
    # For flexibility, let's try to parse a standard 5-part cron string.
    try:
        parts = cron_expression.split()
        if len(parts) == 5:
             minute, hour, day, month, day_of_week = parts
             trigger_args = {
                 'minute': minute,
                 'hour': hour,
                 'day': day,
                 'month': month,
                 'day_of_week': day_of_week
             }
        else:
            # Fallback for simple testing or specific formats
            # If fail, defaulting to every hour
             trigger_args = {'minute': '0'} 
             
        scheduler.add_job(
            id=job_id,
            func=execute_job,
            trigger='cron',
            args=[job_id],
            replace_existing=True,
            **trigger_args
        )
        print(f"Successfully added job {job_id} ({job_type}) for user {user_id} with cron '{cron_expression}'")
    except Exception as e:
        print(f"Error adding job {job_id}: {e}")
        raise e

def remove_job_from_scheduler(job_id):
    try:
        scheduler.remove_job(job_id)
        print(f"Successfully removed job {job_id} from scheduler")
    except Exception as e:
        print(f"Error removing job {job_id}: {e}")

def execute_job(job_id):
    """
    Common entry point for scheduled jobs.
    We need app context to access DB.
    """
    with scheduler.app.app_context():
        job = ScheduledJob.query.get(job_id)
        if not job or not job.is_active:
            return

        print(f"Executing Job: {job.name} ({job.job_type}) for User {job.user_id}")
        
        try:
            if job.job_type == 'reflector':
                asyncio.run(run_reflector(job.user_id))
            elif job.job_type == 'chat':
                if job.message_content:
                    asyncio.run(trigger_chat_workflow(job.user_id, job.message_content))
            
            # Update last run time
            job.last_run_at = datetime.now() 
            db.session.commit()
            
        except Exception as e:
            print(f"Job execution failed: {e}")

async def trigger_chat_workflow(user_id, message):
    # Logic similar to /api/chat
    user = User.query.get(user_id)
    if not user:
        return
        
    current_goal = Goal.query.filter_by(user_id=user_id, status='active').first()
    current_tasks = Task.query.filter_by(user_id=user_id, status='pending').all()

    goal_dict = current_goal.to_dict() if current_goal else None
    tasks_list = [t.to_dict() for t in current_tasks]
    
    # Log as system message or pseudo-user message? 
    # If it's a "morning report", it's like the user said "Give me a morning report".
    user_msg = ChatLog(user_id=user_id, role='user', content=f"[Scheduled Task] {message}")
    db.session.add(user_msg)
    db.session.commit()

    result = await run_agent_workflow(user_id, message, user.to_dict(), goal_dict, tasks_list)
    save_agent_result(user_id, result)
