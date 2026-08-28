import hashlib
import json
from pathlib import Path
import shutil


RATCHET = Path(__file__).resolve().parents[2]
PILOT = RATCHET.parent
TASK_ROOT = RATCHET.parents[2]


def snapshot():
    pairs = [
        (PILOT / "private/reference/engine.py", RATCHET / "private/reference/engine.py"),
        (PILOT / "private/reference/longtime/accelerated.py", RATCHET / "private/reference/accelerated.py"),
        (PILOT / "private/scoring.py", RATCHET / "private/scoring.py"),
        (PILOT / "participant/input/protocol.md", RATCHET / "participant/input/protocol.md"),
        (PILOT / "private/reference/engine.py", RATCHET / "private/weak_baseline/engine.py"),
        (PILOT / "private/reference/longtime/accelerated.py", RATCHET / "private/weak_baseline/accelerated.py"),
    ]
    manifest = []
    for source, destination in pairs:
        if destination.exists():
            raise FileExistsError(f"One-time snapshot refuses to overwrite {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        checksum = hashlib.sha256(source.read_bytes()).hexdigest()
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == checksum
        manifest.append(dict(source=str(source.relative_to(TASK_ROOT)),
                             destination=str(destination.relative_to(RATCHET)), sha256=checksum))
    (RATCHET / "participant/workspace").mkdir(parents=True, exist_ok=True)
    (RATCHET / "attempt").mkdir(parents=True, exist_ok=True)
    (RATCHET / "private/snapshot_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    snapshot()
