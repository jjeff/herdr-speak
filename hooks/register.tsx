// Claude Code mod: a click toggle above the prompt, the recap rules in the
// system prompt (so compaction can't drop them), and the last state carried
// into new sessions. The /speak skill still works and stays in sync.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

const isOn = atom({ plugin: 'herdr-speak', key: 'isOn' } as const, null)

const OFF_RULES =
  'Speech mode is OFF for this session: end responses without the 🔊 recap line.'

// The ON half of the skill, which stays the one source of the recap rules.
const onRules = (skill: string) => {
  const start = skill.indexOf('Otherwise: ')
  const end = skill.lastIndexOf('Reply now')

  return start < 0 || end < start
    ? skill
    : skill.slice(start + 'Otherwise: '.length, end).trim()
}

const set = async ($: EngineInterface, value: boolean) => {
  await update($, isOn, () => value)
  await $.store.set('isOn', value)
}

export const register: Register = on => {
  let rules = ''

  on('session.start', async ($, e, next) => {
    rules = onRules(await $.fs.read(`${$.plugin.root}/skills/speak/SKILL.md`))

    const isFresh = (await read($, isOn)) === null

    if (isFresh && (await $.store.get('isOn')) === true) {
      await update($, isOn, () => true)
    }

    return next(e)
  })

  // The typed toggle: the skill tells the model, this keeps the mod in step.
  on('prompt.submit', async ($, e, next) => {
    const typed = /^\/(?:herdr-speak:)?speak\b(.*)/s.exec(e.text.trim())

    if (typed) {
      await set($, !/\boff\b/i.test(typed[1] ?? ''))
    }

    return next(e)
  })

  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    const state = await read($, isOn)

    if (state === null || rules === '') {
      return composed
    }

    const section = {
      id: 'herdr-speak:recap',
      text: state ? `Speech mode is ON. ${rules}` : OFF_RULES,
      scope: 'session',
    } as const

    return { sections: [...composed.sections, section] }
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const state = await read($, isOn)

    if (e.props.hasSurvey || state === null) {
      return next(e)
    }

    const { Button } = $.ui.resolve(e)

    // 🔉, not 🔊: the Speaker reads a pane line that starts with 🔊 as a recap.

    return (
      <Button
        key="toggle"
        plain
        label={state ? '🔉 speech on' : '🔇 speech off'}
        onPress={() => set($, !state)}
      />
    )
  })
}
