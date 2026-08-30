import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "freeze_manifest.json").read_text())
    failures = []
    for relative, expected in manifest["files_sha256"].items():
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            failures.append(relative)
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            failures.append(relative)
    actual_public = {str(path.relative_to(ROOT)) for path in (ROOT / "participant").rglob("*") if path.is_file()}
    if actual_public != set(manifest["public_allowlist"]):
        failures.append("public_allowlist")
    if any(path.is_symlink() for path in ROOT.rglob("*")):
        failures.append("symlinks")
    report = {"valid": not failures, "frozen_files_checked": len(manifest["files_sha256"]),
              "public_files_checked": len(actual_public), "failures": failures}
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
