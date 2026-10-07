#!/usr/bin/env python3
"""herdr-speak speaker.

Runs on YOUR machine (open it while Local is selected in Herdr). Polls agents on
Local and on every enabled saved SSH machine. When an agent settles after
working, reads its recent output, finds the last line starting with the speaker
emoji, and speaks it with macOS `say`.

Config (optional): $HERDR_PLUGIN_CONFIG_DIR/config.json, see config.example.json.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERDR = os.environ.get("HERDR_BIN_PATH") or shutil.which("herdr") or "herdr"
CONFIG_DIR = os.environ.get(
    "HERDR_PLUGIN_CONFIG_DIR", os.path.expanduser("~/.config/herdr-speak")
)
MARKER = "\U0001F50A"  # 🔊
RECAP_RE = re.compile(MARKER + r"\s*(.+?)\s*$")
BUSY = {"working", "blocked"}
SETTLED = {"idle", "done"}
READ_LINES = "150"
MACHINE_REFRESH_SECONDS = 60
CALL_TIMEOUT = 10


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def load_config():
    cfg = {"voice": None, "rate": 210, "include_local": True,
           "machines": None, "poll_seconds": 2}
    path = os.path.join(CONFIG_DIR, "config.json")
    try:
        with open(path) as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    except Exception as e:  # bad JSON shouldn't kill the speaker
        log(f"config error in {path}: {e}")
    return cfg


def herdr(args, machine=None):
    cmd = [HERDR] + (["--machine", machine] if machine else []) + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=CALL_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None
    return r.stdout if r.returncode == 0 else None


def parse_json(text):
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        return None


def walk(obj):
    """Yield every dict nested anywhere in obj."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def status_of(d):
    for key in ("status", "state", "agent_status"):
        v = d.get(key)
        if isinstance(v, str):
            return v.lower()
        if isinstance(v, dict) and isinstance(v.get("state"), str):
            return v["state"].lower()
    return None


def find_agents(obj):
    """Defensive: return {pane_id: (status, completion_seq)} for any dict that
    looks like an agent. completion_seq is None when Herdr doesn't report it
    (older servers, a pane that is working, or one that never finished a turn)."""
    agents = {}
    for d in walk(obj):
        pane = d.get("pane_id") or d.get("pane")
        st = status_of(d)
        if isinstance(pane, str) and st:
            seq = d.get("completion_seq")
            agents[pane] = (st, seq if isinstance(seq, int) else None)
    return agents


def list_machines(cfg):
    """Return {machine_id: label} for enabled saved machines."""
    if cfg.get("machines"):
        return {m: m for m in cfg["machines"]}
    data = parse_json(herdr(["machine", "list", "--json"]))
    found = {}
    for d in walk(data):
        mid = d.get("id") or d.get("profile_id")
        if isinstance(mid, str) and "label" in d and d.get("enabled", True):
            found[mid] = d.get("label") or mid
    return found


def extract_recap(text):
    lines = (text or "").splitlines()
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        if MARKER not in line or f'"{MARKER}' in line or f"`{MARKER}" in line:
            continue  # skip quoted instruction text
        m = RECAP_RE.search(line)
        if m and m.group(1):
            # Agent TUIs hard-wrap long lines at the pane width, so the recap
            # continues on the following lines until a blank one.
            parts = [m.group(1)]
            for cont in lines[i + 1:]:
                if not cont.strip():
                    break
                parts.append(cont.strip())
            return " ".join(parts)
    return None


def speak(text, cfg):
    cmd = ["say"]
    if cfg.get("voice"):
        cmd += ["-v", cfg["voice"]]
    if cfg.get("rate"):
        cmd += ["-r", str(cfg["rate"])]
    if subprocess.run(cmd + [text]).returncode != 0:
        # Most often: a Premium or Siri voice without Full Disk Access.
        log("`say` failed: Premium and Siri voices need Full Disk Access for the "
            "terminal app running Herdr (then restart the Speaker); see the README")


def main():
    if not shutil.which("say"):
        log("`say` not found: run the speaker on your Mac, with Local selected.")
        sys.exit(1)
    cfg = load_config()
    log(f"herdr-speak listening (herdr: {HERDR})")
    last_seen = {}     # (machine, pane) -> (status, completion_seq)
    last_spoken = {}   # (machine, pane) -> hash of last recap spoken
    machines, refreshed = {}, 0.0

    while True:
        if time.time() - refreshed > MACHINE_REFRESH_SECONDS:
            new = list_machines(cfg)
            if new != machines:
                log("machines: " + (", ".join(new.values()) or "none"))
            machines, refreshed = new, time.time()

        targets = ([(None, "local")] if cfg["include_local"] else []) + list(machines.items())
        for machine, label in targets:
            agents = find_agents(parse_json(herdr(["agent", "list"], machine)))
            for pane, (st, seq) in agents.items():
                key = (machine, pane)
                prev, prev_seq = last_seen.get(key, (None, None))
                # Herdr drops completion_seq while a pane is working; keep the last one.
                last_seen[key] = (st, prev_seq if seq is None else seq)
                if prev is None:
                    continue  # baseline
                # A changed completion_seq catches turns shorter than one poll;
                # the status transition covers servers that don't report it.
                if (seq is not None and seq != prev_seq) or (prev in BUSY and st in SETTLED):
                    out = herdr(["agent", "read", pane, "--source",
                                 "recent-unwrapped", "--lines", READ_LINES], machine)
                    recap = extract_recap(out)
                    if not recap:
                        continue
                    h = hashlib.sha1(recap.encode()).hexdigest()
                    if last_spoken.get(key) == h:
                        continue  # already said this one
                    last_spoken[key] = h
                    log(f"[{label} {pane}] {MARKER} {recap}")
                    speak(recap, load_config())  # re-read so voice/rate edits apply live

        time.sleep(float(cfg.get("poll_seconds", 2)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
