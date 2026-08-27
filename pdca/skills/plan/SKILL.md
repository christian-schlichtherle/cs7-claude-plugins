---
name: plan
description: Split a piece of work into an interactive planning phase that produces a self-sufficient plan file, and an autonomous implementation phase run by a fresh `/goal` session. Use this skill whenever the user wants to plan before implementing, wants a plan another session or another model can execute unattended, says the work is too big for one session, asks to "hand this off", "write a plan I can run later", "set this up so it can run autonomously", mentions PDCA, or types /pdca:plan. Also use it when the user is about to set a `/goal` by hand — a goal grounded in a verified plan beats one grounded in assumptions.
user-invocable: false
---

# PDCA: two-phase development

This is the Deming PDCA cycle with a session boundary in the middle.

- **Plan** — an interactive session with the user. Explore, verify assumptions by
  actually running commands, and write a plan file good enough that nobody has to
  babysit its execution.
- **Do / Check / Act** — a *fresh* session, optionally on a different model and
  effort level, that implements the plan under `/goal` and does not stop until a
  separate evaluator agrees the work is finished.

The split exists because the two phases want opposite things. Planning wants the
user in the loop, wants questions asked, wants to change its mind. Implementation
wants a clean context, an unambiguous specification, and nobody interrupting. Trying
to do both in one session gives you a context window half full of exploration debris
and a user who has to approve every step.

**The plan file is the entire interface between the phases.** Phase 2 gets the plan
and the repository — nothing else. No memory of your conversation, no "as we
discussed", no chance to ask a follow-up question. Everything phase 2 needs to
decide correctly has to be in that file. This is the one thing to hold in mind while
writing it.

## Do not use plan mode for phase 1

Claude Code's `/plan` mode is the wrong tool here, for two concrete reasons:

1. It blocks what the Plan phase produces and some of what it checks. Read-only
   probes do run in plan mode — `kubectl get` and `grep` work fine, verified
   directly — but plan mode cannot write the plan file to `docs/plans/…` (the
   harness plan file is not the same thing), cannot write spike files, and denies
   verification commands that touch state. The phase needs all three.
2. It re-renders the whole plan in the transcript every turn. Here the plan lives in
   a file, is edited in place, and each turn reports only the delta.

Work in the session's normal permission mode. If the session is currently in plan
mode, say so and ask the user to exit before continuing.

Plan mode does have a place in this workflow, just not here: the reviewer in step 6
needs read-only exploration and must not touch the repository, which is exactly what
plan mode enforces.

## Phase 1 — the planning session

### 1. Parse the invocation

The command takes `[model] [effort] <goal or plan path>`. The grammar is
deliberately rigid, because a clever rule here is worse than a predictable one:

- A leading **model** token — `fable`, `opus`, `sonnet`, `haiku`, or a full model ID
  — is consumed as the model.
- An **effort** token — `low`, `medium`, `high`, `xhigh`, `max` — is consumed *only
  when it immediately follows a model token*. A bare leading effort word is always
  goal text.
- Everything remaining is the goal.

So `opus max harden the retry path` parses as model `opus`, effort `max`; and
`max out the connection pool` is entirely a goal, which is the case a looser rule
gets wrong. The deliberate cost: you cannot pass effort without a model —
`high fix the login bug` reads as a goal. Nothing is lost, because step 2 asks for
missing effort anyway.

Then **echo the parse back in your first line** — `Planning for Opus 5 at high
effort — goal: …` — so a misparse is obvious and costs one correction rather than a
whole session.

If the remainder is a path to an existing plan file, reopen that plan instead of
starting a new one — see "Reopening a plan" below.

### 2. Settle the handoff parameters before planning, not after

Ask for anything missing **now**, in one batch:

- **Model and effort for phase 2.** Propose `opus` at `high` when unspecified.
- **Ticket key** (e.g. `ACME-123`), if the repository prefixes commits with one.
  Check `git log --oneline -20` to see whether it does.

