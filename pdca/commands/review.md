---
argument-hint: "[model] [effort] [rounds] <path…> [reader statement]"
description: Cold adversarial review of any file or directory by a fresh process reading it in the reader's position, round after round, until it agrees or the round budget — ten by default — is spent.
---

# PDCA Review

Have a deliverable reviewed the way its real reader will meet it: a **fresh
`claude -p` process** that gets the file and the repository and nothing else, reads it
cold in plan mode, and returns blockers or agreement. Fix what comes back, run it
again, until it agrees or the round budget runs out.

**Follow the `review` skill** — read `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md`.
It is the single source of truth for this command: the grammar and what is interviewed
for when a parameter is missing, the prompt template and the lens its slots are filled
from, the loop and its round budget, how a blocker you disagree with is answered, and
the closing line the run ends on. Read it before doing anything; this file
deliberately does not restate it, so that there is only one place for it to be wrong.

## Examples

- `/pdca:review sonnet xhigh docs/runbook.md for an operator following it at 3am` —
  reviewer, effort and reader named; the budget defaults to ten
- `/pdca:review sonnet xhigh 5 docs/` — a whole directory, five rounds; the reader is
  interviewed for
- `/pdca:review README.md` — model, effort, budget and reader all come from a short
  interview
- `/pdca:review opus high 20 docs/rfcs/0007-quotas.md README.md for a service owner
  who has to implement this next quarter` — several paths, reviewed as one artifact
- `/pdca:review 2026-08-27-cache-ttl-plan.md` — refused and redirected: a plan file is
  reviewed inside `/pdca:plan`, which owns the exit

What it will not do: review a plan written by `/pdca:plan` — plans have exactly one
route to a review, the one that owns the fixpoint between the user, the planner and
the executor, and `/pdca:plan <path>` is it. Nor act as a one-shot proofreader: this
is a loop with a verdict, not a pass of suggestions, and it ends on an agreement, a
spent budget, or you stopping it.
