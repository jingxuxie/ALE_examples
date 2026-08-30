"""Run with a writable output directory before participant development."""

import json
import os
from pathlib import Path
import sys


def main():
    participant = Path(__file__).resolve().parents[1]
    top_level = participant.parents[3]
    output = Path(sys.argv[1]).resolve()
    private_paths = [participant.parent / "evaluator/hidden/isolation_canary.txt",
                     top_level / "private/generation_canary.txt", participant.parent / "status.json"]
    probes = []
    for path in private_paths:
        try:
            with path.open("rb") as stream:
                stream.read(1)
            probes.append({"path": str(path), "readable": True, "result": "unexpected access"})
        except OSError as error:
            probes.append({"path": str(path), "readable": False, "result": type(error).__name__})
    report = {"participant_readable": bool((participant / "TASK.md").read_text()),
              "private_reads_denied": all(not row["readable"] for row in probes),
              "probes": probes, "cwd": os.getcwd()}
    (output / "isolation_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["private_reads_denied"]:
        raise SystemExit("Private content unexpectedly readable")


if __name__ == "__main__":
    main()