These are not administrative details you can collect at the end. How much the plan
has to spell out depends on who is reading it: a plan for `haiku` at `low` effort
needs exact file paths, exact snippets, and no inference; a plan for `opus` at `max`
can state intent and constraints and trust the reader to work out the details. You
cannot write at the right altitude without knowing the audience.

The ticket key ends up in the handoff command, so it can also be supplied at
paste time — but ask now, because it is cheap now and awkward later.

### 3. Explore and verify

This is the substance of the phase. For every claim the plan will rest on, run
something that proves it, and record both the command and what it returned.

The failure mode this prevents is specific and common: phase 2 opens the file,
finds "the retention setting is configured in `values.yaml`", discovers it is not,
and now has to improvise — unsupervised, with no way to ask. Every unverified
assertion in the plan is a place where an autonomous run can quietly go wrong.

Verify at minimum: that the files you name exist and contain what you say; that the
commands you prescribe exist and run in this environment; that the current state is
what you think (config values, schema, cluster state, dependency versions); and that
the acceptance checks pass *now* for the right reason, or fail *now* for the right
reason.

**Run every command you prescribe, under the permission mode phase 2 will use.** This
is the concrete test for a failure that is otherwise invisible until nobody is
watching: `auto` decides without asking, and it decides *both ways* — a command it
refuses is refused silently, with no human to override. If a command you are about to
prescribe needed manual approval or was denied here, that is a defect in the plan, not
a footnote. Substitute a command that runs cleanly, or record an explicit,
user-approved mode escalation in the plan. A prescribed command phase 2 cannot run
makes its acceptance criterion unreachable.

You may prototype throwaway spikes to de-risk an assumption — a scratch script, a
quick patch to see whether something compiles. Restore the working tree before the
handoff; phase 2 must start from a state you understand. Apart from spikes, the plan
file is the only file you write **in the repository**. Scratch files this workflow
needs of its own — the reviewer prompt, its captured verdict — belong outside the
tree, under `mktemp -d` or `/tmp`. A stray scratch file in the repository leaves
phase 2 starting from a dirty tree, which breaks the one signal it has for
recognizing its own work.

### 4. Write the plan file

Path: `docs/plans/<YYYY-MM-DD>-<slug>.md`, slug derived from the goal. If the
repository already has a `docs/` directory, create `docs/plans/` under it as needed.
If it has no `docs/` at all, do not invent one — put the plan at the repository root
as `<YYYY-MM-DD>-<slug>.md`. Either way, say where you put it.

Follow `references/plan-template.md` — it is a fixed template, and its sections
exist to force out the gaps that make a plan unexecutable. Read it before writing
your first draft.

### 5. Iterate with delta reports

Each turn: update the file, then report **only what changed** and what is still
open. A few lines. Do not reprint the plan — the user reads the file, or its diff.

Prefer concrete open questions over generic ones. "Should the retention change
apply to staging too, or dev only?" is answerable in three seconds; "any other
requirements?" is not.

Iterate until the user is satisfied. They decide when planning is done, not you.

### 6. Adversarial review by the executing model

When the user signals they are happy, the plan is reviewed — not by you, but by a
fresh `claude -p` process running **phase 2's model at phase 2's effort level**,
which sees the plan and the repository and nothing else.

You cannot review your own plan for self-sufficiency, and the reason is structural
rather than a matter of diligence: you remember the conversation. The constraint the
user mentioned once, the file you checked and dismissed, what "the usual way" means
in this repository — you read all of that back into the plan without noticing it was
never written down. A reviewer holding your context reads past every such gap. A
reviewer without it walks into them exactly as phase 2 would.

Loop: review, fix the blockers, review again. Until the reviewer returns READY, or
three rounds, whichever comes first. If it does not converge, stop and put both
positions to the user — a persistent disagreement between the planner and the
executor is a finding in itself, and it is the user's to settle.

