---
description: Review any deliverable — a runbook, a spec, a README, an RFC, a directory of docs — the way a reader who cannot ask its author would, by running a fresh `claude -p` process on it cold, in plan mode, until it agrees or the round budget is spent. Use this skill when the user says "review this cold", "have a fresh model review it", "adversarial review", "would someone who has never seen this be able to follow it", "what would a reader who cannot ask me trip over", when another skill needs the loop, or when the user types /pdca:review. Not for plan files written by /pdca:plan — those are reviewed inside `/pdca:plan`, which owns the exit; send them there.
name: review
user-invocable: false
---

# PDCA: the adversarial review loop

A document is reviewed by a fresh `claude -p` process that gets the document and the
repository it lives in, and nothing else.

That isolation is the entire point. Nobody can judge whether their own document is
self-sufficient, because they remember writing it: the constraint mentioned once in
passing, the file they looked at and decided was irrelevant, what "the usual way"
means here. A reviewer holding the author's context reads straight past every gap. A
reviewer without it hits them the way the real reader will.

Running the reviewer at the model and effort the real reader will have matters for the
same reason. A document that Opus at high effort finds obvious may be full of holes
for Haiku at low effort — and the only way to know is to ask the model that has to do
the work.

This skill owns the **mechanics**: the grammar, the loop, the reviewer command, the
verdict rules, the round budget, the report. Every **opinion** — who is reading, what
the artifact is called, what is exempt, what counts as a blocker, what success means,
what a gap costs, what nits do not gate, how a blocker the session disagrees with is
answered — is a slot filled from a **lens**. That is the whole extension mechanism:
adapt by writing a lens, never by changing the loop. `/pdca:plan` is the reference
caller and fills every slot from its own lens, so no default here can reach a plan
review; a change to the loop that would alter what that lens assembles is a change to
`/pdca:plan` and is reviewed as one.

## 1. Parse the invocation

The grammar is `[model] [effort] [rounds] <path…> [reader statement]`, and it is
deliberately rigid, because a clever rule here is worse than a predictable one:

- A leading **model** token — `fable`, `opus`, `sonnet`, `haiku`, or a full model ID —
  is consumed as the model.
- An **effort** token — `low`, `medium`, `high`, `xhigh`, `max` — is consumed *only
  when it immediately follows a model token*.
- An **integer** is consumed as the round budget *only when it immediately follows an
  effort token*. A bare leading number is reader text, not a budget.
- Then every leading token that **exists on disk** is the artifact — files or
  directories, one or more. Several are joined with a space in `{{path}}`, and the
  closing line names the first.
- The first token that does not exist on disk starts the **reader statement**, and
  everything after it is that statement.

So `/pdca:review sonnet xhigh 10 docs/ for an operator at 3am` parses as model
`sonnet`, effort `xhigh`, budget `10`, artifact `docs/`, reader "an operator at 3am".
Model and effort are the **reviewer's**, never this session's.

**Echo the parse back in your first line** — `Reviewing docs/runbook.md with Sonnet at
xhigh effort, budget 10, as: an operator following it at 3am` — so a misparse costs
one correction instead of a whole loop.

No path on the command line, or none of the leading tokens exists on disk: say so and
stop. The artifact is the one parameter never interviewed for — a review of a file
nobody named is a review of nothing.

**A path whose frontmatter says `plugin: pdca` is a plan, and is not reviewed here.**
Say so and send it to `/pdca:plan <path>`: plans have exactly one route to a review,
the one that owns the fixpoint between the user, the planner and the executor. This
is about a direct invocation; a caller such as `/pdca:plan`, which owns the plan's
exit, enters at section 3 with its own lens.

A path outside the project directory is refused the same way: a plan-mode reviewer
will not read one, so the round cannot produce a verdict.

## 2. Interview for what is missing

Whatever is missing of model, effort, round budget and reader statement is asked for —
never silently defaulted. One `AskUserQuestion` call, one question per missing
parameter, at most four, recommended option first and labelled "(Recommended)":

- **Model and effort.** `opus` at `high` recommended.
- **Round budget.** `10` recommended, then `5` and `20`; any other number through
  "Other".
