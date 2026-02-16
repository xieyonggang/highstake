# HighStake — Product Requirements Document

**Version:** 1.0
**Last Updated:** February 2026
**Status:** Active Development

---

## 1. Vision & Problem Statement

### 1.1 Problem

Executives preparing for high-stakes presentations — board meetings, investor pitches, strategic reviews, M&A proposals — have limited options for realistic rehearsal. They can practice alone (no feedback), present to colleagues (scheduling friction, social dynamics, pulled punches), or hire presentation coaches (expensive, not always domain-savvy). None of these options simulate the adversarial, multi-perspective questioning that defines a real boardroom.

### 1.2 Vision

HighStake is an AI-powered virtual boardroom that lets executives upload their presentation deck, deliver it via webcam and microphone in a realistic video-call environment, and face real-time questions from a panel of AI agents — each with a distinct persona, questioning style, and strategic lens. After the session, the presenter receives a detailed debrief with scores, transcript, and prioritized coaching advice.

The goal is to make every executive feel like they've already survived the hardest version of their presentation before they walk into the real room.

### 1.3 Target Users

**Primary:** C-suite executives, VPs, and senior directors preparing for board presentations, investor meetings, strategic reviews, or internal leadership pitches.

**Secondary:** Startup founders preparing for fundraising pitches, sales leaders rehearsing enterprise deal presentations, consultants preparing client deliverables, and MBA students practicing case presentations.

### 1.4 Key Value Propositions

- Realistic simulation of multi-stakeholder scrutiny without scheduling real people
- AI agents that challenge from distinct strategic perspectives (financial, analytical, adversarial)
- A Moderator agent that manages session flow and adapts to presenter preferences
- Immediate, structured feedback with actionable coaching — not just "you did well"
- Repeatable practice sessions with improvement tracking over time
- On-demand availability — practice at 11pm the night before if needed

---

## 2. User Stories & Personas

### 2.1 Core User Stories

**US-1: Session Configuration**
As a presenter, I want to configure the session parameters before presenting so that the AI panel's behavior matches the kind of preparation I need.

Acceptance Criteria:
- Presenter can select interaction mode (section breaks, hand-raise, free flow)
- Presenter can select intensity level (friendly, moderate, adversarial)
- Presenter can select one or more focus areas for the panel to prioritize
- Presenter can upload a PPTX or PDF deck
- The Moderator agent guides the setup conversationally
- Configuration is saved and can be reused for repeat sessions

**US-2: Deck Upload & Parsing**
As a presenter, I want to upload my slide deck and have the AI agents understand its content so their questions are contextually relevant to what I'm presenting.

Acceptance Criteria:
- Supports PPTX and PDF file formats
- Extracts text, titles, and structure from each slide
- Identifies slide sections/themes for agent context
- Renders slides in a viewer the presenter can navigate during the session
- Supports decks up to 100 slides and 50MB file size
- Parsing completes within 10 seconds for a typical 20-slide deck

**US-3: Live Presentation Session**
As a presenter, I want to deliver my presentation in a realistic video-call environment with AI panel members who listen and respond so that I can practice under conditions similar to the real meeting.

Acceptance Criteria:
- Presenter sees their own webcam feed in a video tile
- 4 AI agent tiles are displayed with names, titles, and role indicators
- Presenter can navigate slides while presenting
- Audio is captured via microphone and transcribed in real-time
- AI agents ask questions based on the current slide content and overall presentation context
- The Moderator manages turn-taking according to the selected interaction mode
- Session timer is visible throughout
- Presenter can mute/unmute and toggle camera
- Entire session (audio, video, slides, agent interactions) is recorded

**US-4: Agent Questioning**
As a presenter, I want each AI agent to ask questions from their specific perspective so I can practice defending my presentation from multiple angles.

Acceptance Criteria:
- The Skeptic challenges financial viability, ROI, and feasibility
- The Analyst requests data, methodology details, and evidence
- The Contrarian identifies logical gaps, worst-case scenarios, and contradictions
- The Moderator facilitates flow, manages time, and ensures balanced questioning
- Questions are contextually grounded in the current slide and overall deck content
- Question difficulty scales with the selected intensity level
- Agents reference specific data points, claims, or slides in their questions
- Each agent maintains a consistent persona voice throughout the session

**US-5: Post-Session Debrief**
As a presenter, I want a comprehensive debrief after my session so I know exactly what to improve before the real presentation.

Acceptance Criteria:
- Overall presentation score (0-100) with category breakdowns
- Moderator's narrative summary of the session
- Full searchable transcript with speaker labels and timestamps
- Prioritized list of improvement areas with specific, actionable advice
- Identified strengths with specific examples from the session
- Session recording available for playback
- Debrief exportable as PDF report
- Comparison with previous sessions (if applicable)

