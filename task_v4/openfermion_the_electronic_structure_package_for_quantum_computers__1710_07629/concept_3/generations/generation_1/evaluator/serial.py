"""Optional trusted serialization wrapper, sharing the orchestrator's mutex."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    top_level = root.parents[2]
    shared = top_level / "private/evaluation.lock"
    if shared.exists():
        descriptor = os.open(shared, os.O_RDONLY | os.O_NOFOLLOW)
    else:
        descriptor = os.open(root / "evaluator/evaluation.lock", os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    os.set_inheritable(descriptor, True)
    allowed = sorted(os.sched_getaffinity(0))
    index = int(hashlib.sha256(top_level.name.encode()).hexdigest()[:8], 16) % len(allowed)
    selected = allowed[index]
    (root / "evaluator/serial_affinity.json").write_text(json.dumps({"cpu": selected,
        "selection": "top-level task-name hash", "shared_mutex": str(shared)}, indent=2) + "\n")
    os.sched_setaffinity(0, {selected})
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"
    os.execv(sys.executable, [sys.executable, "-B", *sys.argv[1:]])


if __name__ == "__main__":
    main()
