"""Read-only lineage capture; all writes stay in this private pilot directory."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time


PILOT = Path(__file__).resolve().parent
ROOT = PILOT.parents[1]
ATTEMPT = ROOT / "attempts/v_1"
NAMES = ("hubbard.cpp", "hubbard.so", "physics.py", "solver.py")


def capture():
    records = {}
    content = {}
    for name in NAMES:
        source = ATTEMPT / name
        metadata = source.stat()
        content[name] = source.read_bytes()
        records[name] = {"sha256": hashlib.sha256(content[name]).hexdigest(),
                         "size": len(content[name]), "mtime_ns": metadata.st_mtime_ns,
                         "source": str(source)}
    return records, content


def main():
    if (PILOT / "lineage.json").exists():
        raise SystemExit("Snapshot already exists; do not overwrite lineage")
    initial, _ = capture()
    stable = False
    for retry in range(3):
        before, content = capture()
        time.sleep(0.05)
        after, _ = capture()
        stable = before == after
        if stable:
            break
    if not stable:
        raise RuntimeError("Source changed repeatedly during snapshot capture")
    targets = {PILOT / "snapshot" / name: value for name, value in content.items()
               if not name.endswith(".so")}
    for source, destination in (
        (ROOT / "evaluator/hidden/exact.py", PILOT / "reference/exact.py"),
        (ROOT / "participant/input/distribution.py", PILOT / "reference/distribution.py")):
        targets[destination] = source.read_bytes()
    patch = "*** Begin Patch\n"
    for destination, value in targets.items():
        if destination.exists():
            raise RuntimeError(f"Snapshot target already exists: {destination}")
        patch += f"*** Add File: {destination}\n"
        patch += "".join("+" + line + "\n" for line in value.decode().splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)
    (PILOT / "snapshot/hubbard.so").write_bytes(content["hubbard.so"])
    for name in NAMES:
        assert hashlib.sha256((PILOT / "snapshot" / name).read_bytes()).hexdigest() == before[name]["sha256"]
    report = {"captured_utc": datetime.now(timezone.utc).isoformat(),
              "initial_inspection": initial, "snapshot": before, "stable_capture": stable,
              "adaptation": "none: source uses dynamic site count and allocation; n12 is already supported",
              "source_binary_build_correspondence": "not independently certified; existing shared object captured verbatim",
              "reference_sources": {str(destination.relative_to(PILOT)): hashlib.sha256(value).hexdigest()
                                    for destination, value in targets.items() if destination.parent.name == "reference"},
              "frozen_package_hashes": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted((ROOT / "participant").rglob("*")) if path.is_file()},
              "frozen_evaluator_hashes": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted((ROOT / "evaluator").rglob("*.py")) if path.is_file()}}
    (PILOT / "lineage.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"snapshot": before, "adaptation": report["adaptation"]}, indent=2))


if __name__ == "__main__":
    main()
