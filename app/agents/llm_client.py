"""
LiteLLM client wrapper for unified LLM access
"""
import asyncio
import importlib
import os
import random
import warnings
from typing import Any, Optional
from app.config import config
from app.mcp.client import mcp_client

import litellm


def _otel_sdk_enabled() -> bool:
    """与 app.main 一致：关闭 SDK 时不应注册 LiteLLM otel 回调，否则重载/shutdown 后易报错。"""
    return os.environ.get("OTEL_SDK_DISABLED", "").lower() not in ("true", "1", "yes")


litellm.callbacks = ["otel"] if _otel_sdk_enabled() else []


def _resolve_chat_litellm():
    """优先使用独立包实现，缺失时回退到社区版实现。"""
    try:
        return importlib.import_module("langchain_litellm").ChatLiteLLM
    except ImportError:
        return importlib.import_module("langchain_community.chat_models").ChatLiteLLM


ChatLiteLLM = _resolve_chat_litellm()

class UnifiedLLMClient:
    def __init__(self):
        self._llm_cache: dict[str, ChatLiteLLM] = {}
        self._llm_tools_cache: dict[str, Any] = {}
        self._mcp_tools_ready = False
        self.llm = self._get_llm(config.DEFAULT_MODEL)
        self.llm_with_tools = self.llm

    def _get_llm(self, model_name: str) -> ChatLiteLLM:
        if model_name not in self._llm_cache:
            # 兼容旧版 langchain_community 实现时，屏蔽已知的过渡期弃用告警。
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="The class `ChatLiteLLM` was deprecated.*",
                )
                self._llm_cache[model_name] = ChatLiteLLM(
                    model=model_name,
                    temperature=0.7,
                    drop_params=True,
                    streaming=False,
                )
        return self._llm_cache[model_name]

    async def _get_llm_with_tools(self, model_name: str):
        """
        使用 MultiServerMCPClient 动态加载工具并绑定到模型。
        首次加载后缓存，减少重复发现工具带来的开销。
        """
        if model_name not in self._llm_tools_cache or not self._mcp_tools_ready:
            mcp_tools = await mcp_client.get_tools()
            self._llm_tools_cache[model_name] = self._get_llm(model_name).bind_tools(mcp_tools)
            self._mcp_tools_ready = True
        return self._llm_tools_cache[model_name]

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        if any(token in msg for token in ["429", "rate limit", "timeout", "timed out"]):
            return True
        if "5" in msg and "error" in msg:
            return True
        status_code = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in [429, 500, 502, 503, 504]:
            return True
        return False

    async def invoke_with_retry(
        self,
        messages: list,
        *,
        prefer_tools: bool = False,
        invoke_config: Optional[dict] = None,
    ):
        models = [config.DEFAULT_MODEL] + [m.strip() for m in config.FALLBACK_MODELS if m and m.strip()]
        max_retries = max(1, config.LLM_MAX_RETRIES)
        last_error = None

        for model_name in models:
            use_tools = prefer_tools
            runnable = self._get_llm(model_name)
            if use_tools:
                try:
                    runnable = await self._get_llm_with_tools(model_name)
                except Exception:
                    # MCP 连接异常时降级为无工具模式，保证主流程可继续。
                    runnable = self._get_llm(model_name)

            for attempt in range(max_retries):
                try:
                    return await runnable.ainvoke(messages, config=invoke_config)
                except Exception as exc:
                    last_error = exc
                    if not self._is_retryable_error(exc):
                        break
                    if attempt == max_retries - 1:
                        break
                    exp_delay = config.LLM_RETRY_BASE_DELAY_SEC * (2 ** attempt)
                    jitter = random.uniform(0, 0.3)
                    delay = min(config.LLM_RETRY_MAX_DELAY_SEC, exp_delay + jitter)
                    await asyncio.sleep(delay)

        raise RuntimeError(f"All model retries failed: {last_error}")

llm_client = UnifiedLLMClient()
