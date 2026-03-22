"""
Reflector Agent - Analyzes chat history to update Core Persona README
"""
import os
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.llm_client import llm_client
from app.database.models import ChatLog, User, db
from app.config import config
from app.agents.state import AgentState

PERSONA_DIR = "app/agents/personas"

REFLECTOR_SYSTEM_PROMPT = """You are the Reflector Agent for the Gamified Life Engine.
Your task is to analyze the user's recent interactions and update their 'Core Persona' file.
This file serves as a long-term memory of the user's personality, goals, preferred working style, skills, and current state.

You will be provided with:
1. The current content of the User Persona (Markdown format).
2. Recent chat history.

Your goal is to:
- Identify new information about the user (skills, interests, habits).
- Update progress on long-term goals.
- Refine the persona description based on tone and preferences.
- summary of recent activities.

Output the COMPLETELY UPDATED Markdown content for the User Persona file.
D0 NOT output explanation, just the markdown content.
If the current persona is empty, create a new one with sections like:
- **Profile**: Name, Level
- **Traits**: Personality keywords
- **Skills**: User skills and proficiency
- **Current Focus**: What they are working on
- **Habits/Preferences**: Communication style, timing etc.
- **History Summary**: Brief log of major events
"""

def get_persona_path(user_id):
    if not os.path.exists(PERSONA_DIR):
        os.makedirs(PERSONA_DIR)
    return os.path.join(PERSONA_DIR, f"USER_{user_id}.md")

def get_persona_content(user_id):
    path = get_persona_path(user_id)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return "No persona file yet."

def save_persona_content(user_id, content):
    path = get_persona_path(user_id)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

async def run_reflector(user_id):
    """
    Main entry point for the Reflector Agent.
    """
    print(f"[{datetime.now()}] Running Reflector for User {user_id}")
    
    # 1. Get recent history (e.g., last 50 messages)
    recent_logs = ChatLog.query.filter_by(user_id=user_id).order_by(ChatLog.created_at.desc()).limit(50).all()
    if not recent_logs:
        return "No recent activity to reflect on."
    
    # Reverse to chronological order
    recent_logs.reverse()
    history_text = "\n".join([f"{log.role}: {log.content}" for log in recent_logs])
    
    # 2. Get current persona
    current_persona = get_persona_content(user_id)
    
    # 3. LLM Call
    messages = [
        SystemMessage(content=REFLECTOR_SYSTEM_PROMPT),
        HumanMessage(content=f"CURRENT PERSONA:\n{current_persona}\n\nRECENT HISTORY:\n{history_text}")
    ]
    
    response = await llm_client.ainvoke(messages)
    new_persona = response.content
    
    # 4. Save
    save_persona_content(user_id, new_persona)
    
    # 5. Update user's specific last_reflection_at
    user = User.query.get(user_id)
    if user:
        user.last_reflection_at = datetime.now()
        db.session.commit()
        
    return "Persona updated successfully."

async def reflector_node(state: AgentState) -> AgentState:
    user_id = state["user_id"]
    # Run reflection logic
    # Note: this adds latency (another LLM call). 
    # In a production system, this might be conditional (e.g. random probability or every N turns).
    await run_reflector(user_id)
    
    return {
        "workflow_status": "reflection_completed"
    }
