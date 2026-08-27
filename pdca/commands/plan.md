---
description: Plan a piece of work interactively into a self-sufficient plan file, then hand it off to a fresh autonomous /goal session.
argument-hint: "[model] [effort] <goal or path to existing plan>"
---

# PDCA Plan

Run the two-phase PDCA cycle: an interactive **Plan** phase that produces a
self-sufficient plan file, handed off to a fresh **Do/Check/Act** session driven by
`/goal`.

**Follow the `plan` skill.** It is the single source of truth for this workflow —
argument parsing, what to verify before writing anything, the plan template, the
rules for constructing the goal condition, and the reasoning behind all of it. Read
it before starting, and do not re-derive its rules from this file: this file
deliberately does not restate them, so that there is only one place for them to be
wrong.

## Examples

- `/pdca:plan opus high raise the staging cache TTL from five minutes to an hour`
- `/pdca:plan sonnet rename the metrics client across both services` —
  effort missing, so propose one and ask
- `/pdca:plan add a health endpoint to the api service` — model and effort missing
- `/pdca:plan opus max docs/plans/2026-08-27-cache-ttl.md` — reopen an existing plan
- `/pdca:plan` — ask for the goal, then proceed

The leading `opus high` names the model and effort for the *second* phase, not this
one. The skill explains why that has to be settled before the plan is drafted.
