---
name: plan
description: Split a piece of work into an interactive planning phase that produces a self-sufficient plan file, and an autonomous implementation phase run by a fresh `/goal` session. Use this skill whenever the user wants to plan before implementing, wants a plan another session or another model can execute unattended, says the work is too big for one session, asks to "hand this off", "write a plan I can run later", "set this up so it can run autonomously", mentions PDCA, names a Jira ticket to implement, or types /pdca:plan. Also use it when the user is about to set a `/goal` by hand — a goal grounded in a verified plan beats one grounded in assumptions.
user-invocable: false
---

# PDCA: two-phase development

This is the Deming PDCA cycle with a session boundary in the middle.

- **Plan** — an interactive session with the user. Explore, verify assumptions by
  actually running commands, and write a plan file good enough that nobody has to
  babysit its execution.
- **Do / Check / Act** — a *fresh* session, optionally on a different model and
  effort level, that implements the plan file under `/goal` and does not stop until
  a separate evaluator agrees the work is finished.

The split exists because the two phases want opposite things. Planning wants the
user in the loop, wants questions asked, wants to change its mind. Implementation
wants a clean context, an unambiguous specification, and nobody interrupting. Trying
to do both in one session gives you a context window half full of exploration debris
and a user who has to approve every step.

**The plan file is the entire interface between the phases.** Phase 2 gets the
plan file and the repository — nothing else. No memory of your conversation, no
"as we discussed", no chance to ask a follow-up question. Everything phase 2 needs
to decide correctly has to be in that file. This is the one thing to hold in mind
while writing it.

## Do not use plan mode for phase 1

Claude Code's `/plan` mode is the wrong tool here, for two concrete reasons:

1. It blocks what the Plan phase produces and some of what it checks. Read-only
   probes do run in plan mode — `kubectl get` and `grep` work fine, verified
   directly — but plan mode cannot write the plan file to `docs/plans/…`, cannot
   write spike files, and denies verification commands that touch state. The phase
   needs all three. Plan mode's own plan is a different artifact entirely:
   ephemeral, rendered for approval, never on disk. Only the file under
   `docs/plans/…` is the plan file this skill means.
2. It re-renders its whole plan in the transcript every turn. The plan file instead
   lives on disk, is edited in place, and each turn reports only the delta.

Work in the session's normal permission mode. If the session is currently in plan
mode, say so and ask the user to exit before continuing.

Plan mode does have a place in this workflow, just not here: the reviewer in step 7
needs read-only exploration and must not touch the repository, which is exactly what
plan mode enforces.

## Keep the status line posted

`/goal` gets a progress badge for free in phase 2. Phase 1 gets nothing, and it is
the phase with the long quiet stretches — verification runs commands for minutes at a
time, a review round is an entire background process — so a user watching a spinner
cannot tell step 4 from step 7. A plugin cannot drive Claude Code's status line, but
the user's own status-line command can display whatever a file holds, and it receives
the session id to find one with. So maintain a one-line status file for the phase:

```bash
mkdir -p ~/.cache/claude-pdca
printf 'step 4/8 — verify' > ~/.cache/claude-pdca/"$CLAUDE_CODE_SESSION_ID".status
```

Update it at every step transition, and within step 7 at every review round
(`step 7/8 — review, round 2/3`); a reopened plan starts at `re-verifying a reopened
plan`. Name where the session is *now*, not the furthest point reached — a re-entry
from step 8 back into the iteration loop is `step 6` again.

Two rules govern the file's lifetime. Sweep leftovers on the first write —
`find ~/.cache/claude-pdca -name '*.status' -mtime +7 -delete` — because an abandoned
session cannot clean up after itself. And delete this session's file when the phase
ends, after the launch offer in step 8 or the moment the user abandons planning: a
status file that outlives the phase has the status line asserting work that is not
happening. If the user's status line does not read the file none of this shows, which
is fine — the plugin's README carries the segment they opt into.

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

