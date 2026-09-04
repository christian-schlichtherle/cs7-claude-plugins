---
description: Launch or resume a plan's execution phase as a fresh background claude session — the plan's own Handoff command under /goal, with Remote Control — and report how to reach it.
argument-hint: "[plan path]"
---

# PDCA Execute

Start — or resume — the **execution phase** of a plan file written by `/pdca:plan`.

**Follow the `execute` skill.** It is the single source of truth for this command:
how the plan is found, what each `status` means for a launch, how the Handoff command
is taken from the plan and checked before it runs, and why the launch is always a new
background process rather than work done here. Read it before doing anything; this
file deliberately does not restate it, so that there is only one place for it to be
wrong.

## Examples

- `/pdca:execute 2026-08-27-cache-ttl-plan.md` — launch a handed-off plan
- `/pdca:execute 2026-08-27-cache-ttl-plan.md` on a plan whose `status` is `executing`,
  or `blocked` with a report ending `Next: relaunch` — resume the run where it stopped
- `/pdca:execute` — the one `*-plan.md` at the repository root

What it will not do: execute the plan in this session. A `/goal` can only be set by
the harness, never by a command, and this session is not the one the plan was written
for; the skill has the details. Refining a plan is `/pdca:plan <path>`.
