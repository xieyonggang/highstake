# HighStake — Product Requirements Document

**Version:** 3.1
**Last Updated:** February 19, 2026
**Status:** Active Development
**North Star:** Every session should feel indistinguishable from a real boardroom — zero awkward silences, contextually sharp questions, natural multi-turn exchanges, and seamless flow between challenge and presentation.
**Key Architecture Principle:** Agent personas are immutable templates; each session spawns isolated, session-scoped context folders that accumulate live intelligence. The character never changes — only what they know grows.

---

## Table of Contents

1. [Vision & Problem Statement](#1-vision--problem-statement)
2. [User Stories & Personas](#2-user-stories--personas)
3. [System Architecture](#3-system-architecture)
4. [Real-Time Architecture: Eliminating the Latency Gap](#4-real-time-architecture-eliminating-the-latency-gap)
5. [Session-Scoped Agent Context System](#5-session-scoped-agent-context-system)
6. [Context Stack Architecture](#6-context-stack-architecture)
7. [Multi-Turn Exchange System](#7-multi-turn-exchange-system)
8. [Feature Specifications](#8-feature-specifications)
9. [AI Agent Specifications](#9-ai-agent-specifications)
10. [Data Models](#10-data-models)
11. [API Contracts](#11-api-contracts)
12. [Non-Functional Requirements](#12-non-functional-requirements)
13. [Phased Delivery Plan](#13-phased-delivery-plan)
14. [Success Metrics](#14-success-metrics)
15. [Open Questions & Decisions](#15-open-questions--decisions)
16. [Appendix](#16-appendix)

---

## 1. Vision & Problem Statement

### 1.1 Problem

Executives preparing for high-stakes presentations — board meetings, investor pitches, strategic reviews, M&A proposals — have limited options for realistic rehearsal. They can practice alone (no feedback), present to colleagues (scheduling friction, social dynamics, pulled punches), or hire presentation coaches (expensive, not always domain-savvy). None of these options simulate the adversarial, multi-perspective questioning that defines a real boardroom.

Beyond the availability problem, there is a **realism problem**. Existing AI presentation tools focus narrowly on delivery metrics (filler words, pacing) without simulating the conversational dynamics of a real boardroom — the cross-examination, the follow-up questions, the panelist who builds on a colleague's challenge, the moment where your weakest slide gets exposed by someone who actually read the footnotes and checked last week's news. That dynamic is what HighStake must replicate.

### 1.2 Vision

HighStake is an AI-powered virtual boardroom that lets executives upload their presentation deck, deliver it via webcam and microphone in a realistic video-call environment, and face real-time questions from a panel of AI agents — each with a distinct persona, questioning style, and strategic lens.

The agents don't just ask generic questions — they draw from the deck content, the presenter's live speech, each other's prior challenges, deep domain expertise, and recent real-world news to produce the kind of sharp, contextual scrutiny that only a well-prepared board member could deliver.

When a panelist challenges you, the exchange doesn't end with one question — the agent evaluates your answer, follows up if it's insufficient, and escalates if you're deflecting, just like a real CFO would. The Moderator manages the rhythm, knows when to let the exchange run and when to bring the room back on track.

After the session, the presenter receives a detailed debrief with scores, transcript, and prioritized coaching advice.

The goal is to make every executive feel like they've already survived the hardest version of their presentation before they walk into the real room.

### 1.3 Target Users

**Primary:** C-suite executives, VPs, and senior directors preparing for board presentations, investor meetings, strategic reviews, or internal leadership pitches.

**Secondary:** Startup founders preparing for fundraising pitches, corporate executive leaders rehearsing enterprise deal presentations, consultants preparing client deliverables, and MBA students practicing case presentations.

### 1.4 Key Value Propositions

- Realistic simulation of multi-stakeholder scrutiny without scheduling real people
- AI agents that challenge from distinct strategic perspectives (financial, analytical, adversarial)
- Natural multi-turn exchanges where agents follow up, push back, and escalate — not one-shot Q&A
- A Moderator agent that manages session flow, mediates exchanges, and bridges back to the presentation
- Context-aware questioning powered by deck content, live transcript, panel memory, domain knowledge, and real-world news
- Near-zero perceived latency — agent responses that maintain natural conversational rhythm with no awkward silences
- Immediate, structured feedback with actionable coaching — not just "you did well"
- Repeatable practice sessions with improvement tracking over time
- On-demand availability — practice at 11pm the night before if needed

### 1.5 Design Principles

These principles govern every technical and UX decision in HighStake:

1. **Natural rhythm above all.** A 3-second silence after the Moderator says "Marcus, go ahead" destroys immersion. Every architecture decision must minimize perceived latency. If we can't make it fast, we make it feel natural.

2. **Context is king.** Generic questions are worthless. Every agent question must demonstrate awareness of the specific deck, what the presenter actually said, what the panel has already discussed, what the industry data shows, and what's happening in the world right now.

3. **Conversations, not interrogations.** Agent questions should trigger natural multi-turn exchanges. The agent evaluates the answer, follows up if needed, and the Moderator manages the flow — just like a real boardroom. One-shot questions feel robotic.

4. **The panel is a team, not four isolated bots.** Agents must reference each other, build on prior challenges, and avoid redundancy. The Contrarian should never repeat the Skeptic's concern — they should extend it.

5. **Presenter control, always.** The presenter chooses the rules of engagement. The system adapts to them, not the other way around.

6. **Fail gracefully, never silently.** If a service degrades (TTS fails, search is slow), the experience adapts smoothly — the user should never see a loading spinner in the middle of a boardroom conversation.

7. **Human-level realism.** Agents must exhibit the imperfections, emotional dynamics, and social behaviors of real humans — not the polished, turn-based perfection of chatbots. See [FEATURE_HUMAN_BEHAVIORAL_REALISM.md](FEATURE_HUMAN_BEHAVIORAL_REALISM.md) for the complete 7-dimension realism system.

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

**US-2: Deck Upload, Parsing & Enrichment**
As a presenter, I want to upload my slide deck and have the AI agents deeply understand its content — including how it relates to real-world market conditions — so their questions are contextually devastating.

Acceptance Criteria:
- Supports PPTX and PDF file formats
- Extracts text, titles, structure, speaker notes, chart data, and table data from each slide
- Identifies key claims, projections, and assumptions per slide
- Runs external enrichment pipeline: extracts entities and topics, searches for recent news, market data, and competitive intelligence
- Generates a "Board Preparation Dossier" summarizing what a well-prepared panel would know
- Optionally shows the Dossier to the presenter as a preview before the session
- Renders slides in a viewer the presenter can navigate during the session
- Supports decks up to 100 slides and 50MB file size
- Full parsing + enrichment completes within 30 seconds for a typical 20-slide deck

**US-3: Live Presentation with Natural Conversational Flow**
As a presenter, I want to deliver my presentation in a realistic video-call environment where AI panelists don't just ask one question and stop — they actually engage in back-and-forth dialogue based on my answers, just like real board members.

Acceptance Criteria:
- Presenter sees their own webcam feed in a video tile
- 4 AI agent tiles are displayed with names, titles, and role indicators
- Presenter can navigate slides while presenting
- Audio is captured via microphone and transcribed in real-time
- AI agents ask questions based on the full context stack (deck + transcript + panel memory + domain knowledge + external intelligence)
- When the presenter answers, the questioning agent evaluates the response and can follow up naturally (2-4 turn exchanges)
- The Moderator manages exchange length, prevents runaway dialogues, and bridges back to the presentation seamlessly
- Agent responses begin within 1.5 seconds of being triggered — no awkward silences
- Agents speak with distinct, natural voices via Gemini Live streaming TTS
- Session timer is visible throughout
- Presenter can mute/unmute and toggle camera
- Entire session (audio, video, slides, agent interactions) is recorded

**US-4: Agent Questioning with Full Context**
As a presenter, I want each AI agent to ask questions informed by everything a real board member would know — my slides, what I've said, what other panelists have asked, industry benchmarks, and recent news — so I'm genuinely pressure-tested.

Acceptance Criteria:
- The Skeptic challenges financial viability using deck projections cross-referenced with industry benchmarks and recent market data
- The Analyst requests specific data sources and methodology, referencing what comparable companies have disclosed
- The Contrarian identifies logical gaps by connecting assumptions across different slides and testing them against real-world precedents
- The Moderator steers agents toward uncovered topics and unresolved challenges from earlier in the session
- Agents reference each other's questions ("Building on what Marcus asked about margins...")
- Agents reference specific data points, claims, or slides in their questions
- Agents reference recent real-world events when relevant ("Given last week's Fed decision, how does that affect your rate assumptions?")
- Question difficulty scales with the selected intensity level
- Each agent maintains a consistent persona voice throughout the session
- No two agents ask about the same specific claim simultaneously

**US-5: Post-Session Debrief**
As a presenter, I want a comprehensive debrief after my session so I know exactly what to improve before the real presentation.

Acceptance Criteria:
- Overall presentation score (0-100) with category breakdowns
- Moderator's narrative summary of the session
- Full searchable transcript with speaker labels and timestamps
- Prioritized list of improvement areas with specific, actionable advice referencing exact moments in the session
- Identified strengths with specific examples from the session
- "Unresolved challenges" section — questions the presenter deflected, answered weakly, or where the agent was explicitly not satisfied
- Exchange analysis — how well the presenter handled multi-turn pushback
- Session recording available for playback
- Debrief exportable as PDF report
- Comparison with previous sessions (if applicable)

**US-6: Session Recording & Playback**
As a presenter, I want to watch a recording of my session so I can see my own delivery and the AI panel's reactions.

Acceptance Criteria:
- Records presenter webcam video and audio
- Records slide progression with timestamps
- Records all agent questions, exchanges, and responses with timestamps
- Playback interface with timeline scrubbing
- Ability to jump to specific moments (slide changes, agent questions, exchange starts)
- Downloadable as MP4 or WebM

**US-7: Multi-Session Tracking**
As a presenter, I want to track my improvement across multiple practice sessions so I can see my progress over time.

Acceptance Criteria:
- Dashboard showing session history with dates, scores, and durations
- Score trend charts across sessions
- Recurring weakness identification (issues that persist across sessions)
- Improvement highlights (areas that have gotten better)
- Exchange handling improvement tracking (how well you handle follow-ups over time)
- Ability to re-run a session with the same configuration

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           CLIENT (Browser)                                │
│                                                                          │
│  ┌──────────┐  ┌───────────────┐  ┌──────────┐  ┌───────────────┐      │
│  │  Setup    │→ │  Live Meeting  │→ │  Review   │  │  Dashboard    │      │
│  │  Phase    │  │  Phase         │  │  Phase    │  │  (History)    │      │
│  └──────────┘  └───────────────┘  └──────────┘  └───────────────┘      │
│                  ┌──────┴───────┐                                        │
│                  │ WebRTC Media  │                                        │
│                  │ ┌───┐ ┌────┐ │                                        │
│                  │ │Cam│ │Mic │ │                                        │
│                  │ └───┘ └──┬─┘ │                                        │
│                  │  Audio   │   │                                        │
│                  │  Playback│   │                                        │
│                  │  Engine  │   │                                        │
│                  └──────┬───┘   │                                        │
└─────────────────────────┼───────┼────────────────────────────────────────┘
                          │       │
                          ▼       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION SERVER                                 │
│                   (WebSocket + REST Gateway)                              │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                    SESSION ORCHESTRATOR                          │     │
│  │                                                                 │     │
│  │  ┌──────────────┐  ┌────────────────┐  ┌───────────────────┐   │     │
│  │  │  Session      │  │  Pre-Generation │  │  Context          │   │     │
│  │  │  State        │  │  Pipeline       │  │  Assembler        │   │     │
│  │  │  Machine      │  │  (Background)   │  │  (5-Layer Stack)  │   │     │
│  │  └──────────────┘  └────────────────┘  └───────────────────┘   │     │
│  │                                                                 │     │
│  │  ┌──────────────┐  ┌────────────────┐  ┌───────────────────┐   │     │
│  │  │  Exchange     │  │  Question      │  │  Latency          │   │     │
│  │  │  Manager      │  │  Buffer Pool   │  │  Compensator      │   │     │
│  │  │  (Multi-Turn) │  │  (Pre-gen'd)   │  │  (Fillers/Stall)  │   │     │
│  │  └──────────────┘  └────────────────┘  └───────────────────┘   │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                          │
└──────┬──────────┬──────────┬──────────┬──────────┬───────────────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
│  Deck    │ │Gemini  │ │Gemini  │ │Gemini  │ │  Session   │
│  Parser  │ │Live API│ │ LLM    │ │ Live   │ │  Storage   │
│  +       │ │(STT)   │ │(Agent  │ │ (TTS)  │ │            │
│  Context │ │        │ │ Intel) │ │        │ │ PostgreSQL │
│  Enricher│ │        │ │        │ │        │ │ S3/R2      │
└──────────┘ └────────┘ └────────┘ └────────┘ └────────────┘
       │
       ▼
┌──────────┐
│  Web     │
│  Search  │
│  API     │
│(Enrichmt)│
└──────────┘
```

### 3.2 Core Services

**Deck Parser + Context Enrichment Service** — Accepts PPTX/PDF uploads, extracts text, structure, speaker notes, chart data, and metadata from each slide. Extracts key entities, claims, and projections. Runs external web searches to build a real-world intelligence briefing. Generates a structured "Board Preparation Dossier." Renders slide thumbnails for the in-session viewer.

**Gemini Live API — Speech-to-Text Stream** — Captures presenter audio via browser MediaRecorder API. Streams audio to Gemini Live API for real-time transcription with low latency. Emits transcript segments (interim + final) to the Session Orchestrator. Maintains a running full transcript with word-level timestamps.

**Session Orchestrator (The Brain)** — The central coordination layer. Manages the session state machine (PRESENTING → Q&A_TRIGGER → EXCHANGE → RESOLVING → PRESENTING). Runs the pre-generation pipeline in background. Assembles the 5-layer context stack for each agent call. Manages the question buffer pool. Coordinates turn-taking, exchange flow, and timing. Operates the latency compensation system. Manages the Exchange Manager for multi-turn dialogues.

**Gemini LLM — Agent Intelligence** — Receives assembled context payloads from the Orchestrator. Generates agent questions, follow-up evaluations, and responses with streaming output. Each agent has a distinct system prompt defining persona, expertise, and questioning style. Supports streaming token output for chained TTS delivery.

**Gemini Live API — Text-to-Speech Stream** — Converts agent text responses to spoken audio using Gemini Live's native voice capabilities. Supports streaming input (tokens from LLM) → streaming output (audio chunks to client). Distinct voice profiles per agent. Streams audio back to the client for immediate playback.

**Session Storage Service** — Stores session configurations, transcripts, recordings, scores, and debrief data. Manages user accounts and session history. Handles recording uploads (video, audio) to object storage (S3/R2). Provides APIs for the dashboard and session playback.

### 3.3 Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 18 + Vite | Fast dev cycle, component architecture, hooks for real-time state |
| Styling | Tailwind CSS | Rapid UI development, consistent design system |
| State Management | Zustand or React Context | Lightweight, sufficient for session state |
| Backend | Python (FastAPI) | Native async, excellent Gemini SDK support, WebSocket support |
| AI / LLM | Google Gemini 2.0 Flash | Multimodal, streaming, low latency, native voice I/O via Live API |
| Speech-to-Text | Gemini Live API | Integrated STT with low latency, bidirectional streaming |
| Text-to-Speech | Gemini Live API | Native voice generation with streaming, distinct voice configs |
| Deck Parsing | python-pptx + PyMuPDF | Robust PPTX and PDF text extraction |
| External Intelligence | Google Search API / Tavily / Perplexity API | Real-time news and market data enrichment |
| Database | sqlite | Relational data for users, sessions, scores |
| Object Storage | AWS S3 or Cloudflare R2 | Recordings, uploaded decks, exported reports |
| Auth | Clerk or Auth0 | Quick integration, SSO support for enterprise |
| Hosting | Vercel (frontend) + Railway/Fly.io (backend) | Simple deployment, good WebSocket support |
| WebSocket | Native WebSocket via FastAPI | Real-time bidirectional communication for live session |

---

## 4. Real-Time Architecture: Eliminating the Latency Gap

### 4.1 The Problem

The most critical UX challenge in HighStake is the **latency gap** — the dead air between when the Moderator says "Marcus, go ahead" and when Marcus actually starts speaking. In a real boardroom, this gap is under 1 second. In a naive AI pipeline, it's 4-8 seconds:

```
NAIVE PIPELINE (Serial):
Presenter stops → STT finalizes (500ms) → LLM generates question (2-4s)
  → TTS generates audio (1-3s) → Agent speaks

Total: 4-8 seconds of dead air ← UNACCEPTABLE
```

HighStake's architecture must achieve **under 1.5 seconds perceived latency** from trigger to agent audio. This section defines how.

### 4.2 Solution: Three-Layer Latency Elimination

#### 4.2.1 Layer 1: Background Pre-Generation Pipeline

The core insight: **don't wait for the Moderator to call on an agent — start generating their questions while the presenter is still speaking.**

```
PRESENTER IS SPEAKING (Slide 3)
│
│  [Continuous background loop — every 15s or on significant transcript update]
│
├──→ Context Assembler builds fresh context payload
│     └──→ Gemini LLM call: Skeptic candidate question → text ready
│     └──→ Gemini LLM call: Analyst candidate question → text ready
│     └──→ Gemini LLM call: Contrarian candidate question → text ready
│
├──→ For each candidate question with text ready:
│     └──→ Gemini Live TTS: pre-generate audio → audio buffer ready
│
│  [All 3 agents now have question text + audio buffered and waiting]
│
PRESENTER PAUSES / CHANGES SLIDE
│
├──→ Moderator transition: "Marcus, go ahead." (plays immediately)
│     └──→ During Moderator speech (2-3 seconds):
│           └──→ Validate Marcus's pre-generated question is still relevant
│                 ├── YES (90% of cases): audio buffer ready → play immediately
│                 └── NO: trigger fast streaming LLM→TTS chain (Layer 2)
│
MARCUS SPEAKS ← perceived latency: ~0 seconds
```

**Pre-Generation Refresh Strategy:**

| Trigger | Action |
|---------|--------|
| Every 15 seconds of continuous presenter speech | Refresh all 3 agent candidate questions with latest transcript context |
| On slide change | Immediately refresh all candidates with new slide context (highest priority) |
| After presenter answers an agent question | Refresh the same agent's follow-up candidate |
| On significant new claim detected in transcript | Refresh the agent most relevant to that claim |

**Candidate Validation:** When it's time for an agent to speak, the Orchestrator runs a fast relevance check: does the candidate question still make sense given the last 30 seconds of transcript? This is a lightweight Gemini call with a simple yes/no + confidence score. If yes, play the buffered audio. If no, trigger the streaming fallback.

#### 4.2.2 Layer 2: Streaming Pipeline Chain (LLM → TTS)

For cases where pre-generated questions aren't available or aren't relevant — particularly during multi-turn exchanges where follow-ups depend on what the presenter just said — HighStake uses a streaming chain that pipes LLM output tokens directly into TTS input streaming.

```
STREAMING CHAIN:

Gemini LLM (streaming mode)
  │
  │ token: "What"
  │ token: " evidence"
  │ token: " supports"
  │ token: " your"
  │ ...
  │
  ├──→ Token Buffer (accumulates until sentence fragment boundary)
  │     │
  │     │ fragment: "What evidence supports your claim that"
  │     │
  │     └──→ Gemini Live TTS (streaming input)
  │           │
  │           │ audio chunk 1 ──→ play immediately on client
  │           │ audio chunk 2 ──→ play immediately on client
  │
  TIME TO FIRST AUDIO: 500-800ms from LLM call start
```

**Token buffering rules:** Accumulate tokens until hitting a natural speech boundary — comma, period, semicolon, em dash, or 8+ words. Send the fragment to TTS. This prevents choppy word-by-word synthesis while keeping latency low.

**Streaming chain pseudocode:**

```python
async def stream_agent_response(agent_id: str, context: dict):
    """Stream agent response from LLM directly to TTS."""
    
    # Start Gemini LLM streaming
    llm_stream = gemini.generate_content_stream(
        model="gemini-2.0-flash",
        contents=build_agent_prompt(agent_id, context),
        generation_config={"temperature": 0.7, "max_output_tokens": 200}
    )
    
    # Connect to Gemini Live session for this agent's voice
    live_session = await gemini_live.connect(
        voice_config=AGENT_VOICES[agent_id]
    )
    
    token_buffer = ""
    full_text = ""
    
    async for chunk in llm_stream:
        token_buffer += chunk.text
        full_text += chunk.text
        
        # Send to TTS at natural speech boundaries
        if should_flush(token_buffer):
            await live_session.send_text(token_buffer)
            # Audio chunks stream to client automatically
            token_buffer = ""
    
    # Flush remaining tokens
    if token_buffer:
        await live_session.send_text(token_buffer)
    
    return full_text  # for transcript logging
```

#### 4.2.3 Layer 3: Natural Latency Masking

Even with pre-generation and streaming, there will be moments with 0.5-1.5 seconds of gap. The solution is to make these gaps feel natural — real humans don't respond instantly either.

**Technique 1: Moderator Stalling**

The Moderator's transition phrases are deliberately verbose and buy processing time:

| Instead of | Use | Duration |
|-----------|-----|----------|
| "Marcus?" | "Thank you for that. Marcus, I noticed you wanted to dig into the financials — go ahead." | ~4s |
| "Questions?" | "Let's pause here. I think there are some important points worth examining. Priya, I saw you taking notes — what's on your mind?" | ~5s |
| "Next." | "Good, let's make sure we give this the scrutiny it deserves. James, you've been quiet — your thoughts?" | ~4s |

Moderator phrases are pre-generated during the presentation (they're predictable — the Moderator knows who will speak next) and their audio is buffered. During those 4-5 seconds of Moderator speech, the target agent's question is being finalized.

**Technique 2: Agent Thinking Indicators**

Visual cue on the agent's tile — a subtle "thinking" animation (pulsing dots, slight avatar movement) for 0.5-1s before they speak. This mirrors what you see on a video call when someone unmutes and takes a breath before talking.

**Technique 3: Pre-Recorded Lead-In Phrases**

Each agent has 5-8 pre-recorded "starter" phrases that play instantly while the full response streams in:

| Agent | Lead-In Phrases |
|-------|----------------|
| Marcus (Skeptic) | "That's concerning...", "Let me push back on that.", "I have a question about the numbers.", "Okay, but here's what I'm not seeing..." |
| Priya (Analyst) | "I want to understand the methodology here.", "Can you walk me through...", "The data is interesting, but...", "Let me dig into this a bit." |
| James (Contrarian) | "I see a problem.", "Let me play devil's advocate here.", "What if the opposite is true?", "Here's what keeps me up at night about this." |
| Diana (Moderator) | "Good point.", "Let's make sure we address that.", "Thank you — let's move to...", "We should spend more time on this." |

The system plays the most contextually appropriate lead-in phrase immediately (latency: ~0ms), then seamlessly crossfades into the streamed full response (which starts arriving 500-800ms later). The listener perceives continuous speech.

### 4.3 Complete Latency-Optimized Sequence

```
Presenter finishes speaking
  → Moderator speaks transition (pre-buffered, 0ms latency): 
    "Marcus, I think you had concerns about the revenue model."     [3-4s]
  → During Moderator speech:
    → Validate pre-generated question OR trigger streaming chain
  → Moderator finishes
  → Agent thinking indicator on tile                                [0.5s]
  → Agent lead-in plays (pre-recorded): "Let me push back on that." [1.0s]
  → Streaming response audio: "...you're projecting 40% margins     [seamless]
    by year two, but in the current rate environment..."

PERCEIVED TOTAL LATENCY: ~0 seconds
ACTUAL COMPUTATION TIME: 4-6 seconds (hidden behind Moderator + lead-in)
```

### 4.4 Latency Budget

| Component | Target | Worst Case | Hidden Behind |
|-----------|--------|------------|---------------|
| STT finalization | 300ms | 800ms | Continuous — runs during speech |
| Pre-generated question validation | 200ms | 500ms | Moderator transition speech |
| LLM streaming first token | 400ms | 1200ms | Moderator speech + agent lead-in |
| TTS streaming first audio chunk | 300ms | 800ms | Agent lead-in phrase |
| **Total perceived latency** | **~0ms** | **1500ms** | — |

### 4.5 Failure Modes & Graceful Degradation

| Failure | Detection | Fallback |
|---------|-----------|----------|
| Pre-generated question stale | Validation check returns "no" | Trigger streaming chain; extend Moderator stall by 1-2s |
| LLM streaming slow (>2s first token) | Timeout monitor | Play longer lead-in phrase + thinking animation |
| TTS streaming fails | Audio chunk timeout after 1s | Text-only fallback: display question in chat panel; Moderator says "Marcus has typed his question in the chat" |
| All pre-generation stale (off-script) | All 3 validations fail | Moderator buys time: "Let's take a moment to collect our thoughts on this new direction." Fresh streaming chain starts |
| Network degradation | WebSocket latency >500ms | Reduce to text-only mode with chat panel; disable voice |

---

## 5. Session-Scoped Agent Context System

### 5.1 Core Principle: Immutable Character, Mutable Context

Every AI panelist in HighStake has two layers of information:

**Immutable Layer (Template)** — The agent's persona, domain knowledge, voice configuration, questioning style, satisfaction criteria, and behavioral rules. These NEVER change during or between sessions. Marcus Webb is always the skeptical CFO with deep financial expertise. His character, voice, and approach are constants — just like a real person.

**Mutable Layer (Session-Scoped)** — Everything the agent learns, observes, and produces during a specific session. What claims they've seen in the deck, what external news is relevant, what questions they've asked, how the presenter responded, what's unresolved, and what they're planning to ask next. This context is created fresh for each session, accumulates throughout the session, and is archived when the session ends.

This mirrors how real board members work: their expertise and personality don't change between meetings, but what they know about THIS specific presentation does.

### 5.2 Directory Architecture

```
agents/
│
├── templates/                           ← IMMUTABLE: checked into Git, never modified at runtime
│   ├── moderator/
│   │   ├── persona.md                   ← Diana Chen's identity, personality, voice
│   │   ├── orchestration.md             ← State machine rules, turn limits, coordination logic
│   │   └── phrase-library.md            ← Master library of transition/stalling/bridge phrases
│   │
│   ├── skeptic/
│   │   ├── persona.md                   ← Marcus Webb's identity, style, satisfaction criteria
│   │   └── domain-knowledge.md          ← Financial benchmarks, red flags, frameworks
│   │
│   ├── analyst/
│   │   ├── persona.md                   ← Priya Sharma's identity, style, satisfaction criteria
│   │   └── domain-knowledge.md          ← Data quality frameworks, statistical methods, benchmarks
│   │
│   └── contrarian/
│       ├── persona.md                   ← James O'Brien's identity, style, satisfaction criteria
│       └── domain-knowledge.md          ← Logical fallacies, precedents, contradiction patterns
│
└── sessions/                            ← MUTABLE: created at runtime, one folder per session
    └── {session_id}/
        │
        ├── shared/                      ← Context shared across all agents for THIS session
        │   ├── session-config.md        ← Interaction mode, intensity, focus areas, duration
        │   ├── deck-content.md          ← Parsed slide text, claims, cross-slide dependencies
        │   ├── external-intel.md        ← Recent news, market data, competitive intelligence
        │   ├── board-dossier.md         ← Pre-session intelligence briefing
        │   ├── presenter-transcript.md  ← Running transcript of presenter's speech (Layer 2)
        │   └── exchange-history.md      ← All exchanges, outcomes, claim tracking
        │
        ├── moderator/                   ← Diana's session-specific mutable state
        │   ├── session-state.md         ← Live: current state, slide, time, topics, queue
        │   ├── generated-phrases.md     ← Session-specific phrases (referencing actual agent names/topics)
        │   └── debrief-notes.md         ← Accumulating notes for post-session summary
        │
        ├── skeptic/                     ← Marcus's session-specific mutable state
        │   ├── focus-brief.md           ← Claims to challenge, deck weaknesses, external intel for Marcus
        │   ├── exchange-notes.md        ← Marcus's questions, responses, evaluations, patterns observed
        │   ├── candidate-question.md    ← Current pre-generated question buffer
        │   └── presenter-profile.md     ← How this presenter handles financial challenges
        │
        ├── analyst/                     ← Priya's session-specific mutable state
        │   ├── focus-brief.md
        │   ├── exchange-notes.md
        │   ├── candidate-question.md
        │   └── presenter-profile.md
        │
        └── contrarian/                  ← James's session-specific mutable state
            ├── focus-brief.md
            ├── exchange-notes.md
            ├── candidate-question.md
            └── presenter-profile.md
```

### 5.3 Session Lifecycle

```
SESSION CREATION                              SESSION ACTIVE                        SESSION END
─────────────────                             ──────────────                        ───────────

1. Create session folder:                     4. Mutable files update              7. Archive session:
   agents/sessions/{session_id}/                 continuously:                        - Freeze all mutable files
                                                                                     - Generate final debrief
2. Populate shared/ context:                     - presenter-transcript.md            - Store session folder in
   - Parse deck → deck-content.md                  (every STT segment)                 persistent storage
   - Run enrichment → external-intel.md          - exchange-history.md              
   - Generate → board-dossier.md                   (after each exchange)            8. Session folder becomes
   - Write → session-config.md                   - exchange-notes.md                  read-only archive for
                                                   (after each turn)                  review/playback
3. Generate agent focus briefs:                  - candidate-question.md
   - Read templates/{agent}/persona.md             (every 15s, on slide change)     9. Templates are UNTOUCHED
     + domain-knowledge.md                       - session-state.md                   — ready for next session
   - Cross-reference with deck-content.md          (continuously)
     + external-intel.md                         - presenter-profile.md
   - Write → sessions/{id}/{agent}/                (after each exchange)
     focus-brief.md                              - generated-phrases.md
                                                   (as agents are selected)
   Templates are READ, never WRITTEN.            - debrief-notes.md
   Session files are CREATED and UPDATED.          (accumulating)

                                              5. Pre-generation pipeline reads:
                                                 template persona + domain
                                                 + session mutable context
                                                 → generates candidate questions

                                              6. Context assembly combines:
                                                 IMMUTABLE (from templates/)
                                                 + MUTABLE (from sessions/{id}/)
                                                 → feeds to LLM for each agent call
```

### 5.4 Context Assembly at Runtime

When the Orchestrator needs to generate a question or follow-up for an agent, it reads files from BOTH the immutable templates and the mutable session folder:

```
CONTEXT PAYLOAD FOR AGENT CALL:

┌─────────────────────────────────────────────────────────────────┐
│  FROM templates/{agent}/  (IMMUTABLE — never changes)           │
│                                                                 │
│  1. persona.md              — Who am I? How do I speak?         │
│  2. domain-knowledge.md     — What expertise do I bring?        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  FROM sessions/{id}/shared/ (MUTABLE — grows during session)    │
│                                                                 │
│  3. session-config.md       — Rules of this session             │
│  4. deck-content.md         — What is the presenter showing?    │
│  5. external-intel.md       — What's happening in the world?    │
│  6. presenter-transcript.md — What has the presenter said?      │
│  7. exchange-history.md     — What has the panel discussed?     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  FROM sessions/{id}/{agent}/ (MUTABLE — agent's personal state) │
│                                                                 │
│  8. focus-brief.md          — What should I focus on?           │
│  9. exchange-notes.md       — What have I personally asked?     │
│  10. presenter-profile.md   — How does this presenter respond?  │
│  11. candidate-question.md  — What am I planning to ask next?   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

For the Moderator, the assembly replaces domain-knowledge with orchestration.md, and adds session-state.md, generated-phrases.md, and debrief-notes.md.

### 5.5 File Classification: Immutable vs. Mutable

| File | Location | Mutability | Created When | Updated When |
|------|----------|-----------|-------------|-------------|
| persona.md | templates/{agent}/ | IMMUTABLE | Product development | Product version changes only |
| domain-knowledge.md | templates/{agent}/ | IMMUTABLE | Product development | Periodically (new benchmarks, frameworks) |
| orchestration.md | templates/moderator/ | IMMUTABLE | Product development | Product version changes only |
| phrase-library.md | templates/moderator/ | IMMUTABLE | Product development | When new phrase patterns are added |
| session-config.md | sessions/{id}/shared/ | MUTABLE (write-once) | Session creation | Never (frozen at start) |
| deck-content.md | sessions/{id}/shared/ | MUTABLE (write-once) | Deck parsing | Never (frozen after parsing) |
| external-intel.md | sessions/{id}/shared/ | MUTABLE (write-few) | Deck enrichment | Optionally if new topics emerge mid-session |
| board-dossier.md | sessions/{id}/shared/ | MUTABLE (write-once) | Deck enrichment | Never (frozen after generation) |
| presenter-transcript.md | sessions/{id}/shared/ | MUTABLE (append-only) | First speech detected | Every STT segment (continuous) |
| exchange-history.md | sessions/{id}/shared/ | MUTABLE (append-only) | First exchange | After every exchange resolves |
| session-state.md | sessions/{id}/moderator/ | MUTABLE (overwrite) | Session start | Continuously (Moderator's live state) |
| generated-phrases.md | sessions/{id}/moderator/ | MUTABLE (append) | Session start | As agents are selected to speak |
| debrief-notes.md | sessions/{id}/moderator/ | MUTABLE (append-only) | First notable event | After exchanges, at time warnings, at session end |
| focus-brief.md | sessions/{id}/{agent}/ | MUTABLE (write-once) | Session start | Never (frozen after generation) |
| exchange-notes.md | sessions/{id}/{agent}/ | MUTABLE (append-only) | First exchange involving this agent | After every turn in the agent's exchanges |
| candidate-question.md | sessions/{id}/{agent}/ | MUTABLE (overwrite) | First pre-generation cycle | Every 15s, on slide change, after exchanges |
| presenter-profile.md | sessions/{id}/{agent}/ | MUTABLE (append-only) | After first exchange | After each exchange (behavioral observations) |

### 5.6 Presenter Profile (New — Per-Agent Learning Within Session)

Each agent builds a `presenter-profile.md` during the session that captures how THIS presenter handles their type of challenge. This makes follow-up questions progressively smarter:

```markdown
# Presenter Profile — As Observed by Marcus Webb (Skeptic)

## Response Patterns Under Financial Challenge

- **When challenged on projections:** Provides new data points (good)
- **When challenged on methodology:** Deflects to "our model shows" (weak)
- **When caught in contradiction:** Gets flustered, repeats prior answer (vulnerability)
- **When given room to elaborate:** Shares useful detail willingly (strength)

## Data Readiness Assessment
- Has supporting data for revenue claims: Yes
- Has supporting data for margin claims: Partially
- Has stress-test / sensitivity data: No — this is a gap

## Behavioral Notes
- Tends to rush through financial slides — may be uncomfortable with the data
- Uses hedging language ("I think", "probably") when discussing margins
- Becomes more confident and specific when discussing product/technology

## Recommended Strategy for Remaining Session
- Push harder on margin methodology — presenter doesn't have backup data
- When asking about financials, give presenter time — they reveal more when not rushed
- Reference the 28% downside figure they mentioned earlier — they may not realize they disclosed it
```

This profile is READ by the agent during context assembly but WRITTEN by the Orchestrator based on transcript analysis. It makes each subsequent exchange smarter — the agent learns the presenter's tells within the session.

### 5.7 Session Archival & Reuse

When a session ends:

1. All mutable files are frozen (marked read-only)
2. The complete session folder is archived to persistent storage (S3/R2)
3. The session folder structure is preserved exactly for playback and review
4. The debrief engine reads the entire session folder to generate scores, coaching, and the Moderator's summary

**For repeat sessions with the same deck:**
- A new session folder is created from scratch
- Templates are re-read (same immutable personas)
- Deck content and external intel may be refreshed (deck might be updated, news will be newer)
- Prior session's presenter-profile.md can optionally be carried forward (Phase 4 feature — persistent agent memory)
- All other mutable files start empty — the agents don't remember the prior session by default

**For the dashboard:**
- Session archives are queryable: scores, exchange counts, unresolved challenges
- Presenter-profile evolution across sessions can be tracked (Phase 4)

### 5.8 Storage & Cleanup

| Content | Storage | Retention |
|---------|---------|-----------|
| Templates (agents/templates/) | Git repository | Permanent — version controlled |
| Active session (agents/sessions/{id}/) | Server filesystem or memory-mapped | Duration of session |
| Archived session | S3/R2 as compressed archive | Per user plan (30 days free, unlimited Pro) |
| Session recordings (video/audio) | S3/R2 | Per user plan |

Estimated storage per session:
- Mutable markdown files: ~50-100KB (text is compact)
- Deck content: 100-500KB (depending on deck size)
- Session recording: ~500MB (20 min at 720p)

---

## 6. Context Stack Architecture

### 6.1 Overview

The quality of agent questions is directly proportional to the richness and relevance of the context. HighStake uses a **5-layer context stack** — each layer adds a dimension of intelligence that makes agent questions feel genuinely informed rather than generically challenging.

The context stack is assembled at runtime by reading files from both `agents/templates/` (immutable) and `agents/sessions/{id}/` (mutable). See Section 5 for the complete file mapping.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: EXTERNAL INTELLIGENCE                              │
│  Recent news, market data, competitive moves, regulatory     │
│  changes relevant to the deck's topics                       │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: DOMAIN KNOWLEDGE                                   │
│  LLM's training knowledge — industry benchmarks, financial   │
│  frameworks, historical precedents, best practices           │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: SESSION MEMORY (Panel Dialogue History)            │
│  All prior questions, presenter responses, unresolved        │
│  challenges, exchange outcomes, topics covered vs uncovered  │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: PRESENTER'S LIVE TRANSCRIPT                        │
│  What the presenter has actually said — claims, caveats,     │
│  verbal commitments, hesitations, deviations from slides     │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: DECK CONTENT (Foundation)                          │
│  Full slide text, structure, speaker notes, charts, tables,  │
│  extracted claims and projections                            │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Layer 1: Deck Content (Static, Pre-Loaded)

This is the foundation. Before the session starts, the deck is parsed into a structured representation. The agent knows not just what's on the current slide but what's coming later — just like a real board member who flipped through the printed deck before the meeting.

This enables cross-slide reasoning: "You mention a $15M raise on slide 18, but your unit economics on slide 7 don't support that valuation."

Contents: full slide manifest with extracted text per slide, slide structure and section groupings, speaker notes (often contain the real argument behind bullet points), data extracted from charts and tables (numbers, trends, labels), extracted key claims and projections per slide.

Slide Manifest Schema:
```json
{
  "id": "deck_abc123",
  "filename": "Q4_Strategy_Deck.pptx",
  "totalSlides": 20,
  "uploadedAt": "2026-02-16T10:30:00Z",
  "extractedClaims": [
    {
      "slideIndex": 3,
      "claim": "40% gross margins by year two",
      "type": "financial_projection",
      "confidence": "high",
      "supportingData": "Based on enterprise pipeline and unit economics"
    }
  ],
  "slides": [
    {
      "index": 0,
      "title": "Executive Summary",
      "subtitle": "Q4 Strategic Initiative",
      "bodyText": "Full extracted text content...",
      "notes": "Speaker notes if present...",
      "hasChart": true,
      "hasTable": false,
      "chartData": { "type": "bar", "labels": [...], "values": [...] },
      "thumbnailUrl": "/api/slides/deck_abc123/thumb/0.png"
    }
  ]
}
```

### 6.3 Layer 2: Presenter's Live Transcript

This is the real-time layer — what the presenter has actually said, which is often different from what's on the slides. A good board member listens for the gaps between what's written and what's spoken.

The agent detects: when the presenter skips over a claim on the slide, when they add verbal caveats not on the slides ("we think this could work" vs. the slide saying "this will work"), when they spend disproportionate time on one section (suggesting uncertainty or passion), specific numbers or verbal commitments, and filler words and hedging language patterns.

The transcript is segmented by slide so agents can correlate spoken content against displayed content.

Transcript Segment Schema:
```json
{
  "slideIndex": 3,
  "segments": [
    {
      "type": "final",
      "text": "Our total addressable market is estimated at 4.2 billion by 2027",
      "startTime": 125.4,
      "endTime": 131.2,
      "confidence": 0.94,
      "detectedClaims": ["TAM $4.2B by 2027"],
      "hedgingLanguage": false,
      "fillerWords": []
    }
  ]
}
```

### 6.4 Layer 3: Session Memory (Panel Dialogue History)

Without this layer, agents operate in isolation and ask redundant questions. With it, they build on each other like a real panel.

Session memory enables: the Contrarian referencing the Skeptic's earlier challenge ("Marcus raised concerns about your margins — I want to take that further"), agents avoiding repetition of questions already asked, the Analyst following up on an answer the presenter gave to the Skeptic, the Moderator tracking which topics have been covered and which haven't, and tracking of unresolved challenges (questions where the agent was not satisfied).

Contents: every question asked (with agent ID and timestamp), the presenter's response to each question, exchange outcomes (SATISFIED, FOLLOW_UP, ESCALATE, MODERATOR_INTERVENED), a running list of claims challenged vs. accepted, topics covered vs. uncovered, and unresolved challenges flagged for debrief.

Session Memory Schema:
```json
{
  "exchanges": [
    {
      "id": "exchange_001",
      "slideIndex": 3,
      "primaryAgent": "skeptic",
      "triggerClaim": "40% gross margins by year two",
      "turns": [
        {
          "turn": 1,
          "agentText": "What evidence supports 40% margins by year two?",
          "presenterResponse": "Based on our enterprise pipeline and unit economics.",
          "evaluation": "FOLLOW_UP"
        },
        {
          "turn": 2,
          "agentText": "Your pipeline is early stage. What if conversion is half projected?",
          "presenterResponse": "Stress-tested: still hit 28% margins in downside case.",
          "evaluation": "ESCALATE"
        },
        {
          "turn": 3,
          "agentText": "28% vs 40% is a 12-point range. Has the board seen this range?",
          "presenterResponse": "Plan to include range analysis in appendix.",
          "evaluation": "NOT_SATISFIED"
        }
      ],
      "outcome": "MODERATOR_INTERVENED",
      "unresolvedChallenge": "Margin range (28-40%) not presented upfront; appendix-only",
      "pileOn": null
    }
  ],
  "topicsCovered": ["revenue_projections", "margins", "tam"],
  "topicsUncovered": ["competitive_moat", "team_execution", "regulatory_risk"],
  "claimsChallenged": ["40% margins"],
  "claimsAccepted": ["$4.2B TAM"]
}
```

### 6.5 Layer 4: Domain Knowledge (LLM Training Knowledge)

The LLM brings deep expertise that makes agents feel like real domain experts rather than generic question machines.

The Skeptic (CFO persona) draws on: financial modeling benchmarks, typical margin profiles by industry, red flags in revenue models, common pitfalls in projections, and valuation frameworks.

The Analyst (VP Strategy persona) draws on: statistical methodology, market research frameworks, sensitivity analysis best practices, comparable company analysis, and what "good data" looks like in presentations.

The Contrarian (Board Advisor persona) draws on: historical precedents of failed strategies, competitive dynamics and disruption theory, behavioral economics, technology adoption curves, and regulatory risk patterns.

This layer is activated by explicit system prompt instructions: "Draw on your knowledge of industry benchmarks, historical precedents, and established frameworks to evaluate the presenter's claims. If their projections deviate from industry norms, call it out with specifics."

### 6.6 Layer 5: External Intelligence (Real-Time Enrichment)

This layer makes agents terrifyingly well-prepared — the kind of board member who reads the morning news before your meeting.

Imagine the Skeptic saying: "You're projecting 18% growth in the semiconductor segment, but TSMC just announced capacity cuts last week. How does that affect your timeline?"

**Pre-Session Enrichment Pipeline:**

```
Deck parsed → Extract entities and claims
  → "semiconductor market", "18% CAGR", "TSMC", "regulatory environment"
    → Web search for each entity + "recent news 2026"
      → Filter for relevance and recency (last 30 days)
        → Summarize findings into "External Context Briefing"
          → Store as part of session context
```

**External Context Briefing Schema:**
```json
{
  "generatedAt": "2026-02-16T10:30:45Z",
  "deckId": "deck_abc123",
  "briefings": [
    {
      "topic": "Semiconductor market outlook",
      "deckClaim": "18% CAGR in target segment",
      "externalFindings": "TSMC announced 15% capacity reduction in Q1 2026. Industry analysts now project 12-14% CAGR, down from earlier estimates of 18-20%. Samsung is increasing investment counter-cyclically.",
      "implication": "Presenter's growth assumptions may be optimistic given recent supply-side shifts",
      "relevantSlides": [1, 4, 12],
      "sources": ["Reuters Feb 12 2026", "Semiconductor Industry Association Q4 Report"]
    },
    {
      "topic": "Competitive landscape",
      "deckClaim": "3 major incumbents, defensible moat",
      "externalFindings": "Incumbent X announced entry into presenter's target segment via acquisition of Company Y on Feb 5, 2026.",
      "implication": "Competitive moat thesis needs updating — new entrant not reflected in deck",
      "relevantSlides": [5, 6],
      "sources": ["TechCrunch Feb 5 2026"]
    }
  ]
}
```

**Refresh Strategy:** The bulk of external intelligence is gathered once during deck parsing (pre-session). The system does NOT re-search during the live session to avoid latency impact. However, if the presenter mentions a company, person, or event not covered in the initial briefing, the Orchestrator can queue a lightweight background search for the next pre-generation cycle.

### 6.7 Complete Context Assembly

Here's the full context payload assembled for each agent call:

```
SYSTEM PROMPT:
  Agent persona (role, personality, questioning style, voice)
  Intensity level instructions
  Focus area priorities
  Multi-turn exchange rules (when to follow up vs. accept)
  Coordination rules (reference other agents, don't repeat)

CONTEXT PAYLOAD:
  [LAYER 1: DECK CONTENT]
  Full slide manifest with text, notes, data
  Extracted claims and projections
  Current slide index highlighted
  
  [LAYER 2: PRESENTER TRANSCRIPT]
  Full transcript segmented by slide
  Key verbal claims extracted
  Verbal caveats and hedging language flagged
  Deviations from slide content noted
  
  [LAYER 3: SESSION MEMORY]
  All prior exchanges (questions + responses + outcomes)
  Topics covered vs. uncovered
  Unresolved challenges
  Claims challenged vs. accepted
  Other agents' recent questions (for cross-referencing)
  
  [LAYER 4: DOMAIN KNOWLEDGE]
  (Implicit in LLM training — activated by system prompt)
  Instruction to reference industry benchmarks, frameworks, precedents
  
  [LAYER 5: EXTERNAL INTELLIGENCE]
  External Context Briefing
  Recent news contradicting or supporting deck claims
  Competitive intelligence updates
  Market data and analyst reports

INSTRUCTION:
  Generate ONE focused question for this moment in the presentation.
  Reference specific claims from the deck or transcript.
  Build on the panel discussion so far.
  If external intelligence contradicts a claim, use it.
  Stay in character.
```

### 6.8 Context Window Management

For sessions longer than 20 minutes, the full context will be large. The system implements a tiered compression strategy:

| Content | Strategy |
|---------|----------|
| Current slide + adjacent slides | Full text, always included |
| Other slides | Titles + extracted claims only (compressed) |
| Last 3 minutes of transcript | Full text |
| Earlier transcript | Compressed to key claims + responses |
| Session memory (exchanges) | Full for last 3 exchanges; summarized for earlier ones |
| External briefing | Full (typically 500-1000 tokens, doesn't grow) |
| Extracted claims list | Always full (compact, high value) |

Target context payload: 8,000-15,000 tokens per agent call. This fits comfortably within Gemini 2.0 Flash's context window while keeping response latency low.

### 6.9 The Board Preparation Dossier (Pre-Session Feature)

The context enrichment process produces a valuable artifact: the **Board Preparation Dossier**. This can be shown to the presenter before the session as a "here's what your panel will come armed with" preview.

The Dossier includes: key claims in the deck that are most likely to be challenged, recent news that could affect the deck's thesis, industry benchmarks the panel would reference, common questions for this type of presentation, and weak points the panel will likely target.

This gives the presenter a chance to prepare their defenses before the simulation — which is itself a valuable coaching tool, even without the live session.

---

## 7. Multi-Turn Exchange System

### 7.1 The Problem with One-Shot Q&A

A naive implementation treats agent interaction as: agent asks question → presenter answers → next slide. This feels robotic and misses the most valuable part of a boardroom: the follow-up.

In a real boardroom, a challenge often becomes a 2-4 turn exchange:
- The CFO asks about margins
- The presenter gives a general answer
- The CFO pushes harder, pointing out the answer didn't address the core concern
- The presenter provides specific data or acknowledges a gap
- The Moderator wraps up and moves things forward

This dynamic is where presenters learn the most — and where HighStake must excel.

### 7.2 Session State Machine

The session operates in five states. The EXCHANGE state is the core innovation.

```
                    ┌──────────────────────────────────┐
                    │                                  │
                    ▼                                  │
┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────┐
│PRESENTING│→ │  Q&A     │→ │  EXCHANGE    │→ │  RESOLVING   │
│          │  │  TRIGGER │  │  (Multi-Turn)│  │              │
│Presenter │  │          │  │              │  │  Moderator   │
│speaking, │  │Moderator │  │  Agent ←→    │  │  wraps up,   │
│agents    │  │calls on  │  │  Presenter   │  │  bridges to  │
│listening │  │an agent  │  │  back & forth│  │  next topic  │
└──────────┘  └──────────┘  └──────────────┘  └──────┬───────┘
     ▲                                               │
     │                                               │
     └───────────────────────────────────────────────┘
                    (back to presentation)
```

**PRESENTING** — Presenter is speaking, agents are listening, pre-generation pipeline is running in background.

**Q&A_TRIGGER** — Moderator calls on an agent. Pre-generated question plays (or streaming chain fires). Transition to EXCHANGE.

**EXCHANGE** — Multi-turn dialogue between the active agent and the presenter. The agent evaluates each response and decides whether to follow up, escalate, or accept. The Moderator monitors and enforces turn limits.

**RESOLVING** — Moderator wraps up the exchange, optionally allows one pile-on from another agent, logs the exchange outcome and any unresolved challenges, and speaks a natural bridge-back phrase to return to the presentation.

### 7.3 Exchange Turn Logic

When the presenter answers an agent's question, the active agent receives an evaluation prompt:

```
EVALUATION PROMPT:

You are {agent_name} ({agent_role}). You just asked:
"{your_question}"

The presenter responded:
"{presenter_response}"

Original claim being challenged: "{claim}"
Deck's supporting data: "{deck_data}"
External context: "{relevant_briefing}"
Exchange history so far: {prior_turns}

EVALUATE the response and choose ONE action:

SATISFIED — The response adequately addresses your concern.
  Give a brief 1-sentence acknowledgment. No further questions.
  Use when: presenter provided specific data, acknowledged the issue,
  or gave a compelling counter-argument.

FOLLOW_UP — The response is partial, vague, or evasive. One gap remains.
  Ask ONE short follow-up (max 2 sentences) targeting the specific gap.
  Do NOT repeat your original question. Push deeper on what was missing.
  Use when: presenter gave a general answer without specifics, or
  addressed only part of the question.

ESCALATE — The response is weak, contradicts other evidence, or deflects.
  Point out the specific contradiction or weakness in 1-2 sentences.
  This is your strongest push — make it pointed.
  Use when: presenter's answer contradicts their own deck, contradicts
  external data, or is clearly evasive.

Respond as JSON:
{
  "action": "SATISFIED" | "FOLLOW_UP" | "ESCALATE",
  "text": "Your response to the presenter (spoken aloud)",
  "internalReasoning": "Why you chose this action (not spoken)"
}
```

### 7.4 Exchange Turn Limits

The Moderator enforces maximum turns to prevent runaway exchanges:

| Intensity Level | Max Turns | Moderator Behavior |
|----------------|-----------|-------------------|
| Friendly | 2 (question + 1 follow-up) | Steps in after first follow-up regardless of outcome |
| Moderate | 3 (question + 2 follow-ups) | Steps in if exchange becomes circular or at limit |
| Adversarial | 4 (question + 3 follow-ups) | Only steps in at limit or if presenter explicitly requests to move on |

A "turn" = one agent statement + one presenter response.

If the agent returns SATISFIED before hitting the limit, the exchange ends early and moves to RESOLVING.

### 7.5 Cross-Agent Pile-Ons

After the primary exchange resolves, another agent may want to add a related point. This creates powerful moments: "Building on what Marcus just raised about margins — if your downside scenario shows 28%, your break-even timeline on slide 11 needs to be revised too."

**Pile-On Rules:**
- Only ONE agent can pile on per exchange
- The Moderator decides whether a pile-on is warranted (based on relevance and time)
- The pile-on agent must explicitly reference the previous exchange
- The pile-on is limited to ONE turn (question + answer, no further follow-ups)
- The pile-on question is pre-generated during the primary exchange (the other agents are watching)

**Pile-On Flow:**
```
RESOLVING STATE:
  → Primary exchange ends (Marcus done)
  → Moderator checks: does another agent have a relevant pile-on?
    → IF yes AND time permits:
      Diana: "Good exchange. Priya, I believe you had a related point?"
      Priya: [pre-generated during exchange] "Building on Marcus's concern — 
        if margins could be as low as 28%, your break-even on slide 11 
        shifts from month 18 to month 26. Have you modeled that?"
      Presenter answers (one turn)
      Diana: "Thank you. Let's continue."
    → IF no OR time is tight:
      Diana: "Let's continue." → PRESENTING
```

### 7.6 Moderator Bridge-Back Patterns

The Moderator's bridge-back from an exchange to the presentation must feel natural, not abrupt. The bridge should accomplish three things: acknowledge the exchange, signal to the presenter they can continue, and set up context for the next section.

**After SATISFIED resolution:**
"Good. I think Marcus's concern has been addressed. Let's continue — you were about to walk us through the go-to-market."

**After MODERATOR_INTERVENED (hit turn limit, unresolved):**
"This is clearly a point that needs more work. I'd suggest preparing a detailed sensitivity analysis for the real meeting. For now, let's move forward — I want to make sure we get to the competitive landscape."

**After a particularly tough exchange:**
"That was a productive exchange. Take a moment and continue when you're ready."

**After a pile-on:**
"Marcus and Priya both raised important points about your margin assumptions. Those are flagged for the debrief. Please continue with slide 5."

**When presenter went off-script during the exchange:**
"You brought up some new data points in that exchange that weren't in the deck. That's useful context. Let's get back to the slides — I believe you were on the competitive landscape."

### 7.7 Exchange Integration with Latency Architecture

Multi-turn exchanges create a latency challenge: follow-up questions can't be pre-generated because they depend on what the presenter just said. Here's how the system adapts:

```
PRESENTING STATE:
  → Pre-generation pipeline running (all 3 agents have buffered initial questions)

Q&A_TRIGGER:
  → Agent's pre-generated initial question plays (near-zero latency) ✓
  → Pre-generation pipeline PAUSES for the active agent
  → Pre-generation CONTINUES for other agents (they prepare pile-on candidates
    based on the exchange content as it unfolds)
  → System enters EXCHANGE state

EXCHANGE STATE (Turns 2+):
  → Presenter responds via voice → STT transcribes
  → Active agent's follow-up uses STREAMING CHAIN (not pre-gen)
  → Latency masked by:
    - Moderator micro-phrases: "Mm-hmm...", "Interesting..." (pre-recorded, 0ms)
    - Agent thinking indicator (0.5-1.0s visual cue)
    - Agent lead-in phrase (pre-recorded, 0ms)
    - Streaming audio begins (500-800ms from call start)
  → Meanwhile: Moderator's bridge-back phrase is being pre-generated
  → Meanwhile: pile-on candidates from other agents are being pre-generated

RESOLVING STATE:
  → Moderator bridge-back plays (pre-generated during exchange) ✓
  → If pile-on: their question was pre-generated during the exchange ✓
  → Transition to PRESENTING

PRESENTING STATE (resumed):
  → All pre-generation buffers refresh with full exchange context
  → Future questions can reference the exchange naturally
```

**Latency profile during exchanges:**

| Turn | Latency Source | Perceived Latency | Masking |
|------|---------------|-------------------|---------|
| Turn 1 (initial question) | Pre-generated | ~0ms | Moderator transition phrase |
| Turn 2 (first follow-up) | Streaming chain | 500-800ms | Thinking indicator + lead-in phrase |
| Turn 3 (second follow-up) | Streaming chain | 500-800ms | Thinking indicator + lead-in phrase |
| Moderator bridge-back | Pre-generated during exchange | ~0ms | — |
| Pile-on question | Pre-generated during exchange | ~0ms | Moderator transition |

The slightly higher latency on follow-up turns (500-800ms) actually feels MORE natural than the initial question, because in a real boardroom, a person pauses to process the answer before responding.

### 7.8 Exchange Example with Full Timing

```
[00:00] PRESENTING STATE
        Presenter: "We expect 40% margins by year two based on our
        enterprise pipeline and self-serve expansion."
        [Pre-gen pipeline: Marcus has question + audio buffered]

[00:05] Q&A_TRIGGER
        Diana (pre-buffered, 0ms): "Let's pause here. Marcus,
        I think you had concerns about the revenue model."        [3.5s]
        [During speech: Marcus's audio confirmed ready]

[00:09] EXCHANGE — Turn 1
        Marcus (pre-generated, 0ms): "You're projecting 40%
        margins by year two. What specific evidence supports
        that given current market conditions?"                    [3s]
        [Pipeline: pause Marcus pre-gen; start pile-on candidates]

[00:12] Presenter responds:
        "We've modeled this based on our enterprise contracts
        and the unit economics from pilot customers."             [4s]
        [System: STT → send to Marcus evaluation prompt]
        [Marcus eval returns: FOLLOW_UP — "pipeline is early stage"]

[00:16] EXCHANGE — Turn 2 (streaming chain)
        [Thinking indicator: 0.5s]
        [Lead-in (pre-recorded, 0ms): "But here's the thing—"]   [0.8s]
        [Stream begins, 600ms]: "your pilots are early stage.
        What if enterprise conversion is half projected?"          [3s]
        [Perceived latency: ~0ms due to lead-in masking]

[00:20] Presenter responds:
        "We've stress-tested that scenario and still
        achieve 28% margins in the downside case."                [3s]
        [System: Marcus eval returns: ESCALATE — "28% vs 40% range"]

[00:23] EXCHANGE — Turn 3 (streaming chain)
        [Thinking indicator: 0.5s]
        [Lead-in (pre-recorded, 0ms): "That's a very different—"] [0.8s]
        [Stream]: "story than 40%. That's a 12-point range
        you're not showing. Has the board seen this range?"        [3s]
        [Moderator: turn limit approaching at MODERATE intensity]
        [Moderator pre-generates bridge-back]

[00:27] Presenter responds:
        "We plan to include the range analysis in appendix."       [2s]
        [System: Moderator intercedes — turn limit reached]
        [System: logs unresolved challenge]
        [System: Priya has pile-on ready from pre-gen]

[00:29] RESOLVING
        Diana (pre-generated, 0ms): "Good exchange. Marcus,
        you've surfaced an important point about presenting
        the margin range upfront. Let's flag that for the
        debrief. Priya, I know you had a related thought,
        but let's hold it and move forward."                       [5s]
        [System: logs exchange, refreshes all pre-gen buffers]

[00:34] PRESENTING STATE (resumed)
        Presenter continues to next slide.
        [All agents now have exchange context in their pre-gen prompts]
        [Future questions can reference: "Earlier you told Marcus
        margins could be 28% — that contradicts what this slide shows."]
```

Total exchange: 25 seconds. Natural, productive, with zero awkward silences. The presenter was genuinely pushed and a real weakness was surfaced for the debrief.

---

## 8. Feature Specifications

### 8.1 Phase 1: Pre-Session Setup

The Moderator agent (Diana Chen) guides the presenter through configuration in a conversational, step-by-step flow.

#### 8.1.1 Interaction Mode Selection

| Mode | Behavior | Agent Trigger | Moderator Role |
|------|----------|---------------|----------------|
| Section Breaks | Agents hold all questions until the presenter finishes a slide or section | Presenter clicks "Next Slide" or "Open Q&A" | Announces Q&A windows, calls on agents in order |
| Hand Raise | Agents raise a virtual hand when they have a question; presenter chooses when to acknowledge | Agent AI determines question urgency; raises hand via UI signal | Notifies presenter of raised hands, suggests taking questions |
| Free Flow | Agents can interject at natural pauses in the presenter's speech | STT detects pauses > 2 seconds or end-of-sentence patterns | Manages crosstalk, ensures balanced participation |

All three modes support multi-turn exchanges — the interaction mode only controls when the initial question is triggered, not the depth of the resulting exchange.

#### 8.1.2 Intensity Level Configuration

| Level | Initial Question Style | Exchange Depth | Follow-Up Aggression | Moderator Patience |
|-------|----------------------|----------------|---------------------|-------------------|
| Friendly | Clarifying, supportive | 2 turns max | Accepts partial answers | Steps in after 1 follow-up |
| Moderate | Direct, demands justification | 3 turns max | Pushes on gaps, accepts good answers | Steps in if circular |
| Adversarial | Aggressive, expresses doubt | 4 turns max | Escalates, points out contradictions | Only steps in at limit |

#### 8.1.3 Focus Area Selection

The presenter selects one or more focus areas. These areas are injected into each agent's system prompt and influence the external intelligence enrichment. Available focus areas: Financial Projections, Go-to-Market Strategy, Competitive Analysis, Technical Feasibility, Team & Execution, Market Sizing, Risk Assessment, Timeline & Milestones. Custom focus areas can be typed in by the presenter.

#### 8.1.4 Deck Upload & Enrichment

Accepted formats: PPTX (preferred), PDF. Max file size: 50MB. Max slides: 100.

Processing pipeline:
1. Upload to server
2. Extract text, structure, notes, charts, tables per slide
3. Extract key claims and projections
4. Run external enrichment (web search for entities, news, market data)
5. Generate Board Preparation Dossier
6. Generate slide manifest JSON
7. Create thumbnail renders
8. Return manifest + Dossier to client
9. Populate agent context (Layer 1 + Layer 5)

Full pipeline completes within 30 seconds for a 20-slide deck. Parsing and enrichment run in parallel.

### 8.2 Phase 2: Live Boardroom Session

#### 8.2.1 Video Conference UI Layout

The interface mimics a familiar video conference layout. The presenter's webcam feed occupies one tile (highlighted with a blue ring). Four AI agent tiles display avatars, names, titles, and role badges. Active speaker detection highlights the current speaker's tile with a glow effect and audio waveform animation. A thinking indicator (pulsing dots) appears on agent tiles during follow-up processing. A slide viewer panel shows the current slide with navigation controls. A chat panel on the right displays all agent messages with timestamps. A top bar shows session timer, interaction mode indicator, exchange turn counter, recording status, and "End Session" button.

#### 8.2.2 Presenter Capture Pipeline

```
Browser Mic → MediaRecorder API → Audio Chunks (WebM/Opus, 250ms intervals)
                                        │
                                        ├──→ WebSocket → Gemini Live STT → Transcript Segments
                                        │
                                        └──→ Local Recording Buffer → Session Recording

Browser Camera → MediaStream → Video Element (self-view)
                                        │
                                        └──→ MediaRecorder → Video Chunks → Session Recording
```

Audio: 16kHz minimum (48kHz preferred), WebM/Opus, echo cancellation + noise suppression enabled.
Video: 720p minimum, 30fps, WebM/VP9.

#### 8.2.3 Agent Audio Playback

Agent audio arrives as streaming chunks from Gemini Live TTS. The client maintains a per-agent audio playback queue. When an agent speaks, their tile animates (waveform bars, glow effect). Other agent tiles dim slightly. The presenter's tile shows a "listening" state during agent speech. Audio chunks are buffered minimally (50-100ms) for smooth playback without gaps.

### 8.3 Phase 3: Post-Session Debrief

#### 8.3.1 Scoring Model

| Dimension | Weight | Signals |
|-----------|--------|---------|
| Overall | — | Weighted composite of all dimensions |
| Clarity | 15% | Sentence complexity, filler word frequency, topic coherence per slide |
| Confidence | 15% | Hesitation patterns, response latency to questions, hedging language |
| Data Support | 20% | Specificity of claims, use of numbers/evidence, citation of sources |
| Q&A Handling | 25% | Directness of answers, whether questions were fully addressed, recovery from escalations |
| Exchange Resilience | 15% | Performance under multi-turn pressure, ability to provide new data points when pushed, composure during escalation |
| Structure | 10% | Logical flow, time distribution across slides, transition quality |

Filler words tracked: "um", "uh", "like", "you know", "basically", "actually", "sort of", "kind of", "I mean", "right".

Hedging language tracked: "I think", "maybe", "probably", "I guess", "hopefully", "we'll see", "it depends".

#### 8.3.2 Debrief Tabs

**Summary Tab:** Overall score with radial progress indicator, category score bars, top 4 strengths with specific examples, Moderator's narrative summary, and exchange highlight reel (the most intense exchange, summarized).

**Transcript Tab:** Full transcript with speaker labels (color-coded), timestamps, and role indicators. Exchange turns are visually grouped and labeled. Searchable, filterable by speaker. Copy-all functionality. Exportable as TXT or DOCX.

**Scores Tab:** Individual score cards for each dimension. Score bars with color coding (green ≥80, amber 70-79, red <70). Comparison against previous sessions. Exchange Resilience score with breakdown per exchange.

**Coaching Tab:** Prioritized improvement areas ranked by impact (High, Medium, Low). Each item includes the area name, priority level, specific detail explaining what happened and what to do differently, and a timestamp reference to the relevant moment. Generated by Gemini analyzing the full session with a coaching-specific system prompt.

**Unresolved Challenges Tab:** List of exchanges where the agent was NOT satisfied when the Moderator stepped in. Each entry shows the original claim, the challenge, the presenter's responses, why it remained unresolved, and a suggested preparation strategy for the real meeting.

#### 8.3.3 Moderator's Summary Generation

The Moderator's post-session summary is generated via a dedicated Gemini call with: full transcript, all exchange data with outcomes, scoring results, slide content, session configuration, external context briefing, and comparison to previous sessions if available. The summary is 200-300 words, written in first person as Diana Chen, covering overall impression, strongest moment, most critical unresolved challenge, exchange handling assessment, one specific tactical recommendation, and encouragement.

#### 8.3.4 Report Export

PDF report includes: session metadata (date, duration, configuration), overall and dimension scores, strengths and improvement areas, exchange summaries with outcomes, unresolved challenges with preparation recommendations, full transcript, external context briefing used, and Moderator's summary. Generated server-side.

---

## 8.4 Custom Agent Builder

### 8.4.1 Overview

Users can customize existing panelists or create entirely new ones by providing a simple natural-language brief. The system uses a high-quality LLM (Gemini 2.0 Flash or Claude) to generate production-grade agent templates — persona.md and domain-knowledge.md — that match the quality and structure of the hand-crafted defaults.

This means a user can say "I need a regulatory expert who grills me on FDA compliance" and get a fully realized panelist with a name, title, personality, questioning style, follow-up behavior, satisfaction criteria, domain expertise, and voice configuration — all auto-generated and ready for a session.

### 8.4.2 User Stories

**US-8: Customize Existing Panelist**
As a presenter, I want to modify an existing panelist's focus or background so the panel better matches my real audience.

Acceptance Criteria:
- User can select any of the 4 default panelists to customize
- User provides a natural-language modification brief (e.g., "Make Marcus more focused on biotech financials" or "Priya should have a background in clinical trials data analysis")
- System generates an updated persona.md and domain-knowledge.md that preserves the core archetype (skeptic, analyst, contrarian, moderator) while incorporating the user's customization
- Original default templates are never modified — the customized version is stored as a user-owned variant
- User can preview the generated persona before using it in a session
- User can revert to the default at any time

**US-9: Create New Panelist from Scratch**
As a presenter, I want to create a completely new panelist that represents a specific stakeholder I'll face in my real meeting.

Acceptance Criteria:
- User provides a brief describing the panelist they need (minimum: role/title, what they care about; optional: name, personality traits, industry background)
- System generates a complete agent template: persona.md + domain-knowledge.md
- Generated template follows the exact same structure as hand-crafted defaults (ensuring compatibility with the orchestration system, exchange logic, and TTS pipeline)
- User can assign the new agent to one of the 4 panel seats (replacing a default panelist) or expand the panel up to 6 seats
- User can iterate on the generated persona by providing additional instructions
- Generated panelists are saved to the user's library for reuse across sessions

**US-10: Manage Agent Library**
As a presenter, I want to maintain a library of custom panelists so I can assemble different panels for different presentations.

Acceptance Criteria:
- User can view all their custom agents (generated + modified)
- User can assign agents to panel seats before a session
- User can share custom agents with team members (team plan)
- User can duplicate and modify existing custom agents
- User can delete custom agents they no longer need
- Default agents (Diana, Marcus, Priya, James) are always available and cannot be deleted

### 8.4.3 Agent Generation Pipeline

When a user submits a brief for a new or modified agent, the system runs a multi-step generation pipeline:

```
USER INPUT                           GENERATION PIPELINE                    OUTPUT
─────────                            ───────────────────                    ──────

"I need a regulatory                 1. CLASSIFY ARCHETYPE                 agents/custom/{user_id}/
 expert, former FDA                     Determine base role:                 regulatory_expert/
 reviewer, who focuses                  □ Challenger (like Skeptic)           ├── persona.md
 on compliance risk                     □ Analyst (like Analyst)              └── domain-knowledge.md
 and approval timelines.                □ Adversary (like Contrarian)
 She should be tough                    ■ Specialist (new archetype)
 but fair, named                        □ Moderator variant
 Dr. Sarah Lin."
                                     2. GENERATE PERSONA
                                        Feed to LLM with meta-prompt:
                                        - User's brief
                                        - Reference template structure
                                        - Required fields checklist
                                        → persona.md

                                     3. GENERATE DOMAIN KNOWLEDGE
                                        Feed to LLM with meta-prompt:
                                        - Generated persona
                                        - User's brief
                                        - Reference domain-knowledge structure
                                        - Instruction to include real frameworks,
                                          benchmarks, and red flags for the domain
                                        → domain-knowledge.md

                                     4. VALIDATE COMPLETENESS
                                        Check generated files against schema:
                                        - All required sections present?
                                        - Satisfaction criteria defined?
                                        - Intensity scaling table complete?
                                        - Voice configuration assigned?
                                        - No contradictions with orchestration rules?
                                        → Fix any gaps with targeted follow-up LLM calls

                                     5. ASSIGN VOICE PROFILE
                                        Based on persona gender, age, tone:
                                        → Select best-matching Gemini Live voice
                                        → Store in persona.md voice config section

                                     6. PREVIEW & CONFIRM
                                        Show user:
                                        - Generated name, title, personality summary
                                        - Sample questions at each intensity level
                                        - Voice preview (short TTS sample)
                                        → User confirms or requests changes
```

### 8.4.4 Meta-Prompts for Agent Generation

The quality of generated agents depends entirely on the meta-prompts used. These are the system prompts that instruct the LLM to create agent templates.

**Persona Generation Meta-Prompt:**

```
You are an expert character designer for an AI boardroom simulation product.
Your job is to create a richly detailed panelist persona from a user's brief.

USER'S BRIEF:
{user_brief}

ARCHETYPE CLASSIFICATION:
{archetype}

Generate a persona.md file with EXACTLY this structure:

## Identity
- Name, Title, Role, Agent ID, Color (hex), Avatar (initials)

## Personality
- 2-3 sentences capturing who this person is, their background, what drives them
- Must be specific and vivid — not generic

## Voice Configuration
- Tone, Pace, Characteristics
- Gemini Live voice recommendation
- Speed and pitch settings

## Questioning Style
### Initial Questions (5 examples — specific to their domain, not generic)
### Follow-Up Patterns (4 patterns — what they do when answers are vague, partial, or evasive)
### Escalation Patterns (3 examples — their strongest, most pointed challenges)

## Satisfaction Criteria
### Will Accept (5+ items — specific types of answers that satisfy this panelist)
### Will NOT Accept (5+ items — specific types of answers they reject)

## Context Triggers
- List of 8-12 specific topics/claims that activate this panelist's attention

## Intensity Scaling
- Table with Friendly / Moderate / Adversarial rows
- Columns: Opening Style, Follow-Up Style, Escalation

## Relationship with Other Agents
- How this panelist interacts with each other panel member

CRITICAL RULES:
- The persona must feel like a REAL person, not a generic archetype
- Initial questions must be specific to the domain, not usable by any panelist
- Satisfaction criteria must be concrete and testable, not vague
- The voice must match the personality (authoritative people get deeper voices, etc.)
- Follow-up patterns must describe what the panelist does with bad answers — not just what they say
```

**Domain Knowledge Generation Meta-Prompt:**

```
You are an expert in {domain} creating a domain knowledge reference for an AI panelist.
This document will be used by an LLM to generate contextually sharp questions during a
simulated boardroom presentation.

PANELIST PERSONA:
{generated_persona_summary}

USER'S BRIEF:
{user_brief}

Generate a domain-knowledge.md file with EXACTLY this structure:

## Red Flags in Presentations
- 12-15 specific patterns this expert watches for in presentations
- Organized by category (e.g., "Regulatory Red Flags", "Data Integrity Red Flags")
- Each red flag should explain WHY it's a concern, not just WHAT it is

## Industry Benchmarks
- Real, specific benchmarks for the relevant domain
- Include actual numbers where possible (typical ranges, not single values)
- Organized by metric category

## Questioning Frameworks
- 3-4 structured frameworks for how this panelist evaluates different types of claims
- Each framework: 4-5 specific questions in logical order

## Common Pitfalls This Expert Challenges
- 6-8 common mistakes or bad practices in this domain
- Each with: the pitfall, why presenters fall into it, and the expert's typical challenge

CRITICAL RULES:
- Use REAL domain knowledge — actual frameworks, real benchmarks, genuine best practices
- Do NOT make up statistics — use well-known industry ranges or omit specific numbers
- Be specific to the domain — a regulatory expert's red flags are completely different from a financial expert's
- Frameworks should be actionable — a developer could implement them as decision trees
- Include enough detail that an LLM reading this could ask expert-level questions
```

### 8.4.5 Validation Schema

Every generated agent template is validated against this schema before being accepted:

```json
{
  "persona": {
    "required_sections": [
      "Identity",
      "Personality",
      "Voice Configuration",
      "Questioning Style",
      "Questioning Style > Initial Questions (min 5)",
      "Questioning Style > Follow-Up Patterns (min 3)",
      "Questioning Style > Escalation Patterns (min 2)",
      "Satisfaction Criteria > Will Accept (min 4)",
      "Satisfaction Criteria > Will NOT Accept (min 4)",
      "Context Triggers (min 6)",
      "Intensity Scaling (3 levels × 3 columns)",
      "Relationship with Other Agents"
    ],
    "identity_required_fields": [
      "Name", "Title", "Role", "Agent ID", "Color", "Avatar"
    ],
    "voice_required_fields": [
      "Tone", "Pace", "Gemini Live Voice", "Speed", "Pitch"
    ]
  },
  "domain_knowledge": {
    "required_sections": [
      "Red Flags (min 8 items)",
      "Industry Benchmarks (min 1 category)",
      "Questioning Frameworks (min 2 frameworks × 4 questions each)",
      "Common Pitfalls (min 4 items)"
    ]
  }
}
```

If validation fails, the system runs targeted follow-up LLM calls to fill gaps — it does NOT return an incomplete template to the user.

### 8.4.6 Customization of Existing Agents

When modifying a default agent, the system uses a MERGE strategy — not a full regeneration:

```
MODIFICATION FLOW:

1. User selects default agent (e.g., Marcus Webb — Skeptic)
2. User provides modification brief:
   "Make Marcus more focused on biotech financial metrics.
    He should know about burn rate for clinical-stage companies,
    typical Series B/C biotech raises, and FDA approval probability
    impact on valuation."

3. System reads existing persona.md and domain-knowledge.md

4. LLM generates DELTA changes:
   - persona.md: Add biotech context triggers, adjust questioning examples
   - domain-knowledge.md: Add biotech financial benchmarks, clinical-stage
     burn rates, FDA probability frameworks

5. System MERGES deltas into copies of the originals:
   - Core personality, voice, satisfaction criteria: PRESERVED
   - Domain knowledge: EXTENDED with new biotech expertise
   - Context triggers: EXTENDED with biotech-specific triggers
   - Example questions: PARTIALLY REPLACED with biotech-relevant ones

6. Result: "Marcus Webb (Biotech Variant)" — same skeptical CFO personality,
   now armed with biotech-specific financial expertise
```

### 8.4.7 Custom Agent Storage

Custom agents are stored in a user-scoped area that mirrors the template structure:

```
agents/
├── templates/                     ← System defaults (immutable)
│   ├── skeptic/persona.md
│   ├── skeptic/domain-knowledge.md
│   └── ...
│
├── custom/                        ← User-created and modified agents
│   └── {user_id}/
│       ├── library.json           ← Index of all user's custom agents
│       ├── marcus-biotech/        ← Modified default
│       │   ├── persona.md
│       │   ├── domain-knowledge.md
│       │   └── meta.json          ← Source: "modified", base: "skeptic", created: "..."
│       ├── regulatory-expert/     ← Created from scratch
│       │   ├── persona.md
│       │   ├── domain-knowledge.md
│       │   └── meta.json          ← Source: "generated", archetype: "specialist", created: "..."
│       └── investor-vp/           ← Created from scratch
│           ├── persona.md
│           ├── domain-knowledge.md
│           └── meta.json
│
└── sessions/{session_id}/         ← Runtime (uses whatever agents are assigned)
    ├── shared/
    ├── seat_1/                    ← Could be default OR custom agent
    ├── seat_2/
    ├── seat_3/
    └── seat_4/
```

**Custom Agent Meta Schema:**

```json
{
  "id": "regulatory-expert",
  "userId": "user_abc123",
  "name": "Dr. Sarah Lin",
  "title": "Former FDA Reviewer",
  "role": "Regulatory Compliance Expert",
  "source": "generated",
  "archetype": "specialist",
  "baseAgent": null,
  "userBrief": "I need a regulatory expert, former FDA reviewer, who focuses on compliance risk and approval timelines. She should be tough but fair.",
  "createdAt": "2026-02-18T14:30:00Z",
  "updatedAt": "2026-02-18T14:35:00Z",
  "generationModel": "gemini-2.0-flash",
  "validationPassed": true,
  "sessionsUsed": 3,
  "averageRelevanceRating": 4.2
}
```

### 8.4.8 Session Panel Assembly

Before a session, the user assembles their panel from available agents:

```
PANEL CONFIGURATION (Pre-Session Setup)

Seat 1: [Moderator]  Diana Chen (default)     ← Always moderator role
Seat 2: [Challenger]  Marcus Webb (Biotech)    ← Modified default
Seat 3: [Analyst]     Priya Sharma (default)   ← Original default
Seat 4: [Specialist]  Dr. Sarah Lin            ← Custom-generated
Seat 5: [Empty]       + Add panelist           ← Optional 5th/6th seat

Panel Rules:
- Seat 1 is always a Moderator (default Diana, or custom Moderator variant)
- Seats 2-6 can be any mix of default, modified, or custom agents
- Minimum 3 panelists (1 moderator + 2 others), maximum 6
- System warns if panel lacks coverage (e.g., no financial challenger)
```

When the session starts, the Orchestrator resolves each seat to the correct template:
- Default agent → read from `agents/templates/{agent}/`
- Custom agent → read from `agents/custom/{user_id}/{agent_id}/`
- Session-scoped mutable files are created in `agents/sessions/{session_id}/seat_{n}/` regardless

### 8.4.9 Iterative Refinement

Users can refine generated agents through conversation:

```
User: "Create a regulatory expert focused on FDA compliance."
System: [Generates Dr. Sarah Lin with persona + domain knowledge]
System: "Here's your new panelist — Dr. Sarah Lin, former FDA reviewer.
         Here are sample questions she'd ask at each intensity level..."

User: "Good, but make her more aggressive. She should specifically
       focus on 510(k) vs PMA pathway decisions and post-market
       surveillance requirements."

System: [LLM generates DELTA changes to persona + domain knowledge]
System: "Updated. Dr. Lin now pushes harder on regulatory pathway
         choices and has deep knowledge of post-market requirements.
         Here are updated sample questions..."

User: "Perfect. Save her to my library."
System: [Stores in agents/custom/{user_id}/regulatory-expert/]
```

Each refinement iteration:
1. Reads the current generated files
2. Applies the user's feedback as a delta
3. Re-validates against the schema
4. Shows updated preview with sample questions
5. User confirms or continues refining

### 8.4.10 Quality Guardrails

To ensure generated agents meet the quality bar of hand-crafted defaults:

**Content Quality:**
- Generated domain knowledge must reference real frameworks, not invented ones
- Benchmarks must use well-known industry ranges (LLM should flag if unsure)
- Satisfaction criteria must be concrete and testable
- Example questions must be specific to the domain, not generic boardroom filler

**Behavioral Compatibility:**
- Generated agents must follow the same exchange protocol (SATISFIED/FOLLOW_UP/ESCALATE)
- Intensity scaling must be defined for all three levels
- Context triggers must be specific enough for the pre-generation pipeline
- Voice configuration must be assigned (auto-selected based on persona characteristics)

**Safety:**
- Generated agents must not embody harmful stereotypes
- Names and backgrounds should reflect diverse representation
- Agent behavior must stay within professional boardroom norms regardless of user instructions
- System rejects requests to create agents that harass, demean, or personally attack the presenter

---

## 9. AI Agent Specifications

### 9.1 Agent Persona Definitions

#### Diana Chen — The Moderator

| Attribute | Value |
|-----------|-------|
| Role | Meeting Chair / Orchestrator / Exchange Manager |
| Title | Chief of Staff |
| Personality | Professional, warm but efficient. Keeps the meeting on track. Knows when to let an exchange run and when to intervene. |
| Primary Functions | (1) Manage turn-taking and session flow. (2) Manage multi-turn exchanges — monitor depth, enforce turn limits, intervene when circular. (3) Bridge between exchanges and presentation seamlessly. (4) Track unresolved challenges. (5) Manage cross-agent pile-ons. |
| Speaking Patterns | Opens the session with a brief welcome. Announces Q&A windows. Calls on agents by name. Provides time warnings. Uses natural transition phrases to bridge back. Closes the session with a brief wrap-up. During exchanges, uses micro-phrases ("Mm-hmm", "Interesting point") to maintain presence. |
| Voice | Warm, professional, moderate pace, clear enunciation |

#### Marcus Webb — The Skeptic

| Attribute | Value |
|-----------|-------|
| Role | Financial / Feasibility Challenger |
| Title | CFO |
| Personality | Experienced, direct, slightly impatient. Has seen many pitches fail. |
| Primary Function | Challenges financial projections, ROI claims, and overall feasibility |
| Initial Question Style | "What's your contingency if...?", "What evidence supports...?", "I've seen this before and..." |
| Follow-Up Behavior | Pushes for specifics when answers are general. Points out when presenter repeats the same data point. Escalates by identifying contradictions between verbal answers and deck data. |
| Satisfaction Criteria | Accepts specific data with sources, stress-test results with numbers, honest acknowledgments of risk with mitigation plans. Does NOT accept restated claims, vague references to "our model shows", or deflection to appendix materials. |
| Context Triggers | Revenue projections, margin assumptions, burn rate, unit economics, payback period, competitive pricing, external market data that contradicts claims |
| Intensity Scaling | Friendly: "Can you help me understand...?" Moderate: "I'm not convinced that..." Adversarial: "These numbers don't hold up. Show me..." |
| Voice | Deep, authoritative, measured pace, occasional skeptical tone |

#### Priya Sharma — The Analyst

| Attribute | Value |
|-----------|-------|
| Role | Data & Methodology Deep-Diver |
| Title | VP of Strategy |
| Personality | Thorough, methodical, genuinely curious. Wants to understand the details. |
| Primary Function | Requests supporting data, questions methodology, validates analytical rigor |
| Initial Question Style | "Walk me through the methodology for...", "What's the sample size?", "Can you show the sensitivity analysis?" |
| Follow-Up Behavior | Drills into methodology when answer is surface-level. Asks for confidence intervals or ranges when presented with point estimates. Connects data gaps across slides. |
| Satisfaction Criteria | Accepts detailed methodology descriptions, specific sample sizes and confidence levels, sensitivity analyses with variable ranges. Does NOT accept "industry standard" without specifics, single data points without context, or methodology described only at a high level. |
| Context Triggers | Data sources, sample sizes, confidence intervals, methodology, benchmarks, comparable analysis, sensitivity analysis, statistical validity |
| Intensity Scaling | Friendly: "I'd love to see more detail on..." Moderate: "The data here is thin. Can you..." Adversarial: "This analysis is insufficient. Where's the..." |
| Voice | Clear, measured, slightly formal, precise word choice |

#### James O'Brien — The Contrarian

| Attribute | Value |
|-----------|-------|
| Role | Logic & Assumption Challenger |
| Title | Board Advisor |
| Personality | Experienced, philosophical, enjoys poking holes. Plays devil's advocate deliberately. |
| Primary Function | Identifies logical gaps, contradictions, and unexplored worst-case scenarios |
| Initial Question Style | "What if the opposite is true?", "You're assuming X but what if...?", "Walk me through the failure scenario" |
| Follow-Up Behavior | When presenter addresses one risk, identifies the second-order risk behind it. Points out logical tensions between different parts of the presentation. Uses external intelligence to present real-world failure precedents. |
| Satisfaction Criteria | Accepts honest acknowledgment of risks with specific mitigation strategies, scenario analysis showing resilience, examples of how the team has handled similar challenges. Does NOT accept dismissal of risks, "we'll figure it out", or optimism without evidence. |
| Context Triggers | Unstated assumptions, logical dependencies, single points of failure, market timing risks, competitive responses, behavioral change assumptions, precedents from external intelligence |
| Intensity Scaling | Friendly: "Have you considered what happens if...?" Moderate: "There's a tension here between X and Y..." Adversarial: "This entire thesis collapses if..." |
| Voice | Gravelly, deliberate pace, thoughtful pauses, occasionally provocative |

### 9.2 Agent Coordination Rules

- No two agents should ask about the same specific claim simultaneously
- The Moderator tracks which topics have been covered and steers agents toward uncovered areas
- If a presenter gives an unsatisfactory answer, the same agent may follow up according to exchange rules (section 6) — NOT indefinitely
- Agents should reference each other's exchanges when relevant ("Building on what Marcus just explored with the margin question...")
- The Contrarian should never repeat the Skeptic's financial concerns — the Contrarian challenges logic and assumptions, the Skeptic challenges numbers and feasibility
- The Analyst should not repeat the Contrarian's logical challenges — the Analyst focuses on data and methodology
- Total agent speaking time should not exceed 40% of the session; the presenter should speak at least 60%
- During an exchange, only the active agent and the presenter speak — other agents and the Moderator observe silently (except for Moderator micro-phrases)

### 9.3 Gemini Live Voice Configuration

Each agent requires a distinct voice profile in Gemini Live:

| Agent | Voice Characteristics | Gemini Live Config |
|-------|----------------------|-------------------|
| Diana Chen | Warm, professional female, moderate pace | Voice: Kore or Aoede, pitch: neutral, speed: 1.0 |
| Marcus Webb | Deep, authoritative male, measured | Voice: Charon or Fenrir, pitch: low, speed: 0.95 |
| Priya Sharma | Clear, precise female, slightly formal | Voice: Aoede or Leda, pitch: neutral-high, speed: 1.05 |
| James O'Brien | Gravelly, deliberate male, thoughtful pauses | Voice: Orus or Puck, pitch: low, speed: 0.9 |

Note: Exact Gemini Live voice names may change — the key requirement is four distinctly different voices that match the persona characteristics.

---

## 10. Data Models

### 10.1 User

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

### 10.2 Session

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
  "totalExchanges": 5,
  "unresolvedChallenges": 2,
  "scores": {
    "overall": 78,
    "clarity": 82,
    "confidence": 71,
    "dataSupport": 85,
    "handling": 68,
    "exchangeResilience": 72,
    "structure": 80
  },
  "recordingUrl": "https://storage.highstake.app/recordings/session_xyz789.webm",
  "transcriptUrl": "https://storage.highstake.app/transcripts/session_xyz789.json",
  "reportUrl": "https://storage.highstake.app/reports/session_xyz789.pdf"
}
```

### 10.3 Exchange Record

```json
{
  "id": "exchange_001",
  "sessionId": "session_xyz789",
  "slideIndex": 3,
  "startTime": 125.4,
  "endTime": 159.2,
  "primaryAgent": "skeptic",
  "triggerClaim": "40% gross margins by year two",
  "turns": [
    {
      "turn": 1,
      "speaker": "agent",
      "agentId": "skeptic",
      "text": "What evidence supports 40% margins by year two?",
      "timestamp": 130.2,
      "source": "pre-generated"
    },
    {
      "turn": 1,
      "speaker": "presenter",
      "text": "Based on our enterprise pipeline and unit economics.",
      "timestamp": 133.5,
      "hedgingDetected": false,
      "fillerWords": []
    },
    {
      "turn": 2,
      "speaker": "agent",
      "agentId": "skeptic",
      "text": "Your pipeline is early stage. What if conversion is half projected?",
      "timestamp": 140.1,
      "evaluation": "FOLLOW_UP",
      "source": "streaming"
    },
    {
      "turn": 2,
      "speaker": "presenter",
      "text": "Stress-tested: still hit 28% margins in downside case.",
      "timestamp": 143.8,
      "hedgingDetected": false,
      "newDataPoint": "28% downside margins"
    },
    {
      "turn": 3,
      "speaker": "agent",
      "agentId": "skeptic",
      "text": "28% vs 40% is a 12-point range. Has the board seen this range?",
      "timestamp": 149.0,
      "evaluation": "ESCALATE",
      "source": "streaming"
    },
    {
      "turn": 3,
      "speaker": "presenter",
      "text": "Plan to include range analysis in appendix materials.",
      "timestamp": 152.3,
      "hedgingDetected": true,
      "deflection": true
    }
  ],
  "outcome": "MODERATOR_INTERVENED",
  "agentFinalEvaluation": "NOT_SATISFIED",
  "unresolvedChallenge": "Margin range (28-40%) not presented upfront; deferred to appendix",
  "pileOn": null,
  "moderatorBridgeBack": "Good exchange. Marcus, you've surfaced an important point about presenting the margin range upfront. Let's flag that for the debrief."
}
```

### 10.4 Transcript Entry

```json
{
  "sessionId": "session_xyz789",
  "index": 42,
  "speaker": "presenter",
  "text": "Our customer acquisition cost is currently $45, which we expect to decrease to $28 as we scale.",
  "startTime": 342.5,
  "endTime": 349.8,
  "slideIndex": 3,
  "type": "presentation",
  "exchangeId": null,
  "detectedClaims": ["CAC $45 current", "CAC $28 target"],
  "fillerWords": [],
  "hedgingLanguage": false
}
```

### 10.5 Debrief Coaching Item

```json
{
  "sessionId": "session_xyz789",
  "area": "Exchange Resilience",
  "priority": "high",
  "detail": "When Marcus escalated his margin challenge (exchange_001, turn 3), you deflected to 'appendix materials' instead of addressing the 28-40% range directly. In the real meeting, prepare a slide or verbal bridge that says: 'Our base case is 40%, but we've stress-tested to 28% in a downside scenario — here's what that means for timeline and break-even.' Own the range; don't hide it.",
  "exchangeRef": "exchange_001",
  "transcriptTimestamp": 149.0
}
```

---

## 11. API Contracts

### 11.1 REST Endpoints

```
POST   /api/sessions                  Create a new session with configuration
GET    /api/sessions/:id              Get session details and status
PATCH  /api/sessions/:id              Update session (end session, update config)
DELETE /api/sessions/:id              Delete a session and associated data

POST   /api/decks/upload              Upload and parse a presentation deck
GET    /api/decks/:id                 Get deck manifest
GET    /api/decks/:id/dossier         Get Board Preparation Dossier
GET    /api/decks/:id/slides/:index   Get slide thumbnail image

GET    /api/sessions/:id/transcript   Get full session transcript
GET    /api/sessions/:id/exchanges    Get all exchange records
GET    /api/sessions/:id/debrief      Get debrief data (scores, coaching, summary)
GET    /api/sessions/:id/recording    Get recording URL (signed, time-limited)
GET    /api/sessions/:id/report       Download PDF report

GET    /api/users/me                  Get current user profile
GET    /api/users/me/sessions         List user's session history
GET    /api/users/me/stats            Get aggregate stats (avg score, trends)
```

### 11.2 WebSocket Events

```
Client → Server:
  audio_chunk          { data: ArrayBuffer, timestamp: number }
  slide_change         { slideIndex: number }
  presenter_response   { text: string }  // text fallback
  end_session          {}
  acknowledge_hand     { agentId: string }  // hand-raise mode

Server → Client:
  transcript_segment   { text, startTime, endTime, confidence, isFinal }
  agent_question       { agentId, text, audioChunks[], slideRef?, exchangeId }
  agent_follow_up      { agentId, text, audioChunks[], evaluation, turn, exchangeId }
  agent_satisfied      { agentId, text, audioChunks[], exchangeId }
  agent_hand_raise     { agentId }
  agent_thinking       { agentId, duration_ms }
  agent_lead_in        { agentId, audioChunk, text }
  moderator_message    { text, audioChunks[], type: "transition"|"bridge"|"micro" }
  exchange_started     { exchangeId, primaryAgentId, triggerClaim }
  exchange_ended       { exchangeId, outcome, unresolvedChallenge? }
  pile_on_offered      { agentId, exchangeId }
  session_state        { state: "presenting"|"q_and_a"|"exchange"|"resolving" }
  time_warning         { remainingMinutes: number }
  session_ended        { debriefUrl: string }
```

---

## 12. Non-Functional Requirements

### 12.1 Performance

| Metric | Target | Critical Threshold |
|--------|--------|--------------------|
| STT Latency (Gemini Live) | < 400ms from speech to transcript | < 800ms |
| Pre-generated Question Availability | Ready before needed (background) | < 2s after slide change |
| Agent Initial Question (pre-gen'd) | ~0ms perceived (audio buffered) | < 500ms |
| Agent Follow-Up (streaming chain) | < 800ms to first audio | < 1500ms |
| Moderator Transition Phrase | ~0ms (pre-buffered) | < 300ms |
| Deck Parsing + Enrichment | < 30s for 20-slide deck | < 60s |
| UI Frame Rate | 60fps during session | 30fps minimum |
| Page Load | < 2s initial load | < 4s |
| Recording Start | < 500ms from session start | < 1s |

### 12.2 Scalability

- Support 100 concurrent sessions at launch
- Scale to 1,000 concurrent sessions within 6 months
- Each session: 1 WebSocket connection, 1 Gemini Live STT stream, intermittent LLM calls (pre-gen + exchange), intermittent TTS streams
- Concurrent Gemini API calls per session: avg 2-3, peak 6 (during pre-gen refresh + active exchange)
- Deck storage: 10GB per 1,000 users
- Recording storage: 500MB per session (20-minute session at 720p)

### 12.3 Reliability

- 99.9% uptime for the web application
- Graceful degradation: if TTS fails, fall back to text-only with chat panel
- Graceful degradation: if STT fails, allow slide-triggered questions only
- Graceful degradation: if external enrichment fails, proceed without Layer 5 context
- Auto-save session state every 30 seconds
- Recording buffer: 60 seconds local buffer before upload
- Pre-generation pipeline failures should never block the live session

### 12.4 Security & Privacy

- All data encrypted at rest (AES-256) and in transit (TLS 1.3)
- Presentation decks are private to the uploading user by default
- Session recordings stored with signed, time-limited access URLs
- No presentation content used for AI model training
- SOC 2 Type II compliance target within 12 months
- GDPR-compliant data handling with right to deletion
- User can delete all data (recordings, transcripts, decks) at any time
- External enrichment searches do not include presenter name or company in queries (privacy)

### 12.5 Browser Support

- Chrome 100+ (primary)
- Firefox 100+ (secondary)
- Safari 16+ (secondary)
- Edge 100+ (secondary)
- Mobile browsers: responsive design for review/debrief, but live session requires desktop

### 12.6 Accessibility

- WCAG 2.1 AA compliance for all non-session UI
- Keyboard navigation for setup and debrief phases
- Screen reader support for transcript and debrief content
- High contrast mode option
- Closed captions for agent audio during session (real-time transcript display)

---

## 13. Phased Delivery Plan

### Phase 1 — MVP (Complete)

**Goal:** Validate the core experience with a functional UI prototype.

**Delivered:**
- Moderator-led setup flow (interaction mode, intensity, focus areas, deck upload)
- Video-call-style meeting UI with 4 agent tiles and presenter tile
- Simulated agent questions triggered by slide advancement
- Slide viewer with navigation
- Chat panel with timestamped agent messages
- Post-session debrief with scores, transcript, coaching, and summary
- Demo deck mode for testing without upload

**Status:** Complete. Agents use pre-written questions. No real STT/TTS/LLM integration.

### Phase 2 — Core Intelligence + Real-Time Engine

**Goal:** Replace simulation with real AI intelligence and achieve natural conversational rhythm.

**Deliverables:**
- Gemini Live API integration for real-time STT (presenter speech → transcript)
- Gemini LLM integration for dynamic, contextual agent questions with 5-layer context stack
- Gemini Live TTS integration with distinct voices per agent
- Session-scoped agent context system (templates/ + sessions/{id}/ architecture)
- Background pre-generation pipeline (questions + audio buffered while presenter speaks)
- Streaming LLM → TTS chain for follow-up questions
- Latency compensation system (Moderator stalling, thinking indicators, lead-in phrases)
- Multi-turn exchange system (PRESENTING → Q&A → EXCHANGE → RESOLVING state machine)
- Agent follow-up evaluation logic (SATISFIED / FOLLOW_UP / ESCALATE)
- Moderator exchange management (turn limits, bridge-backs, pile-on control)
- Presenter profile tracking per agent (behavioral learning within session)
- PPTX/PDF parsing with text, structure, and claim extraction
- External intelligence enrichment pipeline (web search for news, market data)
- Board Preparation Dossier generation
- Webcam capture and session recording via MediaRecorder API
- Dynamic scoring engine based on actual transcript and exchange analysis
- Post-session coaching generated with full session context including exchange outcomes
- Unresolved challenges tracking and debrief tab

**Estimated Timeline:** 10-14 weeks.

### Phase 3 — Custom Agents, Polish & Scale

**Goal:** Production-grade experience with custom panel composition and enterprise features.

**Deliverables:**
- **Custom Agent Builder:**
  - Natural-language agent creation ("I need a regulatory expert who grills me on FDA compliance")
  - LLM-powered generation pipeline producing persona.md + domain-knowledge.md
  - Meta-prompts for persona generation and domain knowledge generation
  - Validation schema ensuring generated agents meet quality bar of hand-crafted defaults
  - Modification of existing default agents (merge strategy preserving core personality)
  - Iterative refinement through conversation
  - Preview with sample questions at each intensity level and voice sample
  - User agent library (save, reuse, share, duplicate, delete)
  - Panel assembly UI: assign any mix of default + custom agents to panel seats
  - Support for 3-6 panelists per session (up from fixed 4)
- Session recording playback with timeline scrubbing and jump-to-exchange
- Multi-session dashboard with improvement tracking, score trends, and exchange resilience trends
- PDF report generation and export with exchange summaries
- Presentation template library
- Mobile-responsive debrief and dashboard

**Estimated Timeline:** 10-14 weeks.

### Phase 4 — Enterprise & Growth

**Goal:** Enterprise readiness and market expansion.

**Deliverables:**
- User accounts with authentication (Clerk/Auth0)
- Team/organization accounts with shared agent libraries and session libraries
- SSO integration (SAML/OIDC)
- Admin dashboard for team managers
- API for LMS/training platform integration
- Custom branding (white-label)
- Advanced analytics (speaking pace over time, vocabulary complexity, emotional tone via video analysis)
- AI-generated "challenge playbook" based on deck content (pre-session prep tool)
- Calendar integration (schedule practice sessions)
- Benchmark data ("presenters at your level typically score X")
- SOC 2 Type II certification
- Multi-language support (English first, then Mandarin, Spanish, Japanese, German)
- Persistent agent memory across sessions for the same deck (agents remember prior session weaknesses)

**Estimated Timeline:** 12-16 weeks.

---

## 14. Success Metrics

### 14.1 Product Metrics

| Metric | Phase 1 | Phase 2 | Phase 3 |
|--------|---------|---------|---------|
| Session Completion Rate | 70% | 80% | 85% |
| Avg Session Duration | 10min | 18min | 22min |
| Avg Exchanges Per Session | — | 4-6 | 5-8 |
| Avg Exchange Turns | — | 2.2 | 2.5 |
| Repeat Usage (2+ sessions) | 30% | 50% | 65% |
| Debrief Engagement (all tabs) | 40% | 55% | 70% |
| NPS Score | — | 40+ | 55+ |

### 14.2 Technical Metrics — Real-Time Performance

| Metric | Target |
|--------|--------|
| Perceived agent response latency (initial question) | < 500ms (via pre-generation) |
| Perceived agent response latency (follow-up) | < 1500ms (via streaming + masking) |
| STT Accuracy | > 95% |
| Agent Question Relevance (user-rated) | > 85% |
| Follow-Up Relevance (user-rated) | > 80% |
| Pre-Generation Hit Rate (question used vs discarded) | > 75% |
| Session Recording Success Rate | > 99% |
| System Uptime | 99.9% |

### 14.3 Business Metrics (Post-Launch)

| Metric | 6-Month Target | 12-Month Target |
|--------|----------------|-----------------|
| Monthly Active Users | 500 | 5,000 |
| Paying Customers | 50 | 500 |
| Monthly Recurring Revenue | $5K | $75K |
| Enterprise Accounts | 2 | 15 |

---

## 15. Open Questions & Decisions

| # | Question | Options | Status |
|---|----------|---------|--------|
| 1 | Should agents have persistent memory across sessions for the same deck? | A) No, each session is independent. B) Yes, agents remember prior sessions and push on unresolved issues from before. | Phase 4 target |
| 2 | Should we support real-time video analysis (facial expressions, body language) for confidence scoring? | A) Phase 4 — adds significant value for delivery coaching. B) Out of scope — too complex and privacy-sensitive. | Open |
| 3 | What is the pricing model? | A) Freemium (3 sessions/month free, $49/mo Pro). B) Flat subscription ($29/mo individual, $199/mo team). C) Per-session pricing ($5/session). | Open |
| 4 | Should presenters be able to "pause" an exchange and say "let me come back to that"? | A) Yes — Moderator parks the question and returns to it later. B) No — exchanges must resolve before continuing. | Leaning A |
| 5 | Should the app support collaborative sessions (multiple human presenters or observers)? | A) Phase 4 — useful for team presentations. B) Out of scope. | Open |
| 6 | Should we offer a "Gemini + Claude" option where different agents use different LLMs? | A) Yes — each agent could use the LLM best suited to their persona. B) No — single provider simplifies architecture. | Open |
| 7 | Should the Board Preparation Dossier be a standalone paid feature (no session required)? | A) Yes — valuable even without the simulation. B) No — keep it bundled. | Leaning A |
| 8 | How should we handle presenter responses during exchanges — voice only or also text? | A) Voice only (most realistic). B) Voice primary with text fallback. | Leaning B |
| 9 | Should the Moderator have a "mercy" mode where it intervenes if the presenter seems overwhelmed? | A) Yes — detect stress signals and offer a break. B) No — the presenter chose the intensity level. | Open |
| 10 | Should agents be able to reference the presenter's body language ("I notice you seem less confident about this slide")? | A) Phase 4 with video analysis. B) Out of scope — too intrusive. | Open |
| 11 | Should there be a marketplace for community-created agent templates? | A) Yes — users can share/sell custom agents. B) No — keep it user-private. C) Team sharing only. | Open |
| 12 | What LLM should power the custom agent generation pipeline? | A) Same LLM as agent intelligence (Gemini). B) Best available (Claude for generation quality, Gemini for runtime). C) User chooses. | Leaning B |
| 13 | Should custom agents be able to replace the Moderator, or is the Moderator always Diana? | A) Moderator is customizable (e.g., different meeting culture). B) Moderator is fixed — only challenger roles are customizable. | Leaning A |
| 14 | How many custom agents should free-tier users be able to create? | A) 0 — custom agents are Pro only. B) 1-2 custom agents on free tier. C) Unlimited creation, limited to 3 sessions/month. | Open |

---

## 16. Appendix

### A. Competitive Landscape

| Competitor | Approach | HighStake Differentiation |
|-----------|----------|---------------------------|
| Pitch practice with colleagues | Manual scheduling, social dynamics, pulled punches | AI agents on-demand, no social friction, configurable intensity, multi-turn exchanges |
| Executive coaches | $500-2000/session, scheduling, single perspective | Fraction of cost, instant availability, multi-perspective panel with follow-ups |
| Yoodli, Poised | Delivery metrics only (filler words, pace) | Full boardroom simulation with contextual Q&A, multi-turn exchanges, and real-world intelligence |
| VR presentation simulators | Audience simulation without intelligent interaction | Intelligent, adversarial questioning with multi-turn exchanges grounded in deck content and current events |
| ChatGPT / Gemini (raw) | No structure, no personas, no real-time voice interaction | Purpose-built experience with orchestration, distinct personas, exchange management, and comprehensive debrief |

### B. Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Gemini Live API latency exceeds targets | High | Medium | Pre-generation pipeline + streaming chain + latency masking (3-layer strategy) |
| Agent follow-up quality is inconsistent | High | Medium | Structured evaluation prompt with JSON output; rigorous testing of SATISFIED/FOLLOW_UP/ESCALATE decisions |
| Exchanges become repetitive or circular | Medium | Medium | Moderator enforces turn limits; agent coordination rules prevent redundancy; exchange outcome tracking |
| Context window overflow for long sessions | Medium | High | Tiered compression strategy (section 5.8) — full recent context, summarized older context |
| External enrichment returns irrelevant or misleading results | Medium | Medium | Relevance filtering, recency bias, source quality scoring; graceful degradation (proceed without Layer 5 if quality is low) |
| User audio quality varies widely | Medium | High | Audio quality check at session start; provide recommendations; noise suppression in pipeline |
| Enterprise security requirements block adoption | High | Medium | Prioritize SOC 2; offer on-premise option in Phase 4 |
| Gemini Live voice quality or variety insufficient | Medium | Medium | Fall back to ElevenLabs as alternative TTS provider; abstract TTS layer for swappability |
| Pre-generation pipeline consumes too many API calls (cost) | Medium | Medium | Smart refresh triggers (only on significant context changes, not continuous); candidate caching |
| Presenter finds multi-turn exchanges too intense | Low | Medium | Intensity level controls exchange depth; "mercy mode" as potential Phase 3 feature |
| LLM-generated agent templates are lower quality than hand-crafted defaults | Medium | Medium | Structured meta-prompts, validation schema, required section checklist, iterative refinement loop, quality rating tracking per agent |
| Users create agents that behave inappropriately or break session dynamics | Low | Low | Safety guardrails in generation pipeline, validation against behavioral compatibility rules, Moderator always enforces session protocol regardless of custom agent behavior |
| Custom agent domain knowledge contains fabricated benchmarks | Medium | Medium | Meta-prompt explicitly instructs "do not invent statistics"; validation step flags unverifiable claims; user can report inaccuracies |

### C. Glossary

| Term | Definition |
|------|-----------|
| Exchange | A multi-turn dialogue between one agent and the presenter, managed by the Moderator |
| Turn | One agent statement + one presenter response within an exchange |
| Pile-On | A second agent adding a related question after the primary exchange resolves |
| Bridge-Back | The Moderator's transition phrase that returns the session from an exchange to the presentation |
| Pre-Generation | Background pipeline that generates agent questions and TTS audio before they're needed |
| Streaming Chain | LLM → TTS pipeline where tokens stream directly to voice synthesis for minimal latency |
| Lead-In Phrase | Pre-recorded short phrase that plays instantly while the full streaming response loads |
| Latency Masking | Techniques that hide computation time behind natural conversational elements |
| Context Stack | The 5-layer information structure assembled for each agent LLM call |
| Board Preparation Dossier | Pre-session report summarizing external intelligence relevant to the deck |
| Unresolved Challenge | An exchange where the agent was not satisfied when the Moderator intervened |
| Candidate Validation | Quick check to confirm a pre-generated question is still relevant before playing it |
| Agent Template | Immutable persona.md + domain-knowledge.md that define an agent's character and expertise |
| Custom Agent | User-created or user-modified panelist generated by the LLM-powered agent builder |
| Meta-Prompt | System prompt used to instruct the LLM to generate agent templates from a user's brief |
| Agent Library | User's collection of custom and modified agents, reusable across sessions |
| Panel Assembly | Pre-session step where the user assigns agents to panel seats |
| Merge Strategy | Method for modifying default agents — preserves core personality, extends domain expertise |
| Presenter Profile | Per-agent behavioral model of the presenter, built during the session from exchange observations |
