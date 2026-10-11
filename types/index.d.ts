// null until speech is turned on or off in this session.
export type SpeakState = boolean | null

declare module 'claude-code' {
  interface PluginState {
    'herdr-speak': { isOn: SpeakState }
  }
}