If the remainder is a bare ticket key or ticket URL — `/pdca:plan opus high ACME-123` —
that is the ticket, not the goal. Do not treat the key as a one-line goal and start
planning from it: read the ticket in step 3 and derive the goal with the user from what
it says. A key embedded in a longer goal is both — the ticket and an opening statement
about what the user actually wants from it.

**With no goal at all, interview for one.** `/pdca:plan` on its own, or with only a
model and effort, is a request to start the conversation, not a request to guess.
Ask what the work is.

And when a goal *is* supplied, treat it as an opening statement rather than a
specification. One line of intent is never enough to plan an unattended run from —
it is the thing you ask questions about.

### 2. Settle the handoff parameters before planning, not after

Ask for anything missing **now**, as an interview: one `AskUserQuestion` call with
one question per missing parameter — model, effort, permission mode, ticket is at
most four, which is exactly what the tool holds. The user steps through them picking
options instead of composing a free-form reply, which is what makes asking cheap
enough to do unconditionally: a marked recommendation is one keystroke to accept, and
a composed reply invites the partial answer that leaves a parameter unsettled. Put
your recommended choice first, labelled "(Recommended)"; anything the options cannot
express — a ticket key, a full model ID — arrives through the interview's free-text
"Other" field. Do not re-ask what the invocation already supplied.

The parameters:

- **Model and effort for phase 2.** Propose `opus` at `high` when unspecified.
- **Permission mode for phase 2.** `auto` unless the user asks for something else.
  Settle it now rather than at handoff: the mode decides what phase 1 has to prove
  can run unattended, and it is written into the plan literally so phase 2 can check
  it before starting.
- **Jira ticket.** Always ask, every time — the answer is a key like `ACME-123`, a
  ticket URL, or an explicit "none". In the interview that means: "None" is an
  option, a key inferred from the branch name is another when there is one, and a
  typed key or URL comes in as "Other". Never adopt the inferred key without the
  user picking it, and never skip the question because the goal looks
  self-explanatory; a ticket the user forgot to mention is the commonest source of a
  plan that satisfies its author and not the work item. Check
  `git log --oneline -20` for the commit prefix convention while you are at it. If a ticket is named, step 3 reads it before
  anything else happens.

These are not administrative details you can collect at the end. How much the plan
has to spell out depends on who is reading it: a plan for `haiku` at `low` effort
needs exact file paths, exact snippets, and no inference; a plan for `opus` at `max`
can state intent and constraints and trust the reader to work out the details. You
cannot write at the right altitude without knowing the audience.

The ticket key ends up in the handoff command, in the commit prefix, and in the
closeout that ends phase 2 — so ask now. Supplied at paste time it is merely a
prefix; supplied now it is also requirements to plan against. And it settles one
thing step 8 would otherwise have to ask: a plan with a ticket is committed, always,
because git history is what the ticket's closeout comment links to.

All three of model, effort and mode are also what phase 2 checks itself against
before it touches anything, so settling them here is what makes that gate possible
at all. See `references/preflight.md`.

### 3. Read the ticket and discuss its requirements

Only when a ticket was named in step 2. Skip to step 4 when the user said "none",
and note in the plan that there is no ticket.

Fetch the ticket and read it properly — description, acceptance criteria, comments,
linked issues — then put its requirements to the user as a numbered list and settle
each one before planning. `references/jira.md` has how to fetch it, what to read, and
the exact shape of the conversation.

Two rules govern the whole exchange, and both matter enough to state here:

**The ticket is a request, not a specification.** The plan is allowed to come out
different from it — most often in the non-functional half, the parts that say *how*
rather than *what*: a named mechanism, a library, a metric, a split into phases, a
performance number. Those are the author's guesses, written before anyone verified
anything, and this phase is where things get verified. Where what you verified says
otherwise, propose the deviation with the evidence. But every requirement is still
raised explicitly — none quietly dropped because it looks tangential, none quietly
adopted because it is written down. **The last word is the user's**, not the ticket
author's and not yours.

