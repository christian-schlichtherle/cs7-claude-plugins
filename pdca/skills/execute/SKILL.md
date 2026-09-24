---
description: Launch or resume the execution phase of a pdca plan file as a fresh background `claude` session that runs the plan's own Handoff command under `/goal` with Remote Control, then keep a checklist of its progress in this session. Use this skill whenever the user wants to start, launch, run, kick off, resume or relaunch a plan file, says "execute the plan", asks how to launch a plan without pasting the handoff command, has fixed what a blocked report named and wants the run to continue, accepts the launch offer at the end of the planning phase, or types /pdca:execute. Never execute a plan inside the current session — this skill starts a new process, and says why.
name: execute
user-invocable: false
---

# PDCA: launching the execution phase

`/pdca:plan` ends by writing a launch command into the plan's Handoff section. This
skill runs that command for the user, as a **new background process**, reports how
to reach it, and then keeps a checklist of the run that follows the plan's own
checkboxes. It never works the plan, and the restraint is the design.

## Why a new process, always

Two facts, both verified against Claude Code 2.1.260 on 2026-09-04:

- **Nothing inside a session can set a goal.** `/goal` is a harness command. A command
  or skill body that contains a `/goal …` line is expanded into the prompt as text —
  the model answers it, and no goal exists. A goal is set only by a user typing
  `/goal`, or by `/goal …` as the positional prompt of a new `claude` process. So this
  skill cannot install the plan's goal here, and must not pretend to by working the
  plan itself: a session without the evaluator can stop half-done and nothing notices.
- **This session is the wrong session anyway.** The plan was written for a model, an
  effort and a permission mode settled in the planning phase, and its pre-flight gate
  refuses anything else. This session has its own, and a history the executor must not
  inherit.

`claude --bg` is what makes a launch possible from inside a session: it starts the new
process detached, returns at once with a short id, and the positional `/goal …` prompt
runs as that process's first turn — sentinel written, evaluator judging, Remote Control
connected. The process outlives this session and its terminal.

## 1. Find the plan

The argument is a plan path. Without one, look for `*-plan.md` at the repository root
(`git rev-parse --show-toplevel`): exactly one is the plan, say which; several means
ask; none means say so and stop. Read the frontmatter. `plugin: pdca` is a plan this
plugin wrote; anything else is not a plan, so stop and say what the file is.

Say in your first line which plan and which `status` you found — a wrong file costs
one correction here and a whole run later.

## 2. Dispatch on `status`

`status` is read, never inferred from the file's age or its checkboxes.

| `status` | What it means | What to do |
|---|---|---|
| `handed-off` | Planning finished; no run yet | Launch: steps 3 to 6. |
| `executing` | A run is under way, or was interrupted | Step 3 first: if a run is live, do not start a second one. Otherwise launch — the Execution Protocol resumes from the ticked boxes and the Run Log's last started-line. Say that it is a resume. |
| `blocked` | A run stopped itself and left a report | Read the report the plan's `blocked_report` names — on a plan blocked before 0.13.0 there is no such key, and the report is the plan path with `.md` replaced by `.BLOCKED.md` — and its frontmatter `next`. `next: relaunch` → launch; the pre-flight consumes the report before its first check. `next: reopen` → stop: the plan has to change, and `/pdca:plan <path>` is how. A report written before 0.10.0 has no frontmatter and ends with a `Next:` line instead — read that. A missing report, or one with neither, is something to say and ask about, not to guess past. |
| `drafting` | Planning never finished | Stop. Nothing to launch; `/pdca:plan <path>` continues planning. |
| `done` | Should not exist on disk | A stray copy. Stop and say so. |

## 3. Refuse to double-launch

Before any launch, look for an execution session already running in this repository:

```bash
claude agents --json
```

A `"kind": "background"` entry whose `cwd` is this repository — or the plan's
`work_repo` — and whose `state` is not `done` is a run in progress. Report its `id`
with the `claude attach <id>` and `claude logs <id>` lines, and stop: two sessions
working one plan from the same tree is the one thing a resume cannot recover from. An
entry that is `done` is a finished or stopped run still lingering in the background —
say so, and go on.

## 4. Take the launch command from the plan

The Handoff section's first fenced `bash` block is the command, verbatim; the planning
session wrote it there so that a launch never depends on terminal scrollback:

