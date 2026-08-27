# Building the `/goal` condition

The condition is the whole contract between the planning session and the autonomous
one. It is read by two very different audiences, and both have to be served by the
same few hundred words.

**The executing session** receives it as its directive: it is told to start working
toward the condition and not to pause to ask the user. Anything the condition does
not say, it will decide alone.

**The evaluator** is a separate check that runs after every turn and decides whether
the condition holds. It sees the condition text and the conversation — but the
condition text is stored verbatim and survives compaction, while file attachments
and early transcript may not. On a long autonomous run, the condition may be the
only thing the evaluator can still rely on.

This is why `/goal @<plan-file>` alone is a poor condition: it gives the evaluator
about a dozen characters to judge against, and stakes the rest on an attachment
surviving. Reference the plan file *and* inline what the evaluator has to check.

## Shape

Four parts, in order:

1. **Directive** — execute the plan at `<path>` to completion.
2. **Completion** — the acceptance criteria, inlined with their expected results.
3. **Boundaries** — commit on the current branch with the ticket prefix, do not
   create a branch, delete the plan file.
4. **Escape hatch** — or the blocked report exists, explaining why a check cannot
   pass.

## Rules

**Cap: 4000 characters.** Count before emitting. If you are over: compress the
criteria to command plus expected result, dropping prose; then, if still over, keep
the checks that would catch a wrong outcome and replace the remainder with "and every
remaining criterion in the Acceptance Criteria section of `<path>` was run in this
session, its command and output shown, and passed".

Note the tense — it is doing real work. The condition also orders the plan file
deleted, so at the moment of the final evaluation that file is gone; a clause phrased
as a claim *about the file* is then unjudgeable, and for an untracked plan
unrecoverable even from git. Phrased as a claim about what happened in the session, it
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

**Only require what is actually possible.** Before writing a completion clause,
check that it can be satisfied from the state the run will start in. The failure
seen in testing: "the plan file is deleted and the deletion is committed" is
impossible when the plan was never committed, or when it lives in a different
repository than the work — so the condition can never be met and the session cannot
stop. Match the clause to where the plan file actually is.

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

**No weakening.** State that a check may not be relaxed, skipped, or declared passed
without being run. Add that a permission denial is not a licence to route around it:
under `auto` a prescribed command can be refused silently, and the correct response is
the blocked report, not an improvised substitute nobody reviewed. An autonomous session under a blocking Stop hook is under real
pressure to find a way to be finished; say plainly that the way out is the blocked
report, not a lowered bar.

**Do not create a branch** unless the plan says so. Worth its own clause — it is the
single most common unwanted initiative in autonomous runs.

## Worked example

Plan: `docs/plans/2026-08-27-cache-ttl.md`, ticket `ACME-123`, executor Opus 5
at high effort.

```
Execute the plan at docs/plans/2026-08-27-cache-ttl.md to completion.
Done when all of the following hold: every task checkbox in that file was ticked
before the file was removed; mvn -q verify was run in this session and exited 0;
kubectl -n staging get configmap api-config -o "jsonpath={.data.cacheTtlSeconds}"
was run and printed 3600; git status --porcelain is empty; and the plan file
has been deleted, with all work committed on the current branch, each commit
prefixed ACME-123 and GPG-signed. Do not create a branch. Do not relax, skip, or
declare passed any check that was not actually run, and do not route around a
permission denial - a refused command is a blocked-report situation. If a check
cannot be made to pass, write
docs/plans/2026-08-27-cache-ttl.BLOCKED.md naming the failing check, what
was tried, and why it cannot pass, then stop - that also satisfies this goal.
```

Roughly 800 characters, well inside budget, single-quotes cleanly, and every clause
is something an evaluator can actually look for.

## Emitting the handoff

```bash
claude --model opus --effort high --permission-mode auto '/goal Execute the plan at …'
```

`--permission-mode auto` is not optional: a session that stops at a permission prompt
is not autonomous, and there is nobody there to answer it. But auto decides in both
directions — it also denies, silently — so a prescribed command can be refused with no
human to override. Phase 1 is what prevents that, by running every prescribed command
under this mode first; see the SKILL's handoff section.

When the work is in a different repository than the plan, emit the `cd` form so the
session starts where the changes belong:

```bash
cd /path/to/work-repo && claude --model opus --effort high --permission-mode auto '/goal …'
```

If the ticket key is still unknown at handoff, leave it as a visible placeholder in
the printed command — `each commit prefixed <TICKET>` — and tell the user to fill it
in before running, or to delete that clause to commit unprefixed. Do not leave the
placeholder in silently; an autonomous session will otherwise commit the literal
text.
