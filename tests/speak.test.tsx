import { expect, mock, test } from 'claude-code/testing'

const SKILL = 'If off: stop.\n\nOtherwise: end with a recap.\n\nReply now with one line.'
const START = { cwd: '/', surface: 'terminal', isInteractive: true } as const
const COMPOSE = {
  model: 'm',
  promptModel: 'm',
  surfaces: ['terminal'],
  tools: [],
  outputStyle: null,
  traits: [],
} as const
const BAND = {
  plugin: 'herdr-speak',
  surface: 'terminal',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isWorking: false,
    maxRows: 10,
    bodyColumns: 80,
    scroll: { offset: 0, bodyRows: 10 },
    view: {},
  },
} as const

test('the last state carries over, and the toggles change the prompt', async ($, on) => {
  mock.store(on, { isOn: true })
  on('fs.read', () => ({ value: SKILL }))
  on('prompt.compose', () => ({ sections: [] }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('prompt.submit', (_, e) => ({ text: e.text }))

  const recap = async () => (await $.prompt.compose(COMPOSE)).sections.at(-1)?.text

  await $.session.start(START)
  expect(await recap()).toBe('Speech mode is ON. end with a recap.')

  await $.prompt.submit({ text: '/speak off', wait: false, origin: { kind: 'composer' } })
  expect(await recap()).toContain('OFF')

  const band = await $.ui.mount(BAND)
  expect((await band.find({ key: 'toggle' }))?.text).toBe('🔇 speech off')
  await band.press({ key: 'toggle' })
  expect(await recap()).toContain('ON')
  expect((await band.find({ key: 'toggle' }))?.text).toBe('🔉 speech on')
})

test('a session where speech was never on is left alone', async ($, on) => {
  mock.store(on)
  on('fs.read', () => ({ value: SKILL }))
  on('prompt.compose', () => ({ sections: [] }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))

  await $.session.start(START)
  expect((await $.prompt.compose(COMPOSE)).sections).toEqual([])
})
