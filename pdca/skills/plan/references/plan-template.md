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
| **Executor** | Opus 5, high effort |
| **Ticket** | ACME-123 |
| **Branch** | current branch — do not create a new one |
| **Plan file** | docs/plans/2026-08-27-cache-ttl.md |

## Goal

<One paragraph: what is true after this work that is not true now, and why it is
being done. Enough for a reader to sanity-check a decision the tasks did not
anticipate.>

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
3. `git status --porcelain` is empty — everything committed, plan file gone.

## Rollback

<How to undo this if it goes wrong. A reader in trouble should not have to invent
this under pressure.>

- `git revert <commit>` and re-run the helm upgrade with the previous values.

## Execution Protocol

<Copy this section into every plan. It is what lets a fresh session execute the plan
without supervision.>

You are implementing this plan autonomously. There is nobody to ask, so decide from
what is written here plus the repository, and record what you decided.

1. Read this file completely before starting.
2. Work the tasks in order. After finishing each one, tick its checkbox in this file
   and append a line to the Run Log. Do this as you go, not at the end — if this run
   is interrupted, the ticked boxes are how the next one knows where to resume.
3. Run each task's verification and the Acceptance Criteria for real, and show their
   output. A summary is not evidence.
4. Immediately before the final commit and the removal of this file, re-run the full
   Acceptance Criteria and show every command and result again. The evaluator judging
   whether you are done reads the condition text and the recent conversation — a
   result proved twenty turns ago may no longer be visible to it, and this file is
   about to stop existing.
5. If reality contradicts the Verified Context, stop and record the contradiction in
   the Run Log before deciding anything. Then proceed only if the plan's Goal still
   makes sense; otherwise treat it as blocked.
6. Commit on the current branch with the ticket prefix and signing convention above.
   Do not create a branch.
7. When every acceptance criterion passes, remove this plan file. How depends on
   where it lives, so check rather than assume:
   - **Tracked in the repository being changed** — delete it as part of the final
     commit, so the plan and the work that fulfilled it land together.
   - **Untracked** (the author chose not to commit it) — just `rm` it. There is no
     deletion to commit, and the Run Log has nowhere to survive, so summarize it in
     the final commit message body instead.
   - **In a different repository than the work** — `rm` it after the final commit.
     It cannot be part of a commit in the repository you are changing.
8. If a criterion cannot be made to pass: write the blocked report at **exactly the
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

**Prefer fewer, larger tasks over many tiny ones.** A capable executor does not need
each file edit enumerated, and a long checklist buries the decisions that actually
matter.
