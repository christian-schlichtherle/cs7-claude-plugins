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
3. Read its verdict. For each **blocker**, either fix the plan or write down why it
   is not actually a blocker.
4. If there were blockers, go back to step 2 with the revised plan.
5. Stop when the reviewer returns READY, or after **three rounds**.

Three rounds is a real limit, not a formality. Two things can prevent convergence: a
reviewer that keeps surfacing fresh nitpicks, and a genuine disagreement about the
approach. Neither improves with a fourth round. If the loop does not converge, stop
and put both positions in front of the user — that disagreement is usually the most
interesting thing to have found, and it is theirs to settle.

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

**A round with no verdict line is inconclusive, not a verdict.** If the output
contains neither `READY` nor `BLOCKED:`, the reviewer was killed or failed — retry it
once, and **do not count it against the three rounds**. At xhigh effort that
distinction is the difference between having a review loop and not having one. If the
retry also produces no verdict, fall back to reviewing the plan yourself and say which
you got.

If the reviewer process fails outright — the CLI is unavailable, no model access —
say so plainly and fall back to reviewing the plan yourself against the checklist
below. A self-review is weaker, and the user should know which one they got.

## Reviewer prompt template

````markdown
You are about to implement a plan, alone, in a session that has just started. You
have the plan file and the repository. There is no one to ask: no author to
clarify with, no user to answer a question. Whatever the plan does not say, you
will have to guess, and a wrong guess runs unsupervised.

Read the plan at <path>, then read enough of the repository to judge it.

The Handoff section is written after this review, so do not flag it as missing or
empty — that is the one absence that is expected.

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
  that is not named literally enough to compare against, a privilege the tasks
  need that nothing probes, or a check whose failure you could talk yourself past.
- A ticket whose requirements are not accounted for: a Ticket Requirements table
  that omits something the ticket asks for, or a disposition you would feel entitled
  to overrule by reading the ticket yourself.
- A Ticket Closeout section you could not execute: an unprobed channel, an attach
  command with no verification that it landed, or an order that removes the plan file
  before the attachment is confirmed.
- Ambiguity you could resolve two ways, where the two ways differ materially.
- Ordering that matters but is not stated.
- Anything the plan asks for that you could not actually carry out.

## Nits
Improvements that would not change what you do. Keep these separate — they do not
gate the handoff.

## Verdict
Exactly one line: `READY` if you could execute this plan unattended and be
confident the result is what the author wanted, or `BLOCKED: <n> blockers`.

Be adversarial about blockers and sparing with nits. A plan that ships with a real
gap costs an entire unattended run; a nit costs nothing. But do not manufacture
blockers to seem rigorous — READY is the correct verdict for a good plan, and
inventing objections to avoid giving it wastes a round.
````

Substitute the real plan path. Everything else stays as written — in particular the
opening, which is what puts the reviewer in phase 2's position rather than a
proofreader's.

## Handling the verdict

Fix blockers by making the plan say more, not by making it promise less. If a
blocker points at a genuine unknown, the honest fix is usually a first task that
resolves it, with the branch documented — not deleting the mention.

You are allowed to disagree. If the reviewer misread something, say so in your
round report and leave the plan alone. Two models agreeing because one capitulated
is worth nothing. But check first whether the misreading was invited by how the plan
is worded — if the reviewer could misread it, so can phase 2, and rewording is then
the real fix.
