---
description: Split a piece of work into an interactive planning phase that produces a self-sufficient plan file, and an autonomous execution phase run by a fresh `/goal` session. Use this skill whenever the user wants to plan before implementing, wants a plan another session or another model can execute unattended, says the work is too big for one session, asks to "hand this off", "write a plan I can run later", "set this up so it can run autonomously", mentions PDCA, names a Jira ticket to implement, or types /pdca:plan. Also use it when the user is about to set a `/goal` by hand — a goal grounded in a verified plan beats one grounded in assumptions.
name: plan
user-invocable: false
---

# PDCA: two-phase development

This is the Deming PDCA cycle with a session boundary in the middle.

- **Plan** — the **planning phase**: an interactive session with the user. Explore,
  verify assumptions by actually running commands, and write a plan file good enough
  that nobody has to babysit its execution.
- **Do / Check / Act** — the **execution phase**: a *fresh* session, optionally
  on a different model and effort level, that executes the plan file under `/goal`
  and does not stop until a separate evaluator agrees the work is finished.

"Phase 1" and "phase 2" below are shorthand for those two, and the sessions running
them are the planning session and the execution session. The roles have fixed
names as well: the **planner** is the model in phase 1; the **executor** is the model
in phase 2; the **reviewer** is the executor's model reading the plan cold inside phase 1; and the
**evaluator** is the small model behind the `/goal` Stop hook. The user ends the
planning loop by saying **proceed** — said explicitly, in whatever words; silence, an
absence of objections, or your own confidence is not one.

The split exists because the two phases want opposite things. Planning wants the
user in the loop, wants questions asked, wants to change its mind. Execution
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

1. It blocks what the planning phase produces and some of what it checks. Read-only
   probes do run in plan mode — `kubectl get` and `grep` work fine, verified
   directly — but plan mode cannot write the plan file to the repository root,
   cannot write spike files, and denies verification commands that touch state. The
   phase needs all three. Plan mode's own plan is a different artifact entirely:
   ephemeral, rendered for approval, never on disk. Only the file on disk at the
   repository root is the plan file this skill means.
2. It re-renders its whole plan in the transcript every turn. The plan file instead
   lives on disk, is edited in place, and each turn reports only the delta.

Work in the session's normal permission mode, with the one exception step 4 spells
out: the commands the plan prescribes are verified under phase 2's mode, which may mean
asking the user to switch this session's mode for that part of the work. If the session
is currently in plan mode, say so and ask the user to exit before continuing.

Plan mode does have a place in this workflow, just not here: the reviewer in step 7
needs read-only exploration and must not touch the repository, which is exactly what
plan mode enforces.

## Git is not optional

This workflow needs a git repository, and the plan is always tracked in it. The plan is
committed at handoff, so phase 2 starts from a clean tree and the launch command
survives; its final state is committed again before it is removed, because that commit
is the record of the run once the file is gone. Without git there is nowhere for the
plan to live, nothing for the pre-flight to compare against, and no run record. So the
first thing step 4 verifies is `git rev-parse --show-toplevel`; if the working directory
is not a repository, say so and stop. Do not `git init` on the user's behalf — that is
their decision to make, not a gap to paper over.

There is no untracked plan and no question about committing one. The only tracking
question the workflow ever asks is whether the closeout pushes, and only when a ticket
was named.

## Keep the status line posted

`/goal` gets a progress badge for free in phase 2. Phase 1 gets nothing, and it is
the phase with the long quiet stretches — verification runs commands for minutes at a
time, a review round is an entire background process — so a user watching a spinner
cannot tell step 4 from step 7. A plugin cannot drive Claude Code's status line, but
the user's own status-line command can display whatever a file holds, and it receives
the session id to find one with. So maintain a one-line status file for the phase:

```bash
mkdir -p ~/.cache/claude-pdca
printf 'verify' > ~/.cache/claude-pdca/"$CLAUDE_CODE_SESSION_ID".status
```

Update it at every step transition. Name the
step, not its number: the loops re-enter earlier steps, so a number would read "6 of
8" twice with different meanings. The names are `interview` — the first write, in
step 1, since parsing takes no time a status line could show, and again while step 5's
questions wait for an answer — `sources`, `verify`,
`draft`, `iterate`, `review 2/10` (the round within the round budget), `handoff`, and
`re-verify` for a reopened plan. Step 7's rounds are the one exception: the `review`
skill writes `review N/<budget>` itself at every round, so leave that file to it while
the loop is running and pick the names up again at the handoff. Name where the session is *now*, not the furthest
point reached — a re-entry from the handoff back into the iteration loop is `iterate`
again.

Two rules govern the file's lifetime. Sweep leftovers on the first write —
`find ~/.cache/claude-pdca -name '*.status' -mtime +7 -delete` — because an abandoned
session cannot clean up after itself. And delete this session's file when the phase
ends, after the launch offer in step 8 or the moment the user abandons planning: a
status file that outlives the phase has the status line asserting work that is not
happening. If the user's status line does not read the file none of this shows, which
is fine — the plugin's README carries the segment they opt into.

## Phase 1 — the planning session

### 1. Parse the invocation

The command takes `[model] [effort] [rounds] <goal or plan path>`. The grammar is
deliberately rigid, because a clever rule here is worse than a predictable one:

- A leading **model** token — `fable`, `opus`, `sonnet`, `haiku`, or a full model ID
  — is consumed as the model. `haiku` is consumed like the others so that the parse
  stays predictable; step 5 says why it is then refused as the executor.
- An **effort** token — `low`, `medium`, `high`, `xhigh`, `max` — is consumed *only
  when it immediately follows a model token*. A bare leading effort word is always
  goal text.
- An **integer** is consumed as the review loop's round budget *only when it
  immediately follows an effort token*, for the same reason and with the same
  deliberate cost: a bare leading number is goal text.
- Everything remaining is the goal.

So `opus max harden the retry path` parses as model `opus`, effort `max`; `opus high 20
harden the retry path` adds a round budget of `20`; and `max out the connection pool`
is entirely a goal, which is the case a looser rule gets wrong. The deliberate cost:
you cannot pass effort without a model, nor a budget without both —
`high fix the login bug` reads as a goal, and so does `10 retries is too many`.
Nothing is lost, because step 5 asks for all three anyway — and what the parse does
yield for them is the user's **preference**, not a settlement: step 5 weighs it in its
own proposal and asks the user to confirm it, just before the first draft.