Read `references/review-loop.md` before the first round; it has the exact command,
the reviewer prompt, and how to handle a verdict you disagree with.

### 7. Hand off

The order below is not arbitrary. The commit decision has to be *asked* first
because the condition depends on it, but the commit itself has to *happen* last,
because the plan is still being written until the handoff is in it.

1. **Ask whether to commit the plan — decision only, no commit yet.** Whether the
   plan ends up tracked decides how it can be removed at the end, so the condition
   cannot be written until you know. Committing means phase 2 starts from a clean
   tree — so its own `git status` is a trustworthy signal of its own work — and means
   the plan stays recoverable from history after it self-destructs.
2. **Build the goal condition** per `references/goal-condition.md`. Read that file
   before writing the condition; the constraints there are not obvious.
3. **Write the handoff command into the plan's Handoff section**, then print it.
   Terminal output is the most perishable place a command can live, and the gap
   between the two phases can be weeks. A plan that carries its own launch
   instruction can be picked up by whoever finds the file.
4. **Now commit, if that was agreed.** Follow the repository's commit convention,
   including the ticket prefix and signing if that is what `git log` shows.
   Committing before step 3 would put a plan into history without its own launch
   command and leave phase 2 facing a dirty tree — both of which defeat the point.

   If the convention signs commits, this commit doubles as the live proof that
   signing works unattended: check it with `git log --show-signature -1`.

   If the plan is staying untracked there is no such commit, so probe separately —
   a passphrase-protected key with no warm agent does not fail loudly in phase 2, it
   *hangs* on a pinentry prompt nobody can answer, under a Stop hook that will not
   let the session stop. Branch on `git config gpg.format`: for the gpg default,
   `echo test | gpg --clearsign --batch --pinentry-mode error` (adding
   `-u $(git config user.signingkey)` when that is set) fails immediately in exactly
   the case that would otherwise hang; SSH-signing repositories need the equivalent
   check for their key. Do not synthesize a throwaway commit to test this — this
   phase does not mutate history.

   Say plainly that a passing probe is not a guarantee: it says the agent is warm
   *now*, not that it still will be when phase 2 launches days later. The
   blocked-report hatch is phase 2's fallback if signing fails then.
5. **Offer to launch the fresh session**, and if declined (or if launching is not
   possible), print the command to copy. Either way, explain how the fresh session
   is achieved — see below.

## Reopening a plan

`/pdca:plan <path-to-plan>` reopens an existing plan. This covers two
cases, and they want different treatment.

**Still iterating** — the plan was written recently and is being refined. Continue
where you left off.

**Coming back to it later** — the plan has been sitting, and the repository has
moved on. Re-verify before doing anything else. This is cheap, because the Verified
Context section records the command behind every fact: re-run them, and report
which still hold and which have drifted. Then bring the plan back to true — update
the drifted facts, adjust the tasks and acceptance criteria that depended on them —
and reprint the handoff.

Both cases end the same way: the Handoff section is refreshed and printed. So "I
lost the command you printed" is answered by reopening the plan, and comes with a
freshness check attached.

A stale plan that gets executed anyway is not a disaster either: the Execution
Protocol tells the executing session to check the Verified Context against reality
first and stop if it has diverged. But re-verifying while a human is present is
strictly better than discovering the drift halfway through an unattended run.

## The handoff command

A fresh session is a new `claude` process started in the working directory of the
repository being changed — usually, but not always, the one where planning happened.
When the plan and the work live in different repositories, the printed command takes
the `cd <work-repo> && claude …` form. It shares the repository and nothing else: no
conversation history, no context from phase 1. That is the point.

```bash
claude --model opus --effort high --permission-mode auto '/goal <condition>'
```

- `--model` / `--effort` — as settled in phase 1, step 2 (handoff parameters). These
  are why the plan was written at the altitude it was.