**US-6: Session Recording & Playback**
As a presenter, I want to watch a recording of my session so I can see my own delivery and the AI panel's reactions.

Acceptance Criteria:
- Records presenter webcam video and audio
- Records slide progression with timestamps
- Records all agent questions and responses with timestamps
- Playback interface with timeline scrubbing
- Ability to jump to specific moments (slide changes, agent questions)
- Downloadable as MP4 or WebM

**US-7: Multi-Session Tracking**
As a presenter, I want to track my improvement across multiple practice sessions so I can see my progress over time.

Acceptance Criteria:
- Dashboard showing session history with dates, scores, and durations
- Score trend charts across sessions
- Recurring weakness identification (issues that persist across sessions)
- Improvement highlights (areas that have gotten better)
- Ability to re-run a session with the same configuration

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                         │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Setup    │→ │  Meeting  │→ │  Review   │  │  Dashboard    │  │
│  │  Phase    │  │  Phase    │  │  Phase    │  │  (History)    │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│       │              │              │              │             │
│       │         ┌────┴─────┐       │              │             │
│       │         │ WebRTC   │       │              │             │
│       │         │ Camera   │       │              │             │
│       │         │ Mic      │       │              │             │
│       │         │ Recorder │       │              │             │
│       │         └────┬─────┘       │              │             │
└───────┼──────────────┼─────────────┼──────────────┼─────────────┘
        │              │             │              │
        ▼              ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API GATEWAY                               │