Then **echo the parse back in your first line** — `Planning for Opus at high effort,
review budget 20, to be confirmed before the first draft — goal: …`, or `Planning —
executor and review budget proposed before the first draft — goal: …` when none was
given — so a misparse is obvious and costs one correction rather than a whole
session. A `haiku` token is echoed with the reason it will not be offered back.

If the remainder is a path to an existing file, read its frontmatter. A file whose
frontmatter says `plugin: pdca` is a plan this workflow wrote: reopen it instead of
starting a new one — see "Reopening a plan" below. A file whose frontmatter carries
`plan_file` and `next` — and no `plugin` — is a **blocked report**, not a source, and
its contents are a failure message, not requirements: reopen the plan its `plan_file`
names, whose `status` will be `blocked`, and follow "Reopening a plan" from there. A
report written before plugin 0.13.0 has no `plan_file`, and one written before 0.10.0
has no frontmatter at all; for those, a path ending `.BLOCKED.md` names its plan by
that suffix — `.BLOCKED.md` back to `.md`. Any other readable file — a spec, a
design note, an RFC — is a **requirements source**: the work is to plan what it asks
for, and step 3 reads it. A URL in the remainder is a source too, unless it is a
ticket URL, which is the ticket. A source named alongside intent is both — the
document, and an opening statement about what the user wants from it.

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

### 2. Settle the ticket before planning

Ask for it **now**, as an interview: one `AskUserQuestion` call with one question. The
user picks an option instead of composing a free-form reply, which is what makes
asking cheap enough to do unconditionally: a marked recommendation is one keystroke to
accept, and a composed reply invites the partial answer that leaves the question
unsettled. Put your recommended choice first, labelled "(Recommended)"; a ticket key
or URL, which no option can express, arrives through the interview's free-text
"Other" field.

The ticket comes first because step 3 reads it before anything else happens. The
other handoff parameters — the executor's model, effort and permission mode, and the
review loop's round budget — are not asked here. Nothing before the draft needs them
settled, since step 4 verifies under `auto` until step 5 says otherwise, and nothing
here would inform a proposal for them but a line of intent. Step 5 proposes them once
the work is agreed and understood. That holds for values the command line gave as
well: they wait for step 5's confirmation.

**Jira ticket.** Always ask, every time — the answer is a key like `ACME-123`, a
ticket URL, or an explicit "none". In the interview that means: "None" is an option, a
key inferred from the branch name is another when there is one, and a typed key or URL
comes in as "Other". Never adopt the inferred key without the user picking it, and
never skip the question because the goal looks self-explanatory; a ticket the user
forgot to mention is the commonest source of a plan that satisfies its author and not
the work item. Check `git log --oneline -20` for the commit prefix convention while you
are at it. If a ticket is named, step 3 reads it before anything else happens.

The ticket key ends up in the handoff command, in the commit prefix, and in the
closeout that ends phase 2 — so ask now. Supplied at paste time it is merely a
prefix; supplied now it is also requirements to plan against.

A spec is not interviewed for: a spec the user has is one they hand over — on the
command line, in the goal text, or pasted. Do ask, once,
if step 4 turns up a document in the repository that reads like a spec for this goal;
whether it is a source is the user's call.

### 3. Read the sources and discuss their requirements

Only when there is at least one requirements source — a ticket from step 2, a spec
from step 1. Skip to step 4 when there is none, and let the frontmatter say so:
`ticket: none`, `sources: []`.

Read every source properly. For a ticket that means description, acceptance criteria,
comments, linked issues — `references/jira.md` has how to fetch it and what to read.
For a spec file or URL it means the whole document, including the parts that read like
background. Then put the requirements to the user as one numbered list across all
sources, each item naming its source and carrying a proposed disposition, and settle
each one before planning. `references/jira.md` has the exact shape of that
conversation; a spec goes through the same one.

Two rules govern the whole exchange, and both matter enough to state here:

**A source is a request, not a contract** — even one titled "specification". The plan
is allowed to come out different from it — most often in the non-functional half, the
parts that say *how* rather than *what*: a named mechanism, a library, a metric, a
split into phases, a performance number. Those are the author's guesses, written
before anyone verified anything, and this phase is where things get verified. Where
what you verified says otherwise, propose the deviation with the evidence. But every
requirement is still raised explicitly — none quietly dropped because it looks
tangential, none quietly adopted because it is written down. **The last word is the
user's**, not the source's author's and not yours.

**Where the plan and a source disagree, record the disagreement.** A requirement the
user descopes, defers, or reverses is written into the plan's Requirements section
*as* descoped, deferred or reversed, with the reason and the source. That section is
not bookkeeping: without it, phase 2 reads the ticket or the spec, sees a requirement
the plan does not cover, and helpfully implements it — which is the exact failure the
planning phase exists to prevent.

Naming the ticket also settles, by itself, what the ticket gets at the end: phase 2
preserves the finished plan in a commit of its own — it does that for every plan — and,
with a ticket, posts a comment linking the ticket to the plan at that commit. Jira
cannot hold the file — the MCP server has no attachment upload and no way to link the
plan from the issue — so git holds the artifact and the ticket gets the URL. That is a
standing consequence of the answer given in step 2, not a further decision — do not ask
the user, now or at handoff, what should be done with the plan or the ticket when the
work is finished. What is *not* settled yet is mechanism: the comment channel, and whether the closeout pushes. Step 4
probes both, and `references/jira.md` says what to do when there is no channel — the
only closeout questions that are warranted, and they are about mechanism, never about
whether the closeout happens.

### 4. Explore and verify

This is the substance of the phase. For every claim the plan will rest on, run
something that proves it, and record both the command and what it returned.

The failure mode this prevents is specific and common: phase 2 opens the file,
finds "the retention setting is configured in `values.yaml`", discovers it is not,
and now has to improvise — unsupervised, with no way to ask. Every unverified
assertion in the plan is a place where an execution session can quietly go wrong.

Verify first that the working directory is a git repository — `git rev-parse
--show-toplevel` — and stop if it is not; see "Git is not optional". Then verify at
minimum: that the files you name exist and contain what you say; that the
commands you prescribe exist and run in this environment; that the current state is
what you think (config values, schema, cluster state, dependency versions); and that
the acceptance checks pass *now* for the right reason, or fail *now* for the right
reason.

