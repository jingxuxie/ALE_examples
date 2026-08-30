import datetime
import hashlib
import json
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "concept_2/attempts"


def main():
    states = {}
    for index in (1, 2):
        stem = ROOT / f"v_{index}"
        launch = json.loads(Path(str(stem) + ".launch.json").read_text())
        started = datetime.datetime.fromisoformat(launch["started_utc"]).timestamp()
        destination = ROOT / f"v_{index}_cutoff"
        destination.mkdir(exist_ok=True)
        states[index] = {"stem": stem, "deadline": started + 3600, "destination": destination, "last_signature": None, "captured_sha256": None, "complete": False}
    while not all(state["complete"] for state in states.values()):
        for index, state in states.items():
            if state["complete"]:
                continue
            now = time.time()
            source = state["stem"] / "solution.json"
            if now <= state["deadline"] and source.exists():
                try:
                    before = source.stat()
                    signature = (before.st_mtime_ns, before.st_size)
                    if signature != state["last_signature"] and before.st_size <= 2097152:
                        content = source.read_bytes()
                        after = source.stat()
                        json.loads(content)
                        if (after.st_mtime_ns, after.st_size) == signature and time.time() <= state["deadline"]:
                            temporary = state["destination"] / "pending.json"
                            temporary.write_bytes(content)
                            temporary.replace(state["destination"] / "solution.json")
                            state["last_signature"] = signature
                            state["captured_sha256"] = hashlib.sha256(content).hexdigest()
                            state["captured_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    pass
            try:
                launch = json.loads(Path(str(state["stem"]) + ".launch.json").read_text())
            except json.JSONDecodeError:
                continue
            finished = launch.get("finished_utc") is not None
            if finished or time.time() >= state["deadline"]:
                state["complete"] = True
                report = {"attempt": index, "complete": True, "artifact_directory": str(state["destination"]), "deadline_utc": datetime.datetime.fromtimestamp(state["deadline"], datetime.timezone.utc).isoformat(), "captured_utc": state.get("captured_utc"), "captured_sha256": state["captured_sha256"], "reason": "agent_completed" if finished else "one_hour_deadline", "post_deadline_writes_are_not_scored": True}
                Path(str(state["stem"]) + ".cutoff.json").write_text(json.dumps(report, indent=2))
                print(json.dumps(report), flush=True)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
