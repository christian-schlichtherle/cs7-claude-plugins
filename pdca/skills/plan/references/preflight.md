# The pre-flight gate

Phase 2 opens by proving it is the session the plan was written for, and that it can
actually do what the plan asks. Nothing else happens until those checks pass.

The gate exists because of when the alternative fails. A plan written for Opus at high
effort, launched by accident on Haiku at low effort, does not announce itself — it
produces work that looks plausible for six tasks and then goes wrong somewhere nobody
is watching. A command that needs a privilege the session does not have is not refused
at launch; it is refused at task 5, silently, under `auto`, with no human to override
and a Stop hook that will not let the session give up. Both cost an entire unattended
run. Both are one command to detect in the first turn.

So: fail in turn 1, not in turn 40.

## Failing loud has exactly one spelling here

An autonomous session under a Stop hook cannot fail the way a script does. It cannot
exit, and it must not quietly carry on — the hook blocks stopping until the goal
condition holds, so a session that gives up without saying so just spins.

A failed pre-flight check therefore means: **write the blocked report at the path the
goal condition names, say precisely what was wrong, and stop.** That is the loud
failure. It is the same escape hatch used for an impossible acceptance criterion, and
it is reached in the first turn rather than after hours of work.

The report has to be actionable, because the person reading it was not there:

```markdown
# BLOCKED: pre-flight

Check 1 (executing model) failed.
Expected: claude-opus-5. Actual: claude-haiku-4-5-20251001.
This plan was written for a high-effort reader and states intent rather than exact
edits. Relaunch with the command in the Handoff section of the plan, which sets
--model opus --effort high. No work was done; the working tree is untouched.
```

Three things the executing session must not do instead:

- **Adapt.** Not "the model is smaller than planned, so I will be extra careful". The
  plan's altitude was chosen for a specific reader; a different reader needs a
  different plan, and rewriting it unattended is not the fallback.
- **Route around a denial.** Under `auto` a refusal is a fact about the environment,
  not an obstacle to be clevered past with a different binary.
- **Start the tasks and hope.** Half a plan executed is worse than none: the working
  tree is now dirty in ways the next run cannot distinguish from its own work.

## What the gate checks

Four groups, in this order — cheapest and most fatal first.

### 1. Identity — under /goal, model, effort, permission mode

First, that a `/goal` naming this plan is driving this session. The whole design
assumes the Stop hook and its evaluator: without them the session can stop half-done
and nothing notices, the acceptance criteria are never judged independently, and the
blocked-report hatch has no audience. A launch that lost the `/goal` prefix — a
partial paste of the handoff command is enough — must fail here rather than run as
an ordinary prompt.

Two kinds of transcript record share the type `goal_status`. A sentinel record
(`"sentinel":true`) marks the goal's boundaries:
`{"type":"goal_status","met":false,"sentinel":true,"condition":"…"}` when it is
set — for a `/goal`-launched session, alongside its first prompt — and `met:true`
when it is explicitly cleared with `/goal clear`. The evaluator writes the other
kind, one per judged stop attempt, carrying a `reason` and no `sentinel`:
`met:false` while the goal holds the session, `met:true` when it is met and
auto-clears. Their number is unbounded — a single goal was observed to leave 370
records, one sentinel and 369 evaluator — and they survive resumption, so neither
presence nor count proves anything about now. The check therefore reads the
**last** record — the most recent goal, and whether it was met or cleared:

```bash
T=$(ls -t "$HOME"/.claude/projects/*/"$CLAUDE_CODE_SESSION_ID".jsonl | head -1)
echo "T=$T"                                      # empty: transcript not found
G=$(grep '"type":"goal_status"' "$T" | tail -1)
echo "$G" | grep -o '"met":[a-z]*'               # "met":false — the last goal is still open
echo "$G" | grep -o '"condition":"[^"]\{0,120\}' # and it names this plan file
```

Both grep lines must answer: `"met":false`, and a condition naming this plan. (The
extraction prints only the condition's first 120 characters and stops at the first
escaped quote, so the handoff must put the plan path near the front of the
condition — the `Execute the plan at <path> …` opening that `goal-condition.md`
prescribes already does.) A last record with `"met":true`, a condition for a
different goal, or no record at all in a readable transcript all mean the same
thing — no evaluator is guarding this plan — and each is a failed pre-flight. An
empty `T=` line is different: the transcript
cannot be found, so the fact is unverifiable — a directive that merely reads like a
goal condition proves nothing about the hook — and an unavailable identity fact is a
warning to record and continue from under the degradation rule below, not a failed
check, and not a pass.

