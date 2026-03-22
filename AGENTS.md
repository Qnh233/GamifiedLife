# AGENTS.md

## Project Purpose
- GamifiedLife is a Flask + LangGraph backend that turns user chat into goals, tasks, rewards, and game events.
- The HTTP API is in `app/main.py`; multi-agent orchestration is in `app/agents/workflow.py`.

## System Map (read these first)
- `app/main.py`: request entrypoints, user bootstrap, DB writes, and response shaping.
- `app/agents/workflow.py`: graph nodes (`supervisor`, `planner`, `reward`, `query`, `chat`, `tools`) and routing rules.
- `app/agents/state.py`: canonical shared state keys (`next_agent`, `tool_status`, `current_goal`, `current_tasks`, `final_response`).
- `app/database/models.py`: SQLAlchemy schema + default achievements/rewards via `init_default_data()`.
- `app/mcp/server.py` and `app/mcp/client.py`: MCP-style external tool registry and invocation.

## Request/Data Flow
- `POST /api/chat` (`app/main.py`) loads user + active goal/tasks from MySQL, then awaits `run_agent_workflow(...)`.
- Agents mutate in-memory state only; persistence happens after workflow returns in `app/main.py`.
- New goals/tasks are inserted if IDs do not exist; profile, rewards, and game events are also persisted there.
- `POST /api/tasks/complete/<task_id>` applies deterministic XP/drop logic in `main.py` (separate from agent flow).

## Agent Routing and Tool Calling Conventions
- Routing relies on `state["next_agent"]` and `state["tool_status"]` (`app/agents/workflow.py`).
- Use uppercase decisions for agent handoff (`PLANNING`, `REWARD`, `QUERY`, `CHAT`, `RESPONSE`) because workflow normalizes via `.lower()`.
- Tool call handshake pattern:
  - Agent sets `tool_name`, `tool_args`, `tool_sender`, `tool_status = pending`, `next_agent = TOOLS`.
  - `tools_node` executes MCP call, writes `tool_result`, sets `tool_status = completed`.
  - Workflow routes back to `tool_sender` to continue.
- Reuse `ToolCallState` constants from `app/common/constant.py`.

## Developer Workflows
- Install deps: `pip install -r requirements.txt`.
- Main API server: `python -m app.main` (Flask app on `HOST`/`PORT` from `app/config.py`).
- MCP server (needed for tool-enabled paths): `python -m app.mcp.server` (defaults to `localhost:8001`).
- There is no automated test suite in repo; validate by calling `/health`, `/api/status`, and `/api/chat`.

## Project-Specific Patterns to Follow
- Keep DB side effects in `app/main.py` route handlers; agent nodes should return updated state, not commit DB transactions.
- IDs are UUID-like strings generated in Python (`uuid.uuid4()` usage in `main.py`, `planner.py`, `reward.py`).
- JSON-serializable dicts are the interoperability format between nodes and persistence layer (`to_dict()` across models).
- Game balance values come from `app/config.py` (`BASE_XP_PER_TASK`, `DIFFICULTY_MULTIPLIER`, `DROP_RATE_BASE`); do not hardcode duplicates.
- When adding a new agent node, update both `workflow.add_node(...)` and conditional routing maps in `create_workflow()`.

## External Integrations and Boundaries
- LLM access is centralized in `app/agents/llm_client.py` (LiteLLM with fallback models).
- MCP tools are HTTP calls from `MCPClient`; server-side tool contracts are defined in `MCPServer._register_tools()`.
- SQL tool safety boundary: `sql_query` in `app/mcp/server.py` allows only `SELECT` statements.
- Redis module exists (`app/database/redis.py`) but is not wired into request flow in `app/main.py`.