```bash
awk '/^## Handoff/{h=1;next} h&&!b&&/^## /{exit} h&&/^```bash/{b=1;next} b&&/^```/{exit} b' "$plan"
```

Then check it, because the block is about to be executed, and a plan file is a file in
a repository — written by a session, reviewed by a person, and possibly neither of them
recently:

- It is **one line**, and it is a `claude` invocation: `claude …`, or
  `cd <dir> && claude …`, and nothing else — no `;`, `|`, `$(`, backticks, or a second
  `&&`. Anything else: print the block and ask before running it.
- Its `/goal …` prompt names **this** plan file — `Execute the plan at <path>` — or the
  Handoff is stale and the plan wants a reopen, not a launch.
- It carries `--remote-control`. A plan written before plugin 0.8.0 does not; insert
  `--remote-control <basename>` before the prompt — `<basename>` is the file name
  without `.md` — and say so. The execution phase always runs with Remote Control.

The block has no `/goal` prompt when the planning session emitted the **two-step
form** — a condition with a single quote in it. The full condition is then in the
Handoff section as well, in the fence whose info string is `goal`, and that info
string is how you find it — the plain-fenced `/goal` line further down is the short
form, which also names this plan and is never launched from, because a run started
from it has an evaluator holding no acceptance criteria:

```bash
awk '/^## Handoff/{h=1;next} h&&!b&&/^## /{exit} h&&/^```goal/{b=1;next} b&&/^```/{exit} b' "$plan"
```

Check it as you checked the command — one line, opening `/goal Execute the plan at
<this plan>` — then put it in a shell variable through a quoted heredoc and pass it as
the positional argument, `"$goal"`, so that no quoting hazard survives. A prompt-less
`bash` block with no `goal` fence — including in a plan written before this layout was
fixed — is an incomplete Handoff: print what is there, do not launch, and say that
`/pdca:plan <path>` refreshes it.

## 5. Launch

Insert `--bg` and `--name <basename>` directly after `claude`, and run the result from
the repository root — the plan path in the condition is relative to it; a `cd` form
takes care of its own directory, and its condition names the plan by absolute path:

```bash
marker=$(mktemp) && echo "$marker" && claude --bg --name 2026-08-27-cache-ttl-plan --model opus --effort high --permission-mode auto --remote-control 2026-08-27-cache-ttl-plan '/goal Execute the plan at 2026-08-27-cache-ttl-plan.md …'
```

The marker in front of it is not part of the launch. It is the file step 7's watch
compares a blocked report's age against, and it is created first because a report
written at any point after the launch has to be newer than it. The shape check in step
4 applies to the Handoff block, not to this line.

`--bg` returns at once and prints `backgrounded · <id>` with the commands that take the
id. `--name` puts the plan's name into `claude agents`, where the generated name would
not say which plan is running; the argument of `--remote-control` names the claude.ai
side. Never run the Handoff command in the foreground from a tool: an interactive
`claude` without a terminal hangs the tool call and launches nothing.

Then read the new session's first screen once — `claude logs <id>` — for the Remote
Control line, `/remote-control is active · … https://claude.ai/code/session_…`. It
appears within seconds of launch; if it is not there yet, say so rather than waiting.

## 6. Report

A few lines: the plan and the `status` you launched from, and whether this was a start
or a resume; the id; `claude attach <id>`, `claude logs <id>`, `claude stop <id>`; the
claude.ai URL if it was there. Then what the user needs to know about the
process that is now running:

- It is guarded by `/goal`: inside it, `/goal` shows status and `/goal clear` stops the
  run early. Its pre-flight gate runs in the first turn; a `.BLOCKED.md` appearing
  beside the plan means the run stopped itself; its `next` says which pick-up it
  expects — `relaunch` means `/pdca:execute <path>` again once the environment is
  fixed, `reopen` means `/pdca:plan <path>`.
- It keeps running when this session and its terminal are gone; only the machine has to
  stay up. Remote Control is how to look in from anywhere else.
- It stays alive, idle, after the run finishes, until `claude rm <id>`; `claude agents`
  lists what is lingering.
- The checklist in this session is a view of the plan file and needs this session to
  stay open; the run does not. The execution session keeps a list of its own, which is
  what `claude attach` and Remote Control show.

## 7. Keep the checklist

Right after the report, before the watch starts, build this session's task list —
TaskCreate, or TodoWrite in a session that has that instead — from the plan file as it
stands now. One item per top-level checkbox in the Tasks section, titled with its bold
text:

