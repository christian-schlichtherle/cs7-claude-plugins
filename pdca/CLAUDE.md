# pdca Plugin — Developer Guide

## How It Works

Two commands (`/pdca:plan`, `/pdca:execute`) and two skills (`plan`, `execute`)
implementing a PDCA cycle split across two sessions:

- **Plan**, the planning phase — interactive, runs commands to verify its
  assumptions, writes `<date>-<slug>-plan.md` at the repository root.
- **Do/Check/Act**, the execution phase — a fresh `claude` process under
  `/goal`, executing the plan unattended.

`/pdca:execute` is the bridge between them: it starts the execution session as a
detached background process from the plan's own Handoff command.

The plan file is the only interface between them, which is why the skill pushes so
hard on verified facts and inlined acceptance criteria.

## Vocabulary

One word per concept, used in every file. Phase 2 once went by six names and the
user's exit signal by three; these are the survivors, decided 2026-09-02.

| Concept | Word | Not |
|---|---|---|
| The first phase | planning phase | Plan phase, interactive phase |
| The second phase | execution phase | Do/Check/Act phase, implementation phase, autonomous run |
| The process running each | planning session, execution session | fresh session, autonomous session, executing session, execution session |
| The model in phase 1 | planner | |
| The model in phase 2 | executor | executing model, implementer |
| The executor's model reading the plan cold inside phase 1 | reviewer | |
| The small model behind the `/goal` Stop hook | evaluator | |
| The planner's last step | handoff | |
| A human starting phase 2, maybe weeks later | launch | |
| What a human launches with | `/pdca:execute`, the launcher | pdca-run, a launcher script |
| The user's exit signal for the outer loop | proceed | go-ahead, satisfied, approved |
| What a ticket or a spec is | a requirements source; a request, not a contract | a specification |
| The artifact | the plan, the plan file | recipe, spec |

"Phase 1" and "phase 2" remain as shorthand once the names have been given. "Execute"
is the one verb for the second phase throughout — execution phase, execution session,
executor, Execution Protocol, "Execute the plan at". "Implementation phase" was tried
for a day and dropped for exactly that consistency.

## Conventions

- **One palette entry per command, two files each.** `/pdca:plan` and `/pdca:execute`
  are the commands; the skill of the same name behind each is `user-invocable: false`
  so it does not also appear in the slash-command list. Without that flag Claude Code
  shows each command twice — once for the command with its human-facing description,
  once for the skill with its triggering description.
- **The skill is the single source of truth.** Each command is a thin entry point: a
  description, an argument hint, examples, and a pointer. Argument parsing, the
  verification rules, the plan template, the goal-condition rules and the launch
  procedure live in the skills only. They were duplicated in both files once, and a
  review found the same two defects had to be fixed twice — hence the split.
- The skills stay model-invocable, which is what makes them trigger on intent
  ("write me a plan I can run later", "launch the plan") without the command being
  typed.
- Planning never reaches the handoff in the turn that drafts the plan. The
  interactive loop's exit condition is that the user says proceed, which they have to
  say — so the first draft always ends the turn. There is no waiver and no
  non-interactive mode: anyone who does not want the planning phase can set a
  `/goal` directly instead of using this workflow.
- **AGREED alone does not exit the planning session.** The nested loops — the user's
  iteration outside, the adversarial review inside — exit only on a fixpoint: one
  version of the plan that the user, the planner and the executor all stand
  behind at once. The outer loop ends only when the user *says* proceed, so a
  review that fixed blockers returns its changes to the user as a delta — their
  proceed attached to a version the review has since rewritten. User afterthoughts —
  there, or at any point in the handoff step before launch — reopen the iteration,
  and a material change re-enters the review with a fresh three-round budget. Only
  an AGREED on a plan the review did not touch exits straight to the handoff, because
  that version is exactly the one the user already said proceed on. The one exception is
  the user's override: when the review does not converge, the user settles the
  disagreement and their settlement is the exit — the user outranks both models —
  with the overruled
  objection recorded in the plan so phase 2 knows it was seen, not missed. A
  re-entry from the handoff step rebuilds whatever was already built there: the goal
  condition, the Handoff section, and a follow-up commit when the plan was already
  committed. README.md carries the Mermaid diagram of the loop nest.
- Phase 1 never enters plan mode. Not because plan mode blocks read-only probes (it
  does not — `kubectl get` and `grep` run fine there), but because the phase writes
  the plan file and spike files and runs verification that touches state.
