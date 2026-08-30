import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / "evaluator" / "hidden" / "generation_1_freeze.json"
    if destination.exists():
        raise RuntimeError("generation already frozen")
    paths = []
    for directory in ("participant", "evaluator", "adversary"):
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    manifest = {"generation": 1, "frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "target_changed_after_baseline": False, "model_changed_after_baseline": False,
                "sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)},
                "sandbox_sha256": hashlib.sha256((ROOT.parent / "authoring" / "sandbox.py").read_bytes()).hexdigest()}
    destination.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"frozen": str(destination), "files": len(paths), "time": manifest["frozen_utc"]}))


if __name__ == "__main__":
    main()