**Run every command you prescribe, under the permission mode phase 2 will use.** This
is the concrete test for a failure that is otherwise invisible until nobody is
watching: `auto` decides without asking, and it decides *both ways* — a command it
refuses is refused silently, with no human to override. If a command you are about to
prescribe needed manual approval or was denied here, that is a defect in the plan, not
a footnote. Substitute a command that runs cleanly; where none exists, carry the
refusal into step 5's proposal, where a mode escalation is the user's explicit choice
and never yours. A prescribed command phase 2 cannot run makes its acceptance
criterion unreachable.

**Until step 5, phase 2's mode is `auto`.** The mode is settled only in step 5, with
the rest of the executor, so this step verifies under `auto` — the mode phase 2 runs in
unless the user deliberately chooses another, and the only one this skill ever
proposes. Read "phase 2's mode" in this step that way until step 5 has spoken. What
this step finds under it is what step 5's proposal for the mode rests on, and a
different settlement there brings you back to this test under the settled mode before
the first draft.

"Run" has two forms, and which one a command gets is decided by what it does. A
command with no side effects outside the working tree — a read, a build, a test, a
`grep` — is run as written. A command that changes state outside the tree — a `helm
upgrade`, a `kubectl apply`, a push, a migration, anything that does the work phase 2
exists to do — is **rehearsed**, never run: its `--dry-run` or `--dry-run=server`
form, a `--check` flag, a `kubectl auth can-i`, a scratch target, whatever comes
closest to the real shape without the real effect. Running the real form here would do
phase 2's work in phase 1, falsify the Verified Context you are about to write, and
turn the acceptance criteria into checks that pass without the work being done. The
plan records which commands were proved only in rehearsal; and where the classifier's
verdict on the real shape genuinely cannot be had without the real effect — the
rehearsal form differs in shape, and `references/preflight.md` says shape is what the
classifier judges — say so in the Verified Context as a stated risk, not as a
verified fact. A denial or a prompt on the rehearsal form is still the defect above.

**That test only means something from a session in phase 2's mode.** A session runs
in exactly one permission mode, and you cannot switch it — only the user can, with
`Shift+Tab`, which cycles the modes and reaches `auto` wherever auto mode is available
(`bypassPermissions` is in the cycle only when the session was started with a bypass
flag, and `dontAsk` never is; a mode the cycle does not offer means restarting
planning with `claude --permission-mode <mode>`). So before the first prescribed
command, read this session's own mode the way the pre-flight gate reads phase 2's:

```bash
T=$(ls -t "$HOME"/.claude/projects/*/"$CLAUDE_CODE_SESSION_ID".jsonl | head -1)
grep -o '"permissionMode":"[^"]*"' "$T" | tail -1
```

Say what it printed, and act on it. When it is phase 2's mode, verify as this step
says. When it is broader — `bypassPermissions` — nothing you run here meets the
classifier, so a clean run proves nothing about phase 2: ask the user to switch this
session to phase 2's mode for this step, and if they decline, the plan says in its
Verified Context that its commands were not verified under that mode, as a stated risk
rather than a silent one. When it is narrower or merely different — `default`,
`acceptEdits`, `dontAsk`, or plan mode — a prompt or a denial here is a fact about
this session, not about the plan: it does not mean phase 2 would refuse the command,
and it must not send you rewriting good tasks to dodge a classifier that was never
consulted. Ask the user to switch, then run the commands again under phase 2's mode.
If they decline, the fallback is the same as for the broader mode — the Verified
Context records that the prescribed commands were not verified under phase 2's mode,
as a stated risk — with one addition: nothing observed under this mode is written up
as a plan defect, because no prompt or denial here says what phase 2 would do. In
every case, record in the Verified Context which mode the commands ran under —
"verified under `auto`" is a claim the executor relies on, and it has to be true, and
"not verified under `auto`" is one the reviewer and the executor can tell from an
oversight.

**Enumerate the privileges the tasks need, and probe each one.** Read back through
what the plan will prescribe: every command that pushes, writes outside the
repository, touches a cluster, or reaches the network needs something this session
happens to have and phase 2 may not — a cluster role, a live token, passwordless
sudo. For each, find the cheapest command that proves the right
exists without exercising it (`sudo -n true`, `kubectl auth can-i …`, a `--dry-run`
form), run it here, and record it as a pre-flight check in the plan. Those probes are
what turns a silent refusal at task 5 into a clean abort in turn 1;
`references/preflight.md` has the catalogue and the reasoning.

**The closeout is one of those privileges.** Phase 2 finishes by committing the final
plan and, when a ticket was named, pushing it if that was agreed and posting a comment
linking to it — and none of that is guaranteed to work: an MCP server that
needs interactive authentication, a token this session holds and the next one does not,
an `auto` classifier that refuses an MCP write, a protected branch that rejects the
push. Probe each, record the verified calls and identifiers in the plan, and work out
the permalink template for this repository's host — the proof comes at the handoff
commit in step 8 item 4, where the user opens the resulting URL, so work the template
out now and record it; a link that resolves then is the only honest proof the
template is right. If there is no comment channel, say so now and let the user choose
the fallback — see `references/jira.md`.

**Remote Control is a launch-time privilege too, and the one that is only a warning.**
The handoff starts phase 2 with `--remote-control` — see "The handoff command" — and
that needs a claude.ai subscription login: `claude auth status` prints
`"authMethod": "claude.ai"` and `"apiProvider": "firstParty"`. An API key, a Bedrock
or Vertex login, a custom `ANTHROPIC_BASE_URL`, or any of the variables that switch
off non-essential traffic (`DISABLE_TELEMETRY`, `DO_NOT_TRACK`,
`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_GROWTHBOOK`) blocks it. When the
probe fails, tell the user and keep the flag: a session whose Remote Control cannot
connect still starts, says so on screen, and does the work — it only runs unwatched.
So this is not a plan defect and does not become a pre-flight check.

You may prototype throwaway spikes to de-risk an assumption — a scratch script, a
quick patch to see whether something compiles. Restore the working tree before the
handoff; phase 2 must start from a state you understand. Apart from spikes, the plan
file is the only file you write **in the repository**. Scratch files this workflow
needs of its own — the reviewer prompt, its captured verdict — belong outside the
tree, under `mktemp -d` or `/tmp`. A stray scratch file in the repository leaves
phase 2 starting from a dirty tree, which breaks the one signal it has for
recognizing its own work.

### 5. Settle the executor and the round budget, then write the plan file

