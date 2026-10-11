# herdr-speak

Two halves:

- `speaker.py` is the Herdr plugin (`herdr-plugin.toml`) that reads 🔊 recaps aloud with macOS `say`. It is agent-agnostic: it watches every agent kind Herdr lists.
- `skills/speak/SKILL.md` is the `/speak` toggle that makes an agent end each reply with a `🔊 <recap>` line. It is the single source of truth for the toggle text; each host's packaging only points at it.

`hooks/register.tsx` is a Claude Code mod on top of the skill: a toggle above the prompt, the last state carried into new sessions (`$.store`), and the recap rules in the system prompt. It takes the rules from `SKILL.md`, the text between `Otherwise: ` and `Reply now`. Its toggle shows 🔉, never 🔊, because the Speaker reads any pane line that starts with 🔊 as a recap.

Run tests with `python3 -m unittest`, and the mod's with `claude plugin validate .` and `claude plugin test .`.

## Herdr facts (verified on 0.9.3)

- `herdr agent list` returns `{"result":{"agents":[{pane_id, agent, agent_status, completion_seq?, ...}]}}`. `completion_seq` bumps once per finished turn and is absent while the agent is working. The Speaker keys on it to catch turns shorter than one poll.
- The Speaker reads the recap with `herdr agent read <pane> --source recent-unwrapped` and speaks the last line starting with 🔊.
- Tab-bar entries (`ui.tab_bar_right`) are display-only: no click handlers, and a `command` entry gets `HERDR_BIN_PATH` but no plugin environment. So the Speaker writes 🔊 or 🔇 to `status` in the config dir, which `herdr plugin config-dir` can find; there is no CLI that prints the state dir.
- `herdr pane report-metadata <pane> --source <id> --token speak=🔊` sets a token that sidebar rows show as `$speak`; `--clear-token speak` removes it. It forwards through `--machine`, and the token lasts until the pane closes.
- `herdr --machine <label> <command>` forwards any API command to a saved SSH machine. `herdr machine list --json` lists them.
- Plugin commands (startup hooks, actions, panes) get `HERDR_PLUGIN_ID`, `HERDR_PLUGIN_CONFIG_DIR`, `HERDR_PLUGIN_STATE_DIR`, and `HERDR_BIN_PATH`, with the plugin directory as cwd. Plugin v1 has no supervised daemons: `[[startup]]` hooks are one-shot, so the Speaker relaunches itself detached (`--background`) and holds `speaker.lock` in the state dir so reruns never start a second copy. Its log is `speaker.log` there (`~/.local/state/herdr/plugins/herdr-speak/` on macOS).
- Other commands reach the running Speaker over a UDP socket on 127.0.0.1, whose port is in `speaker.pid` (`<pid> <port>`): the `pane.agent_status_changed` event hook sends `poke` (poll now), and `--skip` sends `skip`. Mute is the `muted` file in the state dir. Signals aren't used, because Windows has no SIGUSR1 or SIGUSR2.
- Every manifest command runs `./herdr-speak.cmd`, a file that is both a shell script (the `:;` line) and a batch file. Verified on Herdr 0.9.3: Windows runs a `.cmd` only when the command names it with its extension, macOS runs the file through `sh` without a `#!` line, and action ids must be unique even across `platforms`, so per-platform duplicates aren't possible. On Windows `python3` is often the Microsoft Store placeholder, so the batch half uses `py -3`.
- On Windows the detached Speaker has no console, so every child process needs `CREATE_NO_WINDOW` or it flashes a window, and stdout and Herdr's output must be decoded as UTF-8 (the default is cp1252).
- Premium and Siri voices need Full Disk Access for the terminal app that runs Herdr. Only processes started after the grant get it, so restart the Speaker after granting.

## Live test recipe

Test a host end to end through Herdr, with the Speaker running on Local:

1. `herdr tab create --workspace <ws> --cwd <trusted dir> --no-focus` — use a directory the agent already trusts; a trust prompt blocks startup.
2. `herdr agent start t --kind <kind> --pane <pane>`
3. `herdr agent prompt <pane> "<text>" --wait --until done --until idle` — first turn on the toggle, then send a normal prompt. Wait longer than the Speaker's poll interval (2 s) between prompts, or it only speaks the later recap.
4. Read `speaker.log` in the plugin state dir and confirm the Speaker logged the recap. After changing `speaker.py`, run `herdr plugin action invoke herdr-speak.start` to restart it.
5. Close the test tab.

Some hosts need a model flag after `--`, for example `herdr agent start t --kind opencode --pane <p> -- --model <provider/model>`.

## Adding a host

Herdr supports more agents than this repo packages. Add one only when someone needs it:

1. Read the host's current docs for skill discovery paths, plugin or extension manifests, and how a user invokes a skill and passes arguments. Hosts rename and replace themselves often; Gemini CLI became Antigravity mid-2026.
2. Prefer zero new files. A host that finds `skills/` in an installed package, or reads `~/.agents/skills`, needs only a README row. Add a manifest only when the host requires one, and keep the toggle text in `SKILL.md`.
3. Run the live test recipe above. Confirm that `herdr agent list` shows the pane. Hermes v0.21 is not listed by Herdr 0.9.3, so its recaps are never spoken.
4. Add the host to the README install table with its exact toggle syntax.
