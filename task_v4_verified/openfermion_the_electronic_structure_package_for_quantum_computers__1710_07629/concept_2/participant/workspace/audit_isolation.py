import json
import os
import sys
from pathlib import Path


def main():
    participant = Path(__file__).resolve().parents[1]
    output = Path(sys.argv[1]).resolve()
    private_paths = [participant.parent / "evaluator/hidden/isolation_canary.txt", participant.parent.parent / "private/generation_canary.txt", participant.parent / "status.json"]
    results = []
    for path in private_paths:
        try:
            with path.open("rb") as stream:
                stream.read(1)
            results.append({"path": str(path), "readable": True, "result": "unexpected access"})
        except OSError as error:
            results.append({"path": str(path), "readable": False, "result": type(error).__name__})
    report = {"participant_readable": (participant / "TASK.md").is_file(), "private_reads_denied": all(not item["readable"] for item in results), "probes": results, "cwd": os.getcwd()}
    (output / "isolation_audit.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if not report["private_reads_denied"]:
        raise SystemExit("private files unexpectedly readable; stop the attempt")


if __name__ == "__main__":
    main()