**Before the first word of the draft, settle who will read it — by proposing, not
merely asking.** This is the latest point at which the executor's model, effort and
permission mode and the review loop's round budget can be settled, and it is that late
on purpose.

It cannot be later. These are not administrative details you can collect at the
end. How much the plan has to spell out depends on who is reading it: a plan for
`sonnet` at `low` effort needs exact file paths, exact snippets, and no inference; a
plan for `opus` at `max` can state intent and constraints and trust the reader to
work out the details. You cannot write at the right altitude without knowing the
audience, and you cannot write the Pre-Flight section without knowing the mode. Model,
effort and mode are what phase 2 checks itself against before it touches anything, so
settling them here is what makes that gate possible at all. See
`references/preflight.md`.

It should not be earlier. Before step 3, the only thing to base a proposal on is a
line of intent. By now the plan exists in substance, agreed with the user though not
yet written down: the goal as the conversation has sharpened it, every requirement
with the disposition the user gave it in step 3, and the ground step 4 verified —
including what `auto` did with every command the plan will prescribe. The proposal
rests on that agreement: how many files the agreed work touches, how much judgement
its tasks leave to the reader, how much of it changes state that cannot be taken back,
whether anything it needs was refused, how long a plan the reviewer will have to read.

**Propose first, in prose, then ask.** A few lines naming a mode, a model, an effort
and a budget, each with its reason from what was agreed: "I propose Sonnet at high
effort under `auto`, and ten review rounds — we agreed on three tasks in two files,
every command they prescribe ran cleanly under `auto`, the one state change is a
`helm upgrade` whose rehearsal did too, and nothing in it asks for judgement the plan
cannot spell out." Then the interview, in step 2's shape: one `AskUserQuestion` call
with four questions — permission mode, model, effort, round budget, which is the
tool's full capacity — in which your proposal is the option labelled "(Recommended)",
its reason in one line in the option's description. Always all four questions,
because a value the command line gave is asked as well, as a confirmation. The
proposal is what makes the answer an informed one; the interview is what makes it a
settled one.

- **Permission mode for phase 2.** Propose `auto`, always: it is the mode step 4
  verified under, and the mode decides what phase 1 has to prove can run unattended.
  What the agreed plan changes is the reason you give — that every prescribed command
  and probe ran cleanly under `auto`, or which one was refused with no substitute. For
  that one the choice is the user's: change the plan so it does not need the command,
  or escalate the mode deliberately. `dontAsk` and `bypassPermissions` are that
  deliberate, risk-acknowledged choice, never your proposal — see "The handoff
  command". The mode is written into the plan literally so phase 2 can check it before
  starting.
- **Model and effort for phase 2.** Propose from the agreed plan; `opus` at `high`
  when nothing in it points elsewhere. The interview offers `fable`, `opus` and
  `sonnet` — **not `haiku`**: `auto` is unavailable under Haiku, so a session launched
  with `--model haiku … --permission-mode auto` prints `auto mode unavailable for this
  model`, falls back to manual mode, and its first Bash call then waits for an
  approval nobody gives (observed 2026-09-12 on Claude Code 2.1.269). The one way a
  Haiku plan runs unattended is `bypassPermissions`, and only as the user's
  deliberate, risk-acknowledged choice made in this same interview — a model and a
  mode they name through "Other", never options you offer — knowing that
  `/pdca:execute` cannot launch such a plan from an `auto` session, because the
  classifier refuses to start a bypass child, so it is launched by hand.
- **Round budget for the review loop.** How many conclusive rounds step 7 may spend
  before it stops and puts both positions to the user. Propose `10`, and offer `5`
  and `20` beside it; any other number arrives through "Other". An agreed plan with
  many tasks or many state changes is a reason to propose `20`, and to say so. It is
  written into the plan's frontmatter as `review_rounds` at the first draft, so a
  reopen reuses it instead of asking again, and step 7 passes it to the `review`
  skill.

**A value the command line gave is confirmed, not assumed** — it is the user's
preference, and the proposal weighs it rather than ignoring it. Its question offers
that value first: labelled "(given, Recommended)" when the proposal agrees with it,
"(given)" when it does not, followed then by your pick labelled "(Recommended)", the
prose having already said what in the agreed plan argues for the change. Keeping what
they typed is one keystroke either way; never swap your pick in silently. A given
`haiku` is the exception: it is not offered back, for the reason above, and a user who
still wants it answers as the model bullet says.

Three consequences of the answer come before the draft as well. A mode other than
`auto` sends you back to step 4's mode test, run under the settled mode — the
verification so far proved what `auto` does, not what the settled mode does. A reader
who needs more than step 4 gathered sends you back to it too: `sonnet` at `low` wants
exact snippets, and each one is verified before it is prescribed. And the model has to
be written the way the gate reads it.

**Resolve the executor's model alias to the literal ID the gate will compare.** The
interview settled an alias — `opus`, `sonnet`, `fable` — and the pre-flight gate
string-matches the ID the transcript records, which is not guessable from the alias:
the plugin's own record has a `haiku` launch whose transcript said `claude-sonnet-5`.
So ask the alias what it resolves to, in a session as short as one can be:

```bash
claude -p --model <alias> --effort low --output-format json 'Reply with the single word ok.' \
  | python3 -c 'import json,sys; m=list(json.load(sys.stdin)["modelUsage"]); assert len(m)==1, m; print(m[0])'
```

The `modelUsage` key is the literal ID — `claude-opus-5` for `opus` — and it is the
same string that session's transcript records, which is what the gate reads (both
verified 2026-09-19). Write exactly that into `executor.model` and into Pre-Flight
check 1, and never this session's own model unless phase 2 runs the same alias. A full
model ID, typed on the command line or into "Other", is resolved the same way; the
comparison in phase 2 is exact, not a prefix.

Then write the plan. Path: `<YYYY-MM-DD>-<slug>-plan.md` at the repository root, slug
derived from the goal.

The root is the whole directory rule — do not file it under `docs/`, `docs/plans/`, or
any other directory, even where one already exists. The plan is short-lived: phase 2
removes it in the Closeout, and a file at the root is the one both phases and the user
can name without looking.

The `-plan.md` ending is not decoration. At the root the plan sits beside `README.md`
and whatever else lives there, and the suffix is what tells a reader — and the next
session — that this file is a plan and not a spec, a note, or a report. Every plan
ends this way, so a plan is recognizable before it is opened. Say where you put it.

