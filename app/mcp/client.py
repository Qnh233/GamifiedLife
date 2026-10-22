"""
MCP 客户端管理器。

统一管理：
1) 本地 FastMCP stdio 服务
2) 外部 MCP 服务（streamable_http / sse）
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.config import config
from langchain_mcp_adapters.client import MultiServerMCPClient


class MCPClientManager:
    """统一管理多 MCP 服务，并提供工具发现与调用能力。"""

    def __init__(self) -> None:
        self._client: MultiServerMCPClient | None = None
        self._tools_by_name: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def _build_servers(self) -> dict[str, dict[str, Any]]:
        """组装本地 + 外部 MCP 服务定义。"""
        project_root = Path(__file__).resolve().parents[2]
        bootstrap_code = (
            "import sys; "
            f"sys.path.insert(0, r'{project_root}'); "
            "from app.mcp.local_stdio_server import mcp; "
            "mcp.run(transport='stdio')"
        )
        servers: dict[str, dict[str, Any]] = {
            "local_stdio_tools": {
                "transport": "stdio",
                "command": "python",
                # 显式注入项目根路径，兼容 Windows 子进程下的 app 包导入。
                "args": ["-c", bootstrap_code],
            }
        }

        # 外部 MCP 服务通过 JSON 注入，支持多个服务统一管理。
        # 示例：
        # {"remote_docs":{"transport":"streamable_http","url":"http://localhost:9000/mcp"}}
        if config.MCP_EXTERNAL_SERVERS_JSON:
            external_servers = json.loads(config.MCP_EXTERNAL_SERVERS_JSON)
            if not isinstance(external_servers, dict):
                raise ValueError("MCP_EXTERNAL_SERVERS_JSON 必须是 JSON 对象")
            servers.update(external_servers)

        return servers

    async def _ensure_client(self) -> MultiServerMCPClient:
        async with self._lock:
            if self._client is None:
                self._client = MultiServerMCPClient(self._build_servers())
            return self._client

    async def get_tools(self) -> list[Any]:
        """拉取并缓存所有 MCP 工具（本地 + 外部）。"""
        client = await self._ensure_client()
        tools = await client.get_tools()
        self._tools_by_name = {tool.name: tool for tool in tools}
        return tools

    async def warmup(self) -> None:
        """
        预热 MCP 连接。
        在应用启动阶段调用一次，可自动拉起本地 stdio MCP 子进程并完成工具发现。
        """
        await self.get_tools()

    async def is_available(self) -> bool:
        """可用性检查：至少成功发现一次工具。"""
        try:
            tools = await self.get_tools()
            return len(tools) > 0
        except Exception:
            return False

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        兼容旧调用方式：按工具名直接调用。
        用于保留原 `mcp_tools.py` 里的直接工具调用能力。
        """
        if tool_name not in self._tools_by_name:
            await self.get_tools()
        tool = self._tools_by_name.get(tool_name)
        if tool is None:
            raise ValueError(f"Unknown MCP tool: {tool_name}")
        return await tool.ainvoke(kwargs)


mcp_client = MCPClientManager()
