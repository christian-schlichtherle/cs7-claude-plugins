---
branch: main
closeout_push: true
created: 2026-09-12
executor:
  effort: high
  model: claude-opus-5
  permission_mode: auto
permalink: https://github.com/christian-schlichtherle/cs7-claude-plugins/blob/<sha>/2026-09-12-review-command-plan.md
plan_file: 2026-09-12-review-command-plan.md
plugin: pdca
plugin_url: https://github.com/christian-schlichtherle/cs7-claude-plugins
plugin_version: 0.11.0
review_rounds: 10
sources: []
status: handed-off
ticket: none
---

# Extract the adversarial review loop into a `review` skill and a `/pdca:review` command

## Goal

The adversarial review loop that `/pdca:plan` runs before its handoff — a fresh
`claude -p` process reading an artifact cold, in plan mode, returning VETOED with
blockers or AGREED with nits, fixed or answered in the artifact and re-read from
scratch until agreement or the round budget is spent — becomes a `review` skill with a `/pdca:review`
command, so that any deliverable a reader has to act on without asking its author
(a runbook, a spec, a README, an RFC) can be reviewed the same way. `/pdca:plan` then
uses that skill instead of its own `references/review-loop.md`.

`/pdca:plan` changes in exactly two ways the user decided on 2026-09-12, and in no
other. First, the loop's cap of three rounds becomes a **round budget** with a default of
ten, asked for in the step 2 interview the way the permission mode is, recorded in the
plan's frontmatter as `review_rounds`, and passed to the review skill; in practice
agreement has regularly taken more than three rounds. Second, the **user's override goes**:
the plan is a contract between the user, the planner and the executor, so a review that
does not converge leaves the plan a draft — the user edits it, raises the budget, or
stops — and never hands it off over the executor's objection. Everything else about the
loop is unchanged, and the plan makes that checkable rather than asserted: the review
skill owns only the loop's mechanics and a prompt *template* with slots; everything that
is an opinion — who is reading, what the artifact is called, what is exempt, what counts
as a blocker, what success means, what a gap costs, how a blocker the author disagrees
with is answered — is a slot filled from a *lens*; the plan skill supplies an *executor
lens* whose slots carry today's wording, so the assembled reviewer prompt is byte for
byte the prompt the plan skill sends today (acceptance criterion 3), and the step 7
paragraphs that decide what an AGREED exits to — the two AGREED bullets, the
afterthoughts rule and the fixpoint — stay verbatim (criterion 4). The review skill
returns to its caller; it never decides a handoff.

## Requirements

No table: this plan has no requirements source — no ticket and no spec. Every decision
below was settled with the user in the planning session on 2026-09-12.

## Verified Context

Each fact carries the command that established it. Run on 2026-09-12 against Claude Code
2.1.269, macOS, in this repository at commit `ebf5f58`.

- **Repository.** Top level `/Users/christian/projects/cs7-claude-plugins`, remote
  `origin https://github.com/christian-schlichtherle/cs7-claude-plugins.git`, branch
  `main`, HEAD `ebf5f58`, working tree clean:
  `git rev-parse --show-toplevel; git remote -v; git branch --show-current; git rev-parse --short HEAD; git status --porcelain`
- **Claude Code 2.1.269**, and every flag this plan uses exists: `--plugin-dir <path>`,
  `-p`, `--model`, `--effort`, `--permission-mode`, `--strict-mcp-config`, `--bg`, `--name`:
  `claude --version; claude --help | grep -E -- '--plugin-dir|--permission-mode|--effort|-p, --print|--strict-mcp-config|--bg|--name'`
- **Plugin version and the bump convention.** `pdca/.claude-plugin/plugin.json` says
  `0.11.0`. Every one of the last eight commits bumped it (0.5.3, 0.5.4, 0.6.0, 0.7.0,
  0.8.0, 0.9.0, 0.10.0, 0.11.0), a minor step for a structural change and a patch step
  for wording, and the frontmatter example at `pdca/skills/plan/references/plan-template.md:41`
  tracks it (0.9.0 at 200c191, 0.10.0 at 308ae4f, 0.11.0 now). A new command is a minor
  step: this plan ends at `0.12.0`.
  `for c in $(git log --format=%h -8); do printf '%s ' $c; git show $c:pdca/.claude-plugin/plugin.json | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])'; done; git show 200c191:pdca/skills/plan/references/plan-template.md | grep -n plugin_version`
- **Commit convention.** Imperative subject, an explanatory body, a `Bump pdca to X.Y.Z.`
  line when the version moves, and a `Co-Authored-By: <model> <noreply@anthropic.com>`
  trailer naming the model that made the commit. No ticket prefix.
  `git log -3 --format='%s%n%b%n---'`
- **What is installed.** `~/.claude/plugins/cache/cs7-claude-plugins/pdca/0.11.0` is
  identical to HEAD's `pdca/` except for its `.in_use` marker, and the marketplace
  `cs7-claude-plugins` is sourced from GitHub with `autoUpdate: true`. So sessions on
  this machine run 0.11.0 until the user pushes, and phase 2 tests the edited tree
  through `--plugin-dir`, not through the installed copy.
  `diff -rq pdca ~/.claude/plugins/cache/cs7-claude-plugins/pdca/0.11.0; python3 -c 'import json; print(json.load(open("/Users/christian/.claude/plugins/known_marketplaces.json"))["cs7-claude-plugins"])'`
- **`--plugin-dir` adds commands the installed plugin lacks, and a plugin command works
  as the `-p` prompt.** A scratch copy of `pdca/` with an extra `commands/probe.md`
  ("Reply with exactly the text PROBE-OK"), loaded into a headless session, listed
  `/pdca:execute`, `/pdca:plan`, `/pdca:probe`, no duplicates, one pdca plugin; and
  `"/pdca:probe"` as the prompt printed `PROBE-OK`.
  `claude -p --model haiku --effort low --permission-mode plan --strict-mcp-config --plugin-dir <copy> "List every slash command available to you whose name starts with /pdca. Print exact names only, one per line, nothing else."` and `… --plugin-dir <copy> "/pdca:probe"`