Say precisely what a passing check proves: *the last goal ever set in this
transcript names this plan and was never recorded as met or cleared.* For the fresh
session the handoff launches — the only launch the Handoff section prescribes, in
its one-step or two-step form — that is the same thing as being guarded now.
`/goal clear` is no exception: clearing writes a sentinel record with `met:true` —
observed in four transcripts spanning Claude Code 2.1.221–2.1.238 — so a cleared
goal fails this check correctly. The one genuinely presumptive case is a resumed
session: records survive resumption, and an abandoned run — goal set, never met,
never cleared — leaves a trailing `met:false` forever. The hook itself does appear
to survive: two resumed sessions (2.1.222→2.1.223 and 2.1.246→2.1.247, each resumed
with a continue prompt) carry further evaluator records for the same single goal
after the resume, ending `met:true` — so a resumed session whose last goal is still
open is in practice still guarded by it. Two observations are not a guarantee, so
the gate still does not try to detect resumption; it rides on the fresh-launch
assumption, and this is where that assumption is written down.

Verified on 2026-08-28 against transcripts spanning Claude Code 2.1.221–2.1.247: at
2.1.247, the finished end-to-end run of 2026-08-27 closes with `met:true`, so its
last record correctly reports no open goal, and the abandoned run's last record is
`met:false` with its own plan's condition; plain-prompt headless and interactive
non-goal transcripts carry no record; a single-goal session at 2.1.241 with many
unmet stop attempts carries 370 records; and a resumed session (2.1.233→2.1.234)
carries two full goal cycles including a no-goal stretch — the last two being why
the last record is read and the records are never counted.

Then the remaining three. The session can observe them all: `CLAUDE_EFFORT` carries
the effort level, and the session transcript records the model and the current
permission mode:

```bash
# T as computed for the /goal check above
grep '"type":"assistant"' "$T" | tail -1 | grep -o '"model":"[^"]*"' | head -1
grep -o '"permissionMode":"[^"]*"' "$T" | tail -1
echo "effort=$CLAUDE_EFFORT"
```

Verified against Claude Code 2.1.247, from a fresh session's first turn:

```
"model":"claude-sonnet-5"
"permissionMode":"auto"
effort=low
```

That gate was then exercised end to end in real `/goal` sessions on 2026-08-27, against
Claude Code 2.1.247, in four cases: a wrong-model launch (A) and a wrong-branch launch
(D) each aborted in the first turn with a blocked report naming the specific mismatch
and no work done; a launch whose privilege probe was denied (C) aborted the same way and
did not route around the denial, though passwordless sudo was within reach; and a
matching launch (B) passed the gate and completed the work, checking its identity before
writing anything. In all four the evaluator accepted the outcome at `iterations=1`, so a
correct abort ends the run rather than spinning under the Stop hook.

**One correction from that run.** The `permissionMode` line above prints nothing when
the session was started with a **slash command** as its prompt — which is precisely what
a phase 2 handoff launches: `claude -p … "/goal …"`. The mode check was therefore dead
in the one kind of session the gate exists to guard.

It is the slash-command prompt that does it, not headless-ness. A headless session with
a plain prompt does carry `"permissionMode":"…"` on its prompt record, next to
`"promptSource":"sdk"`; an interactive session writes standalone `permission-mode`
records; a `/goal`-prompt session writes neither.

When the transcript is silent, try the launch flags — walking up from `$PPID` until the
argv starts with `claude`, since the immediate parent is usually a shell:

```bash
ps -o args= -p "$PPID" | grep -o -- '--permission-mode [a-zA-Z]*\|--dangerously-skip-permissions'
```

This is not a general answer either, and it fails quietly. It reports only what was
passed on the command line: a session started without an explicit mode flag, or one
switched at runtime, shows nothing or shows a stale value. Prefer the transcript wherever
it answers, since it tracks runtime changes.

**If neither source answers, the mode is unverifiable.** Say so in the run log and treat
it under the degradation rule below — a self-reported or unavailable identity fact is a
warning to record, not a check to wave through. Do not infer the mode from what the
session appears to be allowed to do.

Compare each against the values the plan's Pre-Flight section names. A mismatch on any
of the three is fatal — including a *higher* model than planned, which is cheap to
relaunch correctly and not worth guessing about.

If the transcript cannot be located — the path is an internal detail and a future
release may move it — fall back to what the session knows about itself: its own
context states the model it is running as, and `CLAUDE_EFFORT` is independent of the
transcript. Say in the run log which check you got. The gate fails on identity for
unavailability only when no identity fact at all can be established; a check that
is merely self-reported — or unavailable, like the goal check when the transcript
is missing, or the mode when neither the transcript nor the launch flags answer —
is a warning to record and continue from.

