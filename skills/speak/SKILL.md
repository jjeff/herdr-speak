---
name: speak
description: Turn spoken recaps on or off for this session. Use only when the user runs /speak or asks to turn speech on or off.
argument-hint: "[on|off]"
disable-model-invocation: true
---

The user ran the speak toggle.

If the user asked for "off": speech mode is now OFF for this session. Stop adding the 🔊 recap line to your responses. Reply with exactly one line: `🔇 Speech mode off.`

Otherwise: speech mode is now ON for the rest of this session. A tool on the user's machine reads your final 🔊 line aloud with text-to-speech when you finish each turn. From now on, end EVERY response with one final line in this exact form:

🔊 <spoken recap>

If the user's own instructions (AGENTS.md, CLAUDE.md, memory, or text after the toggle) say how to write the recap, such as its length, tone, language, or content, follow them over the rules below. The recap stays one line starting with 🔊, because the tool reads only that line.

Rules for the recap:
- One line, no line breaks, at most two short sentences (about 35 words).
- Plain spoken English. No markdown, code, file paths, URLs, symbols, or numbers that would sound bad read aloud. Say "the config file", not `~/.config/app/settings.json`.
- Say what you did and the outcome. If you need something from the user, end with that question.
- Do not repeat the full response; it is still on screen.
- It must be the very last line of the response.

Reply now with exactly one line: `🔊 Speech mode on.`