│                     (REST + WebSocket)                            │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
│  Deck    │ │ Speech │ │ Agent  │ │  TTS   │ │  Session   │
│  Parser  │ │  STT   │ │ Engine │ │ Engine │ │  Storage   │
│          │ │        │ │        │ │        │ │            │
│ python-  │ │Deepgram│ │ Claude │ │Eleven  │ │ PostgreSQL │
│ pptx     │ │Whisper │ │  API   │ │ Labs   │ │ S3/R2      │
└──────────┘ └────────┘ └────────┘ └────────┘ └────────────┘
```

### 3.2 Core Services

**Deck Parser Service** — Accepts PPTX/PDF uploads, extracts text, structure, and metadata from each slide, generates a slide manifest (JSON) used by the agent engine for contextual awareness, and renders slide thumbnails for the in-session viewer.

**Speech-to-Text Service** — Captures presenter audio via browser MediaRecorder API, streams audio chunks to Deepgram (or OpenAI Whisper) for real-time transcription, emits transcript segments to the Agent Engine for processing, and maintains a running full transcript with timestamps.

**Agent Engine (Orchestrator)** — The brain of the system. Receives real-time transcript segments and current slide context, routes context to individual agent LLM instances (each with distinct system prompts), implements the Moderator's orchestration logic (turn-taking, pacing, flow control), manages the question queue and timing based on the selected interaction mode, and scales question difficulty based on the selected intensity level.

**Text-to-Speech Service** — Converts agent text responses to spoken audio, uses distinct voice profiles for each agent (ElevenLabs), streams audio back to the client for playback, and maintains consistent voice characteristics per agent across the session.

**Session Storage Service** — Stores session configurations, transcripts, recordings, scores, and debrief data. Manages user accounts and session history. Handles recording uploads (video, audio) to object storage (S3/R2). Provides APIs for the dashboard and session playback.

### 3.3 Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 18 + Vite | Fast dev cycle, component architecture, hooks for real-time state |
| Styling | Tailwind CSS | Rapid UI development, consistent design system |
| State Management | Zustand or React Context | Lightweight, sufficient for session state |
| Backend | Node.js (Express) or Python (FastAPI) | WebSocket support, async processing |
| AI / LLM | Anthropic Claude API | Strong reasoning, long context window, reliable instruction-following |
| Speech-to-Text | Deepgram Nova-2 | Low latency real-time streaming, high accuracy |
| Text-to-Speech | ElevenLabs | Natural voices, distinct voice cloning per agent |
| Deck Parsing | python-pptx + PyMuPDF | Robust PPTX and PDF text extraction |
| Database | PostgreSQL | Relational data for users, sessions, scores |
| Object Storage | AWS S3 or Cloudflare R2 | Recordings, uploaded decks, exported reports |
| Auth | Clerk or Auth0 | Quick integration, SSO support for enterprise |
| Hosting | Vercel (frontend) + Railway/Fly.io (backend) | Simple deployment, good WebSocket support |
| WebSocket | Socket.IO or native WS | Real-time bidirectional communication for live session |

---

## 4. Feature Specifications

### 4.1 Phase 1: Pre-Session Setup

The Moderator agent (Diana Chen) guides the presenter through configuration in a conversational, step-by-step flow.

#### 4.1.1 Interaction Mode Selection

| Mode | Behavior | Agent Trigger | Moderator Role |
|------|----------|---------------|----------------|
| Section Breaks | Agents hold all questions until the presenter finishes a slide or section | Presenter clicks "Next Slide" or "Open Q&A" | Announces Q&A windows, calls on agents in order |
| Hand Raise | Agents raise a virtual hand when they have a question; presenter chooses when to acknowledge | Agent AI determines question urgency; raises hand via UI signal | Notifies presenter of raised hands, suggests taking questions |
| Free Flow | Agents can interject at natural pauses in the presenter's speech | STT detects pauses > 2 seconds or end-of-sentence patterns | Manages crosstalk, ensures balanced participation |

#### 4.1.2 Intensity Level Configuration

| Level | Skeptic Behavior | Analyst Behavior | Contrarian Behavior |
|-------|-----------------|-------------------|---------------------|
| Friendly | Asks clarifying questions, accepts most claims | Requests supporting data politely | Gently suggests alternative perspectives |
| Moderate | Pushes back on weak claims, demands justification | Requires specific data sources and methodology | Identifies 1-2 key logical gaps per section |
| Adversarial | Aggressively challenges all projections, expresses doubt | Demands sensitivity analysis, rejects hand-waving | Systematically dismantles arguments, presents worst cases |

#### 4.1.3 Focus Area Selection

The presenter selects one or more focus areas. These areas are injected into each agent's system prompt as priority topics. Available focus areas: Financial Projections, Go-to-Market Strategy, Competitive Analysis, Technical Feasibility, Team & Execution, Market Sizing, Risk Assessment, Timeline & Milestones. Custom focus areas can be typed in by the presenter.

#### 4.1.4 Deck Upload

Accepted formats: PPTX (preferred), PDF. Max file size: 50MB. Max slides: 100. Processing pipeline: upload to server, extract text and structure per slide, generate slide manifest JSON, create thumbnail renders, return manifest to client, and populate agent context.

Slide Manifest Schema:
```json
{
  "id": "deck_abc123",
  "filename": "Q4_Strategy_Deck.pptx",
  "totalSlides": 20,
  "uploadedAt": "2026-02-16T10:30:00Z",
  "slides": [
    {
      "index": 0,
      "title": "Executive Summary",
      "subtitle": "Q4 Strategic Initiative",
      "bodyText": "Full extracted text content...",
      "notes": "Speaker notes if present...",
      "hasChart": true,
      "hasTable": false,
      "thumbnailUrl": "/api/slides/deck_abc123/thumb/0.png"
    }
  ]
}
```

### 4.2 Phase 2: Live Boardroom Session

#### 4.2.1 Video Conference UI Layout

The interface mimics a familiar video conference layout. The presenter's webcam feed occupies one tile (highlighted with a blue ring). Four AI agent tiles display avatars, names, titles, and role badges. Active speaker detection highlights the current speaker's tile with a glow effect and audio waveform animation. A slide viewer panel shows the current slide with navigation controls. A chat panel on the right displays all agent messages with timestamps. A top bar shows session timer, interaction mode indicator, recording status, and "End Session" button.

#### 4.2.2 Presenter Capture Pipeline

```
Browser Mic → MediaRecorder API → Audio Chunks (WebM/Opus)
                                        │
                                        ├──→ WebSocket → STT Service → Transcript Segments
                                        │
                                        └──→ Local Recording Buffer → Session Recording

Browser Camera → MediaStream → Video Element (self-view)
                                        │
                                        └──→ MediaRecorder → Video Chunks → Session Recording
```

Audio capture requirements: sample rate of 16kHz minimum (48kHz preferred), WebM/Opus codec, chunk interval of 250ms for real-time streaming, echo cancellation enabled, noise suppression enabled.

Video capture requirements: 720p minimum resolution, 30fps, WebM/VP9 codec, picture-in-picture support.

#### 4.2.3 Real-Time Transcription Pipeline

Audio chunks stream to the STT service via WebSocket. The STT service returns interim (partial) and final transcript segments. Each segment includes: text content, timestamp (relative to session start), confidence score, and word-level timing. Segments are appended to the running transcript and forwarded to the Agent Engine.

Transcript Segment Schema:
```json
{
  "type": "final",
  "text": "Our total addressable market is estimated at 4.2 billion dollars by 2027",
  "startTime": 125.4,
  "endTime": 131.2,
  "confidence": 0.94,
  "words": [
    { "word": "Our", "start": 125.4, "end": 125.6, "confidence": 0.98 },
    { "word": "total", "start": 125.7, "end": 126.0, "confidence": 0.97 }
  ]
}
```

#### 4.2.4 Agent Engine — Orchestration Logic

The Agent Engine is the core intelligence layer. It operates as follows:

**Context Assembly:** For each agent turn, the engine assembles a context payload containing the agent's system prompt (persona, role, intensity), the full slide manifest (deck structure and content), the current slide index and content, the running transcript of the presentation so far, previous questions asked by all agents (to avoid repetition), the selected focus areas, and the session elapsed time.

**Moderator Orchestration Logic:**

```
ON slide_change:
  IF interaction_mode == "section":
    queue_moderator_announcement("Let's pause for questions on this section.")
    select_next_agent_to_speak()
  IF interaction_mode == "hand-raise":
    evaluate_agent_question_urgency()
    IF urgency > threshold:
      raise_agent_hand(agent_id)
      queue_moderator_announcement("{agent.name} has a question.")
  IF interaction_mode == "free-flow":
    pass  // agents self-trigger

