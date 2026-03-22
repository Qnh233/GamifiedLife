"""
LiteLLM client wrapper for unified LLM access
"""

from langchain_community.chat_models import ChatLiteLLM
from app.config import config
from app.mcp.mcp_tools import agent_tools


class UnifiedLLMClient:
    def __init__(self):
        # 初始化 LiteLLM 封装器
        self.llm = ChatLiteLLM(
            model=config.DEFAULT_MODEL,  # 例如: "gpt-4o-mini" 或 "qwen-max"
            temperature=0.7,
            # 开启这个参数，LiteLLM 会自动剔除提供商 API 不支持的参数（如非法的 tool_choice）
            drop_params=True
        )
        # 核心步骤：将 Python 工具绑定到 LLM。
        # 这样 LLM 就具备了输出原生 tool_calls 的能力
        self.llm_with_tools = self.llm.bind_tools(agent_tools)

llm_client = UnifiedLLMClient()
