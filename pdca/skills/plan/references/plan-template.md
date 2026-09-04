# The plan file template

Every section below exists because leaving it out is a way autonomous runs fail.
Keep the section order and headings — the goal condition and the Execution Protocol
refer to them by name.

Sections may be dropped only when genuinely inapplicable (a docs-only change has no
meaningful Rollback). When you drop one, say so in a single line rather than
silently omitting it, so a reader can tell the difference between "not needed" and
"forgotten".

## Skeleton

The file opens with a YAML frontmatter block — described under "The frontmatter"
below — and then the sections, in order. The goal condition and the Execution Protocol
refer to several of them by name, so the headings are fixed:

**Goal** · **Requirements** · **Verified Context** · **Constraints &
Non-Goals** · **Pre-Flight** · **Tasks** · **Acceptance Criteria** · **Rollback** ·
**Closeout** · **Execution Protocol** · **Handoff** · **Run Log**

`Requirements` is dropped when the plan has no requirements source at all — no ticket
and no spec. `Closeout` is always present: the plan is always tracked in git, so its
final state is always preserved in a commit of its own before the file is removed; only
the ticket steps inside it are dropped when there is no ticket. `Writing guidance`, at
the end of this file, is about writing the plan and is not a section of it.

````markdown
---
plugin: pdca
plugin_version: 0.8.0
plugin_url: https://github.com/christian-schlichtherle/cs7-claude-plugins
created: 2026-08-27
status: handed-off
executor:
  model: claude-opus-5
  effort: high
  permission_mode: auto
sources:
  - ACME-123
  - docs/specs/cache-ttl.md
ticket:
  key: ACME-123
  url: https://acme.atlassian.net/browse/ACME-123
  cloud_id: a1b2c3d4-…
plan_file: 2026-08-27-cache-ttl-plan.md
branch: main
closeout_push: true
permalink: https://github.com/acme/api/blob/<sha>/2026-08-27-cache-ttl-plan.md
---

# <Goal in one line>

## Goal

<One paragraph: what is true after this work that is not true now, and why it is
being done. Enough for a reader to sanity-check a decision the tasks did not
anticipate.>

## Requirements

<Every requirement from every source named in the frontmatter — the ticket, a spec
file, a URL, pasted text — and what the user decided about it. Omit this section only
when there is no source at all, and then say so in one line. See `references/jira.md`;
a spec goes through the same conversation as a ticket.>

**Where this plan and a source disagree, this plan wins.** A ticket or a spec is a
request, not a contract, and this table is what the user decided about it. Do not
implement a requirement that this table marks out of scope, deferred, reversed or
replaced — each of those is a decision made in the planning session, not an oversight.

| # | Source | Requirement (source wording, condensed) | Disposition | Note |
|---|---|---|---|---|
| 1 | ACME-123 | Staging cache TTL raised to 1 hour | In scope — task 1 | |
| 2 | ACME-123 | Same change in production | Out of scope | User: staging only this week |
| 3 | ACME-123 | Add a cache-hit-rate metric | Deferred | Split to ACME-131 |
| 4 | ACME-123 | Document the value in the runbook | In scope — task 3 | |
| 5 | ACME-123 | AC: "cache hits improve measurably" | Reworded | Not testable as written; replaced by acceptance criterion 2 |
| 6 | ACME-123 | "Move the TTL into Redis config" | Replaced | Non-functional; the ConfigMap path is already watched — user chose it over a new dependency |
| 7 | ACME-123 | Restart the pods after the change | Already satisfied | The ConfigMap is watched, not mounted: verified below |
| 8 | docs/specs/cache-ttl.md | The TTL is read from the ConfigMap key cacheTtlSeconds | In scope — task 2 | Spec and ticket agree; the spec names the key |

## Verified Context

<Facts this plan rests on, each with the command that established it. Not a
codebase tour — only what the tasks depend on.>

- The cache TTL is set in `charts/api/values.yaml:88`, currently `300`:
  `grep -n 'ttlSeconds' charts/api/values.yaml`
- The value reaches the pod through a ConfigMap, not a build-time constant:
  `kubectl -n staging get configmap api-config -o yaml | head -30`
- `mvn -q verify` passes on the current HEAD (2m14s).

