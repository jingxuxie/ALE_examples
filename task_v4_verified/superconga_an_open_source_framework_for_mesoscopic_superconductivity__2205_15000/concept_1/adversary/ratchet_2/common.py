import os
import sys

sys.dont_write_bytecode = True
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]
PREVIOUS = ROOT.parent / "ratchet_1"
ASSETS = ROOT / "assets"
tempfile.tempdir = str(ROOT / "scratch")


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    def scalar(value):
        if hasattr(value, "item"):
            return value.item()
        raise TypeError(type(value).__name__)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".partial")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False, default=scalar) + "\n")
    temporary.replace(destination)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def verify_files(files):
    for name, expected in files.items():
        path = ROOT / name
        if not path.is_file() or path.is_symlink() or digest(path) != expected:
            raise ValueError("immutable asset changed: " + name)


def load_corpus():
    manifest = read_json(ROOT / "corpus/manifest.json")
    verify_files(manifest["sha256"])
    return manifest, read_json(ROOT / "policy.json")