Follow `references/plan-template.md` — it is a fixed template, and its sections
exist to force out the gaps that make a plan unexecutable. Read it before writing
your first draft.

The file opens with the frontmatter the template prescribes. Three of its fields come
from the plugin itself: read `"${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"` and
copy `name`, `version` and `repository` into `plugin`, `plugin_version` and
`plugin_url`. If that variable is unset, this skill's own directory names the
installed version — `~/.claude/plugins/cache/<marketplace>/pdca/<version>/`. Set
`status: drafting`. The `executor` block takes the model, effort and mode from this
step's interview, in the literal spellings the pre-flight compares — the model as the
ID the alias resolved to above, never the alias. The `planner` block takes the same
three keys for this session, read the way the pre-flight gate reads phase 2's:

```bash
T=$(ls -t "$HOME"/.claude/projects/*/"$CLAUDE_CODE_SESSION_ID".jsonl | head -1)
grep '"type":"assistant"' "$T" | tail -1 | grep -o '"model":"[^"]*"' | head -1
grep -o '"permissionMode":"[^"]*"' "$T" | tail -1
echo "effort=$CLAUDE_EFFORT"
```

Copy what it prints; where the transcript cannot be found, the model is the one your
own context names, and a value no source gives is written `unknown` rather than
guessed. `review_rounds` takes the round
budget from this step's interview; `sources` and `ticket` record step
3's inputs, `ticket: none` and `sources: []` when there were none. The fields step 8
settles — `branch`, `closeout_push`, `permalink` — are written then, not guessed now.
`blocked_report` is phase 2's alone: a plan being drafted has no report, and the key
appears only when a run leaves one.

### 6. Iterate with delta reports

Each turn: update the file, then report **only what changed** and what is still
open. A few lines. Do not reprint the plan — the user reads the file, or its diff.

Prefer concrete open questions over generic ones. "Should the retention change
apply to staging too, or dev only?" is answerable in three seconds; "any other
requirements?" is not.

Iterate until the user says proceed. They decide when planning is done, not you.

**Never reach the handoff in the same turn as the first draft.** Write the plan, then
stop and hand control back — always, even when the plan looks finished and the goal
was clear. This is not politeness; it is what makes the phase mean anything. The exit
condition of this loop is that the user says proceed, and that is something they say,
not something you infer from a one-line goal and your own confidence. A plan nobody
reviewed has skipped the only step the planning phase exists for.

So: at least one full round-trip before step 7, and the proceed is one the user
actually said. Silence is not one. Nor is the absence of objections to a plan they
have not been given a chance to read.

There is no exception and no non-interactive mode. If someone wants a plan handed
straight to an execution session without review, they do not need this workflow at all —
they can set a `/goal` directly and skip the planning session entirely. Choosing
`/pdca:plan` *is* choosing the planning phase, so treat any pressure to skip it as
a sign the wrong tool was reached for, not as licence to hurry.

### 7. Adversarial review by the executor

When the user says proceed on a version this loop has not already cleared, the plan
is reviewed — not by you, but by a fresh `claude -p` process running **phase 2's model
at phase 2's effort level**, which sees the plan and the repository and nothing else.
(A proceed on the exact version the reviewer already cleared needs no new round —
that is the fixpoint below.)

You cannot review your own plan for self-sufficiency, and the reason is structural
rather than a matter of diligence: you remember the conversation. The constraint the
user mentioned once, the file you checked and dismissed, what "the usual way" means
in this repository — you read all of that back into the plan without noticing it was
never written down. A reviewer holding your context reads past every such gap. A
reviewer without it walks into them exactly as phase 2 would.

The loop itself — the reviewer command, the verdict rules, the cold re-reads, the
inconclusive-round rule, the per-round report — belongs to the sibling `review` skill.
Two things about it are this step's and are not delegated. One is the paragraph
above: the reviewer is **phase 2's model at phase 2's effort**, because a plan is
self-sufficient or not for a particular reader, and that is the reader. The other is
the budget, which is the plan's own `review_rounds`, the number step 5 settled and
this step passes in: review, fix the blockers, review again, until the reviewer
returns AGREED or the budget is spent.

If it does not converge, stop and put both positions to the user — a persistent
disagreement between the planner and the executor is a finding in itself, and it is
the user's to settle. Their settlement is not an exit: the plan is a contract between
the user, the planner and the executor, so a plan the executor vetoed is never handed
off. The user edits the plan, which writes their decision into it and re-enters this
step as a fresh loop with a fresh budget; or they raise the budget and the loop
continues; or they leave the plan as it is, `status: drafting`.

AGREED ends the loop; it does not by itself reach the handoff. What it exits to
depends on whether the review changed the plan:

- **AGREED, plan unchanged** — no blockers were fixed on the way and no nits
  applied: the version the user said proceed on in step 6 is the version the reviewer
  cleared. Nothing new for the user to see; go on to step 8.
- **AGREED after the plan changed** — blockers fixed in an earlier round, or nits
  applied now — the plan the user said proceed on is not the plan about to be handed
  off. Report the review's changes as a step 6 delta and hand control back. A proceed
  attaches to a version of the plan, not to the plan in the abstract, and the review
  has just written a version the user has never seen. Nits applied as the reviewer
  worded them do not by themselves reopen the review; the `review` skill's
  "Handling the verdict" says why.

Expect afterthoughts at that point, and welcome them — returning here is an
invitation to have them, not a signature to collect. They are step 6 resuming, and
a change that alters what phase 2 would do goes back through this step: an
unreviewed edit to a reviewed plan is an unreviewed plan. Each re-entry is a fresh
loop with its own budget, though a re-review of a lightly edited plan usually
returns AGREED in one.

So the exit condition of the nested loops is a fixpoint: **one version of the plan
that all three parties stand behind at once** — the user, whose proceed it carries;
you, its author, who fixed the blockers you agreed with and recorded in the plan why
the rest are not blockers; and the executor, whose AGREED came from
reading that very version. The loops alternate until a single version holds
all three, and only then does step 8 begin.

There is no exception to the fixpoint. The user outranks both models by deciding what
the plan says, not by launching a plan the executor refused to sign: a proceed over a
standing veto hands phase 2 a document one of the three parties has already said it
cannot execute, which is the exact failure this step exists to catch. Editing the plan
is how such a disagreement is settled, and the next cold round is what judges the
settlement.