## Constraints & Non-Goals

<Boundaries the executor cannot infer. What must not change; what is deliberately
out of scope; standards that apply.>

- Do not touch the production values file — this change is staging only.
- No new dependencies.
- Out of scope: the cache invalidation path, tracked separately.

## Pre-Flight

<Run in the first turn, before task 1. Each check is one command with one expected
result, and any failure stops the run: write the blocked report named in step 10 of
the Execution Protocol and do not start the tasks. Model, effort and permission mode
are spelled out literally here, in the same spelling as the frontmatter's `executor`
block, so the comparison is a string match, not a judgement.

Before check 1: if `2026-08-27-cache-ttl-plan.BLOCKED.md` exists, this is a relaunch.
Fold that report into the Run Log below — its date, the check it named, what was
tried, its `Next:` line — then delete it, in this same turn, and only then run the
checks. An inherited report never satisfies this plan's goal and is never left in
place: the Run Log is the record, the report was the message.>

1. **Driven by this plan's /goal; model, effort and permission mode.**

   ```bash
   T=$(ls -t "$HOME"/.claude/projects/*/"$CLAUDE_CODE_SESSION_ID".jsonl | head -1)
   echo "T=$T"
   G=$(grep '"type":"goal_status"' "$T" | tail -1)
   echo "$G" | grep -o '"met":[a-z]*'
   echo "$G" | grep -o '"condition":"[^"]\{0,120\}'
   grep '"type":"assistant"' "$T" | tail -1 | grep -o '"model":"[^"]*"' | head -1
   grep -o '"permissionMode":"[^"]*"' "$T" | tail -1
   echo "effort=$CLAUDE_EFFORT"
   ```

   Expected: `"met":false` with a condition naming this plan file — the last goal
   set in this session is this plan's and was never met and never cleared. A last
   record with `"met":true`, a different goal's condition, or no record at all in
   a readable transcript each mean no evaluator guards this run: stop and write the
   blocked
   report; the fix is relaunching with the command in the Handoff section. If the
   `T=` line prints empty, the transcript could not be found and none of the
   transcript-derived facts can be read — they are unverifiable, not false: record
   that in the Run Log, take the model from what this session states about itself,
   the effort from `CLAUDE_EFFORT`, and the permission mode from the launch flags
   described below; treat the goal check as unverifiable, and continue. Otherwise
   expect `"model":"claude-opus-5"`, `"permissionMode":"auto"`, `effort=high`.

   The `permissionMode` line may print nothing when the session was started with a
   slash command as its prompt — which is what the handoff launches. Fall back to the
   launch flags, walking up from `$PPID` until the argv starts with `claude`, and
   matching `--permission-mode <mode>` or `--dangerously-skip-permissions`. If neither
   source answers, the mode is unverifiable: say so rather than assuming it.

2. **Privileges** — skip this group only if the mode above is `bypassPermissions`,
   and say in the Run Log that you skipped it.
   - `kubectl auth can-i update configmap -n staging` prints `yes`.
   - `helm -n staging upgrade api charts/api -f charts/api/values-staging.yaml --dry-run`
     exits 0. If it is denied rather than failing, that is a pre-flight failure.
   - `echo test | gpg --clearsign --batch --pinentry-mode error` exits 0 — commits
     here are signed, and a cold agent hangs rather than failing.
   - The ticket comment channel answers: a read against the Atlassian MCP server
     succeeds under this permission mode (or, on the REST fallback,
     `GET /rest/api/3/mypermissions?issueKey=ACME-123&permissions=ADD_COMMENTS`
     returns `havePermission: true`).
   - `git push --dry-run` exits 0 — the closeout pushes the preservation commit, and a
     link to a commit that never left the machine is a dead link. A closeout that
     cannot run is a pre-flight failure, because the plan cannot be preserved once it
     is deleted.

3. **Ground.**
   - This file exists at `2026-08-27-cache-ttl-plan.md`, the `plan_file` in its
     frontmatter.
   - `git remote -v` names the `api` repository, `git branch --show-current` prints
     `main`, and `git status --porcelain` is empty — or this is a resume: the
     frontmatter says `status: executing` or `status: blocked`, and the only changes
     are this file, the blocked report just consumed, and the files the Run Log names
     as work in progress. Anything else dirty is a failed check.

