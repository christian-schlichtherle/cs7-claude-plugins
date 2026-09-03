# Building the `/goal` condition

The condition is the whole contract between the planning session and the
execution session. It is read by two very different audiences, and both have to be served by the
same few hundred words.

**The execution session** receives it as its directive: it is told to start
working toward the condition and not to pause to ask the user. Anything the condition
does not say, it will decide alone.

**The evaluator** is a separate check that runs after every turn and decides whether
the condition holds. It is Claude Code's small fast model — Haiku by default — and it
calls no tools: it sees the condition text and the conversation, and nothing else. The
condition text is stored verbatim and survives compaction, while file attachments and
early transcript may not. On a long autonomous run, the condition may be the only
thing the evaluator can still rely on.

This is why `/goal <plan-file>` alone cannot be the condition, however self-sufficient
the plan is. A path is not a proposition, so a Haiku judge has nothing to decide; the
evaluator cannot open the file, so the criteria inside it are invisible to it; and the
plan orders itself deleted, so at the final judgement there is no file even for a
reader that could. Reference the plan file *and* inline what the evaluator has to
check.

## Shape

Six parts, in order:

1. **Directive** — execute the plan at `<path>` to completion.
2. **Gate** — run the Pre-Flight section of that plan first, before any change, and
   stop with the blocked report if any of it fails.
3. **Completion** — the acceptance criteria, inlined with their expected results.
4. **Closeout** — the final plan was committed on its own before the plan file was
   removed in a later commit; when the plan names a ticket, also that it was pushed if
   the plan says so and that a comment linking to it at that commit was posted.
5. **Boundaries** — commit on the current branch with the ticket prefix, do not
   create a branch, delete the plan file.
6. **Escape hatch** — or the blocked report was written in this session, naming a
   check this session ran and could not pass.

## Rules

**Open with the plan path** — `Execute the plan at <path> to completion. …`. The
pre-flight goal check confirms the condition names the plan by printing only its
first 120 characters from the transcript record, stopping at the first escaped
quote, so the path has to sit near the front. Every worked example already has
this shape; keep it.

**Cap: 4000 characters.** Count before emitting. If you are over: compress the
criteria to command plus expected result, dropping prose; then, if still over, keep
the checks that would catch a wrong outcome and replace the remainder with "and every
remaining criterion in the Acceptance Criteria section of `<path>` was run in this
session, its command and output shown, and passed".

Note the tense — it is doing real work. The condition also orders the plan file
deleted, so at the moment of the final evaluation that file is gone; a clause phrased
as a claim *about the file* is then unjudgeable. Phrased as a claim about what happened in the session, it
is judgeable from the transcript, which is what the evaluator actually has. Pair it
with the instruction to re-run those criteria just before finishing, so the evidence
is recent rather than buried.

Say in the handoff which criteria were summarized, so the user knows what the
evaluator is not independently holding. And if conditions routinely overflow, treat it
as a hint that the plan may be doing too much for one unattended run — a hint, not a
rule; some work genuinely needs twelve precise checks.

**Shell-safe: no apostrophes and no backticks.** The condition is emitted inside a
single-quoted shell argument. Write "the plan file" rather than "the plan's file",
and name commands without backticks. Double quotes are fine. If a command genuinely
requires a single quote (a jsonpath, say), do not fight it — emit the two-step form
from the SKILL instead.

**Name the gate, and let it terminate the run.** Two sentences buy the whole
pre-flight: one telling the session to run the Pre-Flight section of the plan before
anything else, one saying that a pre-flight failure is written up as the blocked
report and ends the run. Both are needed, and for different readers. The execution
session needs the first, or it starts with task 1 on whatever model it happens to be —
the directive it receives is this condition, not the plan, and it reads the plan
because the condition told it to. The evaluator needs the second, or a session that
correctly aborts in turn 1 is judged not-done and pushed back into work it already
established it cannot do. Under a Stop hook there is no quiet exit, so the escape
hatch has to cover the gate as well as the finish.

One absence here is deliberate: the condition never asserts the gate's own `/goal`
check. A condition claiming its goal exists would be circular — only a session
already driven by a goal ever receives the condition — so that check lives in the
plan's Pre-Flight section alone. Do not add it here for completeness.

**The closeout earns its own clause, always.** The condition must require that the
final state of the plan was committed on its own and that the plan file was only then
removed, in a later commit; with a ticket, also that it was pushed when the plan says so
and that a comment linking to the plan file at that commit was posted to the ticket. Leave it out and
the evaluator will happily accept a run that deleted the plan without preserving it,
which is the one outcome that destroys the record of the whole run rather than merely
being incomplete. Phrase it, like every other clause, as what happened in the session:
the plan file no longer exists at evaluation time, so a claim about the file is
unjudgeable, while "was committed and a comment linking to it at that commit was posted"
is exactly what the transcript shows. Requiring the deletion to be its own later commit
is worth the words — it is what keeps the linked commit the last one holding the file,
and squashing the two is the natural thing for an execution session to do unprompted.
And when there is no ticket, or the user decided against the comment, the comment part
of the clause must be absent — the two commits stay — because a condition requiring a
comment nobody can post is unsatisfiable, and a Stop hook has no way out of that.

**Only require what is actually possible.** Before writing a completion clause,
check that it can be satisfied from the state the run will start in. The failure
seen in testing: "the plan file is deleted and the deletion is committed on this
branch" is impossible when the plan lives in a different repository than the work —
the condition can never be met and the session cannot stop. Match the clause to where
the plan file actually is.

