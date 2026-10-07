# herdr-speak

[![CI](https://github.com/jjeff/herdr-speak/actions/workflows/ci.yml/badge.svg)](https://github.com/jjeff/herdr-speak/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Hear a short spoken recap when a coding agent (Claude Code, Codex, Antigravity, Gemini CLI, OpenCode, pi, or Hermes) finishes a turn, even when that session runs on another machine you reach through [Herdr](https://herdr.dev).

herdr-speak has two halves, and both live in this repo:

- **A `/speak` skill** (`skills/speak/SKILL.md`) for your coding agent. With speech on, the agent ends every reply with one line: `🔊 <spoken recap>`.
- **A Herdr plugin** that runs a background "Speaker" on the computer in front of you: macOS, Linux, or Windows. Herdr starts it automatically. It watches agents on Local and on your saved SSH machines, and reads each new 🔊 line aloud with the system voice.

## Why herdr-speak

Other ways to hear from your agents make different trade-offs:

- **Herdr's own sounds and toasts** (`[ui.sound]`, `[ui.toast]`) tell you *that* an agent finished or needs input. They don't tell you what it did.
- **Herdr plugins that summarize the pane,** such as [herdr-announcer](https://github.com/nhclink16/herdr-announcer) and [herdr-bleatr](https://github.com/zetlen/herdr-bleatr), run a separate model call on each agent's terminal output. They need no setup inside the agent, but each announcement costs a model call, the summary is a guess from scraped text, and they run on each Herdr server, so remote audio has to be routed back to you over SSH.
- **A stop hook that pipes the reply into `say`** plays the audio on the machine where the agent runs. For an agent on a remote machine you reach through Herdr, that's a computer you aren't sitting at, so you hear nothing. The hook also reads a reply written for the screen, with its code, paths, and tables.

herdr-speak asks the agent that did the work for a one-line recap written to be heard. The Speaker is installed only on the computer you listen at and reaches every machine through Herdr, so remote machines need nothing but the skill. Recaps from several agents queue instead of being dropped, and with speech off a session costs nothing.

## How it works

```
 Remote machine                            Your computer (Herdr "Local")
 ──────────────                            ────────────────────────
 Agent session                             Speaker (speaker.py, background)
   /speak  → ends every reply with           polls `herdr --machine X agent list`
   "🔊 <one-line spoken recap>"              sees a turn finish
                                             `herdr --machine X agent read <pane>`
                                             finds the last 🔊 line → speaks it
```

- **One switch per session.** Run `/speak` or `/speak off` inside the agent. With speech off, the agent writes no recap, so it costs nothing and nothing is spoken.
- **Audio plays where you are.** Install the Herdr plugin only on the computer you listen at. The Speaker runs there and reaches remote machines through `herdr --machine`.
- **The 🔊 line stays on screen,** so you can read along.

## Requirements

- Python 3.9 or newer on the machine where you listen, which runs macOS, Linux, or Windows. macOS ships with it.
- A speech command there: macOS `say` and Windows' built-in voice work out of the box; on Linux, install `spd-say` (speech-dispatcher) or `espeak-ng`, or set `say_command`.
- Herdr 0.9.3 or newer on every machine.
- A supported agent on every machine that runs sessions: Claude Code, Codex, Antigravity, Gemini CLI, OpenCode, pi, or Hermes.

## Install

**1. On the computer you listen at, install the Herdr plugin:**

```sh
herdr plugin install jjeff/herdr-speak
```

**2. On every machine that runs agents** (the one you listen at included, if you run sessions there), install the `/speak` skill for each agent you use:

| agent | install | toggle |
|---|---|---|
| Claude Code | `claude plugin marketplace add jjeff/herdr-speak`<br>`claude plugin install herdr-speak@herdr-speak` | `/speak` |
| Codex | `codex plugin marketplace add jjeff/herdr-speak`<br>`codex plugin add herdr-speak@herdr-speak` | `$herdr-speak:speak` |
| Antigravity (`agy`) | `git clone https://github.com/jjeff/herdr-speak ~/.herdr-speak`<br>`agy plugin install ~/.herdr-speak` | `/speak` |
| Gemini CLI (enterprise and API-key accounts) | `gemini extensions install https://github.com/jjeff/herdr-speak` | `/speak` |
| OpenCode | `git clone https://github.com/jjeff/herdr-speak ~/.herdr-speak`<br>`ln -s ~/.herdr-speak/skills/speak ~/.config/opencode/skills/speak` | `/speak` |
| pi | `pi install git:github.com/jjeff/herdr-speak` | `/skill:speak` |
| Hermes | `hermes skills install jjeff/herdr-speak/skills/speak` | `/speak` |

Restart the agent after installing. Add `on` or `off` after the toggle; on is the default.

**3. Add each remote machine to Herdr** if you haven't already: `herdr machine add <host>`.

**4. Start the Speaker.** Herdr starts it in the background every time Herdr starts. To start it now without restarting Herdr, run:

```sh
herdr plugin action invoke herdr-speak.start
```

That action also restarts a running Speaker. Only one copy ever runs.

To watch what the Speaker hears and says, run `herdr plugin action invoke herdr-speak.log`. It opens a pane that follows the log; close the pane when you're done, and the Speaker keeps running. You can bind any action to a key in your Herdr config:

```toml
[[keys.command]]
key = "prefix+m"
type = "plugin_action"
command = "herdr-speak.mute"
description = "mute speaker"
```

## Use

In any agent session, run the toggle from the table above (in Claude Code its full name is `/herdr-speak:speak`). You should hear "Speech mode on." Add `off` to stop.

When any agent stops to ask you something, the Speaker says "<name> needs you", even in sessions without `/speak`. Turn that off with `alert_blocked` (see [Configure](#configure)).

These Herdr actions control the Speaker. Run each with `herdr plugin action invoke herdr-speak.<id>`, or bind it to a key:

| id | does |
|---|---|
| `mute` | mute or unmute the Speaker; it keeps listening and stays muted across restarts |
| `skip` | stop the recap being spoken now |
| `log` | open a pane that follows the Speaker log |
| `start` | start or restart the Speaker |

Antigravity, Gemini CLI, and Hermes can't stop the model from loading the skill on its own; the skill's description tells it to wait for `/speak`.

## Other agents

The Speaker works with any agent Herdr detects (`herdr agent start --help` lists the kinds). The agent only needs a way to load the toggle in `skills/speak/SKILL.md`. To add one that isn't in the install table:

1. **Check that Herdr detects it.** Start the agent in a Herdr pane, then run `herdr agent list`. The pane must appear with an `agent_status`. If it doesn't, the Speaker can't hear that agent.
2. **Load the skill.** Most agents now read [Agent Skills](https://agentskills.io). Clone this repo, then link the skill into the agent's skills directory. Many agents read `~/.agents/skills`:

   ```sh
   git clone https://github.com/jjeff/herdr-speak ~/.herdr-speak
   mkdir -p ~/.agents/skills
   ln -s ~/.herdr-speak/skills/speak ~/.agents/skills/speak
   ```

   If the agent has no skill support, make a custom command or saved prompt from the body of `SKILL.md`. As a last resort, paste the body into the session to turn speech on.
3. **Find the toggle's name.** Many agents turn each skill into `/speak`. Others namespace it, as in `/herdr-speak:speak`, or use their own syntax, such as `$speak` or `/skill:speak`.
4. **Test it.** Run the toggle, ask a short question, and listen. The Speaker log (`herdr-speak.log` action) shows every recap it speaks.

If it works, please open a pull request that adds the agent to the install table.

## Configure

Create `config.json` in the plugin's config directory:

```sh
cp config.example.json "$(herdr plugin config-dir herdr-speak)/config.json"
```

| key | default | meaning |
|---|---|---|
| `voice` | system voice | macOS only: a `say -v` voice name; `say -v '?'` lists them |
| `rate` | 210 | macOS only: words per minute |
| `say_command` | the platform's | an argv list that speaks; `"{text}"` in an argument is replaced by the recap, otherwise the recap arrives on stdin |
| `include_local` | true | also watch agents on Local |
| `machines` | all enabled | list of machine ids or labels to watch |
| `poll_seconds` | 2 | seconds between checks |
| `alert_blocked` | true | say "<name> needs you" when an agent stops to ask you something |
| `announce` | `["machine", "workspace", "tab"]` | names to say before a recap from a different agent than the last one; `machine` applies to remote agents only, `[]` turns names off |

`voice`, `rate`, `say_command`, `announce`, and `alert_blocked` apply to the next recap. Run the `herdr-speak.start` action to restart the Speaker after changing the other keys.

**Voices on macOS.** Leave `voice` unset to use your macOS system voice (System Settings → Accessibility → Spoken Content → System voice). That is the only way to use a Siri voice, because `say -v` doesn't list them. To pick a voice by name, set its exact name from `say -v '?'`. Better voices, such as "Ava (Premium)", are under System voice → Manage Voices….

**Other voices and platforms.** On Windows the Speaker uses the default voice from Settings → Time & language → Speech. On Linux it uses the first of `spd-say`, `espeak-ng`, or `espeak` it finds. To use anything else, such as Piper or a local OpenAI-compatible speech server, point `say_command` at it. For example, `["espeak-ng", "-v", "en-gb", "{text}"]` picks a British espeak voice.

**Premium and Siri voices need Full Disk Access.** They load their models from a protected folder. Without access, `say` crashes with `failed to open bnns mmap file … errno: 1` and the Speaker logs a hint. Grant Full Disk Access to the terminal app that runs Herdr (System Settings → Privacy & Security → Full Disk Access), then quit and restart Herdr. The Speaker inherits Herdr's access, and only processes started after the grant get it. The built-in compact voices work without it.

## Limits

- **Recaps play one at a time.** When several agents finish together, each recap waits for the one before it, and starts with the agent's name.
- **Only the latest recap is spoken.** If a session finishes several turns between two checks, you hear the last one.
- **Remote machines are polled.** Herdr's event hook wakes the Speaker the moment a local agent changes state, but remote events fire on their own servers, so the Speaker checks remote machines every `poll_seconds`. The checks run one machine at a time.
- **Unreachable machines slow the checks.** An unreachable machine can delay each check by up to 10 seconds. List only the machines you want in `machines`.
- **Hermes recaps aren't spoken yet.** The toggle works, but Herdr 0.9.3 doesn't list Hermes v0.21 panes in `herdr agent list`, so the Speaker never sees their turns finish.
- **Background work delays the recap.** Herdr reports a Claude Code session as working while its background agents or commands run, so a turn that ends with background work pending is spoken only after that work finishes and a later turn ends.
- **Detection uses Herdr's `completion_seq`** to catch turns shorter than one poll. Older servers that don't report it fall back to watching `working` → `done`/`idle`, which can miss a very short turn.

## Development

Link your checkout instead of installing:

```sh
herdr plugin link .
claude plugin marketplace add ./
claude plugin install herdr-speak@herdr-speak
codex plugin marketplace add ./
agy plugin install "$PWD"
gemini extensions link .
ln -s "$PWD/skills/speak" ~/.config/opencode/skills/speak
pi install ./
```

For Hermes, add the checkout's `skills` directory to `skills.external_dirs` in `~/.hermes/config.yaml`.

Run the checks that CI runs with `ruff check .`, `ruff format --check .`, and `python3 -m unittest`. See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Alternatives

If you'd rather not set up each agent, don't use Herdr, or only want speech from one agent on one machine, one of these may suit you better. Listed as of October 2026; descriptions are from each project's README.

| project | agents | how it speaks |
|---|---|---|
| [nhclink16/herdr-announcer](https://github.com/nhclink16/herdr-announcer) | any agent in Herdr | A Herdr plugin that summarizes the pane with a model call when an agent finishes or needs input; dashboard, snooze, and mutes |
| [zetlen/herdr-bleatr](https://github.com/zetlen/herdr-bleatr) | any agent in Herdr | A Herdr plugin that speaks a model-written sentence for agents in tabs you aren't looking at |
| [blacktop/mcp-tts](https://github.com/blacktop/mcp-tts) | any MCP host, including Claude Code, Codex, and Gemini CLI | An MCP server the agent calls to speak, with macOS `say`, ElevenLabs, OpenAI, and local voices |
| [kyleoliveiro/claude-speak](https://github.com/kyleoliveiro/claude-speak) | Claude Code | A stop hook summarizes each reply in one line and speaks it with Kokoro, a local model |
| [hopchouinard/claude-speak](https://github.com/hopchouinard/claude-speak) | Claude Code | Spoken summaries each turn, plus a mode where Claude speaks mid-turn; OpenAI or ElevenLabs voices |
| [ybouhjira/claude-code-tts](https://github.com/ybouhjira/claude-code-tts) | Claude Code | An MCP plugin with a stop hook that speaks the first sentence of each reply with OpenAI TTS |
| [cris-m/claude_voice](https://github.com/cris-m/claude_voice) | Claude Code | Speaks replies, notifications, and command completions with local voice models |
| [silverdolphin863/claude-speak](https://github.com/silverdolphin863/claude-speak) | Claude Code | Speaks replies with Microsoft neural voices through edge-tts, no API key |
| [melderan/claude-code-tts](https://github.com/melderan/claude-code-tts) | Claude Code | A stop hook that speaks new reply text with Piper, a local model |
| [praneybehl/claude-code-voice-hook](https://github.com/praneybehl/claude-code-voice-hook) | Claude Code | A stop hook that sends each reply to a local OpenAI-compatible TTS server |

Know another one? Open a pull request.

## License

MIT