- **How a command reaches a sibling skill.** Three observations on 2.1.269, made with a
  scratch copy of `pdca/` loaded through `--plugin-dir` into headless Sonnet sessions.
  (1) `${CLAUDE_PLUGIN_ROOT}` is expanded when a command body is loaded: a
  `commands/probe.md` whose body was `Reply with … CMD-ROOT=[${CLAUDE_PLUGIN_ROOT}]`, run
  as `"/pdca:probe"`, printed `CMD-ROOT=[<the --plugin-dir path>]`. (2) It is expanded in
  a skill body too, and a `user-invocable: false` skill with no same-named command is
  listed as `pdca:<name>` and loads through the Skill tool: `Skill(pdca:probe-skill)`
  returned its body with the path filled in. (3) When a command and a skill share a name,
  `Skill(pdca:execute)` returns the **command** body — first line `# PDCA Execute` — so the
  skill file is reached only by a path the command body names, and `commands/execute.md`
  names none ("follow the `execute` skill"), which works only where the model already
  knows the plugin's directory. In the Bash environment the variable is unset
  (`echo "${CLAUDE_PLUGIN_ROOT:-unset}"`): the expansion happens in the Markdown the
  model is given, not in the shell. (4) `${CLAUDE_SKILL_DIR}` expands to the skill's own
  directory in a skill body: the same probe skill printed
  `SKILL-DIR=[<the --plugin-dir path>/skills/probe-skill]`. The documentation agrees where
  it speaks: the plugins reference ("Where Variables Are Expanded",
  code.claude.com/docs/en/plugins-reference) lists skill and agent content, "anywhere the
  placeholder appears"; the skills page lists `${CLAUDE_SKILL_DIR}` among the placeholders
  and says `user-invocable: false` leaves a skill invocable by Claude; what a same-named
  command and skill resolve to is undocumented, so observation (3) is the fact.
  Consequence: `commands/review.md` and the plan skill's pointers name
  `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md`, the review skill names its own files as
  `${CLAUDE_SKILL_DIR}/references/…`, and a body that somehow reached the model unexpanded
  falls back to paths relative to the `SKILL.md` actually read — never to the installed
  cache, which may be an older version (it is `0.11.0` while criterion 6 loads `./pdca`).
- **A headless Sonnet session under `auto` can do everything the loop needs.**
  `claude -p --model sonnet --effort low --permission-mode auto --strict-mcp-config` recorded
  `"permissionMode":"auto"` in its transcript and, without a prompt, touched and removed a
  file in the repository, wrote to a `mktemp -d` directory using the literal path a previous
  call had printed, wrote, read and removed `/tmp/pdca-probe-n.txt`, ran a Bash call with
  `run_in_background` and waited for it (`BG-DONE`), and spawned
  `claude -p --model haiku --effort low --permission-mode plan --strict-mcp-config "…"` (`INNER-OK`).
  Fifty seconds. It was launched from an `auto` session, so the classifier allows that
  launch shape. This is the harness shape for criterion 6.
- **Under `--model haiku`, `--permission-mode auto` is unavailable.** A
  `claude --bg --name pdca-probe-L --model haiku --effort low --permission-mode auto …`
  session printed `auto mode unavailable for this model`, switched to manual mode, and its
  first Bash call (`claude -p …`) sat at `This command requires approval`; four headless
  Haiku sessions started with `--permission-mode auto` refused every file mutation,
  including an in-repo `touch`. Consequence: the harness in criterion 6 runs on Sonnet;
  the reviewer inside it runs Haiku in plan mode, which is unaffected (previous fact).
  `claude logs <id>`, read 2026-09-12.
- **The `auto` classifier refuses to launch a bypass child.** This session's classifier
  denied a `claude --bg …` launch whose prompt asked for a
  `claude -p … --permission-mode bypassPermissions …` call:
  `Permission … denied by the Claude Code auto mode classifier. Reason: [Create Unsafe Agents]`.
  Consequence: nothing in this plan uses `bypassPermissions`.
- **A plan-mode reviewer will not read outside the project directory.** Asked to read a
  file under `mktemp -d`, `claude -p --model haiku --effort low --permission-mode plan --strict-mcp-config`
  answered `I don't have permission to read that file … outside the project directory`.
  Consequence: the smoke-test fixture in criterion 6 is a transient untracked file at the
  repository root, not a scratch file.
- **The reviewer prompt at HEAD** is the 61-line block inside the ````markdown fence of
  `pdca/skills/plan/references/review-loop.md`, first line
  `You are about to execute a plan, alone, in a session that has just started. You`,
  last line `inventing objections to avoid giving it wastes a round.`:
  `git show ebf5f58:pdca/skills/plan/references/review-loop.md | awk '/^````markdown$/{f=1;next} /^````$/{f=0} f' | wc -l`
  Its plan-specific spans, and nothing else: the opening paragraph that puts the reader in
  the executor's seat; the word `plan` wherever the artifact is named, including "a good
  plan" in the last paragraph; the paragraph exempting the Handoff section and the
  frontmatter's `status`, `branch`, `closeout_push` and `permalink`; the ten bullets under
  "Include here:"; the Verdict clause "you could execute this plan unattended and be
  confident the result is what the author wanted"; the sentence "A plan that ships with
  a real gap costs an entire unattended run; a nit costs nothing."; and the Nits
  paragraph's clause "they do not gate the handoff". The rest of the file
  — isolation, background execution, the two verdicts, inconclusive rounds, the three-round
  cap, full re-reads, fix-or-dispute, the git-status check, the per-round report — is
  mechanics and mentions plans only as its example.
