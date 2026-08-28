# The plan file template

Every section below exists because leaving it out is a way autonomous runs fail.
Keep the section order and headings — the goal condition and the Execution Protocol
refer to them by name.

Sections may be dropped only when genuinely inapplicable (a docs-only change has no
meaningful Rollback). When you drop one, say so in a single line rather than
silently omitting it, so a reader can tell the difference between "not needed" and
"forgotten".

## Skeleton

````markdown
# <Goal in one line>

| | |
|---|---|
| **Created** | 2026-08-27 |
| **Executor** | Opus 5, high effort, permission mode auto |
| **Ticket** | ACME-123 — https://acme.atlassian.net/browse/ACME-123 (cloudId a1b2c3d4-…) |
| **Branch** | current branch — do not create a new one |
| **Plan file** | docs/plans/2026-08-27-cache-ttl.md |

## Goal

<One paragraph: what is true after this work that is not true now, and why it is
being done. Enough for a reader to sanity-check a decision the tasks did not
anticipate.>

## Ticket Requirements

<Every requirement in the ticket and what the user decided about it. Omit this section
only when there is no ticket, and then say so in one line. See `references/jira.md`.>

**Where this plan and the ticket disagree, this plan wins.** Do not implement a ticket
requirement that this table marks out of scope, deferred or reversed — each of those is
a decision the user made in the planning session, not an oversight.

| # | Requirement (ticket wording, condensed) | Disposition | Note |
|---|---|---|---|
| 1 | Staging cache TTL raised to 1 hour | In scope — task 1 | |
| 2 | Same change in production | Out of scope | User: staging only this week |
| 3 | Add a cache-hit-rate metric | Deferred | Split to ACME-131 |
| 4 | Document the value in the runbook | In scope — task 3 | |
| 5 | AC: "cache hits improve measurably" | Reworded | Not testable as written; replaced by acceptance criterion 2 |
| 6 | Restart the pods after the change | Already satisfied | The ConfigMap is watched, not mounted: verified below |

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
are spelled out literally here so the comparison is a string match, not a judgement.>

1. **Driven by this plan's /goal; executing model, effort and permission mode.**

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

   The `permissionMode` line prints nothing when the session was started with a slash
   command as its prompt — which is what the handoff launches (`claude -p … "/goal …"`).
   Fall back to the launch flags, walking up from `$PPID` until the argv starts with
   `claude`, and matching `--permission-mode <mode>` or `--dangerously-skip-permissions`.
   If neither source answers, the mode is unverifiable: say so rather than assuming it.

2. **Privileges** — skip this group only if the mode above is `bypassPermissions`,
   and say in the Run Log that you skipped it.
   - `kubectl auth can-i update configmap -n staging` prints `yes`.
   - `helm -n staging upgrade api charts/api -f charts/api/values-staging.yaml --dry-run`
     exits 0. If it is denied rather than failing, that is a pre-flight failure.
   - `echo test | gpg --clearsign --batch --pinentry-mode error` exits 0 — commits
     here are signed, and a cold agent hangs rather than failing.
   - The ticket closeout channel answers: `GET /rest/api/3/mypermissions?issueKey=ACME-123&permissions=CREATE_ATTACHMENTS,ADD_COMMENTS`
     returns `havePermission: true` for both. A closeout that cannot run is a
     pre-flight failure, because the plan cannot be preserved once it is deleted.

3. **Ground.**
   - This file exists at `docs/plans/2026-08-27-cache-ttl.md`.
   - `git remote -v` names the `api` repository, and `git status --porcelain` is empty.

4. **Preconditions from the Verified Context.** Re-run the facts the tasks turn on:
   `grep -n 'ttlSeconds' charts/api/values.yaml` still shows `300`, and the staging
   cluster answers `kubectl -n staging get configmap api-config -o name`.

## Tasks

<Ordered. Each: what changes, where, and how to tell it worked. Checkboxes are
ticked by the executing session as it goes.>

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
3. The final plan is attached to ACME-123 as `2026-08-27-cache-ttl.md` — the issue read
   back lists that filename — and a comment summarizing the outcome has been posted.
4. `git status --porcelain` is empty — everything committed, plan file gone.

## Rollback

<How to undo this if it goes wrong. A reader in trouble should not have to invent
this under pressure.>

- `git revert <commit>` and re-run the helm upgrade with the previous values.

## Ticket Closeout

<Run after the work is committed and the Acceptance Criteria have been re-run, and
before this file is removed. Exact commands, verified in phase 1 — the executing session
runs them, it does not work out how to talk to Jira. This section is not a decision
point: do not ask what should be done with this file or the ticket — that was decided
in the planning session, and this section is the decision. Run the recorded commands;
if they cannot complete, the answer is the blocked report, not a question. Omit only
when there is no ticket, or when the user decided against a closeout, and then say
which in one line.>

1. Bring this file to its final state: every task checkbox ticked, the Run Log
   complete, the outcome recorded.
2. Attach it to ACME-123 under its own basename:

   ```bash
   curl -sS -u "$JIRA_EMAIL:$JIRA_TOKEN" -X POST \
     -H "X-Atlassian-Token: no-check" \
     -F "file=@docs/plans/2026-08-27-cache-ttl.md" \
     https://acme.atlassian.net/rest/api/3/issue/ACME-123/attachments
   ```