Read `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md` and
`${CLAUDE_PLUGIN_ROOT}/skills/plan/references/executor-lens.md` before the first
round: the skill has the exact command, the loop and how to handle a verdict you
disagree with, and the lens carries what a plan review looks for.

### 8. Hand off

The order below is not arbitrary. The decision in item 1 has to be *asked* first
because the goal condition depends on it, but the commit itself has to *happen* last,
because the plan is still being written until the handoff is in it.

Item 1 is also the **only** question this step asks, and it is asked only when a ticket
was named. Do not ask whether to commit the plan — it is always committed, see "Git is
not optional" — and do not ask what should happen to the finished plan or the ticket at
the end of phase 2: the plan's final state is preserved in its own commit for every
plan, and the user answered the ticket half by naming the ticket, exactly as the plan's
Closeout section already prescribes. Re-asking a settled decision reads as the workflow
not trusting its own record, and invites an answer that contradicts what the plan and
the goal condition were built on.

One question does not mean one possible reply, though. An answer that changes the
plan — "actually, could it also…" — is not an answer to the item-1 question; it is
step 6 resuming, and a material change goes back through step 7. The fixpoint from
step 7 does not expire because the conversation moved on a step. And a re-entry —
from here, or from the launch offer — rebuilds whatever this step had already
built: the goal condition and the Handoff section are regenerated from the revised
plan, and a plan already committed takes a follow-up commit. A handoff line
pointing at acceptance criteria the plan no longer states is exactly the stale
artifact this step exists to prevent.

1. **Settle whether the closeout pushes — decision only, no commit yet.** Only when a
   ticket was named; the condition cannot be written until you know. Recommend yes — an
   unpushed preservation commit makes the comment's link dead until somebody pushes by
   hand — and respect a no: some branches are protected, and an unattended session
   writing to a shared branch is a real decision. A no means the comment carries the
   SHA and a `git show` command instead of a URL, and the Handoff section says someone
   must push afterwards. Without a ticket there is nothing to ask: the closeout still
   makes its two commits and does not push, unless the user said otherwise while
   iterating.

   Settle the branch here too, without a question. The plan works on the branch
   planning happened on, and `branch` records it. Only when the user asked for the
   work to go on a new branch — in the goal text or while iterating, never inferred
   from a ticket or the repository's habits — create it now, before the commit in
   item 4, so the plan lands on it: `git switch -c <name>`. Phase 2 never creates a
   branch, so this is the only place one comes from. The checkout stays on that branch
   afterwards — say so when you print the handoff, so the user is not surprised to
   find themselves off their usual branch. Record in Rollback how the branch is
   disposed of if the run fails.
2. **Build the goal condition** per `references/goal-condition.md`. Read that file
   before writing the condition; the constraints there are not obvious.
3. **Write the handoff command into the plan's Handoff section**, then print it.
   Terminal output is the most perishable place a command can live, and the gap
   between the two phases can be weeks. A plan file that carries its own launch
   instruction can be picked up by whoever finds it. In the two-step form, both parts
   go in — the flags-only command in the `bash` block and the full condition in the
   `goal` fence the template fixes under "The two-step Handoff" — because a Handoff
   with a prompt-less command and no `goal` fence is one `/pdca:execute` refuses to
   launch. Below the full command, write
   the short form the template shows — the one-line `/goal` a user can type into a
   session they started by hand — and say what it gives up;
   `references/goal-condition.md` has the words. In the same edit, finish the
   frontmatter: `status: handed-off`, `branch` as `git branch --show-current` prints
   it, `closeout_push` from the decision in item 1, `permalink` as the template worked
   out in step 4 or `none`, and the `planner` block read again as step 5 reads it, so
   it names the session handing the plan off — a reopen, or a mode switched in step 4,
   is otherwise misrecorded.
4. **Now commit** — always, and the plan file alone: stage it by name, `git add
   <plan>`, never `-a` or `.`, which would sweep whatever else the user had in the tree
   into the handoff commit — expensive to untangle in a repository whose next act is an
   unattended run. Follow the repository's commit convention, including the
   ticket prefix if that is what `git log` shows. Then check `git status --porcelain`
   shows nothing at all before you print the handoff: phase 2's Ground check requires
   a clean tree, so anything left over is the user's to commit or stash first, or the
   plan has to name it as expected dirt — say which, and do not print a handoff that
   will fail its gate in turn 1. Committing before item 3 would put a plan into
   history without its own launch command and leave phase 2 facing a dirty tree — both
   of which defeat the point.

   When a ticket was named and the closeout pushes, push this commit too — a branch
   created in item 1 goes up as `git push -u origin <branch>`, which sets the upstream
   that phase 2's plain `git push` relies on and proves the remote accepts the new
   branch — and build the permalink for the plan at it. Give the user that URL to open: a link that resolves
   here is the proof that the template recorded in the plan is the right one for this
   host, and it costs one click now instead of a dead link on the ticket weeks later.
   If it does not resolve, the template is wrong — fix `permalink`, take the follow-up
   commit this step's re-entry rule prescribes, and prove it again before offering the
   launch.

5. **Offer to launch the execution session.** If the user accepts, follow the
   `execute` skill — `${CLAUDE_PLUGIN_ROOT}/skills/execute/SKILL.md`: it starts the
   Handoff command as a new background process with
   `claude --bg`, reports the id and the Remote Control URL, and then keeps a
   checklist of the run in this session. Nothing in this
   session can set the goal, so a launch is always a new process — the `execute` skill
   says why. If declined, say that `/pdca:execute <path>` does the same thing later,
   and that the command itself sits in the plan to copy. Either way, explain briefly
   how a fresh process is achieved — see below.

## Reopening a plan

`/pdca:plan <path>` with a file whose frontmatter says `plugin: pdca` reopens that
plan. Its `status` says which case this is; read it, and do not infer the case from
the file's age or its checkboxes.

A reopen reuses the plan's own `review_rounds` for step 7 rather than asking for it
again. A plan written before plugin 0.12.0 has no such field: ask for the budget as
step 5 would, and write it in with the first edit. A plan written before 0.15.0 has no
`planner` block either; nothing asks for it, and the handoff writes it as it does for
every plan.

