import argparse
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=int)
    parser.add_argument("--generation", type=int, default=1)
    args = parser.parse_args()
    concept = ROOT / f"concept_{args.concept}"
    files = {}
    for section in ("participant", "evaluator"):
        for path in sorted((concept / section).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith("score.json"):
                files[str(path.relative_to(concept))] = hashlib.sha256(path.read_bytes()).hexdigest()
    record = {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "generation": args.generation, "fresh_attempt_started": False, "sha256": files}
    destination = concept / "adversary" / f"generation_{args.generation}_freeze.json"
    if destination.exists():
        raise SystemExit("refusing to overwrite an existing generation freeze")
    destination.write_text(json.dumps(record, indent=2) + "\n")
    print(destination)


if __name__ == "__main__":
    main()