**Reachable failure.** Always include the blocked-report clause. Without it, a plan
containing one impossible check becomes a session that cannot stop: the evaluator
keeps saying not-met, the Stop hook keeps blocking, and the run spins until it hits
a usage limit. The clause costs one sentence and turns a runaway into a written
post-mortem.

**Name the blocked report exactly once, and identically everywhere.** The canonical
form is the plan path with `.md` replaced by `.BLOCKED.md`. The evaluator looks for
the path the condition names, so if the condition and the plan's own protocol spell it
differently, the report does not register and the session cannot stop — the escape
hatch fails precisely when it is needed.

**The hatch is for a report this session wrote.** Phrase it as "was written in this
session, naming a check this session ran" — the evaluator judges from the transcript
and can see the write. A report inherited from an earlier launch then satisfies
nothing. The plan's pre-flight consumes such a report anyway, but the condition must
not depend on that step having run: a leftover report that could end a relaunch in
turn 1 is the failure seen in practice, and this clause is the cheaper guard.

**No weakening.** State that a check may not be relaxed, skipped, or declared passed
without being run. Add that a permission denial is not a licence to route around it:
under `auto` a prescribed command can be refused silently, and the correct response is
the blocked report, not an improvised substitute nobody reviewed. An execution session under a blocking Stop hook is under real
pressure to find a way to be finished; say plainly that the way out is the blocked
report, not a lowered bar.

**Do not create a branch** unless the plan says so. Worth its own clause — it is the
single most common unwanted initiative in autonomous runs.

## Worked example

Plan: `2026-08-27-cache-ttl-plan.md`, ticket `ACME-123`, executor Opus 5 at high
effort.

```
Execute the plan at 2026-08-27-cache-ttl-plan.md to completion.
Before changing anything, run the Pre-Flight section of that plan and show the output
of every check: the model must be claude-opus-5, the effort high, the permission mode
auto, and every privilege probe must pass. If any pre-flight check fails, write the
blocked report named below and stop - do not start the tasks and do not continue on a
different model or mode.
Done when all of the following hold: the Pre-Flight checks were run first in this
session and passed; every task checkbox in that file was ticked before the file was
removed; mvn -q verify was run in this session and exited 0;
kubectl -n staging get configmap api-config -o "jsonpath={.data.cacheTtlSeconds}"
was run and printed 3600; the final state of the plan file was committed on its own and
pushed in this session, and a comment was posted to ACME-123 in this session containing a
link to that plan file at that commit, and only then was the plan file deleted in a
separate later commit; git status --porcelain is empty; and the plan file
has been deleted, with all work committed on the current branch, each commit
prefixed ACME-123 and GPG-signed. Do not create a branch. Do not relax, skip, or
declare passed any check that was not actually run, and do not route around a
permission denial - a refused command is a blocked-report situation. If a pre-flight
or acceptance check cannot be made to pass, write 2026-08-27-cache-ttl-plan.BLOCKED.md
in this session, naming a check this session ran, what was tried, and why it cannot
pass, commit it with the plan, then
stop - that also satisfies this goal. A blocked report left by an earlier launch does
not.
```

Roughly 1600 characters, comfortably inside budget, single-quotes cleanly, and every clause
is something an evaluator can actually look for.

## The short form

The plan's Handoff section carries, below the full command, a one-line `/goal` the
user can type into a session they started by hand with the right flags:

```
/goal Execute the plan at 2026-08-27-cache-ttl-plan.md to completion per its Execution Protocol: Pre-Flight first, every Acceptance Criterion shown passing in a final re-run, the Closeout done before the file was removed in a separate later commit; or 2026-08-27-cache-ttl-plan.BLOCKED.md was written in this session.
```

It keeps what cannot be dropped — the plan path up front for the gate's check, the
directive, the protocol by name, the ordering of closeout and deletion, and the escape
hatch — and gives up the inlined criteria. That is a real loss, to be named next to it
in the plan: the evaluator no longer knows which commands and which expected results
the plan prescribes, so a session that quietly runs a weaker check is not caught by
the condition; only the protocol's own "no weakening" rule stands in the way. The
execution session, for its part, receives less directive and reads the plan
because the short form tells it to. Emit the short form as the fallback when the full
command is not to hand, never as the default, and trim the comment out of the
closeout clause when the plan has no ticket.

## Emitting the handoff

```bash
claude --model opus --effort high --permission-mode auto '/goal Execute the plan at …'
```

`--permission-mode auto` is not optional: a session that stops at a permission prompt
is not autonomous, and there is nobody there to answer it. But auto decides in both
directions — it also denies, silently — so a prescribed command can be refused with no
human to override. Phase 1 is what prevents that, by running every prescribed command
under this mode first; see the SKILL's handoff section.

The frontmatter's `executor` block holds the same three flags, and the Handoff
section holds the whole command — which is what lets a shell function launch a plan
from its path alone; the README shows one. When the work is in a different repository
than the plan, emit the `cd` form so the session starts where the changes belong:

```bash
cd /path/to/work-repo && claude --model opus --effort high --permission-mode auto '/goal …'
```

If the ticket key is still unknown at handoff, leave it as a visible placeholder in
the printed command — `each commit prefixed <TICKET>` — and tell the user to fill it
in before running, or to delete that clause to commit unprefixed. Do not leave the
placeholder in silently; an execution session will otherwise commit the literal
text.
