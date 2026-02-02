# Quick Start Guide

## 🚀 Multi-Agent PSUR System

### Prerequisites

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **PostgreSQL 14+** ([Download](https://www.postgresql.org/download/))
- **Redis** ([Windows](https://github.com/microsoftarchive/redis/releases) | [Linux/Mac](https://redis.io/download))
- **API Keys** (OpenAI, Anthropic, Google, Perplexity, Wolfram)

### Installation (5 minutes)

```bash
# 1. Run automated setup
python setup.py

# 2. Edit .env file with your API keys
notepad .env

# 3. Start PostgreSQL and Redis
# (Instructions vary by OS - check your installation)

# 4. Start the backend
cd backend
python main.py
```

### Verify Installation

Open browser to http://localhost:8000

You should see:
```json
{
  "service": "Multi-Agent PSUR System",
  "status": "operational",
  "agents": 17,
  "mcp_servers": 6
}
```

### What We've Built So Far

✅ **Phase 1 Complete:**
- FastAPI backend with health endpoints
- PostgreSQL database models (6 tables)
- Configuration for 17 AI agents
- Environment management

✅ **Phase 2 In Progress:**
- MCP Data Access Server (3 tools)
- Base Agent class with MCP client
- Orchestrator Agent (Alex - Claude Sonnet 4.5)
- First Section Agent (Diana - GPT-5.1)

### Current Features

1. **Database Schema:**
   - PSUR Sessions tracking
   - Chat message storage
   - Section documents
   - Workflow state management
   - Uploaded files registry
   - Calculation audit log

2. **Agents Configured:**
   - Orchestrator (Alex) - Claude Sonnet 4.5
   - Device ID (Diana) - GPT-5.1
   - 15 more coming soon...

3. **MCP Servers:**
   - Data Access Server implemented
   - 5 more coming soon...

### Project Structure

```
psurchatsystem/
├── backend/
│   ├── main.py                    # FastAPI app ✅
│   ├── config.py                  # Configuration ✅
│   ├── database/
│   │   ├── models.py              # Database models ✅
│   │   └── session.py             # DB connections ✅
│   ├── agents/
│   │   ├── base_agent.py          # Base class ✅
│   │   ├── orchestrator.py        # Alex ✅
│   │   └── section_agents/
│   │       └── device_identification.py  # Diana ✅
│   └── mcp_servers/
│       └── data_access/
│           └── server.py          # Data tools ✅
├── requirements.txt               # Dependencies ✅
├── .env.example                   # Template ✅
├── setup.py                       # Setup script ✅
└── README.md                      # Overview ✅
```

### Next Steps

**To continue development:**

1. Implement remaining 12 section agents
2. Build 5 additional MCP servers
3. Create frontend React UI
4. Add WebSocket real-time updates
5. Implement workflow engine

**To test current functionality:**

```python
# Test database connection
from backend.database.session import init_db
init_db()

# Test agent creation
from backend.agents.orchestrator import create_orchestrator
alex = create_orchestrator(session_id=1)

# Test MCP tool (requires running MCP server)
# python backend/mcp_servers/data_access/server.py
```

### API Endpoints Currently Available

- `GET /` - Health check
- `GET /api/health` - Detailed status
- `GET /api/agents` - List all 17 agents

### Documentation

- [Implementation Plan](../../../.gemini/antigravity/brain/.../implementation_plan.md)
- [Output Examples](../../../.gemini/antigravity/brain/.../output_examples.md)
- [Task Breakdown](../../../.gemini/antigravity/brain/.../task.md)

### Need Help?

The system is designed to be built incrementally. Each component is modular and can be tested independently.

**Status: Phase 1 ✅ | Phase 2 🔄 (In Progress)**
