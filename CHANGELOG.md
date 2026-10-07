# Changelog

All notable changes to herdr-speak. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- A README recipe for OpenAI-compatible speech servers, such as VoiceStudio.
- Your own instructions, such as AGENTS.md, CLAUDE.md, or text after the toggle, now win over the toggle's default recap rules. The README shows how to change recap length, tone, and language.

### Fixed

- The Full Disk Access hint appears only for macOS `say`, not for a custom `say_command`.

## [0.2.0] - 2026-10-07

### Added

- The `/speak` toggle is a shared Agent Skill, `skills/speak/SKILL.md`, packaged for Claude Code, Codex, Antigravity, Gemini CLI, OpenCode, pi, and Hermes.
- The Speaker runs on Linux and Windows as well as macOS. A new `say_command` setting plugs in any speech engine.
- The Speaker runs in the background. Herdr starts it on launch, and a lock keeps it to one copy.
- "<name> needs you" alerts when an agent stops to ask you something. Turn them off with `alert_blocked`.
- The agent's name is spoken before a recap when the source changes. The parts come from the `announce` setting.
- Herdr actions: `mute`, `skip`, `log`, and `start` (restart).
- A Herdr event hook wakes the Speaker as soon as a local agent changes state.
- CI on macOS, Ubuntu, and Windows; ruff; a contributing guide; PR and issue templates.

### Fixed

- Recaps that the agent's terminal UI wrapped onto several lines are spoken in full.
- Terminal UI borders, hook output, and the skill's own recap template are no longer read aloud.
- An agent's first turn is spoken even when Herdr detects the agent after that turn has finished.

### Changed

- `commands/speak.md` moved to `skills/speak/SKILL.md`. `/speak` still works in Claude Code.
- The Speaker no longer opens a visible pane. Use the `log` action to watch it.

## [0.1.0] - 2026-10-07

### Added

- First packaged release: the Herdr plugin and the Claude Code `/speak` command.
- Recaps from turns shorter than one poll are caught through Herdr's `completion_seq`.

[Unreleased]: https://github.com/jjeff/herdr-speak/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/jjeff/herdr-speak/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jjeff/herdr-speak/releases/tag/v0.1.0
