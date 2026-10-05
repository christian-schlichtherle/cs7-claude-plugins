import { expect, mock, test } from 'claude-code/testing'

const SPINNER = { word: 'Swirling', message: null, suffix: '…', mode: 'tool-use' } as const

// Stands in for a session whose status file holds `status` (none when
// undefined), starts it, draws the spinner with `props`, and returns the
// suffix the engine is handed to draw after the plugin's hook.
async function drawnSuffix($, on, status: string | undefined, props = SPINNER) {
  let suffix: string | undefined
  on('session.id', () => ({ value: 'sid-1' }))
  mock.env(on, { HOME: '/home/u' })
  on('fs.read', (_$, e) =>
    status !== undefined && e.path === '/home/u/.cache/claude-pdca/sid-1.status'
      ? { value: status }
      : { deny: `no such file: ${e.path}` })
  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  on('ui.render', { component: 'Spinner' }, ($, e) => {
    suffix = e.props.suffix
    const { Text } = $.ui.resolve(e)
    return h(Text, {}, e.props.word)
  })
  await $.session.start({ cwd: '/work', surface: 'terminal' })
  await $.ui.render({ surface: 'terminal', component: 'Spinner', requestId: 'spinner', props })
  return suffix
}

test('adds the step to the spinner', async ($, on) => {
  expect(await drawnSuffix($, on, 'review 2/10\n')).toBe('… · ◎ pdca review 2/10')
})

test('leaves the spinner alone without a status file', async ($, on) => {
  expect(await drawnSuffix($, on, undefined)).toBe('…')
})

test('adds no second ellipsis to a message that ends in one', async ($, on) => {
  expect(await drawnSuffix($, on, 'verify', { ...SPINNER, message: 'Compacting…' })).toBe(' · ◎ pdca verify')
})
