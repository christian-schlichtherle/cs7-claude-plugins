---
description: Plan a piece of work interactively into a self-sufficient plan file, then hand it off to a fresh execution session driven by /goal.
argument-hint: "[model] [effort] <goal, ticket, spec path, or plan path>"
---

# PDCA Plan

Run the two-phase PDCA cycle: an interactive **planning phase** that produces a
self-sufficient plan file, handed off to a fresh **execution phase** driven by
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
- `/pdca:plan opus max 2026-08-27-cache-ttl-plan.md` — reopen an existing plan
- `/pdca:plan opus high docs/specs/cache-ttl.md` — a spec to plan against; plans are
  named `-plan.md`, but what settles it is the frontmatter, not the name
- `/pdca:plan opus high ACME-123` — a bare ticket key as the goal
- `/pdca:plan` — no goal given, so interview for one

The leading `opus high` names the model and effort for the *second* phase, not this
one. The skill explains why that has to be settled before the plan is drafted.

Every run asks for a Jira ticket; the skill says what happens with one, and with a
spec.
