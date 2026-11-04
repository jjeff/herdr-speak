// herdr-speak for the Herdr desktop app: keeps the Speaker running, shows 🔊 or
// 🔇, and takes the mute and skip keys (keys.json: "herdr-speak.mute").
//
// Install: link this folder to ~/.config/herdr-app/mods/herdr-speak. The
// Speaker runs from the repo the link points at, with the Herdr TUI plugin's
// config and state folders, so the TUI and the app share one Speaker, its
// lock, its mute switch and its config.json.
// ponytail: macOS and Linux paths only; Windows needs %APPDATA% equivalents.

import { View, div } from "gpui-kit";
import { h_flex } from "gpui-base";
import { exec, home, appHome, readTextFile, watchFolder, nextCommand, notify, theme } from "herdr";

const CONFIG = `${home()}/.config/herdr/plugins/config/herdr-speak`;
const STATE = `${home()}/.local/state/herdr/plugins/herdr-speak`;
const MUTED = "\u{1f507}";

// Run herdr-speak.cmd from the repo this mod folder links to.
function speaker(flag) {
  const script =
    'd=$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd) && ' +
    `HERDR_PLUGIN_ID=herdr-speak HERDR_PLUGIN_CONFIG_DIR="${CONFIG}" HERDR_PLUGIN_STATE_DIR="${STATE}" ` +
    'exec sh "$d/herdr-speak.cmd" "$1"';
  return exec("sh", ["-c", script, `${appHome()}/mods/herdr-speak/main.js`, flag]);
}

export default class Speak extends View {
  init(_props, cx) {
    this.mark = "";
    cx.spawn(async (cx) => {
      // A no-op when a Speaker is already running (its lock), TUI-started or not.
      const r = await speaker("--background");
      if (r.code !== 0) notify({ title: "herdr-speak", body: r.stderr.trim() || "the Speaker did not start", level: "error" });
      // The Speaker writes the mark to its status file when it starts and on every mute toggle.
      for (;;) {
        this.mark = ((await readTextFile(`${CONFIG}/status`)) ?? "").trim();
        cx.notify();
        await watchFolder(CONFIG);
      }
    });
    cx.spawn(async () => {
      for (;;) {
        const c = await nextCommand();
        if (c === "mute" || c === "skip") await speaker(`--${c}`);
      }
    });
  }

  render() {
    const t = theme();
    // Sits at the right end of the status bar, so it copies that bar's look.
    return h_flex().size_full().px(14).items_center().justify_end().bg(t.chrome).border_t(1).border_color(t.border)
      .text_size(11.8).text_color(t.muted)
      .child(
        div().id("speak").cursor_pointer().hover((s) => s.text_color(t.foreground))
          .on_click(() => speaker("--mute"))
          .child(this.mark ? `${this.mark} ${this.mark === MUTED ? "muted" : "speaking"}` : "speaker starting"),
      );
  }
}