- **Reader.** A few presets — an implementer building from this spec; an operator
  following this runbook with nobody to ask; a newcomer reading this to get started —
  plus "Other" for a statement the presets do not fit.

A headless session cannot interview. There, every parameter comes from the command
line, and a missing one ends the run with the closing line rather than a guess.

## 3. Assemble the reviewer prompt

The prompt is a **template** with `{{slot}}` markers, filled from a **lens**:

- `${CLAUDE_SKILL_DIR}/references/prompt-template.md` — the template. Never edited per
  review.
- `${CLAUDE_SKILL_DIR}/references/default-lens.md` — the lens used when the caller
  brings none.

A caller brings its own lens instead and names its path; `/pdca:plan` brings
`${CLAUDE_PLUGIN_ROOT}/skills/plan/references/executor-lens.md`. You reached this file
by reading it — the Read tool or a `cat` — so `${CLAUDE_SKILL_DIR}` is unexpanded
here, and it is unset inside a Bash call in any case. Resolve both paths, and the two
in the assembly snippet below, relative to the `SKILL.md` you actually read — never to
the installed plugin cache, which may be an older version than the tree you were
loaded from.

A lens is a Markdown file in which each `## <slot>` heading is followed by that slot's
content, which is the text beneath it, trimmed. Exactly these eight, and no others:

| Slot | What it carries |
|---|---|
| `reader` | The opening paragraph: who is reading, what they have, that there is no one to ask. |
| `noun` | What the artifact is called in the prompt — `plan`, `runbook`, `spec`. |
| `exempt` | What is not under review. May be empty; the assembler closes the gap. |
| `checklist` | The bullets under "Include here:". |
| `success` | The clause completing "AGREED when it is empty — meaning …". |
| `cost` | What a shipped gap costs, following "Be adversarial about blockers and sparing with nits." |
| `gate` | What nits do not gate. The template reads `they do not gate {{gate}}.`, so the content carries its own article — `the handoff` for a plan, `the verdict` otherwise. |
| `answers` | How a blocker this session disagrees with is answered. Not part of the prompt; "Handling the verdict" below reads it. |

`{{path}}` comes from the invocation, not from the lens.

The default lens is itself a template — its `reader` carries `{{statement}}` and its
`noun` carries `{{noun}}`. Copy it into the scratch directory, fill both from the
reader statement, and assemble from the copy. A caller's own lens carries no markers
and is used where it lies.

Assembly is mechanical. Run it; do not transcribe the prompt by hand:

```bash
python3 -c 'import re,sys
tpl,lens=(open(p).read() for p in sys.argv[1:3])
parts=re.split(r"(?m)^## (.+?)[ \t]*$",lens)
slots={parts[i].strip():parts[i+1].strip() for i in range(1,len(parts),2)}
slots["path"]=sys.argv[3]
out=re.sub(r"\{\{(\w+)\}\}",lambda m:slots.get(m.group(1),""),tpl)
sys.stdout.write(re.sub(r"\n{3,}","\n\n",out).rstrip("\n")+"\n")' \
  "${CLAUDE_SKILL_DIR}/references/prompt-template.md" <lens> "<path>" \
  > <scratch>/review-prompt.md
```

It maps each `## <slot>` heading to the text beneath it, replaces every `{{slot}}`,
replaces `{{path}}` with its third argument, collapses runs of three or more newlines
to two — which is what an empty `exempt` leaves behind — and prints the result with
one trailing newline.

`python3` is the requirement. Where it is genuinely missing, fill the markers by hand
from the template and the lens and say that you did; a caller whose own contract is
that the assembled prompt is byte for byte a particular text cannot accept a
hand-filled one, and that is a stop, not a workaround.

## 4. The loop

1. Assemble the prompt and write it to a scratch file **outside the repository**. Two
   steps: run `mktemp -d` once, then use the path it printed literally in every later
   call. A scratch file left in the tree hands the next reader a dirty working
   directory it knows nothing about.
2. Run the reviewer.
3. Read its verdict. A round returns exactly one of two results: **VETOED**, with at
   least one blocker; or **AGREED**, with no blockers and any number of nits. Anything
   else is inconclusive — "Running the reviewer" below says what to do with it.
