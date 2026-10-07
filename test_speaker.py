"""Run with: python3 -m unittest"""

import unittest

import speaker


class ExtractRecap(unittest.TestCase):
    def test_last_recap_wins(self):
        text = "⏺ 🔊 Old recap.\nmore output\n⏺ 🔊 Did the thing. Want more?\n\n❯ "
        self.assertEqual(speaker.extract_recap(text), "Did the thing. Want more?")

    def test_joins_wrapped_recap(self):
        # Claude Code hard-wraps at the pane width; recent-unwrapped keeps the break.
        text = ("  🔊 Codex works now. I need you to log in, then tell\n"
                "  me so I can finish testing.\n\n❯ ")
        self.assertEqual(speaker.extract_recap(text),
                         "Codex works now. I need you to log in, then tell me so I can finish testing.")

    def test_strips_tui_borders(self):
        # pi draws a box edge at the end of each line and a rule under the reply.
        text = " 🔊 Grass is green.      ┃\n part two.   ┃\n─────────\n"
        self.assertEqual(speaker.extract_recap(text), "Grass is green. part two.")

    def test_skips_quoted_instruction_text(self):
        self.assertIsNone(speaker.extract_recap("Reply with `🔊 Speech mode on.`"))
        self.assertIsNone(speaker.extract_recap('in the form "🔊 <recap>"'))

    def test_no_recap(self):
        self.assertIsNone(speaker.extract_recap("no marker here"))
        self.assertIsNone(speaker.extract_recap(None))


class FindAgents(unittest.TestCase):
    def test_herdr_agent_list_shape(self):
        # Trimmed from real `herdr agent list` output (herdr 0.9.3).
        data = {"result": {"type": "agent_list", "agents": [
            {"pane_id": "w1:p1", "agent_status": "idle", "completion_seq": 7,
             "agent_session": {"agent": "claude", "kind": "id"}},
            {"pane_id": "w1:p2", "agent_status": "working"},
        ]}}
        self.assertEqual(speaker.find_agents(data), {
            "w1:p1": ("idle", 7),
            "w1:p2": ("working", None),
        })

    def test_garbage(self):
        self.assertEqual(speaker.find_agents(None), {})
        self.assertEqual(speaker.find_agents({"pane_id": 3, "status": "idle"}), {})


if __name__ == "__main__":
    unittest.main()
