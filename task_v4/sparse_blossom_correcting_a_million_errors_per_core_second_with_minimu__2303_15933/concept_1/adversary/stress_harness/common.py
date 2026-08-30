import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
SIDE = Path(__file__).resolve().parent
ROOT = SIDE.parents[1]
PARTICIPANT = ROOT / "participant"
os.environ["MPLCONFIGDIR"] = str(SIDE / "cache/matplotlib")
for name in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]:
    os.environ[name] = "1"
sys.path[:0] = [str(PARTICIPANT / "input/runtime"), str(PARTICIPANT / "input"), str(PARTICIPANT), str(ROOT / "evaluator")]


def private_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(SIDE):
        raise ValueError("All sidecar outputs must stay inside adversary/stress_harness")
    return path


def write_json(path, data):
    path = private_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_inventory(directory):
    directory = Path(directory).resolve()
    files = {}
    total = 0
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Snapshot symlinks are forbidden")
        if path.is_file() and "__pycache__" not in path.relative_to(directory).parts:
            total += path.stat().st_size
            files[str(path.relative_to(directory))] = digest_file(path)
    if total > 256 * 1024 ** 2 or len(files) > 4096:
        raise ValueError("Use a code-only champion directory, at most 256 MiB/4096 files")
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return dict(sha256=digest, files=files, bytes=total)
