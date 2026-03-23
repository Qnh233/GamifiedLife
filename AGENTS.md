# AGENTS.md

## Project Purpose
- GamifiedLife is a Flask + LangGraph backend that turns user chat into goals, tasks, rewards, and game events.
- The HTTP API is in `app/main.py`; multi-agent orchestration is in `app/agents/workflow.py`.

## System Map (read these first)
- `app/main.py`: request entrypoints, user bootstrap, scheduler bootstrap, and response shaping.
- `app/agents/workflow.py`: graph nodes (`supervisor`, `planner`, `reward`, `query`, `chat`, `tools`, `query_tools`, `chat_tools`, `planner_tools`, `response`, `reflector`) and routing rules.
- `app/agents/state.py`: canonical shared state keys (`next_agent`, `current_goal`, `current_tasks`, `messages`, `final_response`, `workflow_status`).
- `app/database/models.py`: SQLAlchemy schema + default achievements/rewards via `init_default_data()` + scheduled jobs (`ScheduledJob`).
- `app/database/services.py`: workflow persistence helper (`save_agent_result`) used by HTTP and scheduler flows.
- `app/scheduler_service.py`: APScheduler integration (`init_scheduler`, `add_job_to_scheduler`, `execute_job`).
- `app/mcp/server.py` and `app/mcp/client.py`: MCP-style external tool registry and invocation.

## Request/Data Flow
- `POST /api/chat` (`app/main.py`) loads user + active goal/tasks from MySQL, then awaits `run_agent_workflow(...)`.
- Agents mutate in-memory state only; persistence happens after workflow returns via `save_agent_result(...)` in `app/database/services.py`.
- New goals/tasks are inserted if IDs do not exist; profile, rewards, game events, and assistant chat logs are persisted in `save_agent_result(...)`.
- Workflow currently routes `response -> reflector -> END`; reflector updates persona markdown in `app/agents/personas/USER_<id>.md` and `User.last_reflection_at`.
- `POST /api/tasks/complete/<task_id>` applies deterministic XP/drop logic in `main.py` (separate from agent flow).
- `POST /api/schedules` / `GET /api/schedules/<user_id>` / `DELETE /api/schedules/<job_id>` manage scheduled `chat`/`reflector` jobs backed by `ScheduledJob` + APScheduler.

## Agent Routing and Tool Calling Conventions
- Routing relies on `state["next_agent"]` for supervisor handoff, and on whether the last AI message has `tool_calls` for tool-loop routing (`app/agents/workflow.py`).
- Use uppercase decisions for agent handoff (`PLANNING`, `REWARD`, `QUERY`, `CHAT`, `RESPONSE`) because workflow normalizes via `.lower()`.
- Tool call pattern in active graph paths is mixed:
  - `query` calls `llm_with_tools` and can emit `AIMessage.tool_calls`.
  - `planner` and `chat` currently call plain `llm` (no bound tools), so `planner_tools`/`chat_tools` loops are present in graph but usually dormant.
  - Conditional edges still route tool-call messages to dedicated ToolNodes (`query_tools`, `chat_tools`, `planner_tools`) and then back to the same agent node.
  - Message history uses `add_messages` reducer in `AgentState` to preserve tool-call/ToolMessage continuity.
- `ToolCallState` constants and `app/agents/tools.py` exist for legacy/manual paths; `create_workflow()` also still registers a legacy `tools` node.

## Developer Workflows
- Install deps: `pip install -r requirements.txt`.
- Main API server: `python -m app.main` (Flask app on `HOST`/`PORT` from `app/config.py`).
- MCP server (needed for tool-enabled paths): `python -m app.mcp.server` (defaults to `localhost:8001`).
- There is no automated test suite in repo; validate by calling `/health`, `/api/status`, `/api/chat`, and scheduler endpoints under `/api/schedules`.

## Project-Specific Patterns to Follow
- Keep DB side effects outside agent nodes; HTTP routes and `app/database/services.py`/`app/scheduler_service.py` handle commits while agent nodes return updated state.
- IDs are UUID-like strings generated in Python (`uuid.uuid4()` usage in `main.py`, `planner.py`, `reward.py`).
- JSON-serializable dicts are the interoperability format between nodes and persistence layer (`to_dict()` across models).
- Game balance values come from `app/config.py` (`BASE_XP_PER_TASK`, `DIFFICULTY_MULTIPLIER`, `DROP_RATE_BASE`); do not hardcode duplicates.
- When adding a new agent node, update `workflow.add_node(...)`, conditional routing maps in `create_workflow()`, and end-path sequencing (`response`/`reflector`) if required.

## External Integrations and Boundaries
- LLM access is centralized in `app/agents/llm_client.py` (single `ChatLiteLLM` instance + `llm_with_tools` binding).
- MCP tools are HTTP calls from `MCPClient`; server-side tool contracts are defined in `MCPServer._register_tools()`.
- Agent-bound LangGraph tools come from `app/mcp/mcp_tools.py`; currently only `get_user_gaming_status` is bound via `agent_tools`.
- SQL tool safety boundary: `sql_query` in `app/mcp/server.py` allows only `SELECT` statements.
- `app/config.py` maps `LITELLM_API_KEY`/`LITELLM_BASE_URL` to `OPENAI_API_KEY`/`OPENAI_API_BASE` when needed for OpenAI-compatible LiteLLM providers.
- Redis module exists (`app/database/redis.py`) but is not wired into request flow in `app/main.py`.

