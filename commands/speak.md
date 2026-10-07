---
description: Turn spoken recaps on or off for this session
argument-hint: "[on|off]"
---

The user ran `/speak $ARGUMENTS`.

If the argument is "off": speech mode is now OFF for this session. Stop adding the 🔊 recap line to your responses. Reply with exactly one line: `🔇 Speech mode off.`

Otherwise: speech mode is now ON for the rest of this session. A tool on the user's machine reads your final 🔊 line aloud with text-to-speech when you finish each turn. From now on, end EVERY response with one final line in this exact form:

🔊 <spoken recap>

Rules for the recap:
- One line, no line breaks, at most two short sentences (about 35 words).
- Plain spoken English. No markdown, code, file paths, URLs, symbols, or numbers that would sound bad read aloud. Say "the config file", not `~/.config/app/settings.json`.
- Say what you did and the outcome. If you need something from the user, end with that question.
- Do not repeat the full response; it is still on screen.
- It must be the very last line of the response.

Reply now with exactly one line: `🔊 Speech mode on.`