A model, effort or permission mode named on the reopen's command line —
`/pdca:plan opus max <plan>` — is a request to replace the plan's `executor` block,
and it is confirmed as on a first run: before the block changes, propose and ask in
step 5's shape, one question per value named — the named value first, labelled
"(given)", the plan's current one beside it, and your proposal saying which of the two
the plan as it now stands argues for. Once it is confirmed, update the block, the
Pre-Flight section's literal values and the altitude of the prose together — a plan
re-pitched for a different reader is a different plan — resolve the new alias to its
literal ID as step 5 does, re-verify the prescribed commands under the new mode, and
report the change as a delta. Step 7 then runs at the new model and effort. A round
budget named there replaces `review_rounds` the same way, once confirmed. When the
invocation names none of them, the plan's own values stand and are not re-asked.

**`drafting`** — planning never finished. Continue where it left off.

**`handed-off`** — the plan was finished and has been sitting, and both the repository
and the sources have moved on. Re-verify before doing anything else, and re-read the
ticket and any spec as part of that: a comment added last week can change a
requirement, and a ticket that has since been closed, split or reprioritized is a
reason to stop and ask rather than to launch. Report what changed in the sources
alongside what drifted in the repository. This is cheap, because the Verified Context
section records the command behind every fact: re-run them, along with the pre-flight
probes, and report which still hold and which have drifted — an access token that has
expired since the plan was written shows up here as readily as a changed config
value. When the plan sits on a branch phase 1 created for it, bringing that branch up to date
with its base — merge or rebase, whichever the repository's convention is — is part of
the same re-verification: the facts are re-checked against the code the run will
actually change, not against a base that has since moved. Then bring the plan back to
true — update the drifted facts, adjust the tasks and acceptance criteria that depended
on them — and set `status` back to `drafting` with the first edit.

**`executing`** — a run is under way or was interrupted. Say so and ask before
touching the file: relaunching — `/pdca:execute <path>` — resumes the run from the
ticked boxes, which is what the Execution Protocol is written for; reopening abandons
that run. Only the user can say which. Once you are reopening, the run's leftovers are
the user's call, exactly as a blocked report's partial work is — and here there is no
report enumerating them, so enumerate them yourself first: the ticked boxes, the Run
Log's started-lines, the run's commits on the branch (`git log` since the handoff
commit), and anything uncommitted in the tree. Then ask: **keep** the committed work
as the new starting state — the checkboxes stay ticked, the tasks are adjusted to
what remains, and the re-verification runs against the tree as the run left it — or
**revert** the run's commits and untick the boxes, so the re-verification runs against
the base the plan was written for. Record the answer in the Run Log, set `status:
drafting` with the first edit, and then treat the plan as `handed-off`: re-verify
against the chosen tree, bring the plan back to true, and take it back through
review. Never reset a plan whose work is still applied without saying so — a task 1
that re-runs an already-applied `helm upgrade` unattended is the failure this branch
exists to prevent.

**`blocked`** — read the blocked report first: the plan's `blocked_report` names it,
and on a plan blocked before plugin 0.13.0 it is the plan path with `.md` replaced by
`.BLOCKED.md`. It names what has to change, points back at the plan through its own
`plan_file`, and carries `next` in its frontmatter. `next: relaunch` means the run expects
the Handoff command once the environment is fixed — `/pdca:execute <path>` runs it — and a
reopen is only needed if the user wants to change the plan anyway — say so. Once you
are reopening: fold the report into
the Run Log, delete it, and clear `blocked_report` as you set the status — a report
never outlives the pick-up that reads it, a leftover one is exactly what a relaunch must
not find, and the key goes with the file it names — then treat the plan as
`handed-off`: re-verify, fix what the report names, and take it back through review.
Partial work the report lists is the user's call: keep it as the new starting state
and re-verify against it, or revert it. Ask, and record the answer in the Run Log.

**`done`** — should not exist on disk; the file is deleted on success. If one is
found, it is a stray copy. Say so and stop.

Every reopen that changes the plan ends the same way: back through steps 7 and 8 as
usual — a plan brought back to true is a changed plan, and an unreviewed edit to a
reviewed plan is an unreviewed plan — and the Handoff section is refreshed and
printed. So "I lost the command you printed" has two answers: `/pdca:execute <path>`
runs it out of the file, and a reopen refreshes it first — the freshness check is the
reopen's whole point, and the launcher does not do it.

A stale plan that gets executed anyway is not a disaster either: the Execution
Protocol tells the execution session to check the Verified Context against reality
first and stop if it has diverged. But re-verifying while a human is present is
strictly better than discovering the drift halfway through an unattended run.

## The handoff command

The execution session is a new `claude` process started in the working directory of the
repository being changed — usually, but not always, the one where planning happened.
When the plan and the work live in different repositories, the printed command takes
the `cd <work-repo> && claude …` form, and its condition names the plan by absolute
path — the session starts in the work repository, where the relative path names
nothing; `references/goal-condition.md` shows the form. It shares the repository and nothing else: no
conversation history, no context from phase 1. That is the point.

`/pdca:execute <path>` runs this command for the user — the `execute` skill owns how —
adding `--bg` so the process is detached and `--name` so `claude agents` shows which
plan is running. The command is written for a human as well, so it stays copyable
exactly as it stands.

```bash
claude --model opus --effort high --permission-mode auto --remote-control 2026-08-27-cache-ttl-plan '/goal <condition>'
```

- `--model` / `--effort` — as settled in phase 1, step 5, just before the first
  draft. These are why the plan was written at the altitude it was.
- `--remote-control <name>` — **always**, and always named. Phase 2 is the phase with
  nobody at the terminal, and Remote Control is what lets the user look in on it from
  claude.ai or the mobile app while it runs — read the transcript, send a message,
  type `/goal clear` — without being where it was launched. The name is the plan's
  file name without `.md`, so a user with several runs going can tell them apart in
  the session list. Never emit the flag bare: its argument is optional, and a bare
  `--remote-control` directly before the prompt takes the `/goal …` text as the
  session name and starts the session with no prompt at all. The flag is not a
  pre-flight check — a launch without it does the same work, only unwatched — so what
  makes "always" true is that the Handoff command carries it and `/pdca:execute` runs
  the Handoff command. It does need a claude.ai login rather than an API key; step 4
  probes that. And it changes nothing about the permission mode: Remote Control lets a
  human answer a prompt from a phone, but it does not put one there, so the mode
  stays `auto`.
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

If the condition cannot be made shell-safe, emit the two-step form instead: the
flags-only command — `claude --model … --effort … --permission-mode auto
--remote-control <name>` — and the `/goal …` line on its own, pasted as the first
message when launching by hand. Both go into the Handoff section in the layout
`references/plan-template.md` fixes under "The two-step Handoff": the command in the
`bash` block, the condition directly below it in a fence whose info string is `goal`,
which is how `/pdca:execute` finds the condition without guessing. Same result, no
quoting hazards.

