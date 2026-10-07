# herder-speak

Hear a short spoken recap when Claude Code finishes a turn. This works even when Claude Code is running on a remote machine you reach through [Herdr](https://herdr.dev).

## How it works

```
 Mac mini (remote)                         Your laptop (Local)
 ─────────────────                         ───────────────────
 Claude Code session                       Herdr "speaker" pane (speaker.py)
   /speak on  → ends every reply with        polls `herdr --machine X agent list`
   "🔊 <one-line spoken recap>"              agent goes working → done
                                             `herdr --machine X agent read <pane>`
                                             finds last 🔊 line → `say`
```

- **One switch, per session:** `/speak` / `/speak off` inside Claude Code. When it's off, Claude generates no recap, so there's no extra latency and nothing gets spoken.
- **Audio plays where you are.** Herdr plugins run on the server that owns the pane, so the speaker must be opened while **Local** is selected. It then reaches remote machines through `--machine`.
- **The 🔊 line is visible on screen,** so you can read along while it speaks.

## Install

**1. On each machine that runs Claude Code** (the Mac minis):

```sh
mkdir -p ~/.claude/commands
cp claude/commands/speak.md ~/.claude/commands/
```

**2. On your laptop:**

```sh
herdr plugin link /path/to/herder-speak/herdr-plugin
# optional config
cp herdr-plugin/config.example.json "$(herdr plugin config-dir herder-speak)/config.json"
```

Make sure each Mac mini is a saved machine (`herdr machine add <host>`). Then, with **Local** selected:

```sh
herdr plugin action invoke herder-speak.start
```

Optional keybinding in your Herdr config:

```toml
[[keys.command]]
key = "prefix+s"
type = "plugin_action"
command = "herder-speak.start"
description = "start speaker"
```

## Use

In any Claude Code session, run `/speak` to turn speech on. You should hear "Speech mode on." Run `/speak off` to stop.

## Config (`config.json` in the plugin config dir)

| key | default | meaning |
|---|---|---|
| `voice` | system default | `say -v` voice (`say -v '?'` lists them) |
| `rate` | 210 | words per minute |
| `include_local` | true | also watch agents on Local |
| `machines` | all enabled | list of machine IDs/labels to watch |
| `poll_seconds` | 2 | how often to check agent state |

## Unverified assumptions (check first)

- **JSON shape.** The `agent list` and `machine list --json` output is parsed defensively, by looking for `pane_id` plus a `status`/`state` key. Run `herdr --machine <label> agent list` once to confirm.
- **Turn detection.** A turn is recognised by the `working → done/idle` transition seen on a 2-second poll. A turn shorter than one poll interval could be missed.
- **`min_herdr_version`** is a guess. Remote forwarding needs a recent Herdr on both ends.
