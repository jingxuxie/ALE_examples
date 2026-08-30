import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--generation", type=int, default=1)
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    output = concept / "adversary" / f"frozen_generation_{arguments.generation}.json"
    if output.exists():
        raise RuntimeError("generation already frozen")
    hashes = {}
    for section in ("participant", "evaluator"):
        for path in sorted((concept / section).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                hashes[str(path.relative_to(concept))] = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata = {"frozen_at": datetime.now(timezone.utc).isoformat(),
                "generation": arguments.generation, "sha256": hashes,
                "status_at_freeze": json.loads((concept / "status.json").read_text())}
    output.write_text(json.dumps(metadata, indent=2) + "\n")
    print(str(output))


if __name__ == "__main__":
    main()
