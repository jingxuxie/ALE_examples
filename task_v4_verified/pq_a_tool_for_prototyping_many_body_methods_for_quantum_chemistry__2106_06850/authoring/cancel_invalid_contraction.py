import datetime
import json
import os
import signal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "concept_1"
status = json.loads((ROOT / "status.json").read_text())
certificate = json.loads((ROOT / "adversary/portfolio/response_universal/verified_summary.json").read_text())
if status["status"] != "invalid" or not certificate["response_family_impossible"]:
    raise RuntimeError("cancellation requires verified task invalidity")
terminated = []
for directory in Path("/proc").iterdir():
    if not directory.name.isdigit():
        continue
    try:
        command = (directory / "cmdline").read_bytes().decode().split("\0")
        if not command or Path(command[0]).name != "timeout" or str(ROOT / "participant") not in command:
            continue
        if not any(Path(argument).name == "run_allowlisted_codex.sh" for argument in command if argument):
            continue
        process_id = int(directory.name)
        os.kill(process_id, signal.SIGTERM)
        terminated.append(process_id)
    except (OSError, UnicodeError, ValueError):
        continue
report = {"reason": "target certified infeasible; cancellation is not hardness evidence",
          "terminated_timeout_pids": terminated,
          "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
(ROOT / "attempts/cancellation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
