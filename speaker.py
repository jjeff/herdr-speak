#!/usr/bin/env python3
"""herdr-speak speaker.

Runs on YOUR machine: Herdr's startup hook launches it in the background with
--background (see herdr-plugin.toml). Polls agents on Local and on every
enabled saved SSH machine. When an agent settles after
working, reads its recent output, finds the last line starting with the speaker
emoji, and speaks it with macOS `say`.

Config (optional): $HERDR_PLUGIN_CONFIG_DIR/config.json, see config.example.json.
Log and lock: $HERDR_PLUGIN_STATE_DIR/speaker.log and speaker.lock.

  speaker.py                 run in the foreground (development)
  speaker.py --background    detach, log to speaker.log; no-op if one is running
  speaker.py --restart       stop the running speaker first (combine with --background)
  speaker.py --poke          make the running speaker poll now (Herdr event hook)
  speaker.py --skip          stop the recap being spoken now
  speaker.py --mute          toggle muting; the speaker keeps listening
"""

import fcntl
import hashlib
import json
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import time

HERDR = os.environ.get("HERDR_BIN_PATH") or shutil.which("herdr") or "herdr"
CONFIG_DIR = os.environ.get("HERDR_PLUGIN_CONFIG_DIR", os.path.expanduser("~/.config/herdr-speak"))
STATE_DIR = os.environ.get("HERDR_PLUGIN_STATE_DIR", CONFIG_DIR)
LOCK_PATH = os.path.join(STATE_DIR, "speaker.lock")
LOG_PATH = os.path.join(STATE_DIR, "speaker.log")
MUTE_PATH = os.path.join(STATE_DIR, "muted")
LOG_MAX_BYTES = 1_000_000
MARKER = "\U0001f50a"  # 🔊
RECAP_RE = re.compile(MARKER + r"\s*(.+?)\s*$")
BOX_CHARS = "".join(map(chr, range(0x2500, 0x2580)))  # TUI borders, e.g. pi's ┃
BUSY = {"working", "blocked"}
SETTLED = {"idle", "done"}
READ_LINES = "150"
MACHINE_REFRESH_SECONDS = 60
CALL_TIMEOUT = 10


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def load_config():
    cfg = {
        "voice": None,
        "rate": 210,
        "include_local": True,
        "machines": None,
        "poll_seconds": 2,
        "announce": ["machine", "workspace", "tab"],
        "alert_blocked": True,
    }
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


def classify(prev, status, seq, baseline=False):
    """Decide what one poll of one pane means.

    prev is the (status, completion_seq) remembered from the last poll, or None
    for a pane not seen before. Returns (event, state): event is "finished",
    "blocked", or None, and state is what to remember for the next poll.
    """
    prev_status, prev_seq = prev or (None, None)
    # Herdr drops completion_seq while a pane is working; keep the last one.
    state = (status, prev_seq if seq is None else seq)
    if baseline:
        return None, state  # don't replay what happened before startup
    if prev_status is None:
        # Herdr lists a new agent only once it detects it, which can be after
        # its first turn (often the /speak toggle) has finished.
        prev_status = "working" if seq is not None or status in SETTLED else status
    if status == "blocked" and prev_status != "blocked":
        return "blocked", state
    # A changed completion_seq catches turns shorter than one poll; the status
    # transition covers servers that don't report it.
    if (seq is not None and seq != prev_seq) or (prev_status in BUSY and status in SETTLED):
        return "finished", state
    return None, state


def source_name(agents_data, pane, machine, machine_label, parts):
    """Spoken name for a pane, built from cfg["announce"] parts in order:
    "machine" (remote panes only), "workspace", and "tab" labels."""
    info = next((d for d in walk(agents_data) if d.get("pane_id") == pane), {})
    names = []
    for part in parts:
        if part == "machine":
            if machine:
                names.append(machine_label)
        elif part in ("workspace", "tab"):
            want = info.get(part + "_id")
            listing = parse_json(herdr([part, "list"], machine)) if want else None
            hit = next((d for d in walk(listing) if d.get(part + "_id") == want), {})
            if hit.get("label"):
                names.append(hit["label"])
    return ", ".join(names)


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
        if m and m.group(1) and not m.group(1).startswith("<"):  # "<spoken recap>" template
            # Agent TUIs hard-wrap long lines at the pane width, so the recap
            # continues on the following lines until a blank one.
            parts = [m.group(1)]
            for cont in lines[i + 1 :]:
                if not cont.strip(BOX_CHARS + " \t"):
                    break
                parts.append(cont)
            text = " ".join(p.strip(BOX_CHARS + " \t") for p in parts)
            return text or None
    return None


SAYING = None  # the running `say`, so --skip can stop it


def speak(text, cfg):
    global SAYING
    if os.path.exists(MUTE_PATH):
        log("(muted)")
        return
    cmd = ["say"]
    if cfg.get("voice"):
        cmd += ["-v", cfg["voice"]]
    if cfg.get("rate"):
        cmd += ["-r", str(cfg["rate"])]
    SAYING = subprocess.Popen(cmd + [text])
    rc = SAYING.wait()
    SAYING = None
    if rc == -signal.SIGTERM:
        log("(skipped)")
    elif rc != 0:
        # Most often: a Premium or Siri voice without Full Disk Access.
        log(
            "`say` failed: Premium and Siri voices need Full Disk Access for the "
            "terminal app running Herdr (then restart the Speaker); see the README"
        )


