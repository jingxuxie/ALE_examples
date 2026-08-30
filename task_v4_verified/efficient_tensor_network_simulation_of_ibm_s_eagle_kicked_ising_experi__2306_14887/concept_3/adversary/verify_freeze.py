import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "freeze_manifest.json").read_text())
    mismatches = []
    for name, expected in manifest["sha256"].items():
        path = ROOT / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        if actual != expected:
            mismatches.append(name)
    result = {"verified": not mismatches, "files": len(manifest["sha256"]),
              "mismatches": mismatches, "threshold": manifest["threshold"]}
    print(json.dumps(result, indent=2))
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
