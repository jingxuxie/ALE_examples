"""Freeze once, then verify the exact public package and evaluator bytes."""

import datetime
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "attempts" / "freeze.json"


def main():
    hashes = {}
    for directory in ("participant", "evaluator"):
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    if MANIFEST.exists():
        saved = json.loads(MANIFEST.read_text())
        if saved["sha256"] != hashes:
            raise SystemExit("FROZEN BYTES CHANGED: requires an explicit formal ratchet")
        print("Frozen participant/baseline/evaluator hashes verified")
        return
    manifest = {
        "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "contract": "single-pair Mode B, ratio >=3, six absolute errors <=1e-7",
        "scope": "public assets, baseline, independent evaluator",
        "calibration_policy": "Subsequent local calibration uses these exact bytes; no fresh agents launched.",
        "exploratory_record": "search_results.json and search_best.json predate this package freeze; scientific target was already fixed in target_frozen.json",
        "sha256": hashes,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