ON transcript_segment(segment):
  update_running_context(segment)
  FOR each agent IN [skeptic, analyst, contrarian]:
    evaluate_question_readiness(agent, context)
    IF should_ask_question(agent):
      IF interaction_mode == "free-flow":
        queue_agent_question(agent)
      ELSE:
        add_to_pending_queue(agent)

ON timer_check (every 30 seconds):
  IF no_questions_in_last_3_minutes AND session_not_ending:
    moderator_prompt_engagement()
  IF session_time > estimated_duration * 0.8:
    moderator_time_warning()
```

**Agent Question Generation:**

Each agent call uses the Claude API with a structured system prompt:

```
System prompt for The Skeptic (Marcus Webb):
- You are Marcus Webb, CFO. You are in a boardroom presentation.
- Your role: challenge financial viability, question ROI assumptions, push back on feasibility.
- Intensity: {intensity_level}
- Focus areas requested by presenter: {focus_areas}
- Current slide: {slide_content}
- Presentation transcript so far: {transcript}
- Questions already asked this session: {previous_questions}
- Guidelines: Ask ONE focused question. Reference specific claims or data from the presentation.
  Be direct but professional. Do not repeat questions already asked. Stay in character.
```

**Question Timing Parameters:**

| Interaction Mode | Min Gap Between Questions | Max Queue Size | Moderator Interjection Rate |
|-----------------|--------------------------|----------------|----------------------------|
| Section Breaks | 0s (batch at section end) | 3 per section | Every section break |
| Hand Raise | 15s | 2 pending hands | When hands are raised |
| Free Flow | 20s | 1 (immediate) | Every 2-3 minutes |

#### 4.2.5 Text-to-Speech Delivery

Each agent has a unique ElevenLabs voice profile. Voice assignments: Diana Chen (Moderator) uses a warm, professional female voice; Marcus Webb (Skeptic) uses a deep, authoritative male voice; Priya Sharma (Analyst) uses a clear, measured female voice; James O'Brien (Contrarian) uses a gravelly, deliberate male voice. Audio is streamed back to the client and played through the respective agent's tile. During playback, the agent's tile shows a speaking animation (waveform bars, glow effect). Other agents' tiles dim slightly to indicate they are listening.

#### 4.2.6 Session State Machine

```
IDLE → CONFIGURING → READY → PRESENTING → Q_AND_A → PRESENTING → ... → ENDING → COMPLETE
                                   │                      ▲
                                   └──────────────────────┘
                                   (cycles per slide/section)