**Where the plan and the ticket disagree, record the disagreement.** A requirement
the user descopes, defers, or reverses is written into the plan's Ticket Requirements
section *as* descoped, deferred or reversed, with the reason. That section is not
bookkeeping: without it, phase 2 reads the ticket, sees a requirement the plan does
not cover, and helpfully implements it — which is the exact failure the interactive
phase exists to prevent.

Naming the ticket also settles, by itself, what happens to the plan at the end:
phase 2 commits the finished plan and posts a comment linking the ticket to it at that
commit. Jira cannot hold the file — the MCP server has no attachment upload and no way
to link the plan from the issue — so git holds the artifact and the ticket gets the URL.
That is a standing consequence of the answer given in step 2, not a further decision —
do not ask the user, now or at handoff, what should be done with the plan or the ticket
when the work is finished, and do not ask whether to commit the plan. What is *not*
settled yet is mechanism: the comment channel, and whether the closeout pushes. Step 4
probes both, and `references/jira.md` says what to do when there is no channel — the
only closeout questions that are warranted, and they are about mechanism, never about
whether the closeout happens.

### 4. Explore and verify

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

**Enumerate the privileges the tasks need, and probe each one.** Read back through
what the plan will prescribe: every command that signs, pushes, writes outside the
repository, touches a cluster, or reaches the network needs something this session
happens to have and phase 2 may not — a warm signing agent, a cluster role, a live
token, passwordless sudo. For each, find the cheapest command that proves the right
exists without exercising it (`sudo -n true`, `kubectl auth can-i …`, a `--dry-run`
form), run it here, and record it as a pre-flight check in the plan. Those probes are
what turns a silent refusal at task 5 into a clean abort in turn 1;
`references/preflight.md` has the catalogue and the reasoning.

**The ticket closeout is one of those privileges.** If a ticket was named, phase 2
finishes by committing the final plan, pushing it if that was agreed, and posting a
comment linking to it — and none of that is guaranteed to work: an MCP server that
needs interactive authentication, a token this session holds and the next one does not,
an `auto` classifier that refuses an MCP write, a protected branch that rejects the
push. Probe each, record the verified calls and identifiers in the plan, and work out
the permalink template for this repository's host — then commit and push the plan here
and give the user the resulting URL to click, which is the only honest proof the
template is right. If there is no comment channel, say so now and let the user choose
the fallback — see `references/jira.md`.

You may prototype throwaway spikes to de-risk an assumption — a scratch script, a
quick patch to see whether something compiles. Restore the working tree before the
handoff; phase 2 must start from a state you understand. Apart from spikes, the plan
file is the only file you write **in the repository**. Scratch files this workflow
needs of its own — the reviewer prompt, its captured verdict — belong outside the
tree, under `mktemp -d` or `/tmp`. A stray scratch file in the repository leaves
phase 2 starting from a dirty tree, which breaks the one signal it has for
recognizing its own work.

### 5. Write the plan file

Path: `docs/plans/<YYYY-MM-DD>-<slug>.md`, slug derived from the goal. If the
repository already has a `docs/` directory, create `docs/plans/` under it as needed.
If it has no `docs/` at all, do not invent one — put the plan at the repository root
as `<YYYY-MM-DD>-<slug>.md`. Either way, say where you put it.

Follow `references/plan-template.md` — it is a fixed template, and its sections
exist to force out the gaps that make a plan unexecutable. Read it before writing
your first draft.

### 6. Iterate with delta reports

Each turn: update the file, then report **only what changed** and what is still
open. A few lines. Do not reprint the plan — the user reads the file, or its diff.

Prefer concrete open questions over generic ones. "Should the retention change
apply to staging too, or dev only?" is answerable in three seconds; "any other
requirements?" is not.

Iterate until the user is satisfied. They decide when planning is done, not you.

