import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=Path)
    args = parser.parse_args()
    root = args.concept.resolve()
    output = root / "adversary/target_freeze.json"
    if output.exists():
        raise RuntimeError("Target already frozen; create an explicit new ratchet generation instead")
    report = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(), "participant_sha256": hashes(root / "participant"),
              "evaluator_sha256": hashes(root / "evaluator"), "status_at_freeze": json.loads((root / "status.json").read_text()),
              "model": "ultima-alpha", "fresh_time_limit_seconds": 3600}
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(output)
