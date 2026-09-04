---
name: execute
description: Launch or resume the execution phase of a pdca plan file as a fresh background `claude` session that runs the plan's own Handoff command under `/goal` with Remote Control. Use this skill whenever the user wants to start, launch, run, kick off, resume or relaunch a plan file, says "execute the plan", asks how to launch a plan without pasting the handoff command, has fixed what a blocked report named and wants the run to continue, accepts the launch offer at the end of the planning phase, or types /pdca:execute. Never execute a plan inside the current session — this skill starts a new process, and says why.
user-invocable: false
---

# PDCA: launching the execution phase

`/pdca:plan` ends by writing a launch command into the plan's Handoff section. This
skill runs that command for the user, as a **new background process**, and reports how
to reach it. That is all it does, and the restraint is the design.

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
| `blocked` | A run stopped itself and left a report | Read the `.BLOCKED.md` beside the plan. `Next: relaunch` → launch; the pre-flight consumes the report before its first check. `Next: reopen` → stop: the plan has to change, and `/pdca:plan <path>` is how. A missing report, or one without a `Next:` line, is something to say and ask about, not to guess past. |
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
form** — a condition with a single quote in it. The `/goal …` line is then in the
Handoff section as well, in its own fenced block: put it in a shell variable through a
quoted heredoc and pass it as the positional argument, `"$goal"`, so that no quoting
hazard survives.

## 5. Launch

Insert `--bg` and `--name <basename>` directly after `claude`, and run the result from
the repository root — the plan path in the condition is relative to it; a `cd` form
takes care of its own directory:

```bash
claude --bg --name 2026-08-27-cache-ttl-plan --model opus --effort high --permission-mode auto --remote-control 2026-08-27-cache-ttl-plan '/goal Execute the plan at 2026-08-27-cache-ttl-plan.md …'
```

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
claude.ai URL if it was there. Then the three things the user needs to know about the
process that is now running:

- It is guarded by `/goal`: inside it, `/goal` shows status and `/goal clear` stops the
  run early. Its pre-flight gate runs in the first turn; a `.BLOCKED.md` appearing
  beside the plan means the run stopped itself, and `/pdca:plan <path>` picks up from
  the report.
- It keeps running when this session and its terminal are gone; only the machine has to
  stay up. Remote Control is how to look in from anywhere else.
- It stays alive, idle, after the run finishes, until `claude rm <id>`; `claude agents`
  lists what is lingering.

## What this skill never does

- Edit the plan file. After the handoff it belongs to the execution session.
- Work the plan in this session, for the reasons above — however small the plan looks.
- Change the model, effort or permission mode in the command. A plan for another model
  is relaunched by a reopen, not by a substitution; the gate would refuse it anyway.
- Re-verify the plan. Do say how long it has been sitting — `git log -1 --format=%cr --
  <plan>` — and how many commits the branch has taken since; a plan that has aged is the
  user's to reopen with `/pdca:plan <path>`, and the freshness check is that reopen's
  whole point. Say it, then do what was asked.