`/goal <plan-path>` on its own is not a launch, and the plan's Handoff section says
so next to the short form it offers instead. The reasons are in
`references/goal-condition.md`; `/pdca:execute <plan-path>` is the honest version of
the same wish — it runs the Handoff command out of the file.

Also tell the user, briefly: `/goal` shows status (turns elapsed, last evaluator
reason), `/goal clear` stops the run early.

## What `/goal` actually does

Worth understanding, because the design of the condition depends on it.

`/goal <condition>` installs a session-scoped Stop hook. After every turn a separate
evaluator judges whether the condition holds; until it does, the hook blocks the
session from stopping. When it holds, the goal auto-clears and the session ends.

Three consequences shape everything in `references/goal-condition.md`:

- The condition is handed to the execution session **as its directive** — it is
  told to start working and not to pause to ask the user. So the condition must be
  self-contained.
- The evaluator sees the **condition text** plus the conversation, and nothing else.
  It is Claude Code's small fast model — Haiku by default — and it calls no tools, so
  it cannot open the plan file; and condition text survives compaction while
  attachments and early transcript may not. Put what matters in the condition.
- The condition is capped at **4000 characters**.

`/goal` also requires a trusted workspace and working hooks — it is unavailable if
`disableAllHooks` or `allowManagedHooksOnly` is set.

## Phase 2 — what the plan makes happen

Phase 2 needs no skill and no plugin: the goal condition points at the plan file, and
the plan's own Execution Protocol section tells the reader how to behave. That section
is not boilerplate you may drop — it is what makes the file self-sufficient.
(`/pdca:execute` is for the human launching the session, not for the session launched.)

You are writing for that session, so know what it will do. Each item below is
prescribed in full by the reference that owns it; this list is the map, not the
specification.

- **Run the Pre-Flight gate in turn 1**, before anything else — that a `/goal` naming
  the plan is driving it, that model, effort and permission mode are the ones the plan
  was written for, that the privileges the tasks need exist, and that the working
  directory, branch and plan path are what the plan expects. Any failure ends the run
  right there as a blocked report: not an adaptation, and not a run that starts
  anyway. `preflight.md`
- **Move the frontmatter's `status` as it goes** — `executing` when the gate
  passes, `done` before the preservation commit, `blocked` beside the blocked report,
  with `blocked_report` naming it — so the file says where it stands and a later reopen
  reads that instead of guessing. `plan-template.md`
- **Work the tasks in order**, ticking each checkbox and appending to the Run Log as it
  goes, so an interrupted run resumes from the file and the user can watch progress by
  reading it — and mirroring the checkboxes in the session's task list, the view that
  `claude attach` and Remote Control show. `plan-template.md`
- **Run the acceptance checks for real and show their output** — not a summary — and
  re-run the work criteria in full immediately before the Closeout, because the
  evaluator can only judge from what is still visible in the transcript; the closeout
  criteria are shown passing as the Closeout's own steps complete, the only place they
  can hold. `goal-condition.md`, `plan-template.md`
- **Treat a permission denial as a blocked report**, not an obstacle to route around: a
  denied command means the plan prescribed something phase 2 cannot do. `preflight.md`
- **Commit as you go on the current branch** — the one `branch` names — with the
  agreed prefix: a task, or a coherent slice of one, per commit. Never create a
  branch: a plan that wanted one already sits on it, made by phase 1 at
  handoff.
- **Preserve the final plan in a commit of its own, close out the ticket if there is
  one, then remove the file** as the final act in a separate commit — so the commit
  holding the record, and linked from the ticket, stays the last one in which the plan
  exists. `plan-template.md`, `jira.md`
- **Write the blocked report if a check genuinely cannot pass**, commit it with the
  plan — each naming the other, `blocked_report` on the plan and `plan_file` on the
  report — then stop; and on a relaunch, consume an inherited report, and the key that
  names it, before the first check. `plan-template.md`, `preflight.md`

That last one matters more than it looks. Without a reachable failure state, a plan
with one impossible check turns into a session that cannot stop, retrying forever.

## References

Each file below **owns** the rules it covers: where this body and a reference
disagree, the reference wins, and a rule that changes changes there. This body says
what each is for so you know what you are reaching for; it deliberately does not
restate them, so that there is only one place for each to be wrong.

One overlap is deliberate and is not drift. `plan-template.md` carries text meant to
be *copied into the plan file* — the Execution Protocol, the Pre-Flight checks, the
Closeout. Those copies are the artifact phase 2 reads, not a second statement
of a rule, because phase 2 runs with no plugin installed and can consult nothing but
the plan and the repository.

- `references/plan-template.md` — **owns the plan file's shape**: the frontmatter
  and its `status` lifecycle, then the template section by section, with what each
  section is for. Read before writing a plan.
- `references/preflight.md` — **owns the gate** phase 2 runs before task 1: how a
  session checks that its plan's `/goal` is driving it and its own model, effort and
  permission mode, which privileges to probe and how, and why a failure there is
  written up rather than worked around. Read before filling in a plan's Pre-Flight
  section.
- `references/jira.md` — **owns the requirements sources**: why a ticket is a request
  rather than a contract, how to fetch one and turn it into a requirements
  conversation, how a spec file or URL goes through the same conversation, how the
  plan records what the user decided, and the closeout that commits the finished plan
  and links the ticket to it at the end of phase 2. Read when a source is named.
- `references/goal-condition.md` — **owns the `/goal` condition**: the character
  budget, shell safety, the escape hatch, worked examples. Read before writing a
  handoff.
- `references/executor-lens.md` — **owns what a plan review looks for**: the eight
  lens slots the `review` skill's prompt template is filled from, carrying this
  plugin's opinions about who is reading a plan, what is exempt from review, what
  counts as a blocker, and where a blocker the planner disagrees with is answered.
  Read before the first review round.

The launch itself is owned by the sibling `execute` skill — what `/pdca:execute` runs —
and step 8 follows it when the user accepts the offer to launch. The review loop is
owned the same way, by the sibling `review` skill — what `/pdca:review` runs — which
step 7 follows, handing it the executor lens and the plan's `review_rounds`; this
skill keeps only what an AGREED exits to, and the fixpoint.
