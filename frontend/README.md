# Multi-Agent PSUR System - Frontend

## 🎨 Modern React TypeScript UI

Stunning discussion forum interface showing real-time AI agent collaboration.

### Features

- **Real-time Discussion Forum** - Watch 17 AI agents collaborate
  - Color-coded agent avatars
- Message type indicators (system, success, error, warning)
- Markdown-style formatting
- Auto-scrolling to latest messages

- **Agent Roster Panel** - Live agent status tracking
  - 17 agents with AI provider badges
  - Real-time status updates (idle, working, complete)
  - Agent statistics dashboard

- **Premium Dark Mode UI**
  - Glassmorphism effects
  - Gradient animations
  - Smooth transitions
  - Custom scrollbars
  - Responsive design

### Tech Stack

- ⚡ **Vite** - Lightning-fast build tool
- ⚛️ **React 18** - Modern React with hooks
- 📘 **TypeScript** - Type safety
- 🎨 **CSS Variables** - Dynamic theming
- 🔌 **Socket.IO** - WebSocket support (ready)
- 🌐 **Axios** - API communication

### Quick Start

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Visit http://localhost:3000
```

### Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── DiscussionForum.tsx    # Main chat interface
│   │   ├── DiscussionForum.css
│   │   ├── AgentRoster.tsx        # Agent status panel
│   │   └── AgentRoster.css
│   ├── App.tsx                     # Root component
│   ├── App.css                     # Layout styles
│   ├── main.tsx                    # Entry point
│   ├── index.css                   # Global styles
│   └── types.ts                    # TypeScript definitions
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### Components

#### DiscussionForum
Shows agent messages in real-time with:
- Agent color-coding
- Message timestamps
- Targeted vs broadcast messages
- Message type styling (system/error/success/warning)

#### AgentRoster
Displays all 17 agents with:
- Real-time status indicators
- AI provider badges (OpenAI, Anthropic, Google, Perplexity)
- Agent statistics (total, active, done)
- Model information

### Customization

#### Colors
Edit `src/index.css` CSS variables:
```css
:root {
  --accent-primary: #6366f1;
  --accent-secondary: #8b5cf6;
  --bg-primary: #0a0e1a;
  /* ... more variables */
}
```

#### Agent Colors
Edit `src/types.ts` AGENT_COLORS object

### API Integration

The frontend is configured to proxy API calls to the backend:

```typescript
// Vite will proxy /api/* to http://localhost:8000
fetch('/api/agents')
fetch('/api/chat/1/messages')
```

### Building for Production

```bash
npm run build

# Built files will be in dist/
# Serve with: npm run preview
```

### Environment Variables

Create `.env` if needed:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### Next Steps

- [ ] Implement WebSocket connection for real-time updates
- [ ] Add file upload interface
- [ ] Add section progress visualization
- [ ] Add workflow control panel
- [ ] Add user intervention prompts

### Status

✅ UI Complete
🔄 Mock data (will connect to backend API)
⏳ WebSocket integration coming next

---

**Built with ❤️ using React + TypeScript + Vite**