4. **Preconditions from the Verified Context.** Re-run the facts the tasks turn on:
   `grep -n 'ttlSeconds' charts/api/values.yaml` still shows `300`, and the staging
   cluster answers `kubectl -n staging get configmap api-config -o name`.

## Tasks

<Ordered. Each: what changes, where, and how to tell it worked. Checkboxes are
ticked by the execution session as it goes, and each task ends in a commit unless the
plan says which tasks land together.>

- [ ] **1. Raise the TTL in the staging values file**
  - Edit `charts/api/values-staging.yaml`, key `cache.ttlSeconds`: `300` → `3600`.
  - Verify: `grep -A2 'cache:' charts/api/values-staging.yaml` shows the new value.

- [ ] **2. Apply the change to the staging cluster**
  - `helm -n staging upgrade api charts/api -f charts/api/values-staging.yaml`
  - Verify: `kubectl -n staging get configmap api-config -o "jsonpath={.data.cacheTtlSeconds}"`
    prints `3600`.

## Acceptance Criteria

<The checks that decide whether the work is done. Exact commands and exact expected
results — these are inlined into the goal condition, so an evaluator must be able to
judge them from the output alone. Every criterion must be runnable in this
environment; you verified that in phase 1.>

1. `mvn -q verify` exits 0.
2. `kubectl -n staging get configmap api-config -o "jsonpath={.data.cacheTtlSeconds}"`
   prints `3600`.
3. The final state of the plan was committed and pushed, and a comment on ACME-123
   links to `2026-08-27-cache-ttl-plan.md` at that commit — which is the last commit
   before the one that deletes the file.
4. `git status --porcelain` is empty — everything committed, plan file gone.

## Rollback

<How to undo this if it goes wrong. A reader in trouble should not have to invent
this under pressure.>

- `git revert` the work commits, newest first, and re-run the helm upgrade with the
  previous values.

## Closeout

<Run after the work is committed and the Acceptance Criteria have been re-run, and
before this file is removed. Always present: this file is the record of the run, and it
is preserved in a commit of its own before it is deleted, ticket or no ticket. Exact
commands, verified in phase 1 — the execution session runs them, it does not work out
how to talk to git or Jira. This section is not a decision point: do not ask what
should be done with this file or the ticket — that was decided in the planning session,
and this section is the decision. Run the recorded commands; if they cannot complete,
the answer is the blocked report, not a question. Steps 3, 4 and 6 apply only with a
ticket; without one, or when the user decided against the comment, say so in one line
where they would stand and run the rest.>

1. Bring this file to its final state: every task checkbox ticked, the Run Log
   complete, the outcome recorded, and `status: done` in the frontmatter.
2. Commit this file on its own — the preservation commit — and push it when
   `closeout_push` in the frontmatter says so:

   ```bash
   git add 2026-08-27-cache-ttl-plan.md
   git commit -m "ACME-123: record final plan state"
   git push
   SHA=$(git rev-parse HEAD); echo "$SHA"
   ```

   It is a commit of its own because the final Run Log entries are written after the
   work commit, so they exist in no earlier commit. Do not squash it into the work
   commit and do not delete the file in it.
3. Build the permalink by substituting that SHA into the `permalink` template from the
   frontmatter:

   ```
   https://github.com/acme/api/blob/$SHA/2026-08-27-cache-ttl-plan.md
   ```

   Check the SHA and path are the ones just committed. A comment carrying a wrong URL
   looks like a record and is not.
4. Post a comment on ACME-123 via the Atlassian MCP tool `addCommentToJiraIssue`
   (cloudId `a1b2c3d4-…`), containing: a Markdown link to that URL on the file name,
   `[2026-08-27-cache-ttl-plan.md](…)`; the outcome in one sentence; the commit SHAs and
   branch; each acceptance criterion as command → result; the ticket's rows of the
   Requirements table, so a reader sees which ticket requirements this run did not
   cover and that it was deliberate; and any deviation from this plan.
