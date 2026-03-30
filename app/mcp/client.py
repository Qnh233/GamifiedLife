"""
MCP Client - Connects to MCP Server for external data access
"""
import httpx
from typing import Any, Optional
from app.config import config
# app/agents/llm_client.py

class MCPClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or f"http://{config.MCP_SERVER_HOST}:{config.MCP_SERVER_PORT}"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def list_tools(self) -> list[dict]:
        response = await self.client.get(f"{self.base_url}/tools")
        response.raise_for_status()
        return response.json().get("tools", [])
    
    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        response = await self.client.post(
            f"{self.base_url}/tools/{tool_name}",
            json=kwargs
        )
        response.raise_for_status()
        return response.json()
    
    async def search_web(self, query: str, limit: int = 5) -> dict:
        return await self.call_tool("web_search", query=query, limit=limit)

    async def query_db(self, query: str) -> dict:
        return await self.call_tool("sql_query", query=query)

    async def read_todos(self, file_path: str) -> dict:
        return await self.call_tool("read_local_todos", file_path=file_path)
    
    async def read_notes(self, directory: str, max_files: int = 10) -> dict:
        return await self.call_tool("read_markdown_notes", directory=directory, max_files=max_files)
    
    async def check_github(self, repo_path: str, days: int = 7) -> dict:
        return await self.call_tool("check_github_commits", repo_path=repo_path, days=days)
    
    async def read_pomodoro(self, log_path: str) -> dict:
        return await self.call_tool("read_pomodoro_log", log_path=log_path)
    
    async def check_calendar(self, ics_path: str, days_ahead: int = 7) -> dict:
        return await self.call_tool("check_calendar_events", ics_path=ics_path, days_ahead=days_ahead)
    
    async def close(self):
        await self.client.aclose()

    async def get_user_gaming_status(self, user_id: str) -> dict:
        return await self.call_tool("get_user_gaming_status", user_id=user_id)


mcp_client = MCPClient()
