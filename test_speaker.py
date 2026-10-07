"""Run with: python3 -m unittest"""

import json
import pathlib
import re
import unittest

import speaker


class ExtractRecap(unittest.TestCase):
    def test_last_recap_wins(self):
        text = "⏺ 🔊 Old recap.\nmore output\n⏺ 🔊 Did the thing. Want more?\n\n❯ "
        self.assertEqual(speaker.extract_recap(text), "Did the thing. Want more?")

    def test_joins_wrapped_recap(self):
        # Claude Code hard-wraps at the pane width; recent-unwrapped keeps the break.
        text = "  🔊 Codex works now. I need you to log in, then tell\n  me so I can finish testing.\n\n❯ "
        self.assertEqual(
            speaker.extract_recap(text),
            "Codex works now. I need you to log in, then tell me so I can finish testing.",
        )

    def test_strips_tui_borders(self):
        # pi draws a box edge at the end of each line and a rule under the reply.
        text = " 🔊 Grass is green.      ┃\n part two.   ┃\n─────────\n"
        self.assertEqual(speaker.extract_recap(text), "Grass is green. part two.")

    def test_skips_quoted_instruction_text(self):
        self.assertIsNone(speaker.extract_recap("Reply with `🔊 Speech mode on.`"))
        self.assertIsNone(speaker.extract_recap('in the form "🔊 <recap>"'))
        # OpenCode shows the skill body, template line included, in the pane.
        self.assertIsNone(speaker.extract_recap("┃  🔊 <spoken recap>\n┃  Rules for the recap:\n"))

    def test_no_recap(self):
        self.assertIsNone(speaker.extract_recap("no marker here"))
        self.assertIsNone(speaker.extract_recap(None))


class SourceName(unittest.TestCase):
    def setUp(self):
        self.real_herdr = speaker.herdr
        lists = {
            "workspace": {
                "result": {
                    "workspaces": [{"workspace_id": "w1", "label": "webapp", "active_tab_id": "w1:t9"}]
                }
            },
            "tab": {
                "result": {"tabs": [{"tab_id": "w1:t2", "workspace_id": "w1", "label": "Fix login bug"}]}
            },
        }
        speaker.herdr = lambda args, machine=None: json.dumps(lists[args[0]])
        self.agents = {
            "result": {
                "agents": [
                    {"pane_id": "w1:p3", "tab_id": "w1:t2", "workspace_id": "w1", "agent_status": "done"}
                ]
            }
        }

    def tearDown(self):
        speaker.herdr = self.real_herdr

    def test_remote_names_machine_workspace_tab(self):
        name = speaker.source_name(self.agents, "w1:p3", "id1", "studio", ["machine", "workspace", "tab"])
        self.assertEqual(name, "studio, webapp, Fix login bug")

    def test_local_skips_machine(self):
        name = speaker.source_name(self.agents, "w1:p3", None, "local", ["machine", "tab"])
        self.assertEqual(name, "Fix login bug")


class FindAgents(unittest.TestCase):
    def test_herdr_agent_list_shape(self):
        # Trimmed from real `herdr agent list` output (herdr 0.9.3).
        data = {
            "result": {
                "type": "agent_list",
                "agents": [
                    {
                        "pane_id": "w1:p1",
                        "agent_status": "idle",
                        "completion_seq": 7,
                        "agent_session": {"agent": "claude", "kind": "id"},
                    },
                    {"pane_id": "w1:p2", "agent_status": "working"},
                ],
            }
        }
        self.assertEqual(
            speaker.find_agents(data),
            {
                "w1:p1": ("idle", 7),
                "w1:p2": ("working", None),
            },
        )

    def test_garbage(self):
        self.assertEqual(speaker.find_agents(None), {})
        self.assertEqual(speaker.find_agents({"pane_id": 3, "status": "idle"}), {})


if __name__ == "__main__":
    unittest.main()


class Classify(unittest.TestCase):
    def test_baseline_is_silent(self):
        self.assertEqual(speaker.classify(None, "done", 4, baseline=True), (None, ("done", 4)))

    def test_seq_bump_is_a_finished_turn(self):
        # Catches a turn shorter than one poll: idle before and after.
        self.assertEqual(speaker.classify(("idle", 4), "idle", 5)[0], "finished")

    def test_same_seq_is_nothing(self):
        self.assertIsNone(speaker.classify(("idle", 4), "idle", 4)[0])

    def test_working_keeps_last_seq(self):
        # Herdr omits completion_seq while working.
        self.assertEqual(speaker.classify(("idle", 4), "working", None), (None, ("working", 4)))

    def test_settling_without_seq_is_finished(self):
        self.assertEqual(speaker.classify(("working", None), "done", None)[0], "finished")

    def test_blocked_alerts_once(self):
        self.assertEqual(speaker.classify(("working", 4), "blocked", None)[0], "blocked")
        self.assertIsNone(speaker.classify(("blocked", 4), "blocked", None)[0])

    def test_new_pane_with_finished_turn(self):
        # Herdr may list an agent only after its first turn has finished.
        self.assertEqual(speaker.classify(None, "done", 1)[0], "finished")

    def test_new_working_pane_is_nothing_yet(self):
        self.assertIsNone(speaker.classify(None, "working", None)[0])


ROOT = pathlib.Path(__file__).parent


class Manifests(unittest.TestCase):
    def test_json_parses(self):
        for path in ROOT.glob("**/*.json"):
            if ".git" not in path.parts:
                json.loads(path.read_text())

    def test_versions_match(self):
        def json_version(name):
            return json.loads((ROOT / name).read_text())["version"]

        toml = (ROOT / "herdr-plugin.toml").read_text()
        versions = {
            "herdr-plugin.toml": re.search(r'^version = "(.+)"', toml, re.M).group(1),
            ".claude-plugin/plugin.json": json_version(".claude-plugin/plugin.json"),
            "gemini-extension.json": json_version("gemini-extension.json"),
        }
        self.assertEqual(len(set(versions.values())), 1, versions)

    def test_herdr_manifest_parses(self):
        try:
            import tomllib
        except ImportError:
            self.skipTest("tomllib needs Python 3.11+")
        manifest = tomllib.loads((ROOT / "herdr-plugin.toml").read_text())
        self.assertEqual(manifest["id"], "herdr-speak")

    def test_skills_have_frontmatter(self):
        for skill in ROOT.glob("skills/*/SKILL.md"):
            head = skill.read_text().split("---")[1]
            self.assertRegex(head, rf"(?m)^name: {skill.parent.name}$", skill)
            self.assertRegex(head, r"(?m)^description: \S", skill)
