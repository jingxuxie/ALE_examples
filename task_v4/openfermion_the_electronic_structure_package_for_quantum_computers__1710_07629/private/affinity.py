import hashlib
import fcntl
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    lock = os.open(ROOT / "private/evaluation.lock", os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX)
    os.set_inheritable(lock, True)
    allowed = sorted(os.sched_getaffinity(0))
    index = int(hashlib.sha256(ROOT.name.encode()).hexdigest()[:8], 16) % len(allowed)
    selected = allowed[index]
    record = {"selection": "fixed task-name hash, chosen before fresh evaluation", "cpu": selected, "allowed_cpu_count": len(allowed), "reason": "Avoid every concurrent benchmark pinning to the lowest CPU. All baseline and fresh runtime comparisons use this same one-CPU placement; no targets are changed."}
    (ROOT / "private/evaluation_affinity.json").write_text(json.dumps(record, indent=2))
    os.sched_setaffinity(0, {selected})
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"
    os.execv(sys.executable, [sys.executable] + sys.argv[1:])


if __name__ == "__main__":
    main()