- **Step 7 of `pdca/skills/plan/SKILL.md`** runs lines 366–425. Lines 381–386 state the
  loop and its cap ("Until the reviewer returns AGREED, or three rounds, whichever comes
  first") and what non-convergence does; lines 388–400 are the two AGREED bullets, with
  the pointer `references/review-loop.md` at 399–400; 402–407 the afterthoughts rule,
  whose lines 405–406 say "Each re-entry is a fresh loop with its own three rounds";
  409–414 the fixpoint; 416–422 the user's override. The other two pointers to
  `review-loop.md` are lines 424 and 719; the sibling-skill delegation this plan copies is
  lines 495–501 and 723 (`execute`). The passage that must survive verbatim — 388–398,
  402–404 and 409–414 — is 19 distinct non-blank lines, all present now:
  `grep -Fxf <(git show ebf5f58:pdca/skills/plan/SKILL.md | sed -n '388,398p;402,404p;409,414p' | grep -v '^$') pdca/skills/plan/SKILL.md | sort -u | wc -l` → `19`
  (blank lines are excluded because macOS grep drops an empty pattern).
- **Where the three-round cap and the override are written down**, from
  `grep -rn -i 'three rounds\|three-round\|review 2/3' pdca README.md` and
  `grep -rn 'overrul\|outrank\|user.s override' pdca README.md`: the cap at
  `pdca/README.md` 52, 187 (the diagram edge "no convergence after three rounds") and 287;
  `pdca/CLAUDE.md` 87, 333 and 358; `pdca/skills/plan/SKILL.md` 90, 382 and 406; root
  `README.md` 27; and five places in `review-loop.md` (lines 33, 55, 69, 110, 203), which
  moves anyway. The override at
  `pdca/README.md` 60, 161–162 and 189 (the diagram edge "you overrule → Handoff");
  `pdca/CLAUDE.md` 90–92; `pdca/skills/plan/SKILL.md` 416–422. Every other hit for
  `override` is the unrelated "no human to override" of the `auto`-mode text, and
  `overrule` at `review-loop.md` 155 is inside the reviewer prompt's checklist ("a
  disposition you would feel entitled to overrule"), which the executor lens keeps
  byte for byte. The prompt itself names no round count:
  `git show ebf5f58:pdca/skills/plan/references/review-loop.md | awk '/^````markdown$/{f=1;next} /^````$/{f=0} f' | grep -n -i 'three'` prints nothing.
- **Where the review is documented today.** Lines mentioning `review`: `pdca/CLAUDE.md`
  18, `pdca/README.md` 18, `pdca/skills/plan/SKILL.md` 32, `review-loop.md` 38, root
  `README.md` 5, plus one each in `skills/execute/SKILL.md`, `goal-condition.md`,
  `plan-template.md` and two in `jira.md`. The root README carries a Commands table and a
  Skills table for pdca (lines 14–30). `pdca/README.md` has the "The three loops" Mermaid
  diagram with the subgraph title `Inner loop — adversarial review`.
  `grep -rc 'review' pdca README.md; grep -rn 'review-loop' pdca README.md`
- **Local tooling.** `python3` is 3.14.7 and `awk` is present: `python3 --version`.
  `.claude/settings.local.json` (gitignored) allows `Bash(python3:*)` and `Bash(test:*)`,
  but `pdca/CLAUDE.md` records that wildcarded interpreter rules are dropped on entering
  `auto`, so nothing here is pre-authorised. What is established is that the assembler's
  call shape runs under `auto`: in this planning session, under `auto`,
  `python3 -c 'import sys; print(open(sys.argv[1]).read()[:1])' pdca/.claude-plugin/plugin.json`
  printed `{`, and every edit to this plan was a `python3 -` heredoc, none refused.
- **The push works from this machine.** `git push --dry-run` prints `Everything up-to-date`
  and exits 0, run under `auto` in the planning session.
- **Remote Control** is available for the handoff: `claude auth status` prints
  `"authMethod": "claude.ai"`, `"apiProvider": "firstParty"`.

## Constraints & Non-Goals

- **`/pdca:plan` changes in the two decided ways and no other**, and the plan makes that
  testable: the executor lens reproduces the 61-line prompt byte for byte (criterion 3);
  the 19 lines of step 7's AGREED bullets, afterthoughts rule and fixpoint stay verbatim
  (criterion 4); no trace of the three-round cap or the override's phrasings remains
  (criterion 9). The reviewer still runs at phase 2's model and effort, in
  plan mode, backgrounded, cold, never on a diff or a resumed session; nits applied as
  worded still do not reopen the review; a re-entry after a material change is still a
  fresh loop with a fresh budget. Step 7 keeps deciding what an AGREED exits to and the
  fixpoint; the review skill returns to its caller.
- **The round budget.** A parameter of the loop, per entry into it, counting only
  conclusive rounds (an inconclusive round is retried and not counted, as today);
  default `10`. `/pdca:plan` asks for it in the step 2 interview exactly as it asks for
  the permission mode — one more question, recommended option `10` first, then `5` and
  `20`, any other number through Other — so the interview now has five candidate
  questions where the tool holds four: when all five are missing, the interview takes
  two calls, model, effort, permission mode and ticket first, the round budget second.
  The budget is written to the frontmatter as `review_rounds` at the first draft, so a
  reopen reuses it instead of asking again, and step 7 passes it to the review skill.
  `/pdca:review` takes it from the command line — an integer directly after an effort
  token, `/pdca:review sonnet xhigh 10 docs/ for …`, the same rigid rule that binds
  effort to model — or interviews for it. The status file names the budget:
  `review 2/10`.
- **Non-convergence never reaches the handoff.** When the budget is spent without an
  AGREED, the loop stops and both positions go to the user, as today — and that is where
  today's exception ends: the user's settlement is not an exit. They edit the plan, which
  writes their decision into it and re-enters the review as a fresh loop with a fresh
  budget; or they raise the budget and the loop continues; or they leave the plan as it
  is, `status: drafting`. The paragraph in step 7 that makes the user's override the
  exit goes, with its instruction to record the overruled objection in Constraints &
  Non-Goals; so do the README diagram's edge "you overrule → Handoff" and the sentences in
  `pdca/CLAUDE.md` and `pdca/README.md` that state the exception. The user outranks both
  models by deciding what the plan says, not by launching a plan the executor vetoed.
- **Ownership rule, to be written into `pdca/CLAUDE.md`:** the review skill owns the
  mechanics and the prompt template; every opinion is a lens slot; `plan` fills every slot
  from its own executor lens, so no default in the review skill can reach a plan review;
  plan is the reference caller, and standalone use adapts through lens slots, never by
  changing the mechanics. A future change to the loop that would alter what the executor
  lens assembles is a change to `/pdca:plan` and is reviewed as one.
- **Sibling files are named by expanded path.** `commands/review.md` sends the reader to
  `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md`; the plan skill's step 7 sends it to
  `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md` and
  `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/executor-lens.md`; the review skill names its own
  files as `${CLAUDE_SKILL_DIR}/references/prompt-template.md` and `…/default-lens.md`.
  The harness fills both variables in when the body loads (Verified Context); a body that arrives unexpanded resolves them relative to the `SKILL.md`
  actually read. The plan skill's step 8 pointer to the `execute` skill gets the same path
  form in passing — same defect, one line — and criterion 11 checks the two pointers that
  matter to this plan.
- **Slots.** Exactly these, each a `## <slot>` heading in a lens file whose content is
  the trimmed text beneath it: `reader` (the opening paragraph: who is reading, what they
  have, that there is no one to ask), `noun` (what the artifact is called in the prompt),
  `exempt` (what is not under review; may be empty), `checklist` (the bullets under
  "Include here:"), `success` (the clause completing "AGREED when it is empty — meaning
  …"), `cost` (what a shipped gap costs, following "Be adversarial about blockers and
  sparing with nits."), `gate` (what nits do not gate: the template reads `they do not gate {{gate}}.` and
  the slot content carries its own article — `the handoff` for a plan, `the verdict`
  otherwise), and `answers` (how
  a blocker the session disagrees with is answered — in the artifact itself, or by the
  user; not part of the prompt). `{{path}}` comes from the
  invocation, not the lens.
- **Assembly is mechanical.** One inline `python3` command carried in the review skill —
  no script file, the way `skills/execute/SKILL.md` carries its `awk` — reads the template
  and the lens, maps each `## <slot>` heading to the text beneath it, replaces every
  `{{slot}}` in the template, replaces `{{path}}` with its third argument, collapses runs
  of three or more newlines to two (an empty `exempt`), and prints the result with one
  trailing newline. The planner runs it rather than transcribing; criterion 3 runs the
  same command. `python3` is documented as the requirement and "fill the markers by hand"
  as the fallback when it is missing. A `python3` call the classifier refuses under `auto`
  is a blocked report naming the denial — hand-filling cannot satisfy criterion 3.
- **The default lens is a lens template**: its `reader` text carries `{{statement}}` and
  its `noun` carries `{{noun}}`; the session copies it to scratch, fills both from the
  reader statement, then assembles. The executor lens carries no markers.
- **Grammar** of `/pdca:review`: `[model] [effort] [rounds] <path…> [reader statement]`,
  with the plan skill's rigid rule extended by one token — an effort token counts only
  directly after a model token, an integer counts as the round budget only directly after
  an effort token — then leading tokens that exist on disk are the artifact (files or
  directories, one or more — several are joined with a space in `{{path}}`, and the
  closing line names the first), and the first token that does not starts the reader
  statement. Echo the parse in the first line. Model and effort are the *reviewer's*.
  Whatever is missing of model, effort, round budget and reader is interviewed for —
  never a silent default — in one `AskUserQuestion` of at most four questions, exactly
  as the plan skill's step 2 does, recommended option first: `opus` at `high`, `10`
  rounds, and for the reader a few presets (an implementer building from this spec; an
  operator following this runbook with nobody to ask; a newcomer reading this to get
  started) plus Other. A headless session cannot interview, so there every parameter
  comes from the command line and a missing one ends the run with the report. No path on
  the command line, or none that exists on disk: say so and stop — the artifact is the
  one parameter never interviewed for.
- **A path whose frontmatter says `plugin: pdca` is redirected** to `/pdca:plan <path>`
  and not reviewed: plans have one route to a review, the one that owns the fixpoint.
- **Fixing stays as written; answering is the `answers` slot.** A blocker the session
  agrees with is fixed in the artifact, as today. A blocker it disagrees with is
  *answered*, as the lens says, and the answer is judged by the next cold round: the loop
  exits only on an AGREED from a reviewer who read the artifact with the answer in it, so
  no artifact leaves the loop with an open disagreement. The skill's prose says *answer*,
  never *dispute*, for exactly that reason. Executor lens — today's rule, unchanged: the
  planner writes its reasoning into the plan, Constraints & Non-Goals or beside the fact.
  Default lens — the user answers: the loop stops, the disagreement is put to the user
  with the reviewer's wording and the session's reason, and the user decides what the
  artifact should say — the reviewer's fix, or their own reasoning, which the session
  folds into the artifact's own text, never into a notes file or a companion — and a
  fresh round follows. There is no exit by overruling: the only exits are AGREED, the
  budget spent without convergence, reported as not agreed, or the user stopping. In a headless
  session there is no user, so a blocker the session would answer ends the loop with the
  report.
- **Reporting.** Each round in a line or two, as today, and a closing line the caller and
  a headless harness can read: `Review of <artifact>: AGREED after N round(s)`,
  `Review of <artifact>: VETOED after N round(s), not converged`, or
  `Review of <artifact>: stopped after N round(s), <reason>`. The skill writes the
  status file `review N/<budget>` at each round; the plan skill's "Keep the status line
  posted" says so instead of writing it itself.
- **Scratch outside the repository, two-step:** run `mktemp -d` once and use the printed
  path literally in later calls. The reviewer never gets `--remote-control`. Nothing in
  this plan uses `bypassPermissions` (Verified Context).
- **Documentation follows the code**: `pdca/CLAUDE.md` (the palette convention now counts
  three commands; the review-loop bullet becomes the ownership rule; the facts about
  `--plugin-dir`, the Skill tool's resolution, and Haiku's missing `auto` mode join the
  facts sections), `pdca/README.md` (a `/pdca:review` paragraph in Usage; "The three loops"
  names the review skill and the executor lens; the inner-loop subgraph title says so),
  root `README.md` (a row in each table, `[rounds]` in the existing `/pdca:plan` row, and
  a bullet), `pdca/commands/plan.md` (the `argument-hint` and an example with a budget),
  `.claude-plugin/marketplace.json`
  (one clause in the pdca description), `plugin.json` → `0.12.0`, `plan-template.md:41` →
  `0.12.0`.
- **Out of scope**: teaching the plan skill's step 2 interview that Haiku cannot run
  `auto` (the fact is recorded in `pdca/CLAUDE.md`; the interview change is a separate
  decision for the user); exercising `/pdca:review`'s interactive interview (phase 2 is
  headless; the user tries it after installing 0.12.0); and a live `/pdca:plan` through the
  extracted loop — this plan's own review runs the installed 0.11.0 loop, and the user's
  next plan is the first live run.