```

States: IDLE (no active session), CONFIGURING (setup phase in progress), READY (setup complete, waiting for presenter to begin), PRESENTING (presenter is speaking, agents are listening), Q_AND_A (agents are asking questions, presenter is responding), ENDING (presenter clicked End Session, final moderator wrap-up), COMPLETE (session ended, generating debrief).

### 4.3 Phase 3: Post-Session Debrief

#### 4.3.1 Scoring Model

The scoring engine analyzes the full session data (transcript, timing, slide content, agent interactions) to produce scores across six dimensions.

| Dimension | Weight | Signals |
|-----------|--------|---------|
| Overall | — | Weighted composite of all dimensions |
| Clarity | 20% | Sentence complexity, filler word frequency, topic coherence per slide |
| Confidence | 20% | Hesitation patterns, response latency to questions, hedging language |
| Data Support | 20% | Specificity of claims, use of numbers/evidence, citation of sources |
| Q&A Handling | 25% | Directness of answers, whether questions were fully addressed, recovery from difficult questions |
| Structure | 15% | Logical flow, time distribution across slides, transition quality |

Filler words tracked: "um", "uh", "like", "you know", "basically", "actually", "sort of", "kind of", "I mean", "right".

Hedging language tracked: "I think", "maybe", "probably", "I guess", "hopefully", "we'll see", "it depends".

#### 4.3.2 Debrief Tabs

**Summary Tab:** Overall score with radial progress indicator, category score bars, top 4 strengths with specific examples, and Moderator's narrative summary (generated by Claude with full session context).

**Transcript Tab:** Full transcript with speaker labels (color-coded), timestamps, and role indicators. Searchable and filterable by speaker. Copy-all functionality. Exportable as TXT or DOCX.

**Scores Tab:** Individual score cards for each dimension. Score bars with color coding (green above 80, amber 70-79, red below 70). Comparison against previous session scores (if available).

**Coaching Tab:** Prioritized improvement areas ranked by impact (High, Medium, Low). Each item includes the area name, priority level, specific detail explaining what happened and what to do differently, and a timestamp reference to the relevant moment in the session. Generated by Claude analyzing the full session with coaching-specific system prompt.

#### 4.3.3 Moderator's Summary Generation

The Moderator's post-session summary is generated via a dedicated Claude API call with the following context: full transcript, all agent questions and presenter responses, scoring results, slide content, session configuration, and (if available) comparison to previous sessions. The summary should be 150-250 words, written in first person as Diana Chen, covering overall impression, biggest strength, most critical area for improvement, one specific tactical recommendation, and encouragement/next steps.

#### 4.3.4 Report Export

PDF report includes: session metadata (date, duration, configuration), overall and dimension scores, strengths and improvement areas, full transcript, and Moderator's summary. Generated server-side using Puppeteer or a PDF library. Downloadable from the debrief screen.

---

## 5. AI Agent Specifications

### 5.1 Agent Persona Definitions

#### Diana Chen — The Moderator

| Attribute | Value |
|-----------|-------|
| Role | Meeting Chair / Orchestrator |
| Title | Chief of Staff |
| Personality | Professional, warm but efficient. Keeps the meeting on track. |
| Primary Function | Manages turn-taking, pacing, transitions, and overall session flow |
| Questioning Style | Does not ask adversarial questions. Asks clarifying questions, facilitates transitions, and prompts the presenter to elaborate when responses are too brief. |
| Interaction Patterns | Opens the session with a brief welcome. Announces Q&A windows. Calls on agents by name. Provides time warnings. Closes the session with a brief wrap-up. |
| Voice Characteristics | Warm, professional, moderate pace, clear enunciation |

#### Marcus Webb — The Skeptic

| Attribute | Value |
|-----------|-------|
| Role | Financial/Feasibility Challenger |
| Title | CFO |
| Personality | Experienced, direct, slightly impatient. Has seen many pitches fail. |
| Primary Function | Challenges financial projections, ROI claims, and overall feasibility |
| Questioning Style | "What's your contingency if...?", "What evidence supports...?", "I've seen this before and..." |
| Focus Triggers | Revenue projections, margin assumptions, burn rate, unit economics, payback period, competitive pricing |
| Intensity Scaling | Friendly: "Can you help me understand...?" Moderate: "I'm not convinced that..." Adversarial: "These numbers don't hold up. Show me..." |
| Voice Characteristics | Deep, authoritative, measured pace, occasional skeptical tone |

#### Priya Sharma — The Analyst

| Attribute | Value |
|-----------|-------|
| Role | Data & Methodology Deep-Diver |
| Title | VP of Strategy |
| Personality | Thorough, methodical, genuinely curious. Wants to understand the details. |
| Primary Function | Requests supporting data, questions methodology, validates analytical rigor |
| Questioning Style | "Walk me through the methodology for...", "What's the sample size?", "Can you show the sensitivity analysis?" |
| Focus Triggers | Data sources, sample sizes, confidence intervals, methodology, benchmarks, comparable analysis, sensitivity analysis |
| Intensity Scaling | Friendly: "I'd love to see more detail on..." Moderate: "The data here is thin. Can you..." Adversarial: "This analysis is insufficient. Where's the..." |
| Voice Characteristics | Clear, measured, slightly formal, precise word choice |

#### James O'Brien — The Contrarian

| Attribute | Value |
|-----------|-------|
| Role | Logic & Assumption Challenger |
| Title | Board Advisor |
| Personality | Experienced, philosophical, enjoys poking holes. Plays devil's advocate deliberately. |
| Primary Function | Identifies logical gaps, contradictions, and unexplored worst-case scenarios |
| Questioning Style | "What if the opposite is true?", "You're assuming X but what if...?", "Walk me through the failure scenario" |
| Focus Triggers | Unstated assumptions, logical dependencies, single points of failure, market timing risks, competitive responses, behavioral change assumptions |
| Intensity Scaling | Friendly: "Have you considered what happens if...?" Moderate: "There's a tension here between X and Y..." Adversarial: "This entire thesis collapses if..." |
| Voice Characteristics | Gravelly, deliberate pace, thoughtful pauses, occasionally provocative |

### 5.2 Agent Coordination Rules

- No two agents should ask questions about the same specific claim simultaneously
- The Moderator tracks which topics have been covered and steers agents toward uncovered areas
- If the presenter gives an unsatisfactory answer, the same agent may follow up once before the Moderator moves on
- Agents should reference each other's questions when relevant ("Building on what Marcus asked...")
- The Contrarian should not repeat the Skeptic's concerns — they challenge logic, not numbers
- Total agent speaking time should not exceed 40% of the session; the presenter should speak at least 60%

### 5.3 Context Window Management

For sessions longer than 20 minutes, the full transcript will exceed typical context windows. The Agent Engine implements a sliding context strategy: always include the full slide manifest (relatively small), always include the current slide and adjacent slides in full, summarize earlier transcript sections (compress to key claims and responses), keep the last 5 minutes of transcript in full, and maintain a "key claims" list extracted from the full transcript. This ensures agents remain contextually aware without hitting token limits.

---

## 6. Data Models

### 6.1 User

```json
{
  "id": "user_abc123",
  "email": "exec@company.com",
  "name": "Sarah Johnson",
  "company": "Acme Corp",
  "title": "VP of Product",
  "plan": "pro",
  "createdAt": "2026-01-15T08:00:00Z",
  "sessionCount": 12,
  "averageScore": 76
}
```

### 6.2 Session

```json
{
  "id": "session_xyz789",
  "userId": "user_abc123",
  "deckId": "deck_abc123",
  "status": "complete",
  "config": {
    "interactionMode": "hand-raise",
    "intensity": "moderate",
    "focusAreas": ["Financial Projections", "Competitive Analysis"],
    "estimatedDuration": 20
  },
  "startedAt": "2026-02-16T14:00:00Z",
  "endedAt": "2026-02-16T14:23:45Z",
  "duration": 1425,
  "slideCount": 20,
  "totalQuestions": 14,
  "scores": {
    "overall": 78,
    "clarity": 82,
    "confidence": 71,
    "dataSupport": 85,
    "handling": 68,
    "structure": 80
  },
  "recordingUrl": "https://storage.highstake.app/recordings/session_xyz789.webm",
  "transcriptUrl": "https://storage.highstake.app/transcripts/session_xyz789.json",
  "reportUrl": "https://storage.highstake.app/reports/session_xyz789.pdf"
}
```

### 6.3 Transcript Entry

```json
{
  "sessionId": "session_xyz789",
  "index": 42,
  "speaker": "presenter",
  "speakerName": "Sarah Johnson",
  "text": "Our customer acquisition cost is currently $45, which we expect to decrease to $28 as we scale the self-serve channel.",
  "startTime": 342.5,
  "endTime": 349.8,
  "slideIndex": 3,
  "type": "presentation"
}
```

```json
{
  "sessionId": "session_xyz789",
  "index": 43,
  "speaker": "agent_skeptic",
  "speakerName": "Marcus Webb",
  "agentRole": "The Skeptic",
  "text": "That's a 38% reduction in CAC. What's driving that decrease specifically, and how does it compare to industry benchmarks?",
  "startTime": 351.2,
  "endTime": 357.0,
  "slideIndex": 3,
  "type": "question",
  "triggerClaim": "CAC decrease from $45 to $28"
}
```

### 6.4 Debrief Coaching Item

```json
{
  "sessionId": "session_xyz789",
  "area": "Q&A Handling",
  "priority": "high",
  "detail": "When Marcus challenged your CAC projections at 5:42, you repeated the same $45→$28 figure without providing additional evidence. Prepare 2-3 supporting data points: industry benchmarks, historical trends from comparable companies, or channel-specific CAC breakdowns.",
  "transcriptRef": {
    "startIndex": 42,
    "endIndex": 45,
    "timestamp": 342.5
  }
}
```

---

## 7. API Contracts

### 7.1 REST Endpoints

```
POST   /api/sessions                  Create a new session with configuration
GET    /api/sessions/:id              Get session details and status
PATCH  /api/sessions/:id              Update session (end session, update config)
DELETE /api/sessions/:id              Delete a session and associated data