### 2. Privilege — only when the mode is not a bypass

Under `--dangerously-skip-permissions` (or `--permission-mode bypassPermissions`)
there is no permission layer to trip over, and this group is skipped. Say so
explicitly rather than silently omitting it.

Under any other mode — `auto` in particular — every elevated thing the plan requires
is proved **now**. Two separate gates can refuse a command, and both are silent:

- **The right itself** — passwordless sudo, a cluster role, a valid cloud token, a
  usable signing key.
- **The classifier** — `auto` judges the command as written. It refuses things a
  human would wave through, and it refuses them without a prompt.

That second gate is why a probe must have the same *shape* as the real command.
Proving `kubectl get pods` runs says nothing about `kubectl delete`; proving a write
inside the repository works says nothing about a write to `/etc`. Where the real
command has a rehearsal form, that is the probe:

| The plan needs | Probe |
|---|---|
| `sudo` anything | `sudo -n true` — a sudo that would prompt hangs an unattended run |
| A cluster mutation | `kubectl auth can-i <verb> <resource> -n <ns>`, or the real command with `--dry-run=server` |
| A signed commit | `echo test \| gpg --clearsign --batch --pinentry-mode error` (SSH signing: the equivalent key check) |
| A push | `git push --dry-run` |
| GitHub API access | `gh auth status` |
| Cloud API access | `aws sts get-caller-identity`, or the provider equivalent |
| Dependency installation | the actual fetch against the real registry |
| A write outside the repository | `touch` the target path and remove it |
| A Jira attachment or comment at closeout | `GET /rest/api/3/mypermissions?issueKey=<key>&permissions=CREATE_ATTACHMENTS,ADD_COMMENTS` returns `havePermission` for both — it writes nothing, so the ticket collects no test attachments |

A probe that needed manual approval, or came back denied, is a failed pre-flight — not
a note to keep in mind.

Two of those rows are worth a word on why they are fatal rather than cosmetic. A cold
signing key does not fail, it *hangs*. And a closeout that cannot run means the plan
file — the record of the entire run, including everything the run is about to append to
it — has nowhere to go before it is deleted. Both are cheaper to catch here than
anywhere else in the workflow.

MCP tool calls are probed the same way as shell commands, and for the same reason: a
server that needs interactive authentication, or a token that expired between the two
phases, refuses at the moment of use. `auto` can also decline an MCP write outright. If
the plan prescribes a tool call, phase 1 makes one — a read against the same server is
usually enough — under phase 2's permission mode.

### 3. Ground — that this is the right place

Cheap, and it catches the launch that went off in the wrong directory or on the wrong
branch:

- The plan file exists at exactly the path the goal condition names.
- The working directory is the repository the plan says it changes (`git remote -v`,
  or a file that only exists there).
- The branch is the one the plan expects, and the working tree is clean — or the plan
  says explicitly why it will not be.
- Every binary the tasks invoke is on `PATH`, and every environment variable and
  credential file they read is present.

### 4. Plan-specific preconditions

Whatever else the plan names: a service reachable, a fixture present, a migration
already applied, a feature flag in a particular state. These are the ones only the
plan author knows about, which is why the template gives them a section rather than
leaving them scattered through the tasks.

The Verified Context spot-check belongs here too. Its facts each carry the command
that established them, so re-running the two or three the plan actually turns on is a
minute's work — and finding the ground has moved *before* the first edit is the whole
point of doing it here rather than at task 4.

## What phase 1 owes the gate

Writing the Pre-Flight section is phase 1's job, and it is not boilerplate:

- **Name the expected model, effort and permission mode literally**, in the spelling
  the checks produce — `claude-opus-5`, `high`, `auto` — so the comparison is a string
  match and not a judgement call.
- **Keep the goal check.** Check 1's first half — the last `goal_status` record
  naming this plan, `met:false` — is the gate's only proof that an evaluator is
  guarding the run. It is in the template; a plan that drops it has lost the check
  that makes every other check enforceable.
- **Enumerate the privileges from the tasks, not from imagination.** Read back through
  the plan; every command that writes outside the tree, touches a cluster, signs,
  pushes, or reaches the network earns a probe.
- **Run every probe yourself, under phase 2's permission mode.** This is the same rule
  that governs prescribed commands generally, and it applies with more force here: a
  probe that is itself denied turns the gate into a false alarm that ends the run
  before it starts.
- **Keep it bounded.** The gate is a first-turn formality when everything is fine —
  each check one command with one expected result, the whole section a handful of
  lines. It is not a second verification phase, and a pre-flight that takes twenty
  turns has become the thing it was meant to prevent.