def take_lock():
    """Hold an exclusive lock for this process's lifetime, so Herdr's startup
    hook (which reruns on server handoff) never starts a second speaker."""
    os.makedirs(STATE_DIR, exist_ok=True)
    f = open(LOCK_PATH, "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    f.seek(0)
    f.truncate()
    f.write(str(os.getpid()))
    f.flush()
    return f


def signal_running(sig):
    """Send sig to the running speaker. False when none is running."""
    try:
        with open(LOCK_PATH) as f:
            os.kill(int(f.read().strip()), sig)
        return True
    except (OSError, ValueError):
        return False


def toggle_mute():
    if os.path.exists(MUTE_PATH):
        os.remove(MUTE_PATH)
        state = "unmuted"
    else:
        os.makedirs(STATE_DIR, exist_ok=True)
        open(MUTE_PATH, "w").close()
        state = "muted"
        signal_running(signal.SIGUSR2)  # and stop anything mid-sentence
    herdr(["notification", "show", "herdr-speak", "--body", f"Speaker {state}", "--sound", "none"])


def stop_running():
    if not signal_running(signal.SIGTERM):
        return  # nothing running
    for _ in range(30):  # wait for its lock to free up
        lock = take_lock()
        if lock:
            lock.close()
            return
        time.sleep(0.1)


def detach():
    if os.fork():
        os._exit(0)  # parent: let Herdr's hook finish
    os.setsid()  # leave the hook's process group so it isn't reaped with it
    os.makedirs(STATE_DIR, exist_ok=True)
    try:
        if os.path.getsize(LOG_PATH) > LOG_MAX_BYTES:
            os.truncate(LOG_PATH, 0)  # ponytail: no rotation, just start over
    except OSError:
        pass
    out = os.open(LOG_PATH, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)
    os.dup2(out, 1)
    os.dup2(out, 2)


def wake_pipe():
    """Return a fd that turns readable when a signal arrives, so the poll sleep
    ends early on --poke. (Lock and Event waits aren't interruptible on macOS.)"""
    r, w = os.pipe()
    os.set_blocking(r, False)
    os.set_blocking(w, False)
    signal.set_wakeup_fd(w)
    signal.signal(signal.SIGUSR1, lambda *_: None)
    signal.signal(signal.SIGUSR2, lambda *_: SAYING and SAYING.terminate())
    return r


def nap(fd, seconds):
    select.select([fd], [], [], seconds)
    try:
        os.read(fd, 512)
    except BlockingIOError:
        pass


def main():
    if "--poke" in sys.argv:
        return signal_running(signal.SIGUSR1)
    if "--skip" in sys.argv:
        return signal_running(signal.SIGUSR2)
    if "--mute" in sys.argv:
        return toggle_mute()
    if "--restart" in sys.argv:
        stop_running()
    if "--background" in sys.argv:
        detach()
    lock = take_lock()  # noqa: F841 (held until exit)
    if not lock:
        log("already running")
        return
    if not shutil.which("say"):
        log("`say` not found: run the speaker on your Mac, with Local selected.")
        sys.exit(1)
    cfg = load_config()
    wake = wake_pipe()
    log(f"herdr-speak listening (herdr: {HERDR})")
    last_seen = {}  # (machine, pane) -> (status, completion_seq)
    last_spoken = {}  # (machine, pane) -> hash of last recap spoken
    baselined = set()  # machines whose agents were listed at least once
    last_source = None  # (machine, pane) of the last recap spoken
    machines, refreshed = {}, 0.0

    while True:
        if time.time() - refreshed > MACHINE_REFRESH_SECONDS:
            new = list_machines(cfg)
            if new != machines:
                log("machines: " + (", ".join(new.values()) or "none"))
            machines, refreshed = new, time.time()

        targets = ([(None, "local")] if cfg["include_local"] else []) + list(machines.items())
        for machine, label in targets:
            data = parse_json(herdr(["agent", "list"], machine))
            if data is None:
                continue  # unreachable; baseline it once it answers
            first_listing = machine not in baselined
            baselined.add(machine)
            for pane, (st, seq) in find_agents(data).items():
                key = (machine, pane)
                event, last_seen[key] = classify(last_seen.get(key), st, seq, first_listing)
                if event == "blocked":
                    live = load_config()
                    if live.get("alert_blocked", True):
                        # No recap to read: the agent stopped to ask. Always name it.
                        name = (
                            source_name(data, pane, machine, label, live.get("announce") or []) or "An agent"
                        )
                        last_source = key
                        log(f"[{label} {pane}] {name} needs you.")
                        speak(f"{name} needs you.", live)
                    continue
                if event == "finished":
                    out = herdr(
                        ["agent", "read", pane, "--source", "recent-unwrapped", "--lines", READ_LINES],
                        machine,
                    )
                    recap = extract_recap(out)
                    if not recap:
                        continue
                    h = hashlib.sha1(recap.encode()).hexdigest()
                    if last_spoken.get(key) == h:
                        continue  # already said this one
                    last_spoken[key] = h
                    live = load_config()  # re-read so voice/rate/announce edits apply live
                    if key != last_source:
                        # Name the source only when it changes, so one agent stays quiet.
                        name = source_name(data, pane, machine, label, live.get("announce") or [])
                        if name:
                            recap = f"{name}. {recap}"
                    last_source = key
                    log(f"[{label} {pane}] {MARKER} {recap}")
                    speak(recap, live)

        nap(wake, float(cfg.get("poll_seconds", 2)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