- **The closeout pushes**, and only the closeout: no task pushes, so what reaches
  GitHub — and, through the marketplace's `autoUpdate`, every session on this machine — is
  the tree after task 4 has bumped the version to `0.12.0`, never an intermediate one. The
  planning session pushes the handoff commit for the same reason it probes the push.

## Pre-Flight

Run in the first turn, before task 1. Each check is one command with one expected result,
and any failure stops the run: write the blocked report named in step 10 of the Execution
Protocol and do not start the tasks.

Before check 1: if `2026-09-12-review-command-plan.BLOCKED.md` exists, this is a relaunch.
Fold that report into the Run Log below — its `date`, the check it named, what was tried,
its `next` — then delete it, in this same turn, and only then run the checks. An inherited
report never satisfies this plan's goal and is never left in place.

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

   Expected: `"met":false` with a condition naming `2026-09-12-review-command-plan.md`;
   `"model":"claude-opus-5"`; `"permissionMode":"auto"`; `effort=high`. A last record
   with `"met":true`, a different goal's condition, or no record at all in a readable
   transcript means no evaluator guards this run: stop and write the blocked report; the
   fix is relaunching with the command in the Handoff section. If the `T=` line prints
   empty, the transcript could not be found: record that in the Run Log, take the model
   from what this session states about itself, the effort from `CLAUDE_EFFORT`, the mode
   from the launch flags (walk up from `$PPID` until the argv starts with `claude`, match
   `--permission-mode <mode>`), treat the goal check as unverifiable, and continue. If the
   `permissionMode` line is empty, use the same launch-flag fallback; if neither answers,
   the mode is unverifiable — say so rather than assuming it.

2. **Privileges** — skip this group only if the mode above is `bypassPermissions`, and say
   in the Run Log that you skipped it.
   - `claude -p --model sonnet --effort low --permission-mode auto --strict-mcp-config "Reply with exactly the text HARNESS-OK and nothing else"`
     prints `HARNESS-OK` — this session may spawn the smoke-test harness of criterion 6.
   - `claude -p --model haiku --effort low --permission-mode plan --strict-mcp-config "Reply with exactly the text INNER-OK and nothing else"`
     prints `INNER-OK` — the reviewer shape runs.
   - `mktemp -d` prints a directory; then, with that literal path, `echo hi > <dir>/f && cat <dir>/f`
     prints `hi` — scratch outside the repository is writable.
   - `python3 -c 'import sys; print(open(sys.argv[1]).read()[:1])' pdca/.claude-plugin/plugin.json`
     prints `{` — the assembler's call shape, a `-c` script with file arguments, runs
     under this mode. A refusal here, or of any assembler call later, is a blocked report
     naming the denial: hand-filling the markers cannot satisfy criterion 3.
   - `claude -p --model haiku --effort low --permission-mode plan --strict-mcp-config --plugin-dir ./pdca "List every slash command available to you whose name starts with /pdca. Print exact names only, one per line, nothing else. Do not run any of them."`
     prints `/pdca:plan` and `/pdca:execute` — `--plugin-dir ./pdca` loads beside the
     installed plugin of the same name, which criteria 5 and 6 rest on.
   - `git push --dry-run` exits 0 — the closeout pushes its two commits.

