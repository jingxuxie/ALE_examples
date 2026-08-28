import json
import os
from pathlib import Path
import signal
import time


root = Path(__file__).resolve().parent.parent
for kind in ["weighted", "fractional", "ewoc"]:
    logs = root / "author" / "runs"
    record_path = logs / (kind + "_pilot.running.json")
    record = json.loads(record_path.read_text())
    log_path = logs / (kind + "_pilot.log")
    text = log_path.read_text()
    if text.strip() != "Reading additional input from stdin...":
        raise RuntimeError("Refusing to stop a run that advanced beyond the stdin preflight")
    process_id = record["pid"]
    command = Path("/proc") / str(process_id) / "cmdline"
    if b"codex" not in command.read_bytes():
        raise RuntimeError("Process identity changed")
    os.killpg(process_id, signal.SIGTERM)
    time.sleep(1)
    for suffix in ["log", "running.json", "json"]:
        path = logs / (kind + "_pilot." + suffix)
        if path.exists():
            path.rename(logs / (kind + "_stdin_preflight." + suffix))
    attempt = root / "pilots" / kind / "attempt"
    if any(attempt.iterdir()):
        raise RuntimeError("Unexpected task writes during stdin preflight")
print("Only three pre-inference stdin-blocked processes were stopped; attempts remain empty.")
