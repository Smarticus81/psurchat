# 🚀 Multi-Agent PSUR System

AI-powered PSUR (Periodic Safety Update Report) generation with 19 specialized agents collaborating in real-time.

## ✨ Features

- **19 AI Agents** working collaboratively
- **Real-time collaboration** via WebSocket
- **API Key Fallback System** - works with just 1 API key
- **Date Range Selection** for coverage periods
- **Live Progress Tracking** with status updates
- **Actual AI Content Generation** (not mocked)

---

## 🎯 Quick Start

### 1️⃣ **First Time Setup**

```bash
# Run quickstart to initialize database
python quickstart.py
```

### 2️⃣ **Start the System**

**Option A: Use the start script** (Recommended)
```bash
# Double-click or run:
start.bat
```
This opens 2 windows (backend + frontend) automatically!

**Option B: Manual start** (Two terminals)

**Terminal 1 - Backend:**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 3️⃣ **Open Browser**

Navigate to: **http://localhost:3000**

---

## 🔑 Configuration

### Required: Add API Keys

Edit `backend/.env`:

```env
# Minimum: Add at least ONE key (OpenAI or Anthropic recommended)
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here

# Optional (will fallback to OpenAI/Anthropic if not set)
GOOGLE_API_KEY=your-key-here
```

**✅ System works with just 1 API key!**

---

## 📖 Usage

1. **Enter Device Info** - Name and UDI-DI
2. **Select Coverage Period** - Use date pickers for start/end dates
3. **Upload Files** - Sales data, complaints, PMCF data
4. **Click "Start PSUR Generation"**
5. **Watch Live Progress**:
   - Discussion Forum shows AI conversations
   - Agent cards update status (idle → working → complete)
   - Section progress shows 1/13, 2/13, etc.
   - Each section takes ~3-5 seconds with real AI

---

## 🏗️ Architecture

### Backend (FastAPI)
- **19 Specialized Agents** (Alex orchestrator, Diana device ID, Sam scope, etc.)
- **Real AI Integration** (OpenAI GPT-4, Anthropic Claude, Google Gemini)
- **SQLite Database** (easy setup, no PostgreSQL needed)
- **WebSocket** for real-time updates
- **API Key Fallback** (intelligent provider switching)

### Frontend (React + TypeScript)
- **Session Management** with date range selection
- **Real-time Dashboard** with WebSocket
- **Discussion Forum** showing agent collaboration
- **Agent Roster** with live status indicators
- **Section Progress** tracking

---

## 🎛️ API Key Fallback

**How it works:**
- If an agent's preferred provider isn't configured, it automatically falls back
- Fallback chain: **Preferred → OpenAI → Anthropic → Google → Perplexity**

**Example:**
```
Agent needs Google Gemini → Not configured → Falls back to OpenAI ✅
```

See `API_KEY_FALLBACK.md` for full details.

---

## 📂 Project Structure

```
psurchatsystem/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── orchestrator.py      # Alex - Orchestrator agent with REAL AI
│   ├── config.py            # Settings & agent configs
│   ├── database/
│   │   ├── models.py        # SQLAlchemy models
│   │   └── session.py       # DB connection
│   └── .env                 # API keys configuration
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── api.ts           # Backend API client
│   │   └── types.ts         # TypeScript types
│   └── package.json
├── quickstart.py            # Database initialization
├── start.bat                # Windows startup script
└── README.md
```

---

## 🔧 Troubleshooting

### Backend won't start
```bash
# Make sure you're in project root:
uvicorn backend.main:app --reload --port 8000
```

### Frontend CORS errors
- Make sure backend is running on port 8000
- Check browser console for actual error

### No AI activity
- Verify API keys in `backend/.env`
- Check backend terminal for error messages
- Create a NEW session (don't reuse old ones)

### Database errors
```bash
# Reinitialize database:
python quickstart.py
```

---

## 📚 Documentation

- `API_KEY_FALLBACK.md` - Fallback system details
- `USER_WORKFLOW.md` - Complete UX journey
- `STATUS.md` - Current system status
- `VERIFICATION.md` - System verification checklist

---

## 🎯 What You'll See

### When Working Correctly:

**Discussion Forum Messages:**
```
🚀 PSUR Generation Workflow Started
Initializing all systems and AI agents...

📋 Data Validation Required
Please validate all uploaded files...

✅ Data Validation Complete
All uploaded files validated successfully...

📝 Starting Section A: General Information (1/13)
Agent: Diana

✅ Section A Complete
Diana has finished General Information.
Word count: 287
```

**Agent Status Changes:**
- Alex (Orchestrator): idle → working → complete
- Diana (Device ID): idle → working → complete
- Sam (Scope): idle → working → complete
- (... continues for all 13 sections)

**Progress Tracking:**
- Workflow State updates: 1/13 → 2/13 → ... → 13/13
- Real-time status updates every 2-5 seconds
- Live WebSocket connection indicator

---

## 🎉 System Ready!

Your Multi-Agent PSUR System is now configured and ready to generate professional safety reports with real AI collaboration!

**Questions?** Check the documentation files or review the backend logs for debugging.