- Phase 2 always runs with `--permission-mode auto` unless the user deliberately
  escalates; an execution session cannot answer permission prompts. Auto decides
  without asking in *both* directions, though — it also denies silently — so phase 1
  must run every prescribed command under that mode before prescribing it.
- **Phase 2 always runs with `--remote-control <plan-basename>`.** Decided 2026-09-04.
  It is the unattended phase, and Remote Control is what lets the user follow and
  steer it — including `/goal clear` — from claude.ai or the mobile app. The name is
  the plan's file name without `.md`, and it is never omitted: the flag's argument is
  optional, so a bare `--remote-control` directly before the prompt would consume the
  `/goal …` text as the session name. It is not a pre-flight check — a session whose
  Remote Control cannot connect starts anyway, says so, and does the same work
  unwatched — so "always" is enforced by the Handoff command carrying the flag and the
  launcher running the Handoff command. Phase 1 probes `claude auth status` for a
  claude.ai login and warns when there is none. The reviewer never gets the flag: it
  is a headless `-p` process, and the flag is interactive-only. The permission mode
  stays `auto` regardless — a phone can answer a prompt, but nobody is guaranteed to
  be holding it.
- Phase 2 opens with a pre-flight gate, and the gate is the reason model, effort and
  permission mode are settled in phase 1 step 2 rather than at handoff. The plan names
  all three literally; phase 2 reads its own back and compares. The gate also checks
  that a `/goal` naming the plan is driving the session — read from the last
  `goal_status` record in the transcript, per the facts below — because a launch
  that lost the prefix runs with no evaluator guarding its completion: it can stop
  half-done and nothing notices. A failure there is a blocked report in turn 1 —
  never an adaptation, never a run that starts anyway, because a wrong-model run
  looks fine for a while and a Stop hook offers no quiet way out later. The gate is
  instructed twice on purpose: the plan's Execution Protocol tells the execution
  session to run it, and the goal condition repeats the instruction — though never
  the `/goal` check as a clause of its own, which would be circular there — because
  the condition is the directive the
  session actually receives and the evaluator has to accept a turn-1 abort as
  terminal.
