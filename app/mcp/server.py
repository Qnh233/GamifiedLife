"""
MCP Server implementation for Gamified Life Engine

This MCP server provides tools for:
1. Reading local calendar data
2. Reading todo list data
3. Reading markdown notes
4. Checking GitHub commits
5. Reading Pomodoro timer logs
"""
from typing import Any
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request
from sqlalchemy import text
from app.database.connection import async_engine, sync_engine

app = Flask(__name__)


class MCPTool:
    def __init__(self, name: str, description: str, input_schema: dict):
        self.name = name
        self.description = description
        self.input_schema = input_schema

    def to_mcp_format(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


class MCPServer:
    def __init__(self):
        self.tools = []
        self._register_tools()

    def _register_tools(self):
        self.tools.append(MCPTool(
            name="web_search",
            description="Search the web for information (Mock)",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "number", "description": "Number of results to return"}
                },
                "required": ["query"]
            }
        ))

        self.tools.append(MCPTool(
            name="sql_query",
            description="Execute a read-only SQL query on the game database",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL SELECT query to execute"}
                },
                "required": ["query"]
            }
        ))

        self.tools.append(MCPTool(
            name="read_local_todos",
            description="Read todo items from a local JSON file",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the todo JSON file"}
                },
                "required": ["file_path"]
            }
        ))

        self.tools.append(MCPTool(
            name="read_markdown_notes",
            description="Read and parse markdown notes from a directory",
            input_schema={
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Path to notes directory"},
                    "max_files": {"type": "number", "description": "Maximum number of files to read"}
                },
                "required": ["directory"]
            }
        ))

        self.tools.append(MCPTool(
            name="check_github_commits",
            description="Check GitHub commit history for a repository",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to local git repository"},
                    "days": {"type": "number", "description": "Number of days to look back"}
                },
                "required": ["repo_path"]
            }
        ))

        self.tools.append(MCPTool(
            name="read_pomodoro_log",
            description="Read Pomodoro timer session logs",
            input_schema={
                "type": "object",
                "properties": {
                    "log_path": {"type": "string", "description": "Path to Pomodoro log file"}
                },
                "required": ["log_path"]
            }
        ))

        self.tools.append(MCPTool(
            name="check_calendar_events",
            description="Check calendar events from a local ICS file",
            input_schema={
                "type": "object",
                "properties": {
                    "ics_path": {"type": "string", "description": "Path to ICS calendar file"},
                    "days_ahead": {"type": "number", "description": "Days to look ahead"}
                },
                "required": ["ics_path"]
            }
        ))
        self.tools.append(MCPTool(
            name="get_user_gaming_status",
            description="Get the gaming status of a user from the database",
            input_schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "ID of the user to query"}
                },
                "required": ["user_id"]
            }
        ))

    def list_tools(self) -> list[dict]:
        return [tool.to_mcp_format() for tool in self.tools]

    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        if tool_name == "web_search":
            return self._web_search(
                arguments.get("query"),
                arguments.get("limit", 5)
            )
        elif tool_name == "sql_query":
            return self._sql_query(arguments.get("query"))
        elif tool_name == "read_local_todos":
            return self._read_local_todos(arguments.get("file_path"))
        elif tool_name == "read_markdown_notes":
            return self._read_markdown_notes(
                arguments.get("directory"),
                arguments.get("max_files", 10)
            )
        elif tool_name == "check_github_commits":
            return self._check_github_commits(
                arguments.get("repo_path"),
                arguments.get("days", 7)
            )
        elif tool_name == "read_pomodoro_log":
            return self._read_pomodoro_log(arguments.get("log_path"))
        elif tool_name == "check_calendar_events":
            return self._check_calendar_events(
                arguments.get("ics_path"),
                arguments.get("days_ahead", 7)
            )
        elif tool_name == "get_user_gaming_status":
            return self.get_user_gaming_status(arguments.get("user_id"))
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _web_search(self, query: str, limit: int) -> dict:
        """Mock web search implementation"""
        try:
            # In a real scenario, this would call Google/Bing API
            # For now, we return mock results based on the query
            results = [
                {
                    "title": f"Result for {query} - 1",
                    "url": f"https://example.com/search?q={query}&p=1",
                    "snippet": f"This is a mock search result for '{query}'. It contains some relevant information about the topic."
                },
                {
                    "title": f"Wikipedia: {query}",
                    "url": f"https://en.wikipedia.org/wiki/{query}",
                    "snippet": f"{query} is a very interesting topic that has been studied extensively..."
                },
                {
                    "title": f"Recent news about {query}",
                    "url": f"https://news.example.com/{query}",
                    "snippet": f"Latest updates and news regarding {query} from around the world."
                }
            ]
            return {"success": True, "results": results[:limit], "count": len(results[:limit])}
        except Exception as e:
            return {"success": False, "error": str(e), "results": []}

    def _sql_query(self, query: str) -> dict:
        """Execute safe SQL query"""
        try:
            if not query.strip().upper().startswith("SELECT"):
                return {"success": False, "error": "Only SELECT queries are allowed for safety.", "data": []}

            with sync_engine.connect() as conn:
                result = conn.execute(text(query))
                keys = result.keys()
                data = [dict(zip(keys, row)) for row in result.fetchall()]

            return {"success": True, "data": data, "count": len(data)}
        except Exception as e:
            return {"success": False, "error": str(e), "data": []}

    def _read_local_todos(self, file_path: str) -> dict:
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": "File not found", "todos": []}

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            todos = data if isinstance(data, list) else data.get("todos", [])
            return {"success": True, "todos": todos}
        except Exception as e:
            return {"success": False, "error": str(e), "todos": []}

    def _read_markdown_notes(self, directory: str, max_files: int) -> dict:
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return {"success": False, "error": "Directory not found", "notes": []}

            notes = []
            for md_file in sorted(dir_path.glob("*.md"))[:max_files]:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    notes.append({
                        "filename": md_file.name,
                        "path": str(md_file),
                        "content": content[:1000]
                    })

            return {"success": True, "notes": notes}
        except Exception as e:
            return {"success": False, "error": str(e), "notes": []}

    def _check_github_commits(self, repo_path: str, days: int) -> dict:
        try:
            import subprocess

            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            result = subprocess.run(
                ["git", "log", f"--since={cutoff}", "--pretty=format:%h|%s|%ai"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {"success": False, "error": "Not a git repository", "commits": []}

            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        commits.append({
                            "hash": parts[0],
                            "message": parts[1],
                            "date": parts[2]
                        })

            return {"success": True, "commits": commits, "count": len(commits)}
        except Exception as e:
            return {"success": False, "error": str(e), "commits": []}

    def _read_pomodoro_log(self, log_path: str) -> dict:
        try:
            if not os.path.exists(log_path):
                return {"success": False, "error": "Log file not found", "sessions": []}

            sessions = []
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        parts = line.strip().split(",")
                        if len(parts) >= 3:
                            sessions.append({
                                "timestamp": parts[0],
                                "duration": parts[1],
                                "task": parts[2] if len(parts) > 2 else "Unknown"
                            })

            return {"success": True, "sessions": sessions, "count": len(sessions)}
        except Exception as e:
            return {"success": False, "error": str(e), "sessions": []}

    def _check_calendar_events(self, ics_path: str, days_ahead: int) -> dict:
        try:
            if not os.path.exists(ics_path):
                return {"success": False, "error": "ICS file not found", "events": []}

            events = []
            cutoff = datetime.now() + timedelta(days=days_ahead)

            with open(ics_path, "r", encoding="utf-8") as f:
                content = f.read()

            current_event = {}
            for line in content.split("\n"):
                if line.startswith("BEGIN:VEVENT"):
                    current_event = {}
                elif line.startswith("END:VEVENT"):
                    if current_event.get("dtstart"):
                        events.append(current_event)
                elif line.startswith("SUMMARY:"):
                    current_event["title"] = line[8:]
                elif line.startswith("DTSTART"):
                    current_event["dtstart"] = line.split(":")[1] if ":" in line else None
                elif line.startswith("DESCRIPTION:"):
                    current_event["description"] = line[12:]

            upcoming = []
            for event in events:
                if event.get("dtstart"):
                    upcoming.append(event)

            return {"success": True, "events": upcoming[:20], "count": len(upcoming)}
        except Exception as e:
            return {"success": False, "error": str(e), "events": []}

    def get_user_gaming_status(self, user_id: str) -> dict:
        """Example of a custom tool that could fetch user gaming status from the database"""
        try:
            with sync_engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM users WHERE id = :user_id"), {"user_id": user_id})
                row = result.fetchone()
                print(row)
                if row:
                    # 修复：获取列名并与行数据 zip 组合成字典
                    keys = result.keys()
                    return {"success": True, "gaming_status": dict(zip(keys, row))}
                else:
                    return {"success": False, "error": "User not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
mcp_server = MCPServer()


@app.route("/", methods=["GET"])
def mcp_root():
    return jsonify({
        "name": "Gamified Life MCP Server",
        "version": "1.0.0",
        "tools": mcp_server.list_tools()
    })


@app.route("/tools", methods=["GET"])
def list_tools():
    return jsonify({"tools": mcp_server.list_tools()})


@app.route("/tools/<tool_name>", methods=["POST"])
def call_tool(tool_name):
    arguments = request.get_json() or {}
    try:
        result = mcp_server.call_tool(tool_name, arguments)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