5. Only now delete this file, in a **separate follow-up commit**, pushed when the
   preservation commit was:

   ```bash
   git rm 2026-08-27-cache-ttl-plan.md
   git commit -m "ACME-123: remove plan file"
   git push
   ```

   Separate is the point: the preservation commit has to stay the last commit in which
   this file exists, because that is where the record of the run lives — and, with a
   ticket, the commit the comment links to.
6. Do not transition ACME-123 and do not edit any of its fields. A comment, nothing
   else.

If the preservation commit, the push or the comment cannot be completed, **leave this
file in place** and write the blocked report — that commit is the only thing that
preserves this record once the file is gone.

## Execution Protocol

<Copy this section into every plan file. It is what lets an execution session execute
one without supervision.>

You are executing this plan file autonomously. There is nobody to ask, so decide
from what is written here plus the repository, and record what you decided.

1. Read this file completely before starting.
2. Run the **Pre-Flight** section first, in your first turn, before changing
   anything. Show each check and its real output. If any check fails, stop there:
   write the blocked report described in step 10, naming the failed check, what was
   expected, what was actually there, and what has to change about the launch. Do not
   start the tasks, do not substitute a different model or mode, and do not proceed
   at a lower spec — a mismatch discovered here costs a relaunch, and the same
   mismatch discovered at task 5 costs the whole run. When every check passes, set
   `status: executing` in the frontmatter and append the gate's outcome to the Run
   Log — the file now says a run is under way, and a later reopen reads that rather
   than guessing. On a resume, continue at the first unticked task; a task the Run
   Log shows started but not finished is inspected before it is redone, because the
   tree may already hold part of it.
3. Work the tasks in order. Append a line to the Run Log when you start a task, and
   tick its checkbox with another line when you finish it. Do this as you go, not at
   the end — if this run is interrupted, the ticked boxes and the last started-line
   are how the next one knows where to resume and what half-done work it may find.
4. Run each task's verification and the Acceptance Criteria for real, and show their
   output. A summary is not evidence.
5. Immediately before the final commit and the removal of this file, re-run the full
   Acceptance Criteria and show every command and result again. The evaluator judging
   whether you are done reads the condition text and the recent conversation — a
   result proved twenty turns ago may no longer be visible to it, and this file is
   about to stop existing.
6. If reality contradicts the Verified Context, stop and record the contradiction in
   the Run Log before deciding anything. Then proceed only if the plan's Goal still
   makes sense; otherwise treat it as blocked.
7. Commit as you go, on the current branch — `branch` in the frontmatter, which the
   gate confirmed — with the ticket prefix and the signing convention this plan
   records: a task, or a coherent slice of one, per commit, so progress is durable and
   a resume or a rollback has real boundaries to work with. Never create a branch: when this plan wanted one, the planning session created it
   at handoff and this file already sits on it.
8. Run the **Closeout** section — after the commit in step 7 and before you remove
   this file in step 9. That order is the whole point: this file is the record of the
   run and it is about to stop existing, so its final state is committed — and, with a
   ticket, linked from it — before anything is deleted. If the closeout cannot be
   completed, do not remove this file — write the blocked report in step 10 instead,
   naming the closeout as what failed.
9. When every acceptance criterion passes and the closeout is done, remove this plan
   file exactly as the Closeout section prescribes: in a separate commit after the
   preservation commit, never folded into it and never folded into the work commit.
   The plan is always tracked, so there is no `rm` path. When the plan lives in a
   different repository than the work — `work_repo` in the frontmatter — the plan
   commits, preservation and deletion alike, go to the repository holding the plan,
   never to the one you are changing.
10. If a criterion cannot be made to pass — or the run cannot finish for any other
    reason: a denied command, a contradiction with the Verified Context that leaves the
    Goal standing but the plan wrong, a run that has to stop clean at a task boundary —
    write the blocked report at **exactly the path named in the goal condition**: the
    plan path with `.md` replaced by `.BLOCKED.md`, so `2026-08-27-cache-ttl-plan.md`
    becomes `2026-08-27-cache-ttl-plan.BLOCKED.md`. It names the failing check, what you
    tried, and why it cannot pass; lists the working tree as you leave it — every
    uncommitted file and the task it belongs to; and ends with one line,
    `Next: relaunch` when the Handoff command can resume once the environment is fixed,
    or `Next: reopen` when the plan itself has to change. Set `status: blocked` in this
    file's frontmatter, bring the Run Log current, and commit this file and the report
    together — the blocked commit, pushed when `closeout_push` says so — leaving
    uncommitted only the work that has not reached a commit boundary. Then stop. Getting
    the path wrong is not cosmetic: the evaluator looks for the path the condition
    names, so a different spelling means the report does not register and the session
    cannot stop. Do not weaken a check, skip it, or declare success without it. A report
    written by mistake — on an estimate rather than a check that ran — is retracted in
    the same session: delete it, say so in the Run Log, and continue.

