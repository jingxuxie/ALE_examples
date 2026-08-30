import json
import sys
from pathlib import Path


def main():
    participant = Path(__file__).resolve().parents[1]
    root = participant.parents[3]
    output = Path(sys.argv[1]).resolve()
    probes = []
    for path in (participant.parent / "evaluator/hidden/isolation_canary.txt", root / "private/generation_canary.txt", participant.parent / "status.json"):
        try:
            path.read_bytes()
            probes.append({"path": str(path), "readable": True})
        except OSError as error:
            probes.append({"path": str(path), "readable": False, "result": type(error).__name__})
    report = {"participant_readable": (participant / "TASK.md").is_file(), "private_reads_denied": all(not item["readable"] for item in probes), "probes": probes}
    (output / "isolation_audit.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if not report["private_reads_denied"]:
        raise SystemExit("isolation failed")


if __name__ == "__main__":
    main()
