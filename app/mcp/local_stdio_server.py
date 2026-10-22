"""
本地 FastMCP 服务（stdio 模式）。

用于把本地工具标准化暴露为 MCP 服务，供 MultiServerMCPClient 通过 stdio 连接。
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from langchain_community.tools import DuckDuckGoSearchRun
from mcp.server.fastmcp import FastMCP
from sqlalchemy import text

from app.database.connection import sync_engine
from app.utils.logging_utils import get_logger, log_event


# 核心服务对象：使用 fastmcp 标准实现工具注册与协议交互。
mcp = FastMCP("gamified-life-local-tools")
logger = get_logger(__name__)


@mcp.tool()
def get_current_date() -> str:
    """获取当前日期，格式 YYYY-MM-DD。"""
    # 关键工具调用记录：便于排查工具是否被成功发现/调用。
    log_event(logger, "mcp.local.get_current_date")
    return datetime.now().strftime("%Y-%m-%d")


@mcp.tool()
def read_local_todos(file_path: str) -> dict:
    """读取本地 JSON 待办文件。"""
    if not os.path.exists(file_path):
        return {"success": False, "error": "File not found", "todos": []}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        todos = data if isinstance(data, list) else data.get("todos", [])
        return {"success": True, "todos": todos}
    except Exception as e:
        return {"success": False, "error": str(e), "todos": []}


@mcp.tool()
def read_markdown_notes(directory: str, max_files: int = 10) -> dict:
    """读取目录下的 Markdown 笔记（最多 max_files 个）。"""
    dir_path = Path(directory)
    if not dir_path.exists():
        return {"success": False, "error": "Directory not found", "notes": []}

    try:
        notes = []
        for md_file in sorted(dir_path.glob("*.md"))[:max_files]:
            with open(md_file, "r", encoding="utf-8") as f:
                notes.append(
                    {
                        "filename": md_file.name,
                        "path": str(md_file),
                        "content": f.read()[:1000],
                    }
                )
        return {"success": True, "notes": notes}
    except Exception as e:
        return {"success": False, "error": str(e), "notes": []}


@mcp.tool()
def check_github_commits(repo_path: str, days: int = 7) -> dict:
    """读取本地仓库近 N 天提交历史。"""
    if not repo_path:
        return {"success": False, "error": "Missing repo_path", "commits": []}

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "log", f"--since={cutoff}", "--pretty=format:%h|%s|%ai"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {"success": False, "error": "Not a git repository", "commits": []}

        commits = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                if len(parts) >= 3:
                    commits.append({"hash": parts[0], "message": parts[1], "date": parts[2]})
        return {"success": True, "commits": commits, "count": len(commits)}
    except Exception as e:
        return {"success": False, "error": str(e), "commits": []}


@mcp.tool()
def get_user_gaming_status(user_id: str) -> dict:
    """从数据库读取用户当前游戏化状态。"""
    log_event(logger, "mcp.local.get_user_gaming_status", user_id=user_id)
    if not user_id:
        return {"success": False, "error": "Missing user_id"}

    try:
        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM users WHERE id = :user_id"), {"user_id": user_id})
            row = result.fetchone()
            if not row:
                return {"success": False, "error": "User not found"}
            keys = result.keys()
            return {"success": True, "gaming_status": dict(zip(keys, row))}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def web_search(query: str) -> str:
    """
    使用在线搜索互联网资料，返回搜索结果。
    在需要实时信息或网络资料时调用。
    """
    log_event(logger, "mcp.local.web_search", query=query)
    search = DuckDuckGoSearchRun()
    start_time = time.time()
    result = await search.arun(query)
    duration = time.time() - start_time
    # 核心功能耗时记录：方便定位外部检索延迟问题。
    log_event(logger, "mcp.local.web_search_success", query=query, duration=duration)
    return result


if __name__ == "__main__":
    # 使用 stdio 作为 MCP 传输层，便于被本地 client 进程托管。
    mcp.run(transport="stdio")