## Handoff

<The verbatim command that starts phase 2. Written here so the plan file carries its
own launch instruction — terminal output is lost, a committed file is not. Keep it
in a fenced block so it can be copied straight out of the file.>

```bash
claude --model opus --effort high --permission-mode auto --remote-control 2026-08-27-cache-ttl-plan '/goal Execute the plan at 2026-08-27-cache-ttl-plan.md to completion. Done when ...'
```

If this plan file has been sitting for a while, do not paste that blindly — reopen it
with `/pdca:plan <this file>` to re-verify the Verified Context and get a
freshened handoff.

Short form, for typing into a session already started with the flags above. The
evaluator then holds only the plan path, the protocol and the escape hatch — not the
acceptance criteria — so it has to trust this session's own account of what it ran.
Prefer the full command; use this when the full one is not to hand. A bare
`/goal 2026-08-27-cache-ttl-plan.md` is not a launch at all: the evaluator cannot open
the file, so it would have nothing to judge.

```
/goal Execute the plan at 2026-08-27-cache-ttl-plan.md to completion per its Execution Protocol: Pre-Flight first, every Acceptance Criterion shown passing in a final re-run, the Closeout done before the file was removed in a separate later commit; or 2026-08-27-cache-ttl-plan.BLOCKED.md was written in this session.
```

## Run Log

<Appended by the execution session: a line when a task starts and one when it ends,
decisions, surprises, deviations — and the summary of any blocked report a relaunch or
a reopen consumed.>
````

## The frontmatter

The frontmatter is the plan's data: what produced it, who it is for, what it was
planned from, and where it stands. Everything a reader or a session might want to
look up without reading prose lives here, and nothing else does — an instruction is a
sentence in a section, not a key. GitHub renders the block as a table at the top of
the file, so it costs the human reader nothing.

| Key | Written by | Meaning |
|---|---|---|
| `plugin`, `plugin_version`, `plugin_url` | phase 1, first draft | Provenance, copied from the plugin's own `.claude-plugin/plugin.json` (`name`, `version`, `repository`). `plugin: pdca` is also how `/pdca:plan <path>` tells a plan to reopen from a spec to plan against; the version tells a reopen which template wrote the file. |
| `created` | phase 1, first draft | Date of the first draft. Never updated. |
| `status` | both phases | The plan's state — see below. |
| `executor` | phase 1, first draft | Model, effort and permission mode for phase 2, in the spellings the pre-flight compares: `claude-opus-5`, `high`, `auto`. |
| `sources` | phase 1, first draft | Every requirements source the plan was planned from: ticket keys, spec paths, URLs. `[]` when there were none. |
| `ticket` | phase 1, first draft | `key`, `url` and `cloud_id` of the Jira ticket, or `none`. Present even when `none`, so an absent ticket can be told from a forgotten one. |
| `plan_file` | phase 1, first draft | This file's path, relative to the repository holding it. |
| `work_repo` | phase 1, first draft | Only when the work lives in a different repository than the plan: its path. Absent otherwise. |
| `branch` | phase 1, handoff | The branch the plan expects at launch; the Ground check compares. Normally the branch planning happened on. When the user asked for the work to go on a new branch, phase 1 created it at handoff and committed the plan on it, and this names it. |
| `closeout_push` | phase 1, handoff | Whether the closeout pushes its two commits. Asked only when a ticket was named; `false` otherwise, and `false` when there is no remote. |
| `permalink` | phase 1, handoff | The host's permalink form with everything but `<sha>` filled in, or `none` when there is no remote. |

