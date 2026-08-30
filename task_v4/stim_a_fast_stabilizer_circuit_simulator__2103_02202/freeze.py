import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=Path)
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--verify", action="store_true")
    arguments = parser.parse_args()
    root = arguments.concept.resolve()
    destination = root / "adversary" / ("freeze_v_" + str(arguments.generation) + ".json")
    observed = {"participant": hashes(root / "participant"), "evaluator": hashes(root / "evaluator")}
    if arguments.verify:
        expected = json.loads(destination.read_text())
        if observed != expected["hashes"]:
            raise SystemExit("frozen assets changed")
        print("Frozen participant and evaluator hashes match: " + str(root))
        return
    if destination.exists():
        raise SystemExit("refusing to overwrite a frozen generation")
    value = {"frozen_at": datetime.now(timezone.utc).isoformat(), "generation": arguments.generation,
             "hashes": observed, "status_at_freeze": json.loads((root / "status.json").read_text())}
    destination.write_text(json.dumps(value, indent=2) + "\n")
    print("Frozen: " + str(destination))


if __name__ == "__main__":
    main()
