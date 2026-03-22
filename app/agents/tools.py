"""
Tools Node - Handles execution of tools via MCP
"""
from app.agents.state import AgentState
from app.common.constant import ToolCallState
from app.mcp.client import mcp_client

async def tools_node(state: AgentState) -> AgentState:
    tool_name = state.get("tool_name")
    tool_args = state.get("tool_args") or {}

    if not tool_name:
        state["tool_result"] = "Error: No tool specified."
        return state

    print(f"🛠️ Executing Tool: {tool_name} with args: {tool_args}")

    try:
        # Execute the tool using the MCP client
        # We assume tool_args is a dictionary of arguments compatible with the tool
        result = await mcp_client.call_tool(tool_name, **tool_args)

        # Store result in state
        # Formatting result might be needed depending on tool output structure
        state["tool_result"] = str(f"Tool {tool_name} executed successfully with result: {result}")

    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        print(error_msg)
        state["tool_result"] = str(f"Tool {tool_name} execution failed: {error_msg}")

    # Clear the tool request to avoid loop, though graph routing should handle it
    state["tool_name"] = None
    state["tool_args"] = None
    state["tool_status"] = ToolCallState.COMPLETED

    return state

