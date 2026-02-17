# Moderator Orchestration Rules

## Session State Machine

```
PRESENTING → Q&A_TRIGGER → EXCHANGE → RESOLVING → PRESENTING
```

### State: PRESENTING
- Presenter is speaking, agents are listening
- Pre-generation pipeline running in background
- Moderator tracks slide changes and elapsed time
- Moderator evaluates when to trigger Q&A based on interaction mode

### State: Q&A_TRIGGER
- Moderator speaks a transition phrase (pre-buffered)
- Calls on selected agent by name
- Transition phrase is deliberately verbose (3-5 seconds) to mask latency

### State: EXCHANGE
- Multi-turn dialogue between active agent and presenter
- Only the active agent speaks (others observe)
- Moderator uses micro-phrases to stay present ("Mm-hmm", "Interesting")
- Moderator monitors turn count against intensity limits
- Moderator pre-generates bridge-back phrase during exchange
- Other agents pre-generate pile-on candidates during exchange

### State: RESOLVING
- Moderator delivers bridge-back phrase
- Optionally allows one pile-on from another agent
- Logs exchange outcome and any unresolved challenges
- Refreshes pre-generation buffers with exchange context
- Transitions back to PRESENTING

## Turn Limit Enforcement

| Intensity | Max Turns | Intervention Style |
|-----------|-----------|-------------------|
| Friendly | 2 | Steps in after first follow-up regardless |
| Moderate | 3 | Steps in if circular or at limit |
| Adversarial | 4 | Only steps in at limit or if presenter requests |

## Q&A Trigger Rules by Interaction Mode

### Section Breaks
- Trigger on slide change or presenter clicking "Open Q&A"
- Select agent based on: relevance to current slide content, time since last question, focus area priority
- Allow 1-2 exchanges per section break before continuing

### Hand Raise
- Agents raise hands when question urgency > threshold
- Moderator notifies presenter: "[Agent] has a question."
- Presenter acknowledges to trigger exchange
- Maximum 2 hands raised simultaneously

### Free Flow
- Agents trigger on natural pauses (>2s silence detected by STT)
- Moderator manages potential crosstalk — only one agent speaks at a time
- If two agents trigger simultaneously, Moderator queues the second
- Minimum 20-second gap between agent interjections

## Agent Selection Priority

When choosing which agent speaks next:
1. Agent whose focus area matches current slide content most closely
2. Agent who hasn't spoken in the longest time
3. Agent whose pre-generated question has the highest relevance score
4. If focus areas are even, rotate: Skeptic → Analyst → Contrarian

## Pile-On Decision Logic

After primary exchange resolves:
1. Check if another agent has a relevant pile-on candidate
2. Check if pile-on references the just-completed exchange (required)
3. Check if time permits (at least 3 minutes remaining)
4. If all yes: allow pile-on (1 turn only)
5. If time is tight: skip pile-on, flag for debrief

## Engagement Monitoring

- If no questions in 3+ minutes and session is not ending: prompt engagement
- If presenter has been speaking for 5+ minutes without interaction: suggest a pause
- If all agents have asked about the same slide: encourage presenter to advance
