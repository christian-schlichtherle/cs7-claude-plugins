import type { Register } from 'claude-code'

// Shows the planning step on the spinner while a turn runs, beside where
// `/goal` draws its own indicator. The skills write the step to a status file
// (see "Keep the status line posted" in skills/plan/SKILL.md); this module
// only reads it, so a session without the file draws the spinner untouched.

// The step the status file last held, or undefined when there is none.
let step: string | undefined

async function refresh($) {
  const sid = await $.session.id()
  const home = await $.env.get('HOME')
  let read: string | undefined
  try {
    read = (await $.fs.read(`${home}/.cache/claude-pdca/${sid}.status`)).trim() || undefined
  } catch {
    read = undefined
  }
  if (read !== step) {
    step = read
    $.ui.invalidate('ui.render')
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await refresh($)
    return next(e)
  })
  // The skills write the file from Bash, so a finished tool call is when it changes.
  on('tool.call', async ($, e, next) => {
    const result = await next(e)
    await refresh($)
    return result
  })
  on('turn.complete', async ($, e, next) => {
    await refresh($)
    return next(e)
  })
  on('ui.render', { component: 'Spinner' }, ($, e, next) => {
    if (step === undefined) return next(e)
    // A rewritten suffix is drawn as given, so add the ellipsis the engine would.
    const text = e.props.message ?? e.props.word
    const ellipsis = text.endsWith('…') ? '' : '…'
    return next({ ...e, props: { ...e.props, suffix: `${ellipsis} · ◎ pdca ${step}` } })
  })
}
