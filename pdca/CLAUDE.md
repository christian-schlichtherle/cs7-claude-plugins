# pdca Plugin — Developer Guide

## How It Works

One command (`/pdca:plan`) and one skill (`plan`) implementing a PDCA
cycle split across two sessions:

- **Plan** — interactive, runs commands to verify its assumptions, writes
  `docs/plans/<date>-<slug>.md`.
- **Do/Check/Act** — a fresh `claude` process under `/goal`, implementing the plan
  unattended.

The plan file is the only interface between them, which is why the skill pushes so
hard on verified facts and inlined acceptance criteria.

## Conventions

- **One palette entry, two files.** `/pdca:plan` is the command; the skill is
  `user-invocable: false` so it does not also appear in the slash-command list.
  Without that flag Claude Code shows `/pdca:plan` twice — once for the command with
  its human-facing description, once for the skill with its triggering description.
- **The skill is the single source of truth.** The command is a thin entry point: a
  description, an argument hint, examples, and a pointer. Argument parsing, the
  pre-flight checks, the plan template and the goal-condition rules live in the skill
  only. They were duplicated in both files once, and a review found the same two
  defects had to be fixed twice — hence the split.
- The skill stays model-invocable, which is what makes it trigger on intent
  ("write me a plan I can run later") without the command being typed.
- Phase 1 never enters plan mode. Not because plan mode blocks read-only probes (it
  does not — `kubectl get` and `grep` run fine there), but because the phase writes
  the plan file and spike files and runs verification that touches state.
- Phase 2 always runs with `--permission-mode auto`; an autonomous session cannot
  answer permission prompts. Auto decides without asking in *both* directions,
  though — it also denies silently — so phase 1 must run every prescribed command
  under that mode before prescribing it.
- The goal condition is capped at 4000 characters, is single-quoted into a shell
  argument (so: no apostrophes, no backticks), and always carries a blocked-report
  escape hatch so an impossible check terminates instead of looping.
- The plan file self-destructs at the end of phase 2 — in the final commit when it is
  tracked there, otherwise with `rm`. Committing the plan is an offer the user can
  decline, so nothing may assume it is tracked.
- Before handoff, the plan is reviewed by a fresh `claude -p` process at phase 2's
  model and effort, in a loop capped at three rounds. The reviewer runs with
  `--permission-mode plan` so it is read-only by construction, and runs in the
  background — a foreground reviewer at xhigh effort outlives the 10-minute tool
  timeout. A round that returns no verdict line is inconclusive and does not consume
  one of the three.
- The handoff command is written into the plan's own `## Handoff` section before it
  is printed, so it survives the gap between phases. The plan is committed only
  *after* the handoff is in it — committing earlier puts a plan into history without
  its own launch command and leaves phase 2 facing a dirty tree.
- The `/goal` condition never makes a present-tense claim about the plan file, since
  the same condition orders that file deleted. Claims are phrased as what happened in
  the session, which is what the evaluator can still see.

## Facts About `/goal` This Plugin Depends On

Verified against Claude Code 2.1.247:

- `/goal <condition>` installs a session-scoped Stop hook; a separate evaluator
  judges the condition after each turn and blocks stopping until it holds, then
  auto-clears. `/goal clear` stops early; bare `/goal` shows status.
- The condition is capped at 4000 characters and is handed to the session as its
  directive, with instructions not to pause to ask the user.
- Requires a trusted workspace; unavailable when `disableAllHooks` or
  `allowManagedHooksOnly` is set.
- Works non-interactively, so it can be passed as the positional prompt to `claude`.

These facts are stated in four places. If a future Claude Code release changes any of
them, all four need updating:

1. `skills/plan/SKILL.md`, section "What `/goal` actually does" — the copy the
   model actually loads.
2. `skills/plan/references/goal-condition.md`, the opening section.
3. `README.md`, section "Requirements".
4. This file, above.
