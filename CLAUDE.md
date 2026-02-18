# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HighStake is an AI-powered boardroom simulator for high-stakes presentation practice. Executives rehearse presentations with 4 AI-powered panel members (Diana Chen/Moderator, Marcus Webb/Skeptic, Priya Sharma/Analyst, James O'Brien/Contrarian) who challenge and question their pitch. Currently at Phase 2 (Core Intelligence) — real AI interactions via Gemini API.

## Commands

```bash
# Run both frontend + backend concurrently
npm run dev:all

# Frontend only (port 3000)
npm run dev

# Backend only (port 8000)
npm run dev:server
# Or directly:
cd server && uvicorn app.main:socket_app --reload --port 8000

# Build frontend for production
npm run build

# Lint frontend
npm run lint

# Backend tests
cd server && pytest
```

## Architecture

**Frontend**: React 18 + Vite, Zustand for state, Tailwind CSS, Socket.IO client
**Backend**: FastAPI + Python-SocketIO, SQLAlchemy async (SQLite), Gemini API (LLM + TTS)

### Phase-Based UI Flow

`App.jsx` routes between three phases:
- **SetupPhase** — moderator-led session configuration, deck upload
- **MeetingPhase** — live boardroom with agent tiles, slide viewer, chat, speech recognition
- **ReviewPhase** — post-session debrief with scores and coaching

### Frontend State

Two Zustand stores:
- `sessionStore` — session config, current phase, deck manifest, session ID
- `meetingStore` — live meeting state (slides, messages, timer, audio/video)

### Backend Layered Architecture

`api/` (REST routes) → `services/` (business logic) → `models/` (SQLAlchemy ORM)

WebSocket events flow through `ws/handler.py` → `ws/events.py` → `AgentEngine`.

### Key Backend Services

- **AgentEngine** (`services/agent_engine.py`) — orchestrates all agent interactions per session; manages context, timing, turn-taking, question generation
- **ContextManager** (`services/context_manager.py`) — assembles sliding context window for agent LLM calls
- **LLMClient** (`services/llm_client.py`) — Gemini API wrapper (gemini-2.5-flash)
- **TTSService** (`services/tts_service.py`) — Gemini TTS (gemini-2.5-flash-preview-tts)
- **AgentPrompts** (`services/agent_prompts.py`) — persona system prompts for each agent

### API Integration

Frontend proxies `/api` and `/socket.io` to `http://localhost:8000` (configured in `vite.config.js`). Backend CORS allows `http://localhost:3000`.

### Local Storage

All files stored in `./data` directory (TTS audio, recordings, uploads). Served via `/api/files/{path}`.

### External Dependencies

Only one API key needed: `GEMINI_API_KEY` (set in `server/.env`). Browser Web Speech API handles speech-to-text. No cloud storage — everything is local filesystem + SQLite.

## Conventions

- Frontend: camelCase variables/functions, PascalCase components (`.jsx`), camelCase services (`.js`)
- Backend: snake_case throughout (PEP 8)
- Fully async Python backend — use `async/await` for all DB and API operations
- Functional React components with hooks only (no class components)
- Backend config via Pydantic Settings (`server/app/config.py`), reads from `.env`

## Progress Tracking

Before committing and pushing to git remote, always update `progress.md` at the project root to reflect any changes made in the session. Mark newly completed features as "Done", update "Partial" items, and add any new items discovered during implementation. Append a dated session summary at the bottom of the file.
