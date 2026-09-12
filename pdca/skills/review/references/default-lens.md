# The default lens

The lens a standalone `/pdca:review` uses when the caller supplies none. Unlike a
caller's own lens, this one is a **template**: its `reader` carries `{{statement}}`
and its `noun` carries `{{noun}}`. Copy it to the scratch directory, replace both from
the reader statement — the noun being whatever the artifact is called in that
statement, `runbook`, `spec`, `README`, or plain `document` when nothing better is on
offer — and assemble from the copy. Assembling from this file unfilled would send
`{{statement}}` to the reviewer.

The wording below is deliberately generic. Anything sharper belongs in a caller's own
lens, the way `/pdca:plan` keeps its opinions in
`${CLAUDE_PLUGIN_ROOT}/skills/plan/references/executor-lens.md`.

## reader

You are about to act on this document, alone, in a session that has just started:
{{statement}}. You have the document and the repository it lives in. There is no one
to ask: no author to clarify with, no user to answer a question. Whatever the
document does not say, you will have to guess, and a wrong guess costs you the
outcome it promises.

## noun

{{noun}}

## exempt

## checklist

- Facts asserted without evidence, or asserted and contradicted by the repository —
  spot-check the ones the rest leans on.
- Steps that assume knowledge not in the file.
- A check or an instruction that would pass, or appear to succeed, without producing
  the outcome the document promises.
- Ambiguity you could resolve two ways, where the two ways differ materially.
- Ordering that matters but is not stated.
- Anything the document asks for that you could not actually carry out.

## success

you could follow this document to the end on your own and be confident the result is
what its author wanted.

## cost

A document that ships with a real gap costs whoever follows it the outcome they came
for, at the moment they have nobody to ask; a nit costs nothing.

## gate

the verdict

## answers

By the user. The loop stops, the disagreement goes to them with the reviewer's
wording and the session's reason beside it, and they decide what the document should
say — the reviewer's fix, or their own reasoning folded into the document's own text,
never into a notes file or a companion document. Then a fresh round reads the result
cold.