**Never reach the handoff in the same turn as the first draft.** Write the plan, then
stop and hand control back — always, even when the plan looks finished and the goal
was clear. This is not politeness; it is what makes the phase mean anything. The exit
condition of this loop is that the user is satisfied, and satisfaction is something
they state, not something you infer from a one-line goal and your own confidence. A
plan nobody reviewed has skipped the only step the interactive phase exists for.

So: at least one full round-trip before step 7, and the user's go-ahead is an actual
go-ahead. Silence is not one. Nor is the absence of objections to a plan they have not
been given a chance to read.

There is no exception and no non-interactive mode. If someone wants a plan handed
straight to an autonomous run without review, they do not need this workflow at all —
they can set a `/goal` directly and skip the planning session entirely. Choosing
`/pdca:plan` *is* choosing the interactive phase, so treat any pressure to skip it as
a sign the wrong tool was reached for, not as licence to hurry.

### 7. Adversarial review by the executing model

When the user signals they are happy with a version this loop has not already
cleared, the plan is reviewed — not by you, but by a fresh `claude -p` process
running **phase 2's model at phase 2's effort level**, which sees the plan and the
repository and nothing else. (A go-ahead on the exact version the reviewer already
cleared needs no new round — that is the fixpoint below.)

You cannot review your own plan for self-sufficiency, and the reason is structural
rather than a matter of diligence: you remember the conversation. The constraint the
user mentioned once, the file you checked and dismissed, what "the usual way" means
in this repository — you read all of that back into the plan without noticing it was
never written down. A reviewer holding your context reads past every such gap. A
reviewer without it walks into them exactly as phase 2 would.

Loop: review, fix the blockers, review again. Until the reviewer returns AGREED, or
three rounds, whichever comes first. If it does not converge, stop and put both
positions to the user — a persistent disagreement between the planner and the
executor is a finding in itself, and it is the user's to settle.

AGREED ends the loop; it does not by itself reach the handoff. What it exits to
depends on whether the review changed the plan:

- **AGREED, plan unchanged** — the version the user approved in step 6 is
  the version the reviewer cleared. Nothing new for the user to see; proceed to
  step 8.
- **AGREED after blockers were fixed** — the plan the user approved is not the plan
  about to be handed off. Report the review's changes as a step 6 delta and hand
  control back. Approval attaches to a version of the plan, not to the plan in the
  abstract, and the review has just written a version the user has never seen.

Expect afterthoughts at that point, and welcome them — returning here is an
invitation to have them, not a signature to collect. They are step 6 resuming, and
a change that alters what phase 2 would do goes back through this step: an
unreviewed edit to a reviewed plan is an unreviewed plan. Each re-entry is a fresh
loop with its own three rounds, though a re-review of a lightly edited plan usually
returns AGREED in one.

So the exit condition of the nested loops is a fixpoint: **one version of the plan
that all three parties stand behind at once** — the user, whose go-ahead it carries;
you, its author, who fixed the blockers you agreed with and recorded in your round
reports why the rest are not blockers; and the executing model, whose AGREED came
from reading that very version. The loops alternate until a single version holds
all three, and only then does step 8 begin.

The one exception is the user's override. When the loop does not converge and the
user settles the disagreement against the reviewer, their settlement is the exit —
the user outranks both models, and holding the handoff hostage to an AGREED that will
never come would make the reviewer the authority instead. Record the overruled
objection in the plan — Constraints & Non-Goals is the natural place — so phase 2
knows the executing model raised it and the user decided against it, rather than
rediscovering the concern mid-run and treating it as news.

Read `references/review-loop.md` before the first round; it has the exact command,
the reviewer prompt, and how to handle a verdict you disagree with.

### 8. Hand off

The order below is not arbitrary. The decision in step 1 has to be *asked* first
because the goal condition depends on it, but the commit itself has to *happen* last,
because the plan is still being written until the handoff is in it.