`status` takes exactly these values, and the file's state is read from it, never
inferred from its age or its checkboxes:

| Value | Set when |
|---|---|
| `drafting` | Phase 1 writes the first draft. Stays through iteration and review. |
| `handed-off` | Phase 1 writes the Handoff section, immediately before the commit that carries it. |
| `executing` | Phase 2 passes the Pre-Flight gate — its first write to the file. |
| `done` | Phase 2 brings the file to its final state, immediately before the preservation commit — so the last commit holding the file says `done`. |
| `blocked` | Phase 2 writes the blocked report and commits it together with the plan. Left by relaunch — the pre-flight consumes the report and sets `executing` — or by reopen — phase 1 consumes it and sets `drafting`. Either way the report is folded into the Run Log and deleted, so it never outlives the next pick-up. |

A reopen reads the value and acts on it — the SKILL's "Reopening a plan" says how.

## Writing guidance

**Inline every command; never factor one into a bundled script.** The transcript
checks in Pre-Flight are fiddly enough to look like they belong in a `scripts/`
directory, and they are duplicated in `references/preflight.md`, which sharpens the
temptation. Resist it. Phase 2 runs with no plugin installed — the goal condition and
this file are all it has — so a path into the skill directory is a dead path in the
artifact, and the check it guards stops running without saying so. Duplication is the
cheaper failure here.

**Verified Context is the anti-hallucination core.** A plan whose facts were checked
is a plan an execution session can trust. If you catch yourself writing "should be"
or "presumably", either go run the command or move the claim into an explicit
assumption the executor is told to verify first.

**Write at the altitude of the executor.** `haiku` at `low` effort needs exact
paths, exact strings, and no inference. `opus` at `max` needs intent and constraints
and will handle the rest — over-specifying it wastes both your time and its
judgment. This is why the model and effort are settled before the plan is drafted.

**Write acceptance criteria apostrophe-free and backtick-free from the start.** They
get inlined into the goal condition, which is emitted inside a single-quoted shell
argument — so a criterion containing `'` corrupts the handoff line and the check can
then never print what it was supposed to. Prefer `-o "jsonpath={…}"` over
`-o 'jsonpath={…}'`. This is cheap to do while writing and annoying to retrofit.

**Acceptance Criteria are load-bearing twice.** They tell the executor when to stop,
and they are inlined into the goal condition, where an evaluator that never read the
plan uses them to judge the run. So each one must be a command with an unambiguous
expected result. "The feature works" is unusable to both readers.

**Tasks are ordered for a reason — say the reason** when the order is not obvious.
An executor that does not know step 3 must follow step 2 may parallelize them.

**A new branch is opt-in, and the planning session makes it.** The default is the
branch planning happened on. When the user asks for the work to go on a new branch,
phase 1 creates it at handoff, before the commit that carries the Handoff section, so
the plan lands on that branch and `branch` in the frontmatter names it. Phase 2 never
creates a branch, whatever the ticket or the repository's habits suggest; a plan that
wants one already sits on it. Say in Rollback how the branch is disposed of if the run
fails.

**When the plan and the work live in different repositories, say so at the top.**
It happens whenever planning starts in one checkout and the code is in another. The
execution session needs to know, in the frontmatter (`work_repo`) and in the
Execution Protocol, which repository it is changing, which it must not touch, and
that the plan file cannot be part of the commit. Left implicit, it will guess — and committing a plan file into
an unrelated repository is a messy thing to undo unattended.

**The Requirements table is for phase 2, not for the record.** It is also where the
source-as-request rule leaves its trace: a ticket's or a spec's non-functional demands —
a named mechanism, a library, a split into phases — are the ones a verified plan most
often deviates from, and each deviation belongs here with its reason. Its job is to stop
an execution session from implementing a requirement the user decided against —
which is a thing it will otherwise do, in good faith, because the ticket key and the
spec path are right there in the frontmatter. So every requirement appears, including
the ones that were dropped, each naming its source, and every disposition says which
task covers it or why nothing does. A table that lists only the in-scope items is the
one shape that fails at this.

**Prefer fewer, larger tasks over many tiny ones.** A capable executor does not need
each file edit enumerated, and a long checklist buries the decisions that actually
matter.
