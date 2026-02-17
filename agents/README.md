# Agent Context System

Each AI panelist in HighStake has a dedicated folder that stores their persona definition, domain knowledge, session context, and real-time intelligence. These markdown files are assembled into the agent's context payload before each LLM call.

## Folder Structure

```
agents/
├── README.md                  ← You are here
├── shared/                    ← Context shared across all agents
│   ├── session-config.md      ← Current session configuration
│   ├── deck-content.md        ← Parsed deck text, claims, structure
│   ├── external-intel.md      ← News, market data, competitive moves
│   ├── board-dossier.md       ← Pre-session Board Preparation Dossier
│   └── exchange-history.md    ← All exchanges, outcomes, unresolved challenges
│
├── moderator/                 ← Diana Chen — The Moderator
│   ├── persona.md             ← Identity, personality, voice
│   ├── orchestration.md       ← Turn-taking rules, state machine, bridge-backs
│   ├── session-state.md       ← Live: current state, topics covered, time tracking
│   └── phrases.md             ← Pre-generated transition and stalling phrases
│
├── skeptic/                   ← Marcus Webb — The Skeptic
│   ├── persona.md             ← Identity, personality, voice, questioning style
│   ├── domain-knowledge.md    ← Financial frameworks, benchmarks, red flags
│   ├── focus-brief.md         ← Session-specific: claims to challenge, deck weaknesses
│   ├── exchange-notes.md      ← Live: questions asked, responses received, evaluations
│   └── candidate-question.md  ← Pre-generated question buffer (refreshed continuously)
│
├── analyst/                   ← Priya Sharma — The Analyst
│   ├── persona.md
│   ├── domain-knowledge.md
│   ├── focus-brief.md
│   ├── exchange-notes.md
│   └── candidate-question.md
│
└── contrarian/                ← James O'Brien — The Contrarian
    ├── persona.md
    ├── domain-knowledge.md
    ├── focus-brief.md
    ├── exchange-notes.md
    └── candidate-question.md
```

## How Context is Assembled

When the Orchestrator needs to generate a question or follow-up for an agent, it assembles the context by reading files in this order:

1. `agents/{agent}/persona.md` — Who am I?
2. `agents/shared/session-config.md` — What are the rules of this session?
3. `agents/shared/deck-content.md` — What is the presenter showing? (Layer 1)
4. `agents/shared/external-intel.md` — What's happening in the real world? (Layer 5)
5. `agents/{agent}/domain-knowledge.md` — What expertise do I bring? (Layer 4)
6. `agents/{agent}/focus-brief.md` — What should I focus on in this session?
7. `agents/shared/exchange-history.md` — What has the panel discussed so far? (Layer 3)
8. `agents/{agent}/exchange-notes.md` — What have I personally asked and heard?
9. `agents/{agent}/candidate-question.md` — What am I planning to ask next?

For the Moderator, the assembly is slightly different — it reads `orchestration.md` and `session-state.md` instead of domain knowledge and focus briefs.

## Update Frequency

| File | Updated When |
|------|-------------|
| `persona.md` | Static — only changes between product versions |
| `domain-knowledge.md` | Static — updated periodically with new frameworks/benchmarks |
| `session-config.md` | Once at session start |
| `deck-content.md` | Once at deck upload (after parsing + enrichment) |
| `external-intel.md` | Once at deck upload; optionally refreshed if new topics emerge |
| `board-dossier.md` | Once at deck upload |
| `focus-brief.md` | Once at session start (generated from deck + config + external intel) |
| `exchange-history.md` | After every exchange resolves |
| `exchange-notes.md` | After every turn within an exchange |
| `candidate-question.md` | Every 15s during presentation, on slide change, after exchanges |
| `session-state.md` | Continuously (Moderator's live tracking) |
| `phrases.md` | Pre-generated at session start; refreshed as agents are selected to speak |