4. On VETOED: for each blocker, either fix the artifact or **answer** it as the
   `answers` slot says — see "Handling the verdict". Apply the nits you agree with in
   the same edit; the next round reads everything anyway. Then go back to step 2.
5. On AGREED: apply the nits you agree with, as the reviewer worded them, and the loop
   is over.

Every round is a fresh process reading the whole artifact cold — never a diff, and
never a resumed session. Reviewing only what changed would be cheaper and would test
the wrong thing. The question is not whether the edits are correct but whether a
reader who has never seen the document can act on it alone, and that is not a
diff-local property: fixing a blocker in one step routinely strands a check in
another, contradicts a fact recorded elsewhere, or quietly changes the order things
have to happen in. Worse, showing a reviewer its own previous verdict turns it from a
simulated reader into a proofreader checking whether you did as you were told — a
reader warmed by exactly the context the loop exists to strip out, who will now read
past new gaps for the same reason you do. Its AGREED only means something because it
came from a cold start, which is the one thing the real reader will always be. The
saving would be small anyway: the document is the cheap input, and the reviewer's real
cost is reading the repository to spot-check its claims — which a diff makes harder,
not cheaper, since it hides which parts of the repository the unchanged sections lean
on. Narrow the reviewer's scope by rule when you must, the way the `exempt` slot does,
never by handing it less of the document.

If a document is too expensive to read ten times, that is a fact about the document.
The real reader has to read it cold too, and only once.

### The round budget

The budget is the **caller's parameter**, one per entry into the loop, and it counts
only conclusive rounds: an inconclusive round is retried and not counted. It defaults
to `10` — `/pdca:review` takes it from the command line or the interview, and another
skill passes its own.

A cap exists at all because two things prevent convergence and neither improves with
another round: a reviewer that keeps surfacing fresh nitpicks, and a genuine
disagreement about the substance. When the budget is spent without an AGREED, stop and
put **both positions** in front of the user — that disagreement is usually the most
interesting thing the loop found, and it is theirs to settle. Their settlement is not
an exit from the loop: they change the document, which re-enters the loop as a fresh
entry with a fresh budget; or they raise the budget and it continues; or they leave it
as it is. Nothing leaves this loop cleared except an AGREED from a reviewer that read
the document as it now stands.

If a re-entry follows a material change to the document, it is a fresh entry with its
own budget. What bounds the total across re-entries is the caller's own exit, not this
one.

## Running the reviewer

Run it in the **background**, capturing the verdict to a file:

```bash
# <scratch> is outside the repository — the directory mktemp -d printed
claude -p --model <caller's model> --effort <caller's effort> --permission-mode plan \
  "$(cat <scratch>/review-prompt.md)" > <scratch>/verdict-round-N.md 2>&1
```

Background it deliberately, not as a nicety: a foreground reviewer at high or xhigh
effort routinely outlives the 10-minute tool timeout and is killed mid-thought
(observed: exit 143, whole round lost). Launch it detached, then read the verdict file
when it finishes. Use the Bash tool's `run_in_background`, so the harness notifies you
on exit; a bare `&` gives you nothing to wait on.

- `-p` — non-interactive, prints the verdict to stdout.
- `--model` / `--effort` — the reader's, not this session's. This is the whole point.
- `--permission-mode plan` — read-only. The reviewer must not touch the repository,
  and plan mode enforces that by construction rather than by asking nicely. If a
  read-only command it wants gets denied, it can still read files, which is enough to
  review a document. A plan-mode reviewer will not read outside the project directory,
  so the artifact has to live inside it.
- No `--remote-control`. That flag belongs to an execution session's launch, where a
  human wants to look in; the reviewer is a headless background process, and the flag
  is interactive-only in any case.

Afterwards, confirm the reviewer changed nothing — compare `git status --porcelain`
before and against after, rather than expecting it to be empty; the artifact itself is
legitimately modified between rounds. Cheap, and it catches a reviewer that found a
way to be helpful.