- `--permission-mode auto` — **required**, but understand what it does. Auto decides
  without asking, and it decides in *both* directions: it allows without a prompt,
  and it also silently denies. Without it the session stops at the first write and
  waits for a human who is not there; with it, a prescribed command may simply be
  refused, no prompt, no override. A refused command makes its acceptance criterion
  unreachable, and the correct exit is then the blocked report — which is why phase 1
  runs every prescribed command under this mode before prescribing it.

  `dontAsk` and `bypassPermissions` remove the denials too. Treat them as the user's
  explicit, risk-acknowledged choice, never as a recommended escalation: an
  unattended run that touches production with the permission layer switched off is a
  decision for a human to make deliberately, not a default this skill hands out.
- The positional prompt runs as the session's first turn, so `/goal` activates
  immediately.

If the condition cannot be made shell-safe, print the two-step form instead: start
`claude --model … --effort … --permission-mode auto`, then paste the `/goal …` line
as the first message. Same result, no quoting hazards.

Also tell the user, briefly: `/goal` shows status (turns elapsed, last evaluator
reason), `/goal clear` stops the run early.

## What `/goal` actually does

Worth understanding, because the design of the condition depends on it.

`/goal <condition>` installs a session-scoped Stop hook. After every turn a separate
evaluator judges whether the condition holds; until it does, the hook blocks the
session from stopping. When it holds, the goal auto-clears and the session ends.

Three consequences shape everything in `references/goal-condition.md`:

- The condition is handed to the executing session **as its directive** — it is told
  to start working and not to pause to ask the user. So the condition must be
  self-contained.
- The evaluator sees the **condition text** plus the conversation. Condition text
  survives compaction; attachments and early transcript may not. Put what matters in
  the condition.
- The condition is capped at **4000 characters**.

`/goal` also requires a trusted workspace and working hooks — it is unavailable if
`disableAllHooks` or `allowManagedHooksOnly` is set.

## Phase 2 — what the plan makes happen

Phase 2 needs no skill and no plugin: the goal condition points at the plan, and the
plan's own Execution Protocol section tells the reader how to behave. That section
is not boilerplate you may drop — it is what makes the file self-sufficient. It
instructs the executing session to:

- Work through the tasks in order, ticking each checkbox in the plan file as it
  completes and appending notable decisions to the run log. This makes the file a
  live progress record: an interrupted run resumes from it, and the user can watch
  progress by reading it.
- Run the acceptance checks and show their real output. Not summarize them — run
  them. And re-run the full set immediately before finishing, so the evidence sits in
  the most recent part of the transcript, which is what the evaluator can still see.
- Treat a permission denial as a blocked-report situation, not an obstacle to route
  around. A denied command means the plan prescribed something phase 2 cannot do; the
  honest response is the post-mortem, not an improvised substitute nobody reviewed.
- Commit on the **current branch**, with the agreed prefix. Never create a branch
  unless the plan explicitly says to.
- Remove the plan file as the final act — in the same commit as the work when it is
  tracked there, otherwise with `rm`. Do not write a condition that requires
  committing the deletion of a file that was never committed, or that lives in
  another repository: that check can never pass, and an unsatisfiable condition is
  the one thing the Stop hook cannot recover from on its own.
- If a check genuinely cannot pass: write the blocked report named in the condition,
  explaining which check failed, what was tried, and why it cannot pass — then stop.

That last one matters more than it looks. Without a reachable failure state, a plan
with one impossible check turns into a session that cannot stop, retrying forever.

## References

- `references/plan-template.md` — the plan file template, section by section, with
  what each section is for. Read before writing a plan.
- `references/goal-condition.md` — how to construct the `/goal` condition: the
  character budget, shell safety, the escape hatch, worked examples. Read before
  writing a handoff.
- `references/review-loop.md` — the adversarial review loop: the reviewer command,
  the prompt that puts it in phase 2's position, and when to stop. Read before the
  first review round.
