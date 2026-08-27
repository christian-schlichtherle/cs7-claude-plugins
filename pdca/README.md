# pdca Plugin

Two-phase development for Claude Code: plan interactively, implement autonomously.

## The idea

This is the Deming PDCA cycle with a session boundary in the middle.

| Phase | Session | What happens |
|-------|---------|--------------|
| **Plan** | interactive, with you | Explore, verify every assumption by running commands, and iterate on a plan file until you are satisfied |
| **Do / Check / Act** | fresh, unattended | A new `claude` process checks it is the session the plan was written for, implements the plan under `/goal`, and cannot stop until an evaluator agrees the work is done |

The plan file is the entire interface between them. Phase 2 has no memory of your
conversation — so the plan has to be good enough that nobody needs to babysit it.

## Usage

```
/pdca:plan opus high raise the staging cache TTL from five minutes to an hour
```

The leading `opus high` sets the model and effort level for the *second* phase.
Both are optional — if omitted you will be asked, before planning starts, because
how much the plan must spell out depends on who will be reading it.

Planning then proceeds interactively. Each turn updates
`docs/plans/<date>-<slug>.md` and reports only what changed; you read the file when
you want the whole picture. When you are satisfied, the plan is handed to a fresh
`claude -p` process running at phase 2's model and effort — which sees the plan and
the repository and nothing else — and asked whether it could execute it unattended.
Blockers get fixed and it is asked again, up to three rounds. Then the session writes
the launch command into the plan, prints it, and — if you agreed — commits the plan:

```bash
claude --model opus --effort high --permission-mode auto '/goal Execute the plan at …'
```

Run that in the work repository's directory — usually the same one you planned in —
and the autonomous phase begins with a pre-flight check. Before it changes anything,
it confirms it is running on the model, effort level and permission mode the plan was
written for, that every privilege the plan needs is actually available — a passwordless
sudo, a warm signing key, a cluster role — and that it is in the right repository on
the right branch. If any of that is wrong it writes a `.BLOCKED.md` naming the
mismatch and stops immediately, rather than producing plausible-looking work on the
wrong model and going wrong somewhere nobody is watching.

Past the gate, it ticks off tasks in the plan file as it goes, so you can watch
progress by reading the file — and an interrupted run resumes from where it stopped. When every acceptance check passes,
it commits the work on the current branch and deletes the plan file in the same
commit.

If a check turns out to be impossible, it writes a `.BLOCKED.md` post-mortem and
stops, rather than retrying forever.

## Coming back to a plan later

The gap between the two phases can be weeks, so the handoff command is never only
terminal output. It is written into the plan's own `## Handoff` section before being
printed, and — if you agreed to commit it — the plan is committed, so the command
survives in the file, in the diff, and in `git log`.

If the plan has been sitting a while, reopen it rather than pasting the old command:

```
/pdca:plan docs/plans/2026-08-27-cache-ttl.md
```

Because every fact in the plan's Verified Context is recorded with the command that
established it, re-verification is cheap: the session re-runs them, tells you what
has drifted since, brings the plan back to true, and reprints a fresh handoff.

And if a stale plan gets executed anyway, the executing session is told to check the
Verified Context against reality before it starts, and to stop with a blocked report
if the ground has moved.

## Requirements

`/goal` needs a trusted workspace and working hooks — it is unavailable when
`disableAllHooks` or `allowManagedHooksOnly` is set.
