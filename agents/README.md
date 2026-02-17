# Agent Context System

## Core Principle

**Agent character is immutable. Agent context is session-scoped.**

Every AI panelist has a fixed identity (persona, domain expertise, voice, questioning style) that NEVER changes. What changes is what they KNOW — the deck content, external news, transcript, exchange history, and observations about the presenter. This mutable context is created fresh for each session.

## Directory Structure

```
agents/
├── README.md                              ← You are here
│
├── templates/                             ← IMMUTABLE: Git-versioned, read-only at runtime
│   ├── moderator/
│   │   ├── persona.md                     ← Diana Chen: identity, personality, voice, rules
│   │   ├── orchestration.md               ← State machine, turn limits, coordination logic
│   │   └── phrase-library.md              ← Master library of all transition/stalling phrases
│   ├── skeptic/
│   │   ├── persona.md                     ← Marcus Webb: identity, style, satisfaction criteria
│   │   └── domain-knowledge.md            ← Financial benchmarks, red flags, frameworks
│   ├── analyst/
│   │   ├── persona.md                     ← Priya Sharma: identity, style, satisfaction criteria
│   │   └── domain-knowledge.md            ← Data quality frameworks, statistical methods
│   └── contrarian/
│       ├── persona.md                     ← James O'Brien: identity, style, satisfaction criteria
│       └── domain-knowledge.md            ← Logical fallacies, precedents, contradiction patterns
│
├── session-templates/                     ← BLUEPRINTS: copied into each new session
│   ├── shared/
│   │   ├── session-config.md              ← Session parameters (populated at start)
│   │   ├── presenter-transcript.md        ← Running transcript (append-only during session)
│   │   └── exchange-history.md            ← All exchanges and outcomes (append-only)
│   ├── moderator/
│   │   ├── session-state.md               ← Live tracking (overwritten continuously)
│   │   └── debrief-notes.md               ← Accumulating notes for post-session summary
│   └── {skeptic,analyst,contrarian}/
│       ├── focus-brief.md                 ← Claims to target (generated at session start)
│       ├── exchange-notes.md              ← Personal exchange log (append-only)
│       ├── candidate-question.md          ← Pre-generated question buffer (overwritten)
│       └── presenter-profile.md           ← Behavioral observations (append-only)
│
└── sessions/                              ← RUNTIME: one folder per active/archived session
    └── {session_id}/
        ├── shared/                        ← Includes deck-content.md, external-intel.md,
        │   │                                 board-dossier.md (generated, not from templates)
        │   ├── session-config.md
        │   ├── deck-content.md
        │   ├── external-intel.md
        │   ├── board-dossier.md
        │   ├── presenter-transcript.md
        │   └── exchange-history.md
        ├── moderator/
        │   ├── session-state.md
        │   ├── generated-phrases.md
        │   └── debrief-notes.md
        ├── skeptic/
        │   ├── focus-brief.md
        │   ├── exchange-notes.md
        │   ├── candidate-question.md
        │   └── presenter-profile.md
        ├── analyst/
        │   └── (same structure)
        └── contrarian/
            └── (same structure)
```

## Session Lifecycle

### 1. Session Created
```
Copy session-templates/ → sessions/{session_id}/
Parse deck → write deck-content.md, external-intel.md, board-dossier.md
Read templates/{agent}/persona.md + domain-knowledge.md
  + deck-content.md + external-intel.md
  → Generate focus-brief.md for each agent
```

### 2. Session Active
```
Templates are READ-ONLY — character never changes
Session files are UPDATED — context accumulates:
  - presenter-transcript.md    (every STT segment)
  - exchange-history.md        (after each exchange)
  - exchange-notes.md          (after each turn)
  - candidate-question.md      (every 15s, on slide change)
  - presenter-profile.md       (after each exchange)
  - session-state.md           (continuously)
  - debrief-notes.md           (at key moments)
```

### 3. Session Ended
```
Freeze all session files → archive to S3/R2
Templates remain untouched → ready for next session
Session folder becomes read-only archive for review
```

## Context Assembly Order (Per Agent Call)

| # | Source | File | Mutability |
|---|--------|------|-----------|
| 1 | templates/{agent}/ | persona.md | IMMUTABLE |
| 2 | templates/{agent}/ | domain-knowledge.md | IMMUTABLE |
| 3 | sessions/{id}/shared/ | session-config.md | Write-once |
| 4 | sessions/{id}/shared/ | deck-content.md | Write-once |
| 5 | sessions/{id}/shared/ | external-intel.md | Write-few |
| 6 | sessions/{id}/shared/ | presenter-transcript.md | Append-only |
| 7 | sessions/{id}/shared/ | exchange-history.md | Append-only |
| 8 | sessions/{id}/{agent}/ | focus-brief.md | Write-once |
| 9 | sessions/{id}/{agent}/ | exchange-notes.md | Append-only |
| 10 | sessions/{id}/{agent}/ | presenter-profile.md | Append-only |
| 11 | sessions/{id}/{agent}/ | candidate-question.md | Overwrite |

Immutable files are always the same. Mutable files grow richer as the session progresses — making every subsequent agent question smarter than the last.
