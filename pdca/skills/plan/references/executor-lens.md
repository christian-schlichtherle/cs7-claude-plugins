# The executor lens

This is the lens `/pdca:plan` fills the `review` skill's prompt template with. Every
slot below is an opinion about a **plan** read by the model that is about to execute
it: who the reader is, what the artifact is called, what is exempt from review, what
counts as a blocker, what an AGREED means, what a shipped gap costs, what nits do not
gate, and how a blocker the planner disagrees with is answered. The mechanics — the
loop, the reviewer command, the verdict rules, the round budget — are the review
skill's and are not repeated here.

The wording is the wording the plan skill sent before the loop was extracted into the
`review` skill, line breaks included, because the line breaks are part of the
assembled prompt. **The assembled prompt must stay byte for byte identical to the one
`/pdca:plan` sent before the extraction**: a change to a slot here is a change to
`/pdca:plan` and is reviewed as one. `{{path}}` comes from the invocation, not from a
lens, and this lens carries no other markers.

## reader

You are about to execute a plan, alone, in a session that has just started. You
have the plan file and the repository. There is no one to ask: no author to
clarify with, no user to answer a question. Whatever the plan does not say, you
will have to guess, and a wrong guess runs unsupervised.

## noun

plan

## exempt

The Handoff section, and the frontmatter's `status`, `branch`, `closeout_push` and
`permalink` fields, are written or refreshed after this review, so
do not flag them as missing, empty, or out of date with the rest of the plan — they
are the one part of the file you are not reviewing.

## checklist

- Facts asserted without evidence, or asserted and contradicted by the repository.
  The Verified Context section records a command behind each fact — spot-check
  them.
- Steps that assume knowledge not in the file.
- Acceptance criteria that are not runnable commands with unambiguous expected
  results, that would pass without the work being done, or that cannot run in
  this environment.
- A Pre-Flight section that would not stop you: a model, effort or permission mode
  that is not named literally enough to compare against, no check that the plan's
  own /goal is driving the session, a privilege the tasks need that nothing probes,
  or a check whose failure you could talk yourself past.
- A source whose requirements are not accounted for: a Requirements table that omits
  something the ticket or the spec asks for, or a disposition you would feel entitled
  to overrule by reading the source yourself.
- A Closeout section you could not execute: an unprobed comment channel, a
  permalink template that is guessed rather than verified against this repository's
  host, an order that removes the plan file before its final state is committed, or a
  deletion folded into the preservation commit so the linked commit no longer holds the
  file.
- A requirement adopted without a decision behind it — a non-functional demand from
  the ticket or the spec that the plan implements because it was written down, where
  the Verified Context suggests something else and the table records no reasoning.
- Ambiguity you could resolve two ways, where the two ways differ materially.
- Ordering that matters but is not stated.
- Anything the plan asks for that you could not actually carry out.

## success

you could
execute this plan unattended and be confident the result is what the author wanted.

## cost

A plan that ships with a real
gap costs an entire unattended run; a nit costs nothing.

## gate

the handoff

## answers

In the plan itself — a sentence in Constraints & Non-Goals, or beside the fact
in question, saying what was raised and why it does not hold. A reason that
lives only in the round report is invisible to the next cold reader, which
raises the same blocker again and burns a round on a disagreement nobody
advanced.
