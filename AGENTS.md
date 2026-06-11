# Agent Black — Agent Instructions

Multi-agent research platform: FastAPI backend (orchestrator + 3 specialist agents) + React 19 frontend.

## Quick Start

```bash
# Backend — starts control panel (:8000) + 3 agent services (:8001-8003)
pip install -r requirements.txt
python start.py

# Frontend (separate terminal)
cd ui && bun install && bun run dev   # → http://localhost:8080
```

Docker alternative: `docker-compose up --build` (does not include frontend; start separately or use `docker-compose.deploy.yml` for full stack).

## Service Ports

| Service            | Port | Process entrypoint                  |
|--------------------|------|-------------------------------------|
| Control Panel API  | 8000 | `app/main.py` (FastAPI)             |
| CV Research Agent  | 8001 | `agents/research-agent/main.py`     |
| NLP Solution Agent | 8002 | `agents/solution-agent/main.py`     |
| ML Experiment Agent| 8003 | `agents/experiment-agent/main.py`   |
| Frontend (dev)     | 8080 | `ui/` via Vite dev server           |

## Key Commands

- `python start.py` — launches all 4 backend services as subprocesses, logs to `logs/`
- `curl -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d '{"query":"..."}'` — submit a research query
- `curl http://localhost:8001/health` — health check on any agent
- `curl -X POST http://localhost:8001/mcp -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'` — list MCP tools

Frontend (from `ui/`):
- `bun run dev` — Vite dev server with proxy to :8000
- `bun run build` — production build
- `bun run lint` — ESLint (uses Prettier integration)
- `bun run format` — Prettier auto-format

## Architecture

5-service system communicating via HTTP:
- **Control Panel** orchestrates queries through a 5-step pipeline: relevance gate → agent selection (LLM) → task decomposition (LLM) → concurrent dispatch → result aggregation (LLM)
- **3 specialist agents** (CV, NLP, ML) each expose 13 MCP tools via JSON-RPC 2.0 (`POST /mcp`) and A2A protocol (`POST /a2a`)
- **React frontend** connects to Control Panel API via `/api` proxy

Config stored in SQLite (`data/agent_black.db`), not env vars. `.env` only holds infra settings (HOST, PORT, VITE_API_URL).

## Frontend Conventions

- **TanStack Start** with file-based routing in `ui/src/routes/`. Do NOT create `src/pages/`, `app/layout.tsx`, or Next.js/Remix patterns.
- Dynamic params use `$param` syntax (e.g., `$id.tsx`). Splat catch-all uses `$` with `_splat` param.
- `routeTree.gen.ts` is auto-generated — do not edit.
- `__root.tsx` is the app shell; preserve `<Outlet />`.
- Path alias: `@/` maps to `src/`.
- Prettier: 100 char width, double quotes, trailing commas.
- ESLint bans `server-only` imports — use `*.server.ts` naming or `@tanstack/react-start/server-only` instead.
- Bun supply-chain guard enabled: packages younger than 24h are rejected by default (`ui/bunfig.toml`).

## Backend Conventions

- Each agent is a standalone FastAPI app started via `uvicorn main:app --port <port>` from its own directory.
- Shared code lives in `shared/` (LLM client, MCP registry, A2A protocol, config, academic API clients).
- The Control Panel imports `shared/` directly; agents use it via relative paths from their directories.
- All agents use SQLite-backed config from `shared/config.py` for LLM provider settings and API keys.
- LLM calls go through `shared/llm.py` — supports Gemini, OpenAI, Anthropic with automatic retry.
- MCP tools registered per-agent in `agents/<name>/tools/` — 7 common + 6 domain-specific per agent.

## Gotchas

- `start.py` runs agents as subprocesses; it does NOT import them. Each agent has its own `main:app`.
- The orchestrator runs inside the Control Panel process (`app/main.py`), not as a separate agent.
- API keys are never returned by `GET /api/settings` — only `api_key_set: true/false` flags.
- Docker Compose (`docker-compose.yml`) runs only the 4 backend services; frontend is separate.
- The deploy flow (`deploy.sh` + `docker-compose.deploy.yml`) pulls pre-built images from GHCR, not local builds.
- `data/` and `logs/` are gitignored; created automatically on first run.
