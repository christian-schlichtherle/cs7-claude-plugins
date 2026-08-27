---
description: Plan a piece of work interactively into a self-sufficient plan file, then hand it off to a fresh autonomous /goal session.
argument-hint: "[model] [effort] <goal or path to existing plan>"
---

# PDCA Plan

Run the two-phase PDCA workflow: an interactive **Plan** phase that produces a
self-sufficient plan file, handed off to a fresh **Do/Check/Act** session driven by
`/goal`.

Follow the `plan` skill for the full method. It carries the plan template, the
rules for building the goal condition, and the reasoning behind both — read it
before starting.

## Arguments

`$ARGUMENTS` is a raw string. The grammar is deliberately rigid — predictable beats
clever here:

- A leading **model** token — `fable`, `opus`, `sonnet`, `haiku`, or a full model ID
  — is consumed as the model.
- An **effort** token — `low`, `medium`, `high`, `xhigh`, `max` — is consumed *only
  when it immediately follows a model token*. A bare leading effort word is always
  goal text, so `max out the connection pool` is entirely a goal.
- Everything remaining is the goal.

The deliberate cost is that effort cannot be passed without a model; that is fine,
because missing effort is asked for before planning starts. Echo the parse back in
your first line so a misparse costs one correction instead of a session.

If the remainder is a path to an existing plan file, reopen it and continue
iterating rather than starting a new plan.

## Examples

- `/pdca:plan opus high raise the staging cache TTL from five minutes to an hour`
- `/pdca:plan sonnet rename the metrics client across both services` —
  effort missing, so propose and ask
- `/pdca:plan add a health endpoint to the api service` — both missing
- `/pdca:plan opus max docs/plans/2026-08-27-cache-ttl.md` — resume
- `/pdca:plan` — ask for the goal, then proceed

## Before starting

- If the session is in plan mode, ask the user to exit. Read-only probes do run in
  plan mode, but this workflow also has to write the plan file, write spike files,
  and run verification commands that touch state — none of which plan mode allows.
- Ask for anything missing — model, effort, and the ticket key if `git log` shows
  the repository prefixes commits — in one batch, before planning begins. The plan
  is written at the altitude of the model that will execute it, so the audience has
  to be known first.