POST   /api/decks/upload              Upload and parse a presentation deck
GET    /api/decks/:id                 Get deck manifest
GET    /api/decks/:id/slides/:index   Get slide thumbnail image

GET    /api/sessions/:id/transcript   Get full session transcript
GET    /api/sessions/:id/debrief      Get debrief data (scores, coaching, summary)
GET    /api/sessions/:id/recording    Get recording URL (signed, time-limited)
GET    /api/sessions/:id/report       Download PDF report

GET    /api/users/me                  Get current user profile
GET    /api/users/me/sessions         List user's session history
GET    /api/users/me/stats            Get aggregate stats (avg score, trends)
```

### 7.2 WebSocket Events

```
Client → Server:
  audio_chunk        { data: ArrayBuffer, timestamp: number }
  slide_change       { slideIndex: number }
  presenter_response { text: string }
  end_session        {}

Server → Client:
  transcript_segment { text, startTime, endTime, confidence, isFinal }
  agent_question     { agentId, text, audioUrl?, slideRef? }
  agent_hand_raise   { agentId }
  moderator_message  { text, audioUrl? }
  session_state      { state: "presenting" | "q_and_a" | "ending" }
  time_warning       { remainingMinutes: number }
  session_ended      { debriefUrl: string }
```

---

## 8. Non-Functional Requirements

### 8.1 Performance

| Metric | Target | Critical Threshold |
|--------|--------|--------------------|
| STT Latency | < 500ms from speech to transcript | < 1000ms |
| Agent Response Time | < 3s from trigger to text response | < 5s |
| TTS Latency | < 1s from text to audio playback start | < 2s |
| Deck Parsing | < 10s for a 20-slide PPTX | < 30s |
| UI Frame Rate | 60fps during session | 30fps minimum |
| Page Load | < 2s initial load | < 4s |
| Recording Start | < 500ms from session start | < 1s |

### 8.2 Scalability

- Support 100 concurrent sessions at launch
- Scale to 1,000 concurrent sessions within 6 months
- Each session consumes approximately 1 WebSocket connection, 1 STT stream, and intermittent LLM/TTS API calls
- Deck storage: plan for 10GB per 1,000 users
- Recording storage: plan for 500MB per session (20-minute session at 720p)

### 8.3 Reliability

- 99.9% uptime for the web application
- Graceful degradation: if TTS fails, fall back to text-only agent responses
- Graceful degradation: if STT fails, allow manual transcript input or slide-triggered questions
- Auto-save session state every 30 seconds to prevent data loss
- Recording buffer: maintain 60 seconds of local buffer before upload

### 8.4 Security & Privacy

- All data encrypted at rest (AES-256) and in transit (TLS 1.3)
- Presentation decks are private to the uploading user by default
- Session recordings are stored with signed, time-limited access URLs
- No presentation content is used for AI model training
- SOC 2 Type II compliance target within 12 months of launch
- GDPR-compliant data handling with right to deletion
- User can delete all session data (recordings, transcripts, decks) at any time
- Audio/video processing happens server-side; no third-party access to raw recordings beyond STT/TTS providers

### 8.5 Browser Support

- Chrome 100+ (primary)
- Firefox 100+ (secondary)
- Safari 16+ (secondary)
- Edge 100+ (secondary)
- Mobile browsers: responsive design for review/debrief, but live session requires desktop

### 8.6 Accessibility

- WCAG 2.1 AA compliance for all non-session UI
- Keyboard navigation for setup and debrief phases
- Screen reader support for transcript and debrief content
- High contrast mode option
- Closed captions for agent audio responses during session

---

## 9. Phased Delivery Plan

### Phase 1 — MVP (Current)

**Goal:** Validate the core experience with a functional prototype.

Deliverables:
- Moderator-led setup flow (interaction mode, intensity, focus areas, deck upload)
- Video-call-style meeting UI with 4 agent tiles and presenter tile
- Simulated agent questions triggered by slide advancement
- Slide viewer with navigation
- Chat panel with timestamped agent messages
- Post-session debrief with scores, transcript, coaching, and summary
- Demo deck mode for testing without upload

Status: Complete (frontend prototype). Agents use pre-written questions. No real STT/TTS/LLM integration yet.

### Phase 2 — Core Intelligence

**Goal:** Replace simulated behavior with real AI-powered interactions.

Deliverables:
- Real-time speech-to-text via Deepgram streaming API
- Claude API integration for dynamic, contextual agent questions
- Agent orchestration engine with Moderator coordination logic
- PPTX/PDF parsing with python-pptx and PyMuPDF
- Webcam capture and session recording via MediaRecorder API
- Text-to-speech for agent responses via ElevenLabs
- Dynamic scoring engine based on actual transcript analysis
- Post-session coaching generated by Claude with full session context

Estimated Timeline: 8-10 weeks.

### Phase 3 — Polish & Scale

**Goal:** Production-grade experience with enterprise features.

Deliverables:
- Session recording playback with timeline scrubbing and moment-jumping
- Multi-session dashboard with improvement tracking and trend charts
- PDF report generation and export
- User accounts with authentication (Clerk/Auth0)
- Team/organization accounts with shared session libraries
- Custom agent personas (user-defined panel members)
- Presentation template library (common deck structures)
- Mobile-responsive debrief and dashboard (session remains desktop-only)

Estimated Timeline: 10-14 weeks.

### Phase 4 — Enterprise & Growth

**Goal:** Enterprise readiness and market expansion.

Deliverables:
- SSO integration (SAML/OIDC) for enterprise clients
- Admin dashboard for team managers (view team scores, assign practice sessions)
- API for LMS/training platform integration
- Custom branding (white-label option)
- Advanced analytics (speaking pace over time, vocabulary complexity, emotional tone)
- AI-generated "challenge playbook" based on deck content (pre-session prep tool)
- Integration with calendar apps (schedule practice sessions)
- Benchmark data ("presenters at your level typically score X on this dimension")
- SOC 2 Type II certification
- Multi-language support (English first, then Mandarin, Spanish, Japanese, German)

Estimated Timeline: 12-16 weeks.

---

## 10. Success Metrics

### 10.1 Product Metrics

| Metric | Phase 1 Target | Phase 2 Target | Phase 3 Target |
|--------|----------------|----------------|----------------|
| Session Completion Rate | 70% | 80% | 85% |
| Avg Session Duration | 10min | 18min | 22min |
| Repeat Usage (2+ sessions) | 30% | 50% | 65% |
| Debrief Engagement (all tabs viewed) | 40% | 55% | 70% |
| NPS Score | — | 40+ | 55+ |

### 10.2 Technical Metrics

| Metric | Target |
|--------|--------|
| STT Accuracy | > 95% word error rate |
| Agent Question Relevance | > 85% rated "relevant" by users |
| Session Recording Success Rate | > 99% |
| P95 Agent Response Latency | < 4s |
| System Uptime | 99.9% |

### 10.3 Business Metrics (Post-Launch)

| Metric | 6-Month Target | 12-Month Target |
|--------|----------------|-----------------|
| Monthly Active Users | 500 | 5,000 |
| Paying Customers | 50 | 500 |
| Monthly Recurring Revenue | $5K | $75K |
| Enterprise Accounts | 2 | 15 |

---

## 11. Open Questions & Decisions

| # | Question | Options | Status |
|---|----------|---------|--------|
| 1 | Should agents have persistent memory across sessions for the same deck? | A) No, each session is independent. B) Yes, agents remember what was discussed in prior sessions and push on unresolved issues. | Open |
| 2 | Should we support real-time video analysis (facial expressions, body language)? | A) Phase 3 — adds significant value for delivery coaching. B) Out of scope — too complex and privacy-sensitive. | Open |
| 3 | What is the pricing model? | A) Freemium (3 sessions/month free, $49/mo Pro). B) Flat subscription ($29/mo individual, $199/mo team). C) Per-session pricing ($5/session). | Open |
| 4 | Should we allow users to customize or create their own agent personas? | A) Phase 3 feature. B) Out of scope — the fixed panel is the product. | Leaning A |
| 5 | Should the app support collaborative sessions (multiple human presenters or observers)? | A) Phase 4 — useful for team presentations. B) Out of scope — single presenter focus. | Open |
| 6 | Which LLM provider for agent intelligence? | A) Anthropic Claude (strong reasoning, long context). B) OpenAI GPT-4 (widely available). C) Support both, user chooses. | Leaning A |
| 7 | Should we build a mobile app or stay web-only? | A) Web-only for sessions, responsive for debrief. B) Native iOS/Android app for everything. | Leaning A |
| 8 | How should we handle presenter responses to agent questions — voice only or also text input? | A) Voice only (most realistic). B) Voice primary with text fallback. C) Both equally supported. | Leaning B |

---

## 12. Appendix

### A. Competitive Landscape

| Competitor | Approach | HighStake Differentiation |
|-----------|----------|---------------------------|
| Pitch practice with colleagues | Manual scheduling, social dynamics, lack of adversarial depth | AI agents available on-demand, no social friction, configurable intensity |
| Executive coaches | $500-2000/session, scheduling required, single perspective | Fraction of the cost, instant availability, multi-perspective panel |
| Presentation AI tools (e.g., Yoodli, Poised) | Focus on delivery metrics (filler words, pace) only | Full boardroom simulation with contextual Q&A, not just delivery metrics |
| VR presentation simulators | Audience simulation without intelligent interaction | Intelligent, adversarial questioning grounded in presentation content |

### B. Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM API latency too high for real-time interaction | High | Medium | Implement question pre-generation, fall back to text-only if TTS delayed |
| STT accuracy insufficient for real-time context | High | Low | Use Deepgram Nova-2 (industry-leading accuracy), implement correction UI |
| Context window overflow for long sessions | Medium | High | Implement sliding context strategy with summarization (see section 5.3) |
| User audio quality varies widely | Medium | High | Implement audio quality check at session start, provide recommendations |
| Enterprise security requirements block adoption | High | Medium | Prioritize SOC 2, offer on-premise deployment option in Phase 4 |
| ElevenLabs rate limits during high usage | Medium | Medium | Implement TTS caching, pre-generate common moderator phrases, queue system |