3. **Ground.**
   - This file exists at `2026-09-12-review-command-plan.md`, the `plan_file` in its
     frontmatter.
   - `git remote -v` names `christian-schlichtherle/cs7-claude-plugins`,
     `git branch --show-current` prints `main`, and `git status --porcelain` is empty — or
     this is a resume: the frontmatter says `status: executing` or `status: blocked`, and
     the only changes are this file, the blocked report just consumed, and the files the
     Run Log names as work in progress. Anything else dirty is a failed check.

4. **Preconditions from the Verified Context.**
   - `test -f pdca/skills/plan/references/review-loop.md && test ! -e pdca/skills/review && test ! -e pdca/commands/review.md && echo PRE-OK` prints `PRE-OK`.
   - `git show ebf5f58:pdca/skills/plan/references/review-loop.md | awk '/^````markdown$/{f=1;next} /^````$/{f=0} f' | wc -l` prints `61`.
   - `grep -Fxf <(git show ebf5f58:pdca/skills/plan/SKILL.md | sed -n '388,398p;402,404p;409,414p' | grep -v '^$') pdca/skills/plan/SKILL.md | sort -u | wc -l` prints `19`.
   - `python3 -c 'import json; print(json.load(open("pdca/.claude-plugin/plugin.json"))["version"])'` prints `0.11.0`.

## Tasks

Ordered. Task 2 depends on task 1's template and slot names; criterion 3 must pass at the
end of task 2, before anything else is touched, so a mismatch is found while the two files
are the only ones that changed. Tasks 1–4 each end in a commit; task 5 changes nothing
and ends in a Run Log entry instead.

