# HighStake

**AI-powered boardroom simulator for high-stakes presentation practice.**

HighStake lets executives rehearse critical presentations in a realistic virtual boardroom with AI-powered panel members who challenge, question, and stress-test your pitch — so you're battle-ready before the real thing.

## Features

### Pre-Session Setup (Moderator-Led)
- **Interaction Mode**: Choose between section breaks, hand-raise, or free-flow interruptions
- **Intensity Level**: Friendly dry run → moderate challenge → full adversarial stress test
- **Focus Areas**: Direct the panel to pressure-test specific aspects (financials, GTM, competitive analysis, etc.)
- **Deck Upload**: Upload your PPTX/PDF and present with real slides

### Live Boardroom Session
- **4 AI Agent Personas**:
  - 🟣 **Diana Chen** (Moderator / Chief of Staff) — manages flow, turn-taking, and pacing
  - 🔴 **Marcus Webb** (The Skeptic / CFO) — challenges viability, questions ROI
  - 🟢 **Priya Sharma** (The Analyst / VP Strategy) — deep-dives into data and methodology
  - 🟡 **James O'Brien** (The Contrarian / Board Advisor) — finds logical gaps, worst-case scenarios
- Video-call-style interface with presenter + agent tiles
- Real-time slide viewer with navigation
- Live meeting chat with contextual AI questions
- Session timer and recording indicator

### Post-Session Debrief
- **Overall Score** with category breakdowns (clarity, confidence, data support, Q&A handling, structure)
- **Moderator's Summary** — narrative feedback from your session chair
- **Full Transcript** of all agent interactions
- **Prioritized Coaching** — specific, actionable improvement areas ranked by priority
- **Strengths** — what you did well

## Tech Stack

- **Frontend**: React 18 + Vite
- **Styling**: Tailwind CSS
- **Fonts**: Playfair Display (headings) + DM Sans (body)

## Getting Started

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

## Roadmap

### Phase 2
- [ ] Real-time speech-to-text (Deepgram / Whisper)
- [ ] Claude API integration for dynamic agent responses
- [ ] Text-to-speech with distinct voices per agent (ElevenLabs)
- [ ] Webcam capture and session recording
- [ ] PPTX parsing with `python-pptx`

### Phase 3
- [ ] Real-time agent interruptions with natural timing
- [ ] Animated avatars with lip-sync (D-ID / HeyGen)
- [ ] Multi-session tracking and improvement over time
- [ ] Team/org accounts
- [ ] Export to PDF reports

## Architecture

```
src/
├── components/
│   ├── AgentTile.jsx        # AI agent video tile
│   ├── ChatMessage.jsx      # Meeting chat message
│   ├── MeetingPhase.jsx     # Live boardroom session
│   ├── PresenterTile.jsx    # Presenter webcam tile
│   ├── ReviewPhase.jsx      # Post-session debrief
│   ├── SetupPhase.jsx       # Moderator-led configuration
│   └── SlideViewer.jsx      # Slide deck viewer
├── utils/
│   └── constants.js         # Agents, modes, questions, slides
├── App.jsx                  # Phase router
├── main.jsx                 # Entry point
└── index.css                # Global styles + Tailwind
```

## License

MIT
