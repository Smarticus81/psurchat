# CLAUDE.md

## Project Overview

Multi-Agent PSUR (Periodic Safety Update Report) System — 19 specialized AI agents collaborate via real-time WebSocket to generate medical device safety reports. FastAPI backend, React/TypeScript frontend, multi-provider AI support (OpenAI, Anthropic, Google, Perplexity).

## Tech Stack

- **Backend:** Python 3, FastAPI 0.115, Uvicorn, SQLAlchemy 2.0 (SQLite), Pydantic 2.9, python-socketio
- **Frontend:** React 18, TypeScript 5.6, Vite 5.4, Axios, socket.io-client
- **AI Providers:** OpenAI, Anthropic, Google Generative AI, Perplexity (via httpx)
- **MCP:** mcp 1.1.2 (Model Context Protocol) — 6 servers exposing 23 tools
- **Data/Viz:** pandas, numpy, scipy, statsmodels, matplotlib, seaborn
- **Document Processing:** python-docx, PyPDF2, openpyxl
- **Testing:** pytest, pytest-asyncio

## Project Structure

```
psurchat/
├── backend/
│   ├── main.py                  # FastAPI app, routes, WebSocket manager
│   ├── orchestrator.py          # OrchestratorAgent (Alex)
│   ├── config.py                # Settings, agent configs, provider fallback
│   ├── data_processor.py        # Data processing utilities
│   ├── document_endpoints.py    # Document handling endpoints
│   ├── init_db.py               # Database initialization
│   ├── requirements.txt         # Python dependencies
│   ├── agents/
│   │   ├── base_agent.py        # Base Agent class with MCP support
│   │   ├── orchestrator.py      # Orchestration logic
│   │   ├── qc_agent.py          # Quality Control agent (Victoria)
│   │   ├── section_agents/      # 13 section-specific agents
│   │   └── analytical_agents/   # 3 analytical agents
│   ├── database/
│   │   ├── models.py            # SQLAlchemy ORM models (6 tables)
│   │   └── session.py           # Database session management
│   └── mcp_servers/             # 6 MCP tool servers
│       ├── data_access/
│       ├── statistical_tools/
│       ├── collaboration/
│       ├── document_processing/
│       ├── visualization/
│       └── external_search/
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main app component
│   │   ├── api.ts               # Axios API client
│   │   ├── types.ts             # TypeScript interfaces
│   │   ├── components/          # React components
│   │   │   ├── SessionSetup.tsx
│   │   │   ├── DiscussionForum.tsx
│   │   │   ├── AgentRoster.tsx
│   │   │   ├── AgentGraph.tsx
│   │   │   └── SessionList.tsx
│   │   └── hooks/
│   │       └── useWebSocket.ts  # WebSocket hook
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── Documentation/               # Project docs (README, SETUP, STATUS, etc.)
├── quickstart.py                # DB init script
├── reset_db.py                  # DB reset utility
├── start.sh                     # Linux/Mac startup
└── start.bat                    # Windows startup
```

## Common Commands

### Backend

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Initialize database
python quickstart.py

# Reset database
python reset_db.py

# Run backend server (port 8000)
cd backend && uvicorn main:app --reload --port 8000
```

### Frontend

```bash
# Install dependencies
cd frontend && npm install

# Run dev server (port 3000)
cd frontend && npm run dev

# Production build
cd frontend && npm run build

# Lint
cd frontend && npm run lint
```

### Quick Start (Both)

```bash
# Linux/Mac
./start.sh

# Windows
start.bat
```

### Testing

```bash
pytest backend/
pytest -v --asyncio-mode=auto
```

## Architecture

```
React Frontend (TypeScript)
    ↓ Axios REST + WebSocket (socket.io)
FastAPI Backend (Python)
    ↓
19 AI Agents (orchestrator, section, analytical, QC)
    ↓ MCP Protocol
6 MCP Servers (23 tools)
    ↓
AI Providers (OpenAI / Anthropic / Google / Perplexity)
    ↓
SQLite Database (SQLAlchemy ORM)
```

**19 Agents:** Alex (orchestrator), Victoria (QC), Diana, Sam, Raj, Vera, Carla, Tara, Frank, Cameron, Rita, Brianna, Eddie, Clara, Marcus (section agents), Statler, Charley, Quincy (analytical).

**6 MCP Servers:** data_access (3 tools), statistical_tools (4 tools), collaboration (6 tools), document_processing (4 tools), visualization (3 tools), external_search (3 tools).

**API key fallback:** Works with a single API key. Agents prefer their configured provider but fall back through: OpenAI → xAI/Grok → Google → Anthropic → Perplexity.

## Key API Endpoints

- `POST /api/sessions` — Create PSUR session
- `POST /api/sessions/{id}/upload` — Upload data files
- `POST /api/sessions/{id}/start` — Start PSUR generation
- `GET /api/sessions/{id}/messages` — Get agent messages
- `GET /api/sessions/{id}/sections` — Get generated sections
- `GET /api/sessions/{id}/agents` — Get agent statuses
- `WS /ws/{session_id}` — WebSocket for real-time updates

## Database

6 tables: `psur_sessions`, `agents`, `chat_messages`, `section_documents`, `workflow_state`, `data_files`. Models defined in `backend/database/models.py`.

## Configuration

Environment variables via `.env` file (see `backend/.env.example`). Key vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `PERPLEXITY_API_KEY`, `XAI_API_KEY`, `DATABASE_URL`, `API_PORT`.

## Code Style

- Backend: Python with type hints, async/await patterns, Pydantic models for validation
- Frontend: TypeScript strict mode, functional React components with hooks, CSS modules
- Linting: ESLint with TypeScript plugin (frontend)