- [ ] **1. Create the `review` skill.** Three files under `pdca/skills/review/`:
  - `SKILL.md` — frontmatter `description`, `name: review`, `user-invocable: false`, keys
    alphabetical; a description that triggers on intent ("review this cold", "have a fresh
    model review it", "adversarial review", "what would a reader who cannot ask me trip
    over", `/pdca:review`) and says it does not review plan files. Body: what the skill is
    and why isolation is the point (moved from `review-loop.md`'s opening); the grammar with the rounds token,
    the parse echo, the plan-file redirect, the interview for a missing model, effort,
    round budget or reader (Constraints); the template and lenses named as
    `${CLAUDE_SKILL_DIR}/references/prompt-template.md` and `…/default-lens.md`, with the
    relative-to-this-file fallback (Constraints); the lens — the
    eight slots, the `## <slot>` format, the default lens as a template to copy and fill,
    the inline assembler; the loop — moved from `review-loop.md` with `plan` generalized:
    scratch outside the repository in two steps, the reviewer command with `-p`, the
    caller's model and effort, `--permission-mode plan`, no `--remote-control`, background
    execution and why, the verdict rules and inconclusive rounds, full cold re-reads and
    why never a diff, the round budget as the caller's parameter with its default of
    ten and why a cap exists at all (a loop that will not converge ends in front of the
    user instead of burning rounds), fixing blockers, and answering the ones it
    disagrees with as the `answers` slot says — in the artifact, or by the user — under a
    heading named exactly "Handling the verdict", which the plan skill's step 7 points at
    and which carries `review-loop.md`'s nits-do-not-reopen paragraph (lines 207–213); the
    git-status check, the status file
    `~/.cache/claude-pdca/$CLAUDE_CODE_SESSION_ID.status` holding `review N/<budget>`,
    deleted when a standalone loop ends and left to the caller otherwise, the per-round
    report and the closing line; the return to a caller (verdict, rounds used of the budget, whether the artifact
    changed, answers recorded, and — when the budget is spent — both positions for the
    caller to put to the user); the headless note (no user to ask → the report; every
    parameter from the command line; a harness needs a model with `auto` available — not
    Haiku).
  - `references/prompt-template.md` — the 61-line block from `review-loop.md` with exactly
    the plan-specific spans of the Verified Context replaced by `{{reader}}`, `{{noun}}`,
    `{{exempt}}`, `{{checklist}}`, `{{success}}`, `{{cost}}`, `{{gate}}`, and `<path>` by `{{path}}`.
    Nothing else changes; criterion 3 is the test.
  - `references/default-lens.md` — the generic lens template: a `reader` paragraph built
    around `{{statement}}` (they have the artifact and the repository it lives in, no one
    to ask, a wrong guess costs them the outcome); `noun` `{{noun}}`; `exempt` empty;
    a `checklist` that is the generic subset of the executor's — facts asserted without
    evidence or contradicted by the repository, steps that assume knowledge not in the
    artifact, ambiguity resolvable two materially different ways, ordering that matters
    but is not stated, anything the reader could not actually carry out, a check or
    instruction that would pass or succeed without the outcome the artifact promises;
    `success` and `cost` phrased for a reader who acts alone; `gate`: `the verdict`;
    `answers`: by the user.
  - Verify: `test -f pdca/skills/review/SKILL.md && test -f pdca/skills/review/references/prompt-template.md && test -f pdca/skills/review/references/default-lens.md && grep -c 'user-invocable: false' pdca/skills/review/SKILL.md`
    prints `1`. Commit.

- [ ] **2. Move the plan skill onto it.**
  - Write `pdca/skills/plan/references/executor-lens.md`: the eight `## <slot>` sections
    carrying today's exact wording from the fenced block (`reader` = the opening paragraph
    through "a wrong guess runs unsupervised."; `noun` = `plan`; `exempt` = the Handoff
    paragraph; `checklist` = the ten bullets; `success` and `cost` as quoted in the
    Verified Context; `gate` = `the handoff`; `answers` = "in the plan — a sentence in Constraints & Non-Goals,
    or beside the fact in question", from `review-loop.md`'s "Handling the verdict").
    A short preamble above the slots says what the lens is and that the assembled prompt
    must stay identical to the one the plan skill sent before the extraction.
  - `git rm pdca/skills/plan/references/review-loop.md`.
  - Edit `pdca/skills/plan/SKILL.md`. Step 1: the grammar gains the rounds token
    (`[model] [effort] [rounds] <goal or plan path>`, an integer directly after an effort
    token, with the same "a bare leading number is goal text" reasoning as effort) and the
    parse echo names the budget. Step 2: a fifth interview parameter, the round budget,
    recommended `10`, with the two-call rule when all five are missing; the paragraph on
    "at most four" changes accordingly, and so does the sentence "A spec is not
    interviewed for. The tool has no fifth slot.", whose reason the two-call rule makes
    false — reword it to "the interview is already at two calls, and a spec the user has
    is one they hand over." Step 5: `review_rounds` joins the frontmatter
    fields written at the first draft. "Keep the status line posted": the review skill
    writes `review N/<budget>`, and the example reads `review 2/10`. Step 7: lines
    366–387 may swap restated mechanics for pointers to the review skill but keep that the
    reviewer runs *phase 2's model at phase 2's effort* and why a cold reader is the only
    one who can judge self-sufficiency; "or three rounds, whichever comes first" becomes
    the budget from `review_rounds`; the non-convergence sentence says what the
    Constraints say — both positions to the user, who edits, raises the budget or stops,
    and no handoff; lines 399–400 point to the review skill's "Handling the verdict"
    instead of `references/review-loop.md`; lines 405–406 say "its own budget" instead of
    "its own three rounds"; the override paragraph, lines 416–422, is removed; line 424
    becomes "Read `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md` and
    `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/executor-lens.md` before the first
    round". Step 8, lines 495–497: "follow the `execute` skill" names its file the same
    way, `${CLAUDE_PLUGIN_ROOT}/skills/execute/SKILL.md`. "Reopening a plan": a reopen
    reuses `review_rounds`, and a plan written before 0.12.0, which has none, is asked for
    it as step 2 would. The References
    list replaces the `review-loop.md` entry with one for `executor-lens.md` and adds,
    after the `execute` sentence at line 723, that the loop itself is owned by the sibling
    `review` skill. Lines 388–398, 402–404 and 409–414 do not change.
  - Edit `pdca/skills/plan/references/plan-template.md`: `review_rounds: 10` in the
    frontmatter example, alphabetically placed, and a row in the frontmatter table
    ("phase 1, first draft — the review loop's round budget from the step 2 interview;
    a reopen reuses it").
  - Verify: criteria 2, 3, 4 and 10 pass now. Criterion 9 cannot pass yet — the other
    files that mention the cap and the override are task 4's — so it is task 4's check.
    Commit.

- [ ] **3. Create the command.** `pdca/commands/review.md` in the shape of
  `commands/execute.md`: frontmatter `argument-hint: "[model] [effort] [rounds] <path…> [reader statement]"`
  and a `description` for the palette (cold adversarial review of any file or directory by
  a fresh process in the reader's position, until agreement or the round budget, ten by
  default, is spent); body: follow the `review` skill,
  named by path — "read `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md`", which the harness
  expands to the plugin's directory when the command loads — then four or five examples (`/pdca:review sonnet xhigh docs/runbook.md for an operator
  following it at 3am`, one with a budget — `/pdca:review sonnet xhigh 5 docs/`, a bare
  path that triggers the interview, a plan file that is redirected), and what it will not do (review a plan file; act as a one-shot
  proofreader). Verify: criteria 5 and 11. Commit.

- [ ] **4. Documentation and version.** `pdca/CLAUDE.md`, `pdca/README.md`, root
  `README.md`, `.claude-plugin/marketplace.json`, `pdca/.claude-plugin/plugin.json` →
  `0.12.0` (the minor number: a new command and two changed rules), the template's
  frontmatter example → `0.12.0`, and `pdca/commands/plan.md` — its `argument-hint`
  becomes `"[model] [effort] [rounds] <goal, ticket, spec path, or plan path>"` and its
  examples gain one that passes a budget — as the Constraints list them, including every
  cap and override mention the Verified Context locates: in `pdca/CLAUDE.md` the "AGREED alone
  does not exit" bullet loses its exception and gains the budget, the review bullet says
  "capped by the round budget, default ten" instead of "three rounds", the interview
  bullet says five candidate questions and two calls, its line 151 — "the interview is at
  the tool's four-question capacity, and a spec the user has is one they hand over" —
  loses the capacity clause for the reason task 2 gives, `review 2/3` becomes
  `review 2/10`,
  and a dated convention records the two decisions and why (agreement has regularly
  taken more than three rounds; the plan is a contract); in `pdca/README.md` the Usage
  prose, "The three loops" and its diagram drop the override and the edge "you overrule
  → Handoff" and say "the round budget you chose, ten by default" where they said three;
  the root README's bullet likewise, and its existing `/pdca:plan` row gains `[rounds]` beside the new
  `/pdca:review` row. In `pdca/CLAUDE.md`'s facts, record with dates: `--plugin-dir`
  merging an extra command into an installed plugin and a plugin command working as the
  `-p` prompt (2.1.269, 2026-09-12); the Skill tool resolving a name to the command body;
  `auto mode unavailable for this model` under Haiku and what it means for an
  `executor.model` of `haiku`; the classifier's `Create Unsafe Agents` refusal of a
  bypass child. Verify: criteria 2, 7, 9 and 12. Commit, with `Bump pdca to 0.12.0.` in the body.

- [ ] **5. Smoke-test the command headlessly.** Write the fixture
  `pdca-review-fixture.md` at the repository root with exactly this content:

  ```markdown
  # Generate a test image

  1. Export your Gemini API key.
  2. Run the image script with a prompt of your choice.
  3. Look in the output folder for the image.
  ```

  Every gap in it is answerable from this repository — the variable is `GEMINI_API_KEY`,
  the script is `gemini-media/skills/generate-image/scripts/generate_image.py`, the output
  folder is `./generated-images/` (root `CLAUDE.md`, lines 14–16) — so the harness can fix
  what the reviewer flags and the loop can reach its second and last round; a blocker
  it disagrees with goes to a user who is not there and ends the loop with the report,
  which is also a valid outcome for criterion 6. Run criterion 6 as it says — in the
  background — then remove `pdca-review-fixture.md`; the step 5 re-run rewrites it first
  and removes it again. Record the closing line the harness printed in the Run Log. No
  commit: the tree is as task 4 left it.

## Acceptance Criteria

1. `test -f pdca/commands/review.md && test -f pdca/skills/review/SKILL.md && test -f pdca/skills/review/references/prompt-template.md && test -f pdca/skills/review/references/default-lens.md && test -f pdca/skills/plan/references/executor-lens.md && test ! -e pdca/skills/plan/references/review-loop.md && echo LAYOUT-OK`
   prints `LAYOUT-OK`.
2. `grep -rn 'review-loop' pdca README.md | wc -l` prints `0`.
3. `diff <(git show ebf5f58:pdca/skills/plan/references/review-loop.md | awk '/^````markdown$/{f=1;next} /^````$/{f=0} f') <(ASSEMBLE) && echo PROMPT-IDENTICAL`
   prints `PROMPT-IDENTICAL` and nothing else, where `ASSEMBLE` is the assembly command
   exactly as `pdca/skills/review/SKILL.md` carries it, given
   `pdca/skills/review/references/prompt-template.md`,
   `pdca/skills/plan/references/executor-lens.md`, and the literal string `<path>` as the
   path, shell-quoted — a bare `<path>` is a redirection.
4. `grep -Fxf <(git show ebf5f58:pdca/skills/plan/SKILL.md | sed -n '388,398p;402,404p;409,414p' | grep -v '^$') pdca/skills/plan/SKILL.md | sort -u | wc -l`
   prints `19`.
5. `claude -p --model haiku --effort low --permission-mode plan --strict-mcp-config --plugin-dir ./pdca "List every slash command available to you whose name starts with /pdca. Print exact names only, one per line, nothing else. Do not run any of them."`
   prints a line that is exactly `/pdca:review`.
6. With `pdca-review-fixture.md` present as task 5 writes it, and `<scratch>` a directory
   `mktemp -d` printed, run this **in the background** — `run_in_background` on the Bash
   call, then wait for its completion notice before reading anything. Never run it as a
   plain foreground call: it is a whole nested review loop, a Sonnet harness spawning a
   Haiku reviewer, editing, spawning another, and it outlives the Bash tool's two-minute
   default timeout (the plan skill's own reviewer is backgrounded for the same reason).
   `claude -p --model sonnet --effort low --permission-mode auto --strict-mcp-config --plugin-dir ./pdca "/pdca:review haiku low 2 pdca-review-fixture.md for a developer who has just cloned this repository and has nobody to ask" > <scratch>/smoke.txt 2>&1; echo "exit=$?" >> <scratch>/smoke.txt`
   Then: `tail -1 <scratch>/smoke.txt` prints `exit=0`;
   `grep -Ec '^Review of pdca-review-fixture\.md: (AGREED|VETOED|stopped) after [0-9]+ round' <scratch>/smoke.txt`
   prints a number of at least `1` — any of the three closing lines counts, since a blocker
   sent to an absent user ends the loop with `stopped` (a budget of `2` keeps the test
   short and exercises the rounds token); and after removing the fixture, `git status --porcelain` prints nothing except
   a line for `2026-09-12-review-command-plan.md`. If the harness was killed or exited
   non-zero, check `claude agents --json` for a lingering harness, rewrite the fixture, and
   retry once the same way; a second failure is a blocked report.
7. `python3 -c 'import json; print(json.load(open("pdca/.claude-plugin/plugin.json"))["version"])'`
   prints `0.12.0`, and `grep -c 'plugin_version: 0.12.0' pdca/skills/plan/references/plan-template.md`
   prints `1`.
8. `git log --oneline -2` shows the deletion commit above the preservation commit;
   `git show --stat --name-only HEAD | grep -c 2026-09-12-review-command-plan.md` prints `1`
   and `git show --stat --name-only HEAD~1 | grep -c 2026-09-12-review-command-plan.md`
   prints `1` — the file is touched by each of the two commits and by no work commit;
   `git status --porcelain` prints nothing; `git status -sb | head -1` shows no `ahead` —
   both commits were pushed.
9. `grep -rn -i 'three rounds\|three-round\|review [0-9]/3' pdca README.md | wc -l` prints `0`,
   and `grep -rn -i "user.s override\|your override\|you overrule\|overruled objection\|settlement is the exit" pdca README.md | wc -l`
   prints `0`. These are the old rule's phrasings — on `ebf5f58` the second grep prints
   `8` lines, spanning every override mention the Verified Context lists — not a
   banned vocabulary: prose explaining why the override is gone may say "overrule" or
   "outrank", and the executor lens's "feel entitled to overrule" is untouched by it.
10. `grep -c 'review_rounds' pdca/skills/plan/references/plan-template.md` prints a number
    of at least `2`, and `grep -c 'review_rounds' pdca/skills/plan/SKILL.md` prints a
    number of at least `1`.
11. `grep -c 'CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md' pdca/commands/review.md` and
    `grep -c 'CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md' pdca/skills/plan/SKILL.md` each
    print a number of at least `1`.
12. `grep -c '\[rounds\]' pdca/commands/plan.md` prints a number of at least `1`, and
    `grep -c '\[rounds\]' README.md` prints a number of at least `2` — the `/pdca:plan` row
    and the `/pdca:review` row.

## Rollback

`git revert` the task commits, newest first, and push the reverts — never force-push
`main`. Everything changed is Markdown and JSON inside this repository; nothing outside
it moved. Once the closeout has pushed, the marketplace's auto-update carries whatever
`main` holds, so a revert is what takes 0.12.0 back out of circulation.

## Closeout

Run after the work is committed and the Acceptance Criteria have been re-run, and before
this file is removed. This section is not a decision point: do not ask what should be done
with this file — run the recorded commands; if they cannot complete, the answer is the
blocked report, not a question. Steps 3, 4 and 6 of the template apply only with a ticket;
this plan has none, so they are absent.

1. Bring this file to its final state: every task checkbox ticked, the Run Log complete,
   the outcome recorded, and `status: done` in the frontmatter.
2. Commit this file on its own — the preservation commit — and push it — the Constraints
   say the closeout pushes, and only the closeout:

   ```bash
   git add 2026-09-12-review-command-plan.md
   git commit -m "Record final plan state for the review command"
   git push
   git rev-parse HEAD
   ```

   It is a commit of its own because the final Run Log entries are written after the work
   commits, so they exist in no earlier commit. Do not squash it into a work commit and do
   not delete the file in it.
3. Only now delete this file, in a **separate follow-up commit**, pushed as the
   preservation commit was:

   ```bash
   git rm 2026-09-12-review-command-plan.md
   git commit -m "Remove the review command plan file"
   git push
   ```

   Separate is the point: the preservation commit has to stay the last commit in which
   this file exists, because that is where the record of the run lives.

If the preservation commit or its push cannot be completed, **leave this file in place** and write the
blocked report — that commit is the only thing that preserves this record once the file
is gone.

## Execution Protocol

You are executing this plan file autonomously. There is nobody to ask, so decide from
what is written here plus the repository, and record what you decided.

1. Read this file completely before starting.
2. Run the **Pre-Flight** section first, in your first turn, before changing anything.
   Show each check and its real output. If any check fails, stop there: write the blocked
   report described in step 10, naming the failed check, what was expected, what was
   actually there, and what has to change about the launch. Do not start the tasks, do
   not substitute a different model or mode, and do not proceed at a lower spec. When
   every check passes, set `status: executing` in the frontmatter and append the gate's
   outcome to the Run Log. On a resume, continue at the first unticked task; a task the
   Run Log shows started but not finished is inspected before it is redone, because the
   tree may already hold part of it.
3. Work the tasks in order. Append a line to the Run Log when you start a task, and tick
   its checkbox with another line when you finish it. Do this as you go, not at the end.
4. Run each task's verification and the Acceptance Criteria for real, and show their
   output. A summary is not evidence.
5. Immediately before the final commit and the removal of this file, re-run the full
   Acceptance Criteria and show every command and result again — criterion 8 excepted,
   since it describes the closeout itself and is verified after the deletion commit, in
   this session; criterion 6 included, run the same way, in the background, with
   `pdca-review-fixture.md` rewritten first exactly as task 5 writes it and removed again
   afterwards, because task 5 deleted it.
   The evaluator judging whether you are done reads the condition text and the recent
   conversation; a result proved twenty turns ago may no longer be visible to it, and
   this file is about to stop existing.
6. If reality contradicts the Verified Context, stop and record the contradiction in the
   Run Log before deciding anything. Then proceed only if the plan's Goal still makes
   sense; otherwise treat it as blocked.
7. Commit as you go, on the current branch — `branch` in the frontmatter, which the gate
   confirmed — following the repository's convention: an imperative subject, a body that
   says why, `Bump pdca to 0.12.0.` in the body of the commit that moves the version, and
   a `Co-Authored-By: <the model you are running as> <noreply@anthropic.com>` trailer.
   No ticket prefix. One task per commit, as the Tasks section says. Never create a
   branch.
8. Run the **Closeout** section — after the last work commit and before you remove this
   file in step 9. If the closeout cannot be completed, do not remove this file — write
   the blocked report in step 10 instead, naming the closeout as what failed.
9. When every acceptance criterion passes and the closeout is done, remove this plan file
   exactly as the Closeout section prescribes: in a separate commit after the
   preservation commit, never folded into it and never folded into a work commit.
10. If a criterion cannot be made to pass — or the run cannot finish for any other reason:
    a denied command, a contradiction with the Verified Context that leaves the Goal
    standing but the plan wrong, a run that has to stop clean at a task boundary — write
    the blocked report at **exactly** `2026-09-12-review-command-plan.BLOCKED.md`. It names
    the failing check, what you tried, and why it cannot pass; lists the working tree as
    you leave it — every uncommitted file and the task it belongs to; and opens with a
    frontmatter block of exactly two keys, alphabetically — `date:` the day the run
    stopped, and `next:` `relaunch` when the Handoff command can resume once the
    environment is fixed, or `reopen` when the plan itself has to change. Set
    `status: blocked` in this file's frontmatter, bring the Run Log current, and commit
    this file and the report together, leaving uncommitted only the work that has not
    reached a commit boundary. Then stop. Getting the path wrong is not cosmetic: the
    evaluator looks for the path the condition names. Do not weaken a check, skip it, or
    declare success without it. A report written by mistake — on an estimate rather than
    a check that ran — is retracted in the same session: delete it, say so in the Run
    Log, and continue.

## Handoff

The verbatim command that starts phase 2, kept here so the plan carries its own launch
instruction. It is one line; `/pdca:execute 2026-09-12-review-command-plan.md` reads this
block and runs it as a background session with Remote Control, so nothing needs pasting.

```bash
claude --model opus --effort high --permission-mode auto --remote-control 2026-09-12-review-command-plan '/goal Execute the plan at 2026-09-12-review-command-plan.md to completion. Before changing anything, run the Pre-Flight section of that plan and show the output of every check: the model must be claude-opus-5, the effort high, the permission mode auto, and every privilege probe must pass. If any pre-flight check fails, write the blocked report named below and stop - do not start the tasks and do not continue on a different model or mode. Done when all of the following hold, each shown in this session, the acceptance checks in a final re-run immediately before the closeout: the Pre-Flight checks were run first and passed; every task checkbox in that file was ticked before the file was removed; the criterion 1 test printed LAYOUT-OK (pdca/commands/review.md, pdca/skills/review/SKILL.md with its references/prompt-template.md and references/default-lens.md, and pdca/skills/plan/references/executor-lens.md exist, and pdca/skills/plan/references/review-loop.md does not); grep -rn for review-loop across pdca and README.md printed 0 lines; the assembly command carried by pdca/skills/review/SKILL.md, given prompt-template.md, executor-lens.md and the literal path <path>, produced output that diffed clean against the 61-line fenced block of review-loop.md at commit ebf5f58 and PROMPT-IDENTICAL was printed; the grep -Fxf check of criterion 4 against pdca/skills/plan/SKILL.md printed 19; a headless claude -p with --plugin-dir ./pdca listed /pdca:review among the /pdca commands; the criterion 6 smoke test was run in the background - a Sonnet auto harness with --plugin-dir ./pdca reviewing pdca-review-fixture.md at haiku low with a budget of 2 - and its output file ended with exit=0 and contained a closing line of the form Review of pdca-review-fixture.md: AGREED, VETOED or stopped after N rounds, and the fixture was removed afterwards; pdca/.claude-plugin/plugin.json says version 0.12.0 and plan-template.md contains plugin_version: 0.12.0 exactly once; greps across pdca and README.md for three rounds, three-round or review N/3, and for the old override phrasings (user override, your override, you overrule, overruled objection, settlement is the exit) each printed 0 lines; plan-template.md contains review_rounds at least twice and pdca/skills/plan/SKILL.md at least once; pdca/commands/review.md and pdca/skills/plan/SKILL.md each name CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md; pdca/commands/plan.md contains [rounds] and README.md contains it at least twice; the final state of the plan file was committed on its own and pushed in this session, and only then was the plan file deleted in a separate later commit, also pushed, so that git log shows the deletion commit directly above the preservation commit and git status --porcelain is empty with nothing ahead of origin/main; and all work was committed on the current branch main, a task per commit, imperative subjects, no ticket prefix, each with a Co-Authored-By trailer naming the model. Do not create a branch. Do not relax, skip, or declare passed any check that was not actually run, and do not route around a permission denial - a refused command is a blocked-report situation. If a pre-flight or acceptance check cannot be made to pass, write 2026-09-12-review-command-plan.BLOCKED.md in this session, naming a check this session ran, what was tried, and why it cannot pass, commit it with the plan, then stop - that also satisfies this goal. A blocked report left by an earlier launch does not.'
```

If this plan has been sitting for a while, do not launch it blindly — reopen it first
with `/pdca:plan 2026-09-12-review-command-plan.md` to re-verify the Verified Context and
get a freshened handoff. The condition inlines every acceptance criterion as command plus
expected result; none was summarized away, so the evaluator holds the whole set.

Short form, for typing into a session already started with the flags above. The
evaluator then holds only the plan path, the protocol, the closeout order and the escape
hatch — not the acceptance criteria — so it has to trust this session's own account of
what it ran; only the protocol's "no weakening" rule stands in the way of a quietly
weaker check. Prefer the full command; use this when the full one is not to hand. A bare
`/goal 2026-09-12-review-command-plan.md` is not a launch at all: the evaluator cannot
open the file, so it would have nothing to judge.

```
/goal Execute the plan at 2026-09-12-review-command-plan.md to completion per its Execution Protocol: Pre-Flight first, every Acceptance Criterion shown passing in a final re-run, the Closeout done - the final plan committed on its own and pushed - before the file was removed in a separate later commit, also pushed; or 2026-09-12-review-command-plan.BLOCKED.md was written in this session.
```

## Run Log