3. Verify it landed — read the issue back and find the filename among its attachments:

   ```bash
   curl -sS -u "$JIRA_EMAIL:$JIRA_TOKEN" \
     "https://acme.atlassian.net/rest/api/3/issue/ACME-123?fields=attachment" \
     | grep -o '2026-08-27-cache-ttl.md'
   ```

   An upload that exited 0 is not evidence. This listing is.
4. Post a comment on ACME-123 via the Atlassian MCP tool `addCommentToJiraIssue`
   (cloudId `a1b2c3d4-…`), containing: the outcome in one sentence; the commit SHAs and
   branch; each acceptance criterion as command → result; the dispositions from the
   Ticket Requirements table, so a reader sees which ticket requirements this run did
   not cover and that it was deliberate; and any deviation from this plan.
5. Do not transition ACME-123 and do not edit any of its fields. An attachment and a
   comment, nothing else.

If the attachment or the comment cannot be completed, **leave this file in place** and
write the blocked report — the attachment is the only thing that preserves this record
once the file is gone.

## Execution Protocol

<Copy this section into every plan. It is what lets a fresh session execute the plan
without supervision.>

You are implementing this plan autonomously. There is nobody to ask, so decide from
what is written here plus the repository, and record what you decided.

1. Read this file completely before starting.
2. Run the **Pre-Flight** section first, in your first turn, before changing
   anything. Show each check and its real output. If any check fails, stop there:
   write the blocked report described in step 10, naming the failed check, what was
   expected, what was actually there, and what has to change about the launch. Do not
   start the tasks, do not substitute a different model or mode, and do not proceed
   at a lower spec — a mismatch discovered here costs a relaunch, and the same
   mismatch discovered at task 5 costs the whole run.
3. Work the tasks in order. After finishing each one, tick its checkbox in this file
   and append a line to the Run Log. Do this as you go, not at the end — if this run
   is interrupted, the ticked boxes are how the next one knows where to resume.
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
7. Commit on the current branch with the ticket prefix and signing convention above.
   Do not create a branch.
8. Run the **Ticket Closeout** section — after the commit in step 7 and before you
   remove this file in step 9. That order is the whole point: this file is the record
   of the run and it is about to stop existing, so it is attached to the ticket first
   and the attachment is confirmed to be there before anything is deleted. If the
   closeout cannot be completed, do not remove this file — write the blocked report in
   step 10 instead, naming the closeout as what failed.
9. When every acceptance criterion passes and the closeout is done, remove this plan
   file. How depends on where it lives, so check rather than assume:
   - **Tracked in the repository being changed** — delete it as part of the final
     commit, so the plan and the work that fulfilled it land together.
   - **Untracked** (the author chose not to commit it) — just `rm` it. There is no
     deletion to commit, and the Run Log has nowhere to survive, so summarize it in
     the final commit message body instead.
   - **In a different repository than the work** — `rm` it after the final commit.
     It cannot be part of a commit in the repository you are changing.
10. If a criterion cannot be made to pass: write the blocked report at **exactly the
    path named in the goal condition** — the plan path with `.md` replaced by
    `.BLOCKED.md`, so `2026-08-27-cache-ttl.md` becomes
    `2026-08-27-cache-ttl.BLOCKED.md`. Name the failing check, what you tried,
    and why it cannot pass — then stop. Getting this path wrong is not cosmetic: the
    evaluator looks for the path the condition names, so a different spelling means
    the report does not register and the session cannot stop. Do not weaken a check,
    skip it, or declare success without it.

## Run Log

<Appended by the executing session: decisions, surprises, deviations.>

## Handoff

<The verbatim command that starts phase 2. Written here so the plan carries its own
launch instruction — terminal output is lost, a committed file is not. Keep it in a
fenced block so it can be copied straight out of the file.>

```bash
claude --model opus --effort high --permission-mode auto '/goal Execute the plan at docs/plans/2026-08-27-cache-ttl.md to completion. Done when ...'
```

If this plan has been sitting for a while, do not paste that blindly — reopen it
with `/pdca:plan <this file>` to re-verify the Verified Context and get a
freshened handoff.
````

## Writing guidance

**Verified Context is the anti-hallucination core.** A plan whose facts were checked
is a plan an autonomous session can trust. If you catch yourself writing "should be"
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

**When the plan and the work live in different repositories, say so at the top.**
It happens whenever planning starts in one checkout and the code is in another. The
executing session needs to know, in the header and in the Execution Protocol, which
repository it is changing, which it must not touch, and that the plan file cannot be
part of the commit. Left implicit, it will guess — and committing a plan file into
an unrelated repository is a messy thing to undo unattended.

**The Ticket Requirements table is for phase 2, not for the record.** Its job is to
stop an executing session from implementing a ticket requirement the user decided
against — which is a thing it will otherwise do, in good faith, because the ticket key
is right there in the header. So every requirement appears, including the ones that were
dropped, and every disposition says which task covers it or why nothing does. A table
that lists only the in-scope items is the one shape that fails at this.

**Prefer fewer, larger tasks over many tiny ones.** A capable executor does not need
each file edit enumerated, and a long checklist buries the decisions that actually
matter.
