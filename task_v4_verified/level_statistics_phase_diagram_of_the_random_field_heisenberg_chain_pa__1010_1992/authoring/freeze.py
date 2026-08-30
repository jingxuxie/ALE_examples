import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("concept", type=Path)
parser.add_argument("--generation", type=int, default=1)
arguments = parser.parse_args()
root = arguments.concept.resolve()
paths = [path for tree in ("participant", "evaluator") for path in sorted((root / tree).rglob("*"))
         if path.is_file() and "__pycache__" not in path.parts]
manifest = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
report = {"generation": arguments.generation, "frozen_utc": datetime.now(timezone.utc).isoformat(),
          "sha256": digest, "files": manifest, "target_fixed_before_fresh_launch": True}
destination = root / "adversary" / ("generation_" + str(arguments.generation) + "_freeze.json")
if destination.exists():
    raise ValueError("Refusing to overwrite a frozen generation")
destination.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({key: value for key, value in report.items() if key != "files"}))
