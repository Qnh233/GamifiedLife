from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool, InjectedToolArg
from app.mcp.client import mcp_client  # 你的原始 MCP 客户端

# 1. 显式包装你的 MCP 工具。
# 注意：Docstring (注释) 和参数类型 (Type Hints) 极其重要，LLM 全靠它们来做决策！
# 你需要为每个工具定义一个函数，并使用 @tool 装饰器来标记它们。这样才能bind_tool绑定进llm。
@tool
async def get_user_gaming_status(
    # 使用 Annotated 和 InjectedToolArg 标记此参数
    # 这告诉 LangChain：不要让 LLM 填充这个参数，而是从 invoke 时的 config['configurable'] 中获取
    config: RunnableConfig) -> str:
    """
    获取用户的**当前**游戏化状态，包括等级(level)、经验值(exp)和当前任务(tasks)。
    当用户询问自己**最新**的的进度或状态时调用此工具。
    """
    # 1. 从 config 中安全获取 user_id
    # RangeChain 会自动忽略类型为 RunnableConfig 的参数，不会将其发给 LLM
    configuration = config["configurable"]
    user_id = configuration.get("user_id")
    if not user_id:
        return "错误: 无法确定当前用户身份 (Context missing user_id)。请联系管理员检查系统配置。"
    try:
        # 这里直接调用你现有的 MCP 客户端逻辑
        result = await mcp_client.call_tool("get_user_gaming_status", user_id=user_id)
        return str(result)
    except Exception as e:
        return f"查询状态失败: {str(e)}"


# 将你需要暴露给这个 Agent 的工具放进一个列表
agent_tools = [get_user_gaming_status]