Step 1 is also the **only** question this step asks, and which question it is depends
on the ticket. Do not ask what should happen to the finished plan or the ticket at the
end of phase 2 — the user answered that by naming the ticket: the final plan is
committed and the outcome is commented with a link to it, exactly as the plan's Ticket
Closeout section already prescribes. Re-asking a settled decision reads as the workflow
not trusting its own record, and invites an answer that contradicts what the plan and
the goal condition were built on.

One question does not mean one possible reply, though. An answer that changes the
plan — "actually, could it also…" — is not an answer to the step-1 question; it is
step 6 resuming, and a material change goes back through step 7. The fixpoint from
step 7 does not expire because the conversation moved on a step. And a re-entry —
from here, or from the launch offer — rebuilds whatever this step had already
built: the goal condition and the Handoff section are regenerated from the revised
plan, and a plan already committed takes a follow-up commit. A handoff line
pointing at acceptance criteria the plan no longer states is exactly the stale
artifact this step exists to prevent.

1. **Settle how the plan is tracked — decision only, no commit yet.** Whether the
   plan ends up tracked decides how it can be removed at the end, so the condition
   cannot be written until you know. Which question this is depends on the ticket:

   - **A ticket was named — do not ask whether to commit.** It is committed. Git
     history is what the closeout comment links to, so an untracked plan would leave
     the comment with nothing to point at and the run with no surviving record. Say
     that it is being committed and why; the question here is instead **whether the
     closeout pushes.** Recommend yes — an unpushed preservation commit makes the
     comment's link dead until somebody pushes by hand — and respect a no: some
     branches are protected, and an unattended session writing to a shared branch is a
     real decision. A no means the comment carries the SHA and a `git show` command
     instead of a URL, and the Handoff section says someone must push afterwards.
   - **No ticket — ask whether to commit the plan.** Committing means phase 2 starts
     from a clean tree, so its own `git status` is a trustworthy signal of its own
     work, and it means the plan stays recoverable from history after it
     self-destructs. Either answer is fine; the plan and the condition follow it.
2. **Build the goal condition** per `references/goal-condition.md`. Read that file
   before writing the condition; the constraints there are not obvious.
3. **Write the handoff command into the plan's Handoff section**, then print it.
   Terminal output is the most perishable place a command can live, and the gap
   between the two phases can be weeks. A plan file that carries its own launch
   instruction can be picked up by whoever finds it.
4. **Now commit** — always when a ticket was named, otherwise if that was agreed.
   Follow the repository's commit convention, including the ticket prefix and signing
   if that is what `git log` shows. Committing before step 3 would put a plan into
   history without its own launch command and leave phase 2 facing a dirty tree — both
   of which defeat the point.

   When a ticket was named and the closeout pushes, push this commit too and build the
   permalink for the plan at it. Give the user that URL to open: a link that resolves
   here is the proof that the template recorded in the plan is the right one for this
   host, and it costs one click now instead of a dead link on the ticket weeks later.

   If the convention signs commits, this commit doubles as the live proof that
   signing works unattended: check it with `git log --show-signature -1`.

   If the plan is staying untracked — only possible without a ticket — there is no
   such commit, so probe separately —
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

**Coming back to it later** — the plan has been sitting, and both the repository and
the ticket have moved on. Re-verify before doing anything else, and re-read the ticket
as part of that: a comment added last week can change a requirement, and a ticket that
has since been closed, split or reprioritized is a reason to stop and ask rather than
to launch. Report what changed on the ticket alongside what drifted in the repository. This is cheap, because the Verified
Context section records the command behind every fact: re-run them, along with the
pre-flight probes, and report which still hold and which have drifted — an access
token or a signing key that has expired since the plan was written shows up here as
readily as a changed config value. Then bring the plan back to true — update
the drifted facts, adjust the tasks and acceptance criteria that depended on them.