**A round without a consistent verdict is inconclusive, not a verdict.** If the output
contains neither `AGREED` nor `VETOED:`, the reviewer was killed or failed. If it says
`AGREED` above a Blockers section that lists something, or `VETOED` above one that
lists nothing, it has contradicted itself and has not given a verdict either. In both
cases retry once, and **do not count it against the budget**. At xhigh effort that
distinction is the difference between having a review loop and not having one. If the
retry also produces no verdict, fall back to reviewing the document yourself and say
which you got.

If the reviewer process fails outright — the CLI is unavailable, no model access — say
so plainly and fall back to reviewing the document yourself against the assembled
checklist. A self-review is weaker, and whoever asked should know which one they got.

## Handling the verdict

Fix blockers by making the document say more, not by making it promise less. If a
blocker points at a genuine unknown, the honest fix is usually a first step that
resolves it, with the branch documented — not deleting the mention.

You are allowed to disagree. If the reviewer misread something, leave the document's
substance alone — two models agreeing because one capitulated is worth nothing. But a
disagreement is **answered**, never merely disputed in the round report, and the
`answers` slot of the lens says where the answer goes: into the document itself for a
caller like `/pdca:plan`, or to the user for a standalone review. Every round is a
cold read of the document alone, so a reason that lives only in the round report is
invisible to the next reviewer, which raises the same blocker again and burns a round
on a disagreement nobody advanced.

The answer is then judged by the next cold round, and that is what makes answering
safe: the loop exits only on an AGREED from a reviewer that read the document with the
answer already in it, so nothing leaves the loop carrying an open disagreement. There
is no exit by overruling. The only exits are an AGREED, the budget spent without
convergence and reported as not converged, or the user stopping.

Where the lens sends the answer to the user, the loop stops for it: put the blocker to
them in the reviewer's wording with this session's reason beside it, let them decide
what the document should say — the reviewer's fix, or their own reasoning, folded into
the document's own text and never into a notes file or a companion — and run a fresh
round on the result. In a headless session there is no user to ask, so a blocker this
session would answer that way ends the loop with the closing line instead.

Check first, though, whether the misreading was invited by how the document is worded
— if the reviewer could misread it, so can the real reader, and rewording is then the
real fix.

Nits are yours to take or leave, and taking them does not reopen the review. The
reviewer classified each one as not changing what it would do, so it has already
agreed to the document with the nit applied; apply the ones you agree with as worded,
and report them as part of the delta — what is being cleared is not the byte-for-byte
version anyone last read. A change that goes beyond the nit's wording is not a nit any
more; it is a material edit and re-enters the review like any other.

## Reporting

Say the loop is starting and report each round in a line or two: how many blockers
came back and what you did about them. It costs real time and tokens, and a silent
multi-minute pause is worse than a noisy one.

Keep a one-line status file so a status line can show the round:

```bash
mkdir -p ~/.cache/claude-pdca
printf 'review 2/10' > ~/.cache/claude-pdca/"$CLAUDE_CODE_SESSION_ID".status
```

`review N/<budget>` — the round within the budget — rewritten at every round. A
standalone `/pdca:review` deletes the file when the loop ends; when a caller owns the
phase, leave it in place and let the caller's own transitions carry on from there.

End with **one closing line**, the last line of the report, so that a caller or a
headless harness can read the outcome without parsing prose:

```
Review of <artifact>: AGREED after N round(s)
Review of <artifact>: VETOED after N round(s), not converged
Review of <artifact>: stopped after N round(s), <reason>
```

`<artifact>` is the path as it was given — the first one, when several were reviewed.

## Returning to a caller

This skill never decides what an AGREED exits to. It returns to whoever entered it:
the verdict, the rounds used out of the budget, whether the artifact changed, what was
answered and where, and — when the budget was spent — both positions, for the caller
to put to the user. What that outcome means for a handoff, a merge, a publication, is
the caller's to decide.

## Headless sessions

A headless run has no user, so: every parameter comes from the command line and a
missing one ends the run with the closing line; a blocker the session would answer by
asking the user ends the loop the same way, which is a legitimate outcome and not a
failure. A harness that spawns this loop must run on a model that has `auto` available
— Haiku does not, and refuses the file edits the loop makes between rounds. The
reviewer inside the loop runs in plan mode and is unaffected.
