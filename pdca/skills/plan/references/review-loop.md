# The adversarial review loop

Before handing off, the plan is reviewed by the model and effort level that will
actually execute it — running as a separate `claude -p` process, so it gets the plan
and the repository and nothing else.

That isolation is the entire point. You cannot judge whether your own plan is
self-sufficient, because you remember the conversation that produced it: the
constraint the user mentioned in passing, the file you looked at and decided was
irrelevant, what "the usual way" means here. A reviewer with your context will read
straight past every gap. A reviewer without it hits them the way phase 2 will.

Running the reviewer at phase 2's model and effort matters for the same reason the
plan is written at that altitude. A plan that Opus at high effort finds obvious may
be full of holes for Haiku at low effort — and the only way to know is to ask the
model that has to do the work.

## The loop

1. Write the reviewer prompt to a scratch file **outside the repository** (`mktemp -d`
   or `/tmp`). A scratch file left in the tree hands phase 2 a dirty working
   directory it knows nothing about.
2. Run the reviewer.
3. Read its verdict. A round returns exactly one of two results: **VETOED**, with at
   least one blocker; or **AGREED**, with no blockers and any number of nits. Anything
   else — no verdict line, AGREED above a Blockers section that lists something,
   VETOED above one that lists nothing — is inconclusive, and "Running the reviewer"
   below says what to do with it.
4. On VETOED: for each blocker, either fix the plan or dispute it **in the plan** —
   see "Handling the verdict". Apply the nits you agree with in the same edit; the
   next round reads everything anyway. Then go back to step 2 with the revised plan.
5. On AGREED: apply the nits you agree with, as the reviewer worded them, and the
   loop is over. Stop after **three rounds** either way.

Every round is a fresh process reading the whole plan cold — never a diff, and never
a resumed session. Reviewing only what changed would be cheaper and would test the
wrong thing. The question is not whether the edits are correct but whether a reader
who has never seen the plan can execute it unattended, and that is not a
diff-local property: fixing a blocker in one step routinely strands an acceptance
criterion in another, contradicts a Verified Context fact, or quietly changes the
order things have to happen in. Worse, showing a reviewer its own previous verdict
turns it from a simulated executor into a proofreader checking whether you did as
you were told — a reader warmed by exactly the context the loop exists to strip out,
who will now read past new gaps for the same reason you do. Its AGREED only means
something because it came from a cold start, which is the one thing phase 2 will
always be. The saving would be small anyway: the plan file is the cheap input, and
the reviewer's real cost is reading the repository to spot-check the plan's claims —
which a diff makes harder, not cheaper, since it hides which parts of the repository
the unchanged sections lean on. Narrow the reviewer's scope by rule when you must,
the way the prompt exempts the Handoff section, never by handing it less of the plan.

If a plan is too expensive to read three times, that is a fact about the plan. Phase
2 has to read it cold too, and only once.

Three rounds is a real limit, not a formality. Two things can prevent convergence: a
reviewer that keeps surfacing fresh nitpicks, and a genuine disagreement about the
approach. Neither improves with a fourth round. If the loop does not converge, stop
and put both positions in front of the user — that disagreement is usually the most
interesting thing to have found, and it is theirs to settle.

AGREED ends this loop, not the planning conversation. If reaching it took fixing
blockers, or if nits were applied on the way out, the plan has changed since the user
said proceed on it, and the changes go back to the user as an ordinary delta report
before anything else happens — and their
afterthoughts may send the plan through this loop again. The exit rule for the
whole nest is in the skill, step 7: the handoff needs one version of the plan that
the user, the planner and the executor all stand behind at once — or, when
this loop would not converge, the user's explicit settlement over the reviewer's
objection, recorded in the plan. The three-round budget is per entry into the loop;
what bounds the total across re-entries is the outer loop's own exit, the user.

Tell the user the loop is starting and report each round in a line or two: how many
blockers came back and what you did about them. It costs real time and tokens, and a
silent multi-minute pause is worse than a noisy one.

## Running the reviewer

Run it in the **background**, capturing the verdict to a file:

```bash
# <scratch> is outside the repository — mktemp -d or /tmp
claude -p --model <phase-2 model> --effort <phase-2 effort> --permission-mode plan \
  "$(cat <scratch>/review-prompt.md)" > <scratch>/verdict-round-N.md 2>&1
```

Background it deliberately, not as a nicety: a foreground reviewer at high or xhigh
effort routinely outlives the 10-minute tool timeout and is killed mid-thought
(observed: exit 143, whole round lost). Launch it detached, then read the verdict file
when it finishes.

- `-p` — non-interactive, prints the verdict to stdout.
- `--model` / `--effort` — phase 2's, not this session's. This is the whole point.
- `--permission-mode plan` — read-only. The reviewer must not touch the repository,
  and plan mode enforces that by construction rather than by asking nicely. If a
  read-only command it wants gets denied, it can still read files, which is enough
  to review a plan.

Afterwards, confirm the reviewer changed nothing — compare `git status --porcelain`
before and against after, rather than expecting it to be empty; the plan file itself
is legitimately new or modified. Cheap, and it catches a reviewer that found a way to
be helpful.

