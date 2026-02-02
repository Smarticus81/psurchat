# Multi-Agent PSUR System - Setup & Run Guide

## Phase 5: Full Integration Complete ✅

### Backend Setup

1. **Install Python Dependencies**
```bash
cd backend
pip install -r requirements.txt
```

2. **Initialize Database**
```bash
python init_db.py
```

3. **Start Backend Server**
```bash
uvicorn main:app --reload --port 8000
```

Backend will be available at: `http://localhost:8000`
API Docs: `http://localhost:8000/docs`

### Frontend Setup

1. **Install Node Dependencies** (if not done)
```bash
cd frontend
npm install
```

2. **Start Frontend Dev Server**
```bash
npm run dev
```

Frontend will be available at: `http://localhost:3000`

---

## Features Implemented - NO MOCKS ✅

### Backend API (FastAPI)
- ✅ **POST /api/sessions** - Create new PSUR session
- ✅ **GET /api/sessions/{id}** - Get session details
- ✅ **POST /api/sessions/{id}/upload** - Upload data files
- ✅ **GET /api/sessions/{id}/files** - List uploaded files
- ✅ **POST /api/sessions/{id}/start** - Start generation
- ✅ **GET /api/sessions/{id}/messages** - Get chat messages
- ✅ **GET /api/sessions/{id}/agents** - Get agent statuses
- ✅ **GET /api/sessions/{id}/sections** - Get section documents
- ✅ **GET /api/sessions/{id}/workflow** - Get workflow state
- ✅ **WebSocket /ws/{id}** - Real-time updates

### Database Layer
- ✅ SQLite database with SQLAlchemy ORM
- ✅ Full schema for all entities
- ✅ Automatic table creation
- ✅ Transaction management

### Frontend Integration
- ✅ Axios API client
- ✅ WebSocket hook for real-time updates
- ✅ Components fetch real data from API
- ✅ Live agent status updates
- ✅ Real-time message streaming

### MCP Servers (6 Total)
- ✅ Data Access Server
- ✅ Statistical Tools Server
- ✅ Collaboration Server
- ✅ Document Processing Server
- ✅ Visualization Server
- ✅ External Search Server

### AI Agents (19 Total)
- ✅ All section agents implemented
- ✅ All analytical agents implemented
- ✅ Orchestrator & QC agents

---

## Usage Example

### 1. Start Backend
```bash
cd backend
python init_db.py  # First time only
uvicorn main:app --reload --port 8000
```

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

### 3. Use the System
- Open `http://localhost:3000`
- System will connect to session ID 1
- Real data flows from backend → frontend
- WebSocket provides real-time updates

---

## Database Schema

**Tables Created:**
- `psur_sessions` - PSUR generation sessions
- `agents` - Agent instances and status
- `chat_messages` - Agent discussions
- `section_documents` - Generated sections
- `workflow_state` - Current workflow progress
- `data_files` - Uploaded files

---

## Next Steps

To run a complete PSUR generation:

1. Create a session via API
2. Upload data files (sales, complaints, etc.)
3. Call `/api/sessions/{id}/start` to begin
4. Watch real-time progress in UI
5. Agents will collaborate and generate sections
6. QC validator reviews each section
7. Final PSUR document assembled

---

## NO MOCKS - 100% Real Implementation ✅

Every component connects to real services:
- Frontend → Backend REST API (no mock data)
- Frontend → WebSocket (real-time updates)
- Backend → SQLite Database (real persistence)
- Agents → MCP Servers (real tools)
- MCP Servers → AI Providers (real LLM calls)

**Phase 5: COMPLETE!** 🎉
