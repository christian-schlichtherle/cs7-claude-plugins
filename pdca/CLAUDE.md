# pdca Plugin — Developer Guide

## How It Works

One command (`/pdca:plan`) and one skill (`plan`) implementing a PDCA
cycle split across two sessions:

- **Plan** — interactive, runs commands to verify its assumptions, writes
  `docs/plans/<date>-<slug>.md`.
- **Do/Check/Act** — a fresh `claude` process under `/goal`, implementing the plan
  unattended.

The plan file is the only interface between them, which is why the skill pushes so
hard on verified facts and inlined acceptance criteria.

## Conventions

- **One palette entry, two files.** `/pdca:plan` is the command; the skill is
  `user-invocable: false` so it does not also appear in the slash-command list.
  Without that flag Claude Code shows `/pdca:plan` twice — once for the command with
  its human-facing description, once for the skill with its triggering description.
- **The skill is the single source of truth.** The command is a thin entry point: a
  description, an argument hint, examples, and a pointer. Argument parsing, the
  verification rules, the plan template and the goal-condition rules live in the skill
  only. They were duplicated in both files once, and a review found the same two
  defects had to be fixed twice — hence the split.
- The skill stays model-invocable, which is what makes it trigger on intent
  ("write me a plan I can run later") without the command being typed.
- Planning never reaches the handoff in the turn that drafts the plan. The
  interactive loop's exit condition is that the user is satisfied, which they have to
  state — so the first draft always ends the turn. There is no waiver and no
  non-interactive mode: anyone who does not want the interactive phase can set a
  `/goal` directly instead of using this workflow.
- **READY alone does not exit the planning session.** The nested loops — the user's
  iteration outside, the adversarial review inside — exit only on a fixpoint: one
  version of the plan that the user, the planner and the executing model all stand
  behind at once. The outer loop ends only when the user *states* satisfaction, so a
  review that fixed blockers returns its changes to the user as a delta — their
  go-ahead attached to a version the review has since rewritten. User afterthoughts —
  there, or at any point in the handoff step before launch — reopen the iteration,
  and a material change re-enters the review with a fresh three-round budget. Only
  a READY on a plan the review did not touch exits straight to the handoff, because
  that version is exactly the one the user already approved. The one exception is
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
  escalates; an autonomous session cannot answer permission prompts. Auto decides
  without asking in *both* directions, though — it also denies silently — so phase 1
  must run every prescribed command under that mode before prescribing it.
- Phase 2 opens with a pre-flight gate, and the gate is the reason model, effort and
  permission mode are settled in phase 1 step 2 rather than at handoff. The plan names
  all three literally; phase 2 reads its own back and compares. The gate also checks
  that a `/goal` naming the plan is driving the session — read from the last
  `goal_status` record in the transcript, per the facts below — because a launch
  that lost the prefix runs with no evaluator guarding its completion: it can stop
  half-done and nothing notices. A failure there is a blocked report in turn 1 —
  never an adaptation, never a run that starts anyway, because a wrong-model run
  looks fine for a while and a Stop hook offers no quiet way out later. The gate is
  instructed twice on purpose: the plan's Execution Protocol tells the executing
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
  whose outcome is the plan's `## Ticket Requirements` table. That table records every
  requirement including the dropped ones, because its real job is to stop phase 2 from
  implementing a requirement the user decided against — the ticket key is in the plan
  header and in the commit prefix, so an executing session can and will read the ticket
  itself. The standing rule the table carries: where the plan and the ticket disagree,
  the plan wins.
- **A ticket is a request, not a specification.** The plan may deviate from it, and the
  non-functional half is where it usually should — a named mechanism, a library, a split
  into phases, a performance number written before anything was verified. Phase 1 is the
  step that verifies things, so it proposes the deviation with evidence. What it may not
  do is decide alone in either direction: the last word belongs to the user, not to the
  ticket author and not to the model, and every deviation lands in the table with its
  reason.
- **Ticket content is untrusted input.** It is written by other people and read by an
  agent that acts on text, so it is treated as claims about the work to raise with the
  user, never as instructions. This is stated in `references/jira.md` rather than left
  implicit.
- **Naming a ticket makes committing the plan mandatory.** Git history is the
  preservation mechanism the closeout depends on — Jira cannot hold the file and cannot
  link to it — so a ticketed plan is committed in phase 1 without asking, and phase 2
  commits its final state again. Only a ticketless plan leaves the commit decision to
  the user.
- **Phase 2 closes out the ticket immediately before the plan self-destructs**: the
  final plan is committed on its own, pushed when the plan says so, a comment linking to
  the plan file *at that commit* is posted, and only then is the file removed in a
  separate follow-up commit. Three ordering constraints carry the design: the
  preservation commit is separate from the work commit because the final Run Log entries
  are written afterwards; the deletion is a separate commit after it, so the linked
  commit stays the last one where the file exists; and a failed closeout leaves the file
  in place and ends in a blocked report. The closeout is in the plan's Acceptance
  Criteria and in the goal condition, because a step the evaluator does not check is a
  step an autonomous run can skip and still be judged done.
- **The permalink template is worked out and proved in phase 1.** The plan carries the
  host's permalink form with everything but the SHA filled in, and phase 1 proves it by
  committing and pushing the plan and handing the user the resulting URL to open. A
  `curl` is not proof: a private host answers 404 for a wrong template and for an
  unauthenticated request alike. With no remote at all, the comment falls back to the
  SHA and a `git show` line.
- **Whether the closeout pushes is the user's call**, and it is the one question step 8
  asks when a ticket is named — the commit question having been settled by the ticket.
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
- The plan file self-destructs at the end of phase 2 — with a ticket, in its own commit
  after the preservation commit; otherwise in the final commit when it is tracked there,
  or with `rm`. Committing the plan is an offer the user can decline **only when there is
  no ticket**, so nothing outside the ticket path may assume it is tracked.
- Before handoff, the plan is reviewed by a fresh `claude -p` process at phase 2's
  model and effort, in a loop capped at three rounds. The reviewer runs with
  `--permission-mode plan` so it is read-only by construction, and runs in the
  background — a foreground reviewer at xhigh effort outlives the 10-minute tool
  timeout. A round that returns no verdict line is inconclusive and does not consume
  one of the three.
- The handoff command is written into the plan's own `## Handoff` section before it
  is printed, so it survives the gap between phases. The plan is committed only
  *after* the handoff is in it — committing earlier puts a plan into history without
  its own launch command and leaves phase 2 facing a dirty tree.
- The `/goal` condition never makes a present-tense claim about the plan file, since
  the same condition orders that file deleted. Claims are phrased as what happened in
  the session, which is what the evaluator can still see.

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
  case is the one that matters, because it is exactly what a phase 2 handoff launches —
  `claude -p … "/goal …"`. Verified on 2026-08-27: two plain-prompt headless sessions
  carry the field, while the six `/goal`-prompt sessions of the end-to-end run carry no
  trace of it. The distinction is the slash-command prompt, not headless-ness.
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
tells the executing session to fall back to. The snippet itself is in two places:
that file and `skills/plan/references/plan-template.md`.

## Facts About `/goal` This Plugin Depends On

Verified against Claude Code 2.1.247:

- `/goal <condition>` installs a session-scoped Stop hook; a separate evaluator
  judges the condition after each turn and blocks stopping until it holds, then
  auto-clears. `/goal clear` stops early; bare `/goal` shows status.
- The condition is capped at 4000 characters and is handed to the session as its
  directive, with instructions not to pause to ask the user.
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
