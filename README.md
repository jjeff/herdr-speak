# herdr-speak

Hear a short spoken recap when a Claude Code session finishes a turn, even when that session runs on another machine you reach through [Herdr](https://herdr.dev).

herdr-speak has two halves, and both live in this repo:

- **A Claude Code plugin** that adds `/speak`. With speech on, Claude ends every reply with one line: `🔊 <spoken recap>`.
- **A Herdr plugin** that runs a small "Speaker" pane on your Mac. It watches agents on Local and on your saved SSH machines, and reads each new 🔊 line aloud with macOS `say`.

## How it works

```
 Remote machine                            Your Mac (Herdr "Local")
 ──────────────                            ────────────────────────
 Claude Code session                       Speaker pane (speaker.py)
   /speak  → ends every reply with           polls `herdr --machine X agent list`
   "🔊 <one-line spoken recap>"              sees a turn finish
                                             `herdr --machine X agent read <pane>`
                                             finds the last 🔊 line → `say`
```

- **One switch per session.** Run `/speak` or `/speak off` inside Claude Code. With speech off, Claude writes no recap, so it costs nothing and nothing is spoken.
- **Audio plays where you are.** Herdr runs a plugin pane on the server that owns it, so open the Speaker while **Local** is selected. It reaches remote machines through `herdr --machine`.
- **The 🔊 line stays on screen,** so you can read along.

## Requirements

- macOS on the machine where you listen (`say` and `python3` ship with it).
- Herdr 0.9.3 or newer on every machine.
- Claude Code on every machine that runs sessions.

## Install

**1. On your Mac, install the Herdr plugin:**

```sh
herdr plugin install jjeff/herdr-speak
```

**2. On every machine that runs Claude Code** (your Mac included, if you run sessions there), install the Claude Code plugin:

```sh
claude plugin marketplace add jjeff/herdr-speak
claude plugin install herdr-speak@herdr-speak
```

**3. Add each remote machine to Herdr** if you haven't already: `herdr machine add <host>`.

**4. Start the Speaker.** Select **Local** in Herdr, then run:

```sh
herdr plugin action invoke herdr-speak.start
```

You can also bind it to a key in your Herdr config:

```toml
[[keys.command]]
key = "prefix+s"
type = "plugin_action"
command = "herdr-speak.start"
description = "start speaker"
```

## Use

In any Claude Code session, run `/speak` (its full name is `/herdr-speak:speak`). You should hear "Speech mode on." Run `/speak off` to stop.

## Configure

Create `config.json` in the plugin's config directory:

```sh
cp config.example.json "$(herdr plugin config-dir herdr-speak)/config.json"
```

| key | default | meaning |
|---|---|---|
| `voice` | system voice | a `say -v` voice name; `say -v '?'` lists them |
| `rate` | 210 | words per minute |
| `include_local` | true | also watch agents on Local |
| `machines` | all enabled | list of machine ids or labels to watch |
| `poll_seconds` | 2 | seconds between checks |

`voice` and `rate` apply to the next recap. Restart the Speaker after changing the other keys.

**Voices.** Leave `voice` unset to use your macOS system voice (System Settings → Accessibility → Spoken Content → System voice). That is the only way to use a Siri voice, because `say -v` doesn't list them. To pick a voice by name, set its exact name from `say -v '?'`. Better voices, such as "Ava (Premium)", are under System voice → Manage Voices….

**Premium and Siri voices need Full Disk Access.** They load their models from a protected folder. Without access, `say` crashes with `failed to open bnns mmap file … errno: 1` and the Speaker logs a hint. Grant Full Disk Access to the terminal app that runs Herdr (System Settings → Privacy & Security → Full Disk Access), then restart the Speaker. The built-in compact voices work without it.

## Limits

- **Only the latest recap is spoken.** If a session finishes several turns between two polls, you hear the last one.
- **Polling is sequential.** An unreachable machine can delay each check by up to 10 seconds. List only the machines you want in `machines`.
- **Detection uses Herdr's `completion_seq`** to catch turns shorter than one poll. Older servers that don't report it fall back to watching `working` → `done`/`idle`, which can miss a very short turn.

## Development

Link your checkout instead of installing:

```sh
herdr plugin link .
claude plugin marketplace add ./
claude plugin install herdr-speak@herdr-speak
python3 -m unittest
```

## License

MIT