- **The step-2 questions are an interview, not a free-form prompt.** The missing
  handoff parameters are collected in a single `AskUserQuestion` call — one question
  per missing parameter (model, effort, permission mode, ticket: at most four, the
  tool's exact capacity), recommended option first and marked. Options are answered
  in a keystroke where a composed reply invites the partial answer that leaves a
  parameter unsettled; the tool's "Other" field still takes a ticket key, URL, or
  full model ID as free text. Parameters already on the command line are not
  re-asked.
- **The ticket is asked for on every run**, unconditionally, and the answer may be
  "none". Given one, phase 1 reads it and turns it into a requirements conversation
  whose outcome is the plan's `## Requirements` table. That table records every
  requirement including the dropped ones, each naming its source, because its real job
  is to stop phase 2 from implementing a requirement the user decided against — the
  ticket key and the spec path are in the plan's frontmatter and the key is in the
  commit prefix, so an execution session can and will read the sources itself. The
  standing rule the table carries: where the plan and a source disagree, the plan wins.
- **A spec is an input, never an output.** `/pdca:plan` receives specifications; it
  does not write them, and there is no `/pdca:spec`. A spec file, a URL or a paste is a
  requirements source beside the ticket and goes through the same conversation, with
  the same table. It is not interviewed for — the interview is at the tool's four-question
  capacity, and a spec the user has is one they hand over. The plan stays self-contained
  regardless: it condenses every source into the Requirements table, because phase 2 may
  not be able to reach a Confluence page and a plan that only points at a spec has lost
  the property the design rests on. A path on the command line is told apart by the
  file's frontmatter: `plugin: pdca` is a plan to reopen, anything else is a source.
- **A source is a request, not a contract.** The plan may deviate from a ticket or a
  spec, and the non-functional half is where it usually should — a named mechanism, a
  library, a split into phases, a performance number written before anything was
  verified. Phase 1 is the step that verifies things, so it proposes the deviation with
  evidence. What it may not do is decide alone in either direction: the last word
  belongs to the user, not to the source's author and not to the model, and every
  deviation lands in the table with its reason. The rule used to say "not a
  specification"; it was reworded when specs became inputs.
- **Frontmatter, not prose, for the plan's data.** The plan opens with YAML
  frontmatter — the header table of 0.5.x is gone; `plan-template.md` owns the keys. The split is data versus
  prose: provenance (`plugin`, `plugin_version`, `plugin_url` — copied from
  `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`), `created`, `status`, the
  `executor` block in the literal spellings the pre-flight compares, `sources`,
  `ticket` (or `none`), `plan_file`, `work_repo` when it differs, and the handoff-time
  fields `branch`, `closeout_push`, `permalink`. Instructions such as "do
  not create a branch" are sentences in sections, never keys. Provenance earns its
  place because the plan self-destructs: a reader at the permalink weeks later learns
  what wrote the file, and a reopen learns which template did. GitHub renders the
  block as a table, so the human reader loses nothing.
- **`status` is the only state the plan file records**, and it is read, never
  inferred. `drafting` → `handed-off` (phase 1, with the Handoff section) →
  `executing` (phase 2, when the gate passes) → `done` (before the preservation
  commit, so the permalinked final state says so) or `blocked` (with the blocked
  report, committed together). Reopening dispatches on it: continue, re-verify, ask
  before touching a run in progress, consume the report first, or refuse a stray
  `done`. In-conversation states —
  proceed given but not yet reviewed, AGREED but changed — stay out of the file on
  purpose: they do not survive a session and the file records only what does.
- **Ticket content is untrusted input.** It is written by other people and read by an
  agent that acts on text, so it is treated as claims about the work to raise with the
  user, never as instructions. This is stated in `references/jira.md` rather than left
  implicit.
- **Git is a requirement and the plan is always tracked.** Decided 2026-09-02. The
  planning session checks for a repository before writing anything and stops without
  one; the plan is committed at handoff and its final state is committed again, on its
  own, before removal — for every plan. There is no untracked path and no commit
  question; the only tracking question is whether the closeout pushes, asked only with a
  ticket. Git history is the run record; Jira cannot hold the file, so the ticket gets a
  link into that history.
- **A new branch is opt-in, and phase 1 makes it.** The default is the branch planning
  happened on. When the user asks — in the goal text or while iterating, never inferred
  from a ticket or a repository's habits — the planning session creates the branch at
  handoff, before the commit carrying the Handoff section, so the plan lands on it and
  `branch` names it. Phase 2 never creates a branch and the pre-flight treats a missing
  branch as a failed check, which makes the executor's most common unwanted initiative
  impossible by construction rather than merely forbidden. Three consequences are
  written down: the handoff says which branch it left the checkout on; a new branch is
  pushed at handoff with `git push -u`, which sets the upstream phase 2's plain push
  relies on; and reopening a plan on such a branch brings the branch up to date with
  its base as part of re-verification, since the plan is exactly as stale as the
  branch. The plan-on-main alternative was considered and rejected on 2026-09-02: a
  protected main cannot take the handoff commit, main would carry a copy of the plan
  whose status lies once the run moves on, and deferring branch creation to launch puts
  it either in a fragile Handoff command or back into phase 2.
- **Phase 2 commits as it goes** — a task, or a coherent slice of one, per commit, on
  the branch the plan names. This is the default, not an option a plan enables:
  reaching for `/pdca:plan` at all says the work is non-trivial, and multiple commits
  are the ordinary practice for non-trivial work. Decided 2026-09-03: one work commit
  at the end was the protocol's unstated assumption, and it made every interruption or
  block lose everything since launch. Per-task commits are what make a resume, a
  rollback and a blocked report's tree listing mean anything; a plan may only say which
  tasks land together, never that everything waits for the end.
- **Phase 2 runs the Closeout immediately before the plan self-destructs**, for every
  plan: the final plan is committed on its own — the preservation commit — and only then
  is the file removed in a separate follow-up commit; with a ticket, the preservation
  commit is pushed when the plan says so and a comment linking to the plan file *at that
  commit* is posted in between. Three ordering constraints carry the design: the
  preservation commit is separate from the work commit because the final Run Log entries
  are written afterwards; the deletion is a separate commit after it, so the linked
  commit stays the last one where the file exists; and a failed closeout leaves the file
  in place and ends in a blocked report. The closeout is in the plan's Acceptance
  Criteria and in the goal condition, because a step the evaluator does not check is a
  step an execution session can skip and still be judged done.
- **The permalink template is worked out and proved in phase 1.** The plan carries the
  host's permalink form with everything but the SHA filled in, and phase 1 proves it by
  committing and pushing the plan and handing the user the resulting URL to open. A
  `curl` is not proof: a private host answers 404 for a wrong template and for an
  unauthenticated request alike. With no remote at all, the comment falls back to the
  SHA and a `git show` line.
- **Whether the closeout pushes is the user's call**, and it is the one question step 8
  asks, and only when a ticket is named — there is no commit question, since the plan is
  always tracked.
  Recommend pushing, because an unpushed preservation commit makes the comment's link
  dead; accept a no, because an unattended session writing to a shared branch is a real
  decision. `git push --dry-run` is probed in phase 1 either way.
- **The comment channel must be probed in phase 1** under phase 2's permission mode: an
  MCP server needing interactive auth, or an `auto` classifier declining an MCP write,
  fails at the moment of use. The MCP server's `addCommentToJiraIssue` is the ordinary
  channel; the REST fallback is probed with the read-only `mypermissions` check for
  `ADD_COMMENTS`. With no channel, the user picks a fallback — a credential, or keeping
  the preservation commit and dropping the comment — and the choice is written into the
  plan, so an absent closeout section can be told from a forgotten one.
- **The blocked report is a message; the Run Log is the record.** Decided 2026-09-03
  after the art-backend-nt runs left two reports behind for good and one plan had to
  invent the rule itself. A blocked run commits the plan and the report together and
  leaves only work short of a commit boundary uncommitted; the report lists the tree and ends with `Next: relaunch`
  or `Next: reopen`. Whichever session picks the plan up next — a relaunch's pre-flight
  before its first check, or a reopen — folds the report into the Run Log and deletes
  it, so a report never outlives the pick-up and a finished run has none. The goal's
  hatch requires a report *written in this session*, so a leftover one cannot end a
  relaunch in turn 1 even if the consuming step is missed — that trap was real. A
  report written on an estimate rather than a check that ran is retracted in the same
  session. A boundary stop — a run that cannot finish everything and stops clean at a
  task boundary — is the same mechanism with `Next: relaunch`; the Run Log's
  started-lines tell the resume which task was cut mid-way.
- **The closeout writes a comment, nothing else.** No transition, no field edits, no
  worklog; and a blocked run says nothing on the ticket by default, because an
  unattended failure is for the developer to triage before it notifies everyone watching
  the work item.
- **The closeout is never re-asked.** Naming the ticket in the step-2 interview *is*
  the decision about what happens to the finished plan: commit it, comment the outcome
  with a link to it. Neither phase may end by asking the user what to do with the plan
  or the ticket — phase 1 not at handoff (its only question there is whether the
  closeout pushes), phase 2 not at the end of the run (its only alternative is the
  blocked report). The legitimate closeout questions are about mechanism — the push, and
  the channel fallback when no comment channel probes clean — never about whether to
  close out. This rule exists because a planning session ended by asking exactly
  that question with the ticket named from the start — a settled decision re-asked.
- The goal condition is capped at 4000 characters, is single-quoted into a shell
  argument (so: no apostrophes, no backticks), and always carries a blocked-report
  escape hatch so an impossible check terminates instead of looping.
- **No turn or time cap in the condition.** Decided 2026-09-03. The `/goal` docs
  suggest one, and it was considered: a turn is one stop attempt of unbounded size, so
  a cap would count evaluator rejections, and real finished runs have gone into the
  hundreds. This is a tool for complex work, and any number would be a blind guess that
  ends a healthy run. The runaway case is bounded by the blocked-report hatch, which the
  session reaches when a check genuinely cannot pass, and by the user's `/goal clear`.
- The plan file self-destructs at the end of phase 2, always in its own commit after
  the preservation commit — never in the work commit and never with a bare `rm`; when
  the plan lives in a different repository than the work, both commits go to the plan's
  repository.
- **`/goal <plan-path>` alone cannot launch phase 2**, however self-sufficient the
  plan. Three documented reasons: the evaluator is the small fast model and calls no
  tools, so a bare path gives it nothing to judge and no way to open the file; the plan
  deletes itself before the final judgement; and the escape hatch has to be in the
  condition text or a blocked run cannot stop. So the full condition inlines the
  criteria, the Handoff section carries the full command plus a short form (path,
  protocol, closeout order, hatch — no criteria, and it says what that costs), and
  `/pdca:execute` runs the Handoff block from the plan path. Phase 2 still needs no
  plugin: the launcher is for the human launching, not for the session launched.
- **The launcher is a command, not a script and not a README shell function.** Decided
  2026-09-04, replacing the `pdca-run` function the README carried. A plugin cannot put
  anything on `PATH`, and its cache directory is versioned — this repo bumps the version
  on every commit — so a script would need a hand-made symlink re-pointed after each
  update; the README function was the same logic with no status dispatch and a copy for
  every user to keep current. A command is installed with the plugin and updated with
  it. The user's own suggestion; the executable-plan-file variant was rejected because a
  polyglot plan loses GitHub rendering at the permalink, the frontmatter-first
  convention the reopen relies on, the `-plan.md` rule, and puts identical launcher
  code into every plan.
- **`/pdca:execute` launches a new background process; it never works the plan in the
  session it is typed into.** Two verified facts force this (below): a command body
  cannot set a goal, and the session at hand is not the one the plan was written for.
  The skill reads `status` and dispatches — `handed-off` launches; `executing` and
  `blocked` with `Next: relaunch` resume, after `claude agents --json` shows no live
  background session in this repository; `drafting`, `Next: reopen` and `done` refuse —
  then takes the Handoff block, checks that it is one `claude` (or `cd … && claude`)
  command whose `/goal` names this plan, inserts `--remote-control <basename>` into a
  pre-0.8.0 plan that lacks it, and runs it with `--bg` and `--name <basename>` added
  directly after `claude`. `--bg` is what makes a launch possible from inside a session
  at all: it detaches, returns an id, and the positional `/goal …` runs as the new
  process's first turn. The block is executed, so its shape is checked first: a plan is
  a file in a repository, and the launcher must not `eval` arbitrary text found under a
  heading. Step 8 of the `plan` skill follows the same skill for its launch offer, so
  there is one launch procedure with two entry points. The launcher does not re-verify
  the plan — it reports the plan's age and the commits since, and the reopen owns the
  freshness check.
- Before handoff, the plan is reviewed by a fresh `claude -p` process at phase 2's
  model and effort, in a loop capped at three rounds. The reviewer runs with
  `--permission-mode plan` so it is read-only by construction, and runs in the
  background — a foreground reviewer at xhigh effort outlives the 10-minute tool
  timeout. Each round returns exactly one of two results: VETOED with at least one
  blocker, or AGREED with no blockers and any number of nits; the verdict line follows
  from the Blockers section, and the prompt says so. A round with no verdict line, or
  one that contradicts its own Blockers section, is inconclusive and does not consume
  one of the three. A disputed blocker is answered in the plan text, never only in the
  round report, because the next round is a cold read that never sees the report.
  Nits applied as the reviewer worded them do not reopen the review — the reviewer has
  already classified them as not changing what it would do — but they reach the user
  as a delta like any other change; a fix beyond the nit's wording is material and
  re-enters review.
- The handoff command is written into the plan's own `## Handoff` section before it
  is printed, so it survives the gap between phases. The plan is committed only
  *after* the handoff is in it — committing earlier puts a plan into history without
  its own launch command and leaves phase 2 facing a dirty tree.
- The `/goal` condition never makes a present-tense claim about the plan file, since
  the same condition orders that file deleted. Claims are phrased as what happened in
  the session, which is what the evaluator can still see.
- **Phase 1 progress reaches the status line through a status file, never directly.**
  Plugins cannot ship a `statusLine` — a plugin's own `settings.json` supports only
  `agent` and `subagentStatusLine` — and `/goal`'s `◎` indicator is hardcoded in the
  harness, so parity with it is not available. Instead the skill has the planning
  session maintain `~/.cache/claude-pdca/<session-id>.status` (one line naming the current
  step — `verify`, `iterate`, `review 2/3`, `handoff` — never its number, because the
  loops re-enter earlier steps; updated on step transitions and review rounds,
  leftovers swept after seven days, deleted when the phase ends), and README.md documents the opt-in status-line segment that
  displays it. When nothing reads the file, writing it is harmless — which is why the
  skill writes it unconditionally rather than asking whether the user's status line
  is wired up. The segment sanitizes with `tr -d '[:cntrl:]'`, not `[:print:]`: the
  status text carries UTF-8 em-dashes, and stripping to printable ASCII would mangle
  them, while control characters are the actual injection surface (`\e`, `\n`).

## Facts About the Status Line This Plugin Depends On

From the Claude Code documentation (`statusline.md`, `plugins.md`, `goal.md`),
checked 2026-08-30:

- `statusLine` is user- or project-settings only; there is no plugin mechanism for
  it. `/goal`'s `◎ /goal active` indicator and its Ctrl+O status view are built into
  the harness, not implemented via `statusLine`.
- The status-line command receives JSON on stdin including `session_id` and
  `transcript_path`; there are **no goal-state fields** in that JSON.
- It re-runs on every new assistant message (debounced at 300ms), on permission-mode
  changes, and optionally on a `refreshInterval` timer (minimum 1s) — so a file the
  skill updates at step transitions is re-read without any timer.
- `CLAUDE_CODE_SESSION_ID` (see the session-introspection facts below) holds the same
  session id the status-line command receives as `session_id`, which is what lets the
  writer and the reader agree on the file path.

## Facts About the Atlassian MCP Server This Plugin Depends On

Verified by inspecting the available toolset on 2026-08-27:

- The Jira tools include `getJiraIssue`, `getAccessibleAtlassianResources` (for the
  `cloudId`), `searchJiraIssuesUsingJql`, `addCommentToJiraIssue`, `editJiraIssue`,
  `addWorklogToJiraIssue` and `transitionJiraIssue`.
- There is **no attachment upload tool and no way to link a repository file from the
  issue**, which is the entire reason the closeout preserves the plan in git and posts a
  permalink instead. If a future release adds an attachment tool, that becomes a second
  channel worth having and `references/jira.md` should say so — the git permalink still
  earns its place, since it survives independently of the ticket.
- `acli` and `jira` are not on `PATH` in a default environment, and no Jira credentials
  are exported by default.

The REST endpoints named in `references/jira.md` — the comment `POST` and
`mypermissions` — come from Atlassian's documented API, not from a call made here. The
same goes for the permalink forms in that file's host table. That is exactly why the
skill prescribes probing them in phase 1 rather than trusting them.

## Facts About Session Introspection This Plugin Depends On

Verified against Claude Code 2.1.247. Most of it from a fresh session's first turn —
`claude -p --model sonnet --effort low --permission-mode auto`, asked to report these
back — and the rest as each bullet says. The pre-flight gate these facts support was
exercised end to end in real `/goal` sessions on 2026-08-27 in four cases — a wrong-model
launch, a wrong-branch launch, a denied privilege probe, and a matching launch — which
confirmed the model and effort checks and corrected the permission-mode one below.

- `CLAUDE_EFFORT` holds the session effort level; `CLAUDE_CODE_SESSION_ID` holds the
  session id.
- The session transcript is `~/.claude/projects/<cwd-slug>/<session-id>.jsonl`. It
  records the permission mode in one of two shapes, and in one case neither: an
  interactive session writes a standalone `{"type":"permission-mode","permissionMode":"…"}`
  record per turn; a headless session started with a *plain* prompt carries
  `"permissionMode":"…"` as a field on its prompt record, beside `"promptSource":"sdk"`;
  and a headless session whose prompt is a **slash command** records neither. That last
  case was the one that mattered while the handoff launched headless —
  `claude -p … "/goal …"`. Verified on 2026-08-27: two plain-prompt headless sessions
  carry the field, while the six `/goal`-prompt sessions of the end-to-end run carry no
  trace of it. Since 2026-09-04 the handoff launches interactively, with
  `--remote-control`, and that shape does write the record: observed 2026-09-04 at
  2.1.260, a `--bg --remote-control '/goal …'` launch carried one `permission-mode`
  record with the launch mode. So the transcript answers for the handoff as now
  launched; the argv fallback stays for sessions started some other way.
- When the transcript is silent, the launch flags are the next source —
  `ps -o args= -p "$PPID"`, walking up the ancestry until the argv starts with `claude`,
  and matching `--permission-mode <mode>` or `--dangerously-skip-permissions`. This
  answers only when the mode came from an explicit flag: a session started without one,
  or switched at runtime, shows nothing or shows something stale. (In the session that
  wrote this, the parent argv is `claude --allow-dangerously-skip-permissions -c` while
  the mode is `bypassPermissions` — set at runtime, and absent from argv.) When neither
  source answers, the mode is **unverifiable**: record it as such and treat it under the
  degradation rule in `preflight.md`. Never infer a value and never pass the check
  silently.
- Two kinds of transcript record share the type `goal_status`: a sentinel record
  (`"sentinel":true`) is written when a goal is set (`met:false` — for a
  `/goal`-launched session, alongside its first prompt) and again when it is
  explicitly cleared (`met:true`, observed in four transcripts spanning
  2.1.221–2.1.238 — so `/goal clear` fails the last-record check correctly); and
  the evaluator writes one per judged stop attempt (a `reason` field, no
  `sentinel`), `met:false` while the goal holds
  the session, `met:true` when it is met and auto-clears. Their number is unbounded
  (one goal at 2.1.241 left 370 records: one sentinel, 369 evaluator) and they
  survive resumption, so neither presence nor count proves anything; the pre-flight
  gate reads the **last** record and requires `met:false` with a condition naming
  the plan. Verified 2026-08-28 against transcripts spanning 2.1.221–2.1.247: the
  two still-inspectable `/goal`-prompt transcripts of the 2026-08-27 end-to-end
  runs, both 2.1.247 (the
  other four ran in scratch project directories that have since been removed), carry
  the sentinel from turn 1 — the finished run closes with `met:true`, the abandoned
  one stays `met:false`; plain-prompt headless and interactive non-goal transcripts
  carry none; and a resumed session (2.1.233→2.1.234) in another project carries two
  full goal cycles, including a no-goal stretch where a count-based check would pass
  wrongly. The absence of any record in a plain-prompt session, and the `met:true`
  tail of a finished or cleared goal, are what let the pre-flight gate fail a
  phase 2 that is not driven by its plan's `/goal`. The Stop hook itself appears to
  survive a resume: two resumed sessions (2.1.222→2.1.223, 2.1.246→2.1.247) carry
  further evaluator records for the same goal after the resume — so a resumed
  session whose last goal is still open appears to be genuinely guarded by it, which
  narrows the resume caveat without removing it. The check is exact for the fresh
  launch the Handoff section prescribes and only presumptive for a resumed session —
  an abandoned goal leaves a trailing `met:false` forever — which `preflight.md`
  states as the fresh-launch assumption.
- The model check is unaffected by all of this: every `{"type":"assistant"}` record has
  `message.model` as its first key — which is why grepping the last assistant line for
  the first `"model":"…"` match is safe, and it worked in every session tested.
- There is no environment variable for the model, so the transcript (or the session's
  own context) is the only source.
- In an interactive session a `permission-mode` record is written every turn and
  reflects the mode *now*, so a session switched mid-run records the new value from that
  turn on — which is why the check reads the last record rather than the first.
- `--permission-mode` accepts `acceptEdits`, `auto`, `bypassPermissions`, `manual`,
  `dontAsk`, `plan`. Two recorded spellings are observed directly: `auto`, and
  `bypassPermissions` after a session was switched into bypass mode. That
  `--dangerously-skip-permissions` selects that same mode is from the CLI help, not
  from a transcript.

These are internal formats, not public API. If a release moves the transcript, the
identity check degrades to self-report — which `references/preflight.md` already
tells the execution session to fall back to. The snippet itself is in two places:
that file and `skills/plan/references/plan-template.md`.

## Facts About Remote Control This Plugin Depends On

From `claude --help` at Claude Code 2.1.260, `claude auth status`, and the Remote
Control and CLI reference pages of the documentation, checked 2026-09-04:

- `--remote-control [name]` (alias `--rc`) starts an **interactive** session with Remote
  Control enabled; `claude remote-control` is a different thing — server mode, serving
  sessions to several remote connections — and the plugin does not use it. `-p` is
  non-interactive, so the two are not combined; the handoff carries no `-p`.
- The `[name]` argument is optional and is taken from the next token when that token
  does not start with `-`. This is why the handoff always names the session: a bare
  flag placed before the `/goal …` prompt would swallow the prompt. `--name <name>` and
  `--remote-control-session-name-prefix <prefix>` (env
  `CLAUDE_REMOTE_CONTROL_SESSION_NAME_PREFIX`, default hostname) exist as well; the
  plugin uses the flag's own argument because it removes the hazard by construction.
- Requires a claude.ai subscription login (Pro, Max, Team, Enterprise). Not available
  with an API key, Bedrock, Vertex or Foundry, behind a custom `ANTHROPIC_BASE_URL`, or
  when `DISABLE_TELEMETRY`, `DO_NOT_TRACK`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`
  or `DISABLE_GROWTHBOOK` is set. `claude auth status` prints the login as JSON by
  default — `"authMethod": "claude.ai"`, `"apiProvider": "firstParty"` — which is the
  phase 1 probe.
- Failure behavior differs by form: the flag starts the interactive session locally and
  shows a Remote Control failure notification shortly after launch; server mode exits.
  So a handoff on an account that cannot use Remote Control still runs, unwatched.
- One remote session per interactive process. The local `claude` process is the
  session: closing the terminal takes it offline, and it retries the connection
  indefinitely while the process lives. Permission prompts and `AskUserQuestion`
  dialogs forwarded to a remote device stay open until answered.
- `remoteControlAtStartup` in `settings.json` and the `/remote-control` (`/rc`) slash
  command are the other ways to turn it on; the plugin relies on neither, because the
  Handoff command has to work on a machine configured however it is.
- `claude --bg` prints `backgrounded · <id>` and the `claude attach|logs|stop <id>`
  lines; `claude agents` needs a TTY, `claude agents --json` does not and lists every
  session with `pid`, `cwd`, `kind` (`interactive` or `background`), `startedAt`,
  `sessionId`, `name`, `status` (`busy`/`idle`) and, for background sessions, `id` and
  `state` (`done` once finished). A background session's `name` is generated from the
  conversation unless `--name` sets it — which is why the launcher passes `--name`.
  `claude stop <id>` then `claude rm <id>` remove one; a finished session lingers until
  they are run. Observed 2026-09-04 at 2.1.260.
- **Observed 2026-09-04 at 2.1.260**, with
  `claude --bg --model haiku --effort low --permission-mode plan --remote-control <name> '/goal …'`
  in a scratch repository: the positional `/goal …` prompt ran as the first turn — the
  sentinel was written, the evaluator judged the goal and met it in one turn — Remote
  Control connected and printed `/remote-control is active · … https://claude.ai/code/session_…`,
  and the transcript carried a `permission-mode` record, so the gate's transcript check
  works for the interactive launch. `--bg` returned at once with a short id for
  `claude attach`, `logs`, `stop` and `rm`; the process outlived the launching shell and
  stayed alive, idle, after the goal was met until stopped. Two things it did not
  settle: `claude agents --json` showed an auto-generated session name rather than the
  one given to `--remote-control` (that listing is what `--name` sets), and the name on
  the claude.ai side was not checked. Also seen: the `haiku` alias produced a session
  whose transcript said `claude-sonnet-5` — exactly the wrong-model launch the gate
  exists to catch.

## Facts About `/goal` This Plugin Depends On

Verified against Claude Code 2.1.247:

- `/goal <condition>` installs a session-scoped Stop hook; a separate evaluator
  judges the condition after each turn and blocks stopping until it holds, then
  auto-clears. `/goal clear` stops early; bare `/goal` shows status.
- The evaluator is Claude Code's small fast model — Haiku by default,
  `ANTHROPIC_DEFAULT_HAIKU_MODEL` to change it, which also changes every other use of
  that model. It receives the condition text and the conversation and **calls no
  tools**: it cannot read files or run commands, so a condition has to be judgeable
  from what the session surfaced. Checked against `goal.md` on 2026-09-02. This is why
  `/goal <plan-path>` cannot work and why the criteria are inlined.
- The condition is capped at 4000 characters and is handed to the session as its
  directive, with instructions not to pause to ask the user.
- There is no `--goal` flag; `/goal …` as the positional prompt works in both
  interactive and `-p` mode. A command body **cannot** set a goal: verified 2026-09-04
  at 2.1.260 — a project command whose body was a single `/goal …` line expanded into
  the prompt as text, the model answered it, and the transcript holds no `goal_status`
  record. Only the harness sets goals: a user typing `/goal`, or `/goal …` as the
  positional prompt of a new process — which is why a launch is always a new process.
- Requires a trusted workspace; unavailable when `disableAllHooks` or
  `allowManagedHooksOnly` is set.
- Works non-interactively, so it can be passed as the positional prompt to `claude`.

These facts are stated in four places. If a future Claude Code release changes any of
them, all four need updating:

1. `skills/plan/SKILL.md`, section "What `/goal` actually does" — the copy the
   model actually loads.
2. `skills/plan/references/goal-condition.md`, the opening section.
3. `README.md`, section "Requirements".
4. This file, above.