```bash
awk '/^## Tasks/{t=1;next} t&&/^## /{exit} t&&/^- \[[ xX]\] /' "$plan"
```

Before them an item for the pre-flight gate, in progress, and after them one for the
Closeout. A task already ticked, which is what a resume looks like, starts completed.
The first unticked task starts pending: the gate runs again on every launch, a resume
included.

Then watch the file with Monitor, `timeout_ms` at its maximum. `$plan` is the plan's
absolute path, because a `cd` form moves the execution session and not this one. `$id`
is the id `--bg` printed, and `$marker` is a file created **before** the launch
command ran — `marker=$(mktemp)` in the same call — so that a blocked report the relaunch
inherited reads as `old` rather than as a new blockage:

```bash
plan=/abs/path/2026-08-27-cache-ttl-plan.md id=<id> marker=<marker path>
report=${plan%.md}.BLOCKED.md prev=
while :; do
  if [ -f "$plan" ]; then
    s=$(awk 'NR==1&&/^---$/{f=1;next} f&&/^---$/{exit} f&&/^status:/{print $2;exit}' "$plan")
    t=$(awk '/^## Tasks/{t=1;next} t&&/^## /{exit} t&&/^- \[ \] /{printf "."} t&&/^- \[[xX]\] /{printf "x"}' "$plan")
  else s=gone t=; fi
  r=none; if [ -f "$report" ]; then r=old; [ "$report" -nt "$marker" ] && r=new; fi
  a=$(claude agents --json 2>/dev/null | jq -r --arg id "$id" '[.[]|select(.id==$id)|.state][0] // "gone"' 2>/dev/null)
  cur="status=$s tasks=$t report=$r session=${a:-unknown}"
  if [ "$cur" != "$prev" ]; then echo "$cur"; prev=$cur; fi
  if [ "$s" = gone ] || [ "$r" = new ]; then exit 0; fi
  case $a in done|gone) exit 0;; esac
  sleep 10
done
```

Each event is one snapshot, and `tasks` holds one character per checkbox in order, `x`
for ticked. Bring the list up to date from each one:

- `status=executing`: the gate passed. Ticked tasks are completed and the first unticked
  one is in progress, because the Execution Protocol works them in order. When every
  task is ticked, the Closeout is in progress.
- `status=done`: every task is completed and the Closeout is in progress. The file is
  committed as the record, and its deletion comes next.
- `status=gone`: the Closeout is completed. The deletion commit is the run's last
  step. Say that the run finished, and stop watching.
- `report=new`: the run blocked itself. Leave the item that was in progress as it is,
  read the report's `next`, and say what it asks for, as in step 6. Then stop watching.
- `session=done` or `session=gone` while the file is still there and no new report
  exists: the process ended without finishing or blocking. `/goal clear`, `claude
  stop`, a crash or a launch that died before its gate all look like this. Say so, with
  the `status` the file was left in: `executing` or `handed-off` is one
  `/pdca:execute <path>` picks up again, after a look at `claude logs <id>` for why it
  ended. Stop watching.

Anything else, such as the `status=blocked report=none` of a relaunch whose gate has
just consumed the inherited report, changes nothing on the list. When the monitor
expires, re-arm it with the same `$marker`; its first event then repeats the current
state. `session=unknown` means `claude agents` or `jq` did not answer. The plan file
still drives the list, but the loop cannot notice a process that ended, so say that
once.

The list is a view, never the record, and the watch only reads. Whether the session
watching stays open is the user's affair: stopping the watch, with TaskStop or by
closing this session, stops nothing in the run. The same holds when the launch came
from the planning session's handoff, which follows this skill and then keeps the
checklist in its own terminal.

## What this skill never does

- Edit the plan file. After the handoff it belongs to the execution session. The
  checklist only reads it.
- Work the plan in this session, for the reasons above — however small the plan looks.
- Change the model, effort or permission mode in the command. A plan for another model
  is relaunched by a reopen, not by a substitution; the gate would refuse it anyway.
- Re-verify the plan. Do say how long it has been sitting — `git log -1 --format=%cr --
  <plan>` — and how many commits the branch has taken since; a plan that has aged is the
  user's to reopen with `/pdca:plan <path>`, and the freshness check is that reopen's
  whole point. Say it, then do what was asked.