**A round without a consistent verdict is inconclusive, not a verdict.** If the output
contains neither `AGREED` nor `VETOED:`, the reviewer was killed or failed. If it says
`AGREED` above a Blockers section that lists something, or `VETOED` above one that
lists nothing, it has contradicted itself and has not given a verdict either. In both
cases retry once, and **do not count it against the three rounds**. At xhigh effort that
distinction is the difference between having a review loop and not having one. If the
retry also produces no verdict, fall back to reviewing the plan yourself and say which
you got.

If the reviewer process fails outright — the CLI is unavailable, no model access —
say so plainly and fall back to reviewing the plan yourself against the checklist
below. A self-review is weaker, and the user should know which one they got.

## Reviewer prompt template

````markdown
You are about to execute a plan, alone, in a session that has just started. You
have the plan file and the repository. There is no one to ask: no author to
clarify with, no user to answer a question. Whatever the plan does not say, you
will have to guess, and a wrong guess runs unsupervised.

Read the plan at <path>, then read enough of the repository to judge it.

The Handoff section, and the frontmatter's `status`, `branch`, `closeout_push` and
`permalink` fields, are written or refreshed after this review, so
do not flag them as missing, empty, or out of date with the rest of the plan — they
are the one part of the file you are not reviewing.

Report, in this order:

## Blockers
Things that would make you guess, stall, or do the wrong thing. For each: quote
the part of the plan at fault, say what you would have done wrong, and say what
the plan would need to say instead.

Include here:
- Facts asserted without evidence, or asserted and contradicted by the repository.
  The Verified Context section records a command behind each fact — spot-check
  them.
- Steps that assume knowledge not in the file.
- Acceptance criteria that are not runnable commands with unambiguous expected
  results, that would pass without the work being done, or that cannot run in
  this environment.
- A Pre-Flight section that would not stop you: a model, effort or permission mode
  that is not named literally enough to compare against, no check that the plan's
  own /goal is driving the session, a privilege the tasks need that nothing probes,
  or a check whose failure you could talk yourself past.
- A source whose requirements are not accounted for: a Requirements table that omits
  something the ticket or the spec asks for, or a disposition you would feel entitled
  to overrule by reading the source yourself.
- A Closeout section you could not execute: an unprobed comment channel, a
  permalink template that is guessed rather than verified against this repository's
  host, an order that removes the plan file before its final state is committed, or a
  deletion folded into the preservation commit so the linked commit no longer holds the
  file.
- A requirement adopted without a decision behind it — a non-functional demand from
  the ticket or the spec that the plan implements because it was written down, where
  the Verified Context suggests something else and the table records no reasoning.
- Ambiguity you could resolve two ways, where the two ways differ materially.
- Ordering that matters but is not stated.
- Anything the plan asks for that you could not actually carry out.

## Nits
Improvements that would not change what you do. Keep these separate — they do not
gate the handoff. Word each as the edit you would make, because the author may apply
it exactly as written without another round.

## Verdict
Exactly one line, and it follows from the Blockers section: `VETOED: <n> blockers`
when that section lists anything, `AGREED` when it is empty — meaning you could
execute this plan unattended and be confident the result is what the author wanted.
Nits never change the verdict.

Be adversarial about blockers and sparing with nits. A plan that ships with a real
gap costs an entire unattended run; a nit costs nothing. But do not manufacture
blockers to seem rigorous — AGREED is the correct verdict for a good plan, and
inventing objections to avoid giving it wastes a round.
````

Substitute the real plan path. Everything else stays as written — in particular the
opening, which is what puts the reviewer in phase 2's position rather than a
proofreader's.

## Handling the verdict

Fix blockers by making the plan say more, not by making it promise less. If a
blocker points at a genuine unknown, the honest fix is usually a first task that
resolves it, with the branch documented — not deleting the mention.

You are allowed to disagree. If the reviewer misread something, leave the plan's
substance alone — two models agreeing because one capitulated is worth nothing. But
put the dispute **in the plan**, not only in your round report: a sentence in
Constraints & Non-Goals, or beside the fact in question, saying what was raised and
why it does not hold. Every round is a cold read of the plan alone, so a reason that
lives only in the round report is invisible to the next reviewer, which raises the
same blocker again and burns a round on a disagreement nobody advanced. A reviewer
that reads the recorded reasoning and still vetoes on that point has a real
disagreement with you, and that is what the three-round exit hands to the user. Check
first, though, whether the misreading was invited by how the plan is worded — if the
reviewer could misread it, so can phase 2, and rewording is then the real fix.

Nits are yours to take or leave, and taking them does not reopen the review. The
reviewer classified each one as not changing what it would do, so it has already
agreed to the plan with the nit applied; apply the ones you agree with as worded, and
report them to the user as part of the delta — the plan being handed off is not the
byte-for-byte version they said proceed on. A change that goes beyond the nit's
wording is not a nit any more; it is a material edit and re-enters the review like any
other.