Both cases end the same way: back through steps 7 and 8 as usual — a plan brought
back to true is a changed plan, and an unreviewed edit to a reviewed plan is an
unreviewed plan — and the Handoff section is refreshed and printed. So "I lost the
command you printed" is answered by reopening the plan, and comes with a freshness
check attached.

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

  `dontAsk` and `bypassPermissions` (the latter is what
  `--dangerously-skip-permissions` selects) remove the denials too. Treat them as the
  user's explicit, risk-acknowledged choice, never as a recommended escalation: an
  unattended run that touches production with the permission layer switched off is a
  decision for a human to make deliberately, not a default this skill hands out.

  Whichever mode is settled, it is named literally in the plan's Pre-Flight section
  and checked by phase 2 before it starts — so a plan that assumed the permission
  layer was off, launched under `auto`, stops in turn 1 rather than discovering the
  difference halfway through.
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

Phase 2 needs no skill and no plugin: the goal condition points at the plan file, and
the plan's own Execution Protocol section tells the reader how to behave. That section
is not boilerplate you may drop — it is what makes the file self-sufficient.

You are writing for that session, so know what it will do. Each item below is
prescribed in full by the reference that owns it; this list is the map, not the
specification.

- **Run the Pre-Flight gate in turn 1**, before anything else — that a `/goal` naming
  the plan is driving it, that model, effort and permission mode are the ones the plan
  was written for, that the privileges the tasks need exist, and that the working
  directory, branch and plan path are what the plan expects. Any failure ends the run
  right there as a blocked report: not an adaptation, and not a run that starts
  anyway. `preflight.md`
- **Work the tasks in order**, ticking each checkbox and appending to the Run Log as it
  goes, so an interrupted run resumes from the file and the user can watch progress by
  reading it. `plan-template.md`
- **Run the acceptance checks for real and show their output** — not a summary — and
  re-run the full set immediately before finishing, because the evaluator can only
  judge from what is still visible in the transcript. `goal-condition.md`
- **Treat a permission denial as a blocked report**, not an obstacle to route around: a
  denied command means the plan prescribed something phase 2 cannot do. `preflight.md`
- **Commit on the current branch** with the agreed prefix. Never create a branch unless
  the plan explicitly says to.
- **Close out the ticket before removing the plan file**, and remove that file as the
  final act — with a ticket, in a separate commit after the preservation commit, so the
  commit the comment links to stays the last one in which the plan exists. `jira.md`
- **Write the blocked report if a check genuinely cannot pass**, then stop.

That last one matters more than it looks. Without a reachable failure state, a plan
with one impossible check turns into a session that cannot stop, retrying forever.

## References

Each file below **owns** the rules it covers: where this body and a reference
disagree, the reference wins, and a rule that changes changes there. This body says
what each is for so you know what you are reaching for; it deliberately does not
restate them, so that there is only one place for each to be wrong.

One overlap is deliberate and is not drift. `plan-template.md` carries text meant to
be *copied into the plan file* — the Execution Protocol, the Pre-Flight checks, the
Ticket Closeout. Those copies are the artifact phase 2 reads, not a second statement
of a rule, because phase 2 runs with no plugin installed and can consult nothing but
the plan and the repository.

- `references/plan-template.md` — **owns the plan file's shape**: the template section
  by section, with what each section is for. Read before writing a plan.
- `references/preflight.md` — **owns the gate** phase 2 runs before task 1: how a
  session checks that its plan's `/goal` is driving it and its own model, effort and
  permission mode, which privileges to probe and how, and why a failure there is
  written up rather than worked around. Read before filling in a plan's Pre-Flight
  section.
- `references/jira.md` — **owns the ticket side** of the workflow: why a ticket is a
  request rather than a specification, how to fetch one and turn it into a requirements
  conversation, how the plan records what the user decided against it, and the closeout
  that commits the finished plan and links the ticket to it at the end of phase 2. Read
  when a ticket is named.
- `references/goal-condition.md` — **owns the `/goal` condition**: the character
  budget, shell safety, the escape hatch, worked examples. Read before writing a
  handoff.
- `references/review-loop.md` — **owns the adversarial review loop**: the reviewer
  command, the prompt that puts it in phase 2's position, and when to stop. Read
  before the first review round.
