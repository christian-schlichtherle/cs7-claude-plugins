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
  verification rules, the plan template and the goal-condition rules live in the skill
  only. They were duplicated in both files once, and a review found the same two
  defects had to be fixed twice — hence the split.
- The skill stays model-invocable, which is what makes it trigger on intent
  ("write me a plan I can run later") without the command being typed.
- Planning never reaches the handoff in the turn that drafts the plan. The
  interactive loop's exit condition is that the user is satisfied, which they have to
  state — so the first draft always ends the turn. There is no waiver and no
  non-interactive mode: anyone who does not want the interactive phase can set a
  `/goal` directly instead of using this workflow.
- Phase 1 never enters plan mode. Not because plan mode blocks read-only probes (it
  does not — `kubectl get` and `grep` run fine there), but because the phase writes
  the plan file and spike files and runs verification that touches state.
- Phase 2 always runs with `--permission-mode auto` unless the user deliberately
  escalates; an autonomous session cannot answer permission prompts. Auto decides
  without asking in *both* directions, though — it also denies silently — so phase 1
  must run every prescribed command under that mode before prescribing it.
- Phase 2 opens with a pre-flight gate, and the gate is the reason model, effort and
  permission mode are settled in phase 1 step 2 rather than at handoff. The plan names
  all three literally; phase 2 reads its own back and compares. A failure there is a
  blocked report in turn 1 — never an adaptation, never a run that starts anyway,
  because a wrong-model run looks fine for a while and a Stop hook offers no quiet way
  out later. The gate is instructed twice on purpose: the plan's Execution Protocol
  tells the executing session to run it, and the goal condition repeats it, because
  the condition is the directive the session actually receives and the evaluator has
  to accept a turn-1 abort as terminal.
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

## Facts About Session Introspection This Plugin Depends On

Verified against Claude Code 2.1.247. Most of it from a fresh session's first turn —
`claude -p --model sonnet --effort low --permission-mode auto`, asked to report these
back — and the rest as each bullet says:

- `CLAUDE_EFFORT` holds the session effort level; `CLAUDE_CODE_SESSION_ID` holds the
  session id.
- The session transcript is `~/.claude/projects/<cwd-slug>/<session-id>.jsonl`. It
  carries one `{"type":"permission-mode","permissionMode":"…"}` record per turn, and
  every `{"type":"assistant"}` record has `message.model` as its first key — which is
  why grepping the last assistant line for the first `"model":"…"` match is safe.
- There is no environment variable for the model, so the transcript (or the session's
  own context) is the only source.
- A `permission-mode` record is written every turn and reflects the mode *now*, so a
  session switched mid-run records the new value from that turn on — which is why the
  check reads the last record rather than the first.
- `--permission-mode` accepts `acceptEdits`, `auto`, `bypassPermissions`, `manual`,
  `dontAsk`, `plan`. Two recorded spellings are observed directly: `auto`, and
  `bypassPermissions` after a session was switched into bypass mode. That
  `--dangerously-skip-permissions` selects that same mode is from the CLI help, not
  from a transcript.

These are internal formats, not public API. If a release moves the transcript, the
identity check degrades to self-report — which `references/preflight.md` already
tells the executing session to fall back to. The snippet itself is in two places:
that file and `skills/plan/references/plan-template.md`.

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
