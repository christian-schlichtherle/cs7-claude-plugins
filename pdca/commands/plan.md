---
argument-hint: "[model] [effort] [rounds] <goal, ticket, spec path, or plan path>"
description: Plan a piece of work interactively into a self-sufficient plan file, then hand it off to a fresh execution session driven by /goal.
---

# PDCA Plan

Run the two-phase PDCA cycle: an interactive **planning phase** that produces a
self-sufficient plan file, handed off to a fresh **execution phase** driven by
`/goal`.

**Follow the `plan` skill** — read `${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md`. It is
the single source of truth for this workflow —
argument parsing, what to verify before writing anything, the plan template, the
rules for constructing the goal condition, and the reasoning behind all of it. Read
it before starting, and do not re-derive its rules from this file: this file
deliberately does not restate them, so that there is only one place for them to be
wrong.

## Examples

- `/pdca:plan opus high raise the staging cache TTL from five minutes to an hour`
- `/pdca:plan sonnet rename the metrics client across both services` —
  effort missing, so propose one, and confirm `sonnet` beside it
- `/pdca:plan add a health endpoint to the api service` — model, effort and rounds
  missing, so all three are proposed just before the first draft
- `/pdca:plan opus high 20 raise the staging cache TTL` — twenty rounds for the
  adversarial review instead of the default ten
- `/pdca:plan opus max 2026-08-27-cache-ttl-plan.md` — reopen an existing plan
- `/pdca:plan opus high docs/specs/cache-ttl.md` — a spec to plan against; plans are
  named `-plan.md`, but what settles it is the frontmatter, not the name
- `/pdca:plan opus high ACME-123` — a bare ticket key as the goal
- `/pdca:plan` — no goal given, so interview for one

The leading `opus high` names the model and effort you would like for the *second*
phase, not this one, and a number after them the review loop's round budget. They are
preferences, never settlements: just before the plan is drafted, the skill proposes
the executor — model, effort and permission mode — and the round budget from the work
agreed so far, and asks for confirmation, of what was given as well. It also explains
why that is the right moment.

Every run asks for a Jira ticket before planning starts; the skill says what happens
with one, and with a spec.

Once the plan is handed off, `/pdca:execute <plan path>` launches it.
