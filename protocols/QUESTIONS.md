# QUESTIONS — machine → owner

Agents NEVER block on a human. When judgement is needed: write the question
(via the planner), pick the safer interpretation, proceed, and record what you
did in `proceeded_by`. The owner answers by moving an entry to `## Answered`
and adding `answer:`. Planners apply answers idempotently: every session,
every blocked/open task referencing a Q-id is checked against `## Answered`
directly — no timestamp watermarks (they can permanently miss; learned the
hard way).

## Open

_(none)_

## Answered

_(none yet)_

## Format

```
### Q<NNN> — <one-line topic>
- raised_at: <ISO>
- raised_during: <task id or "planning">
- context: <2-3 sentences>
- question: <the question>
- proceeded_by: <what the machine did without the answer>
```
