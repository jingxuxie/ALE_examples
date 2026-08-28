import os
from pathlib import Path
import sys


def enable_vendor():
    candidates = []
    if os.environ.get("PILOT04_VENDOR"):
        candidates.append(Path(os.environ["PILOT04_VENDOR"]))
    for ancestor in Path(__file__).resolve().parents:
        candidates.extend([ancestor / "output/research/vendor", ancestor / "research/vendor",
                           ancestor / "tasks_v3/decoding_across_the_quantum_ldpc_code_landscape__2005_07016/research/vendor"])
    for candidate in candidates:
        if (candidate / "stim").is_dir():
            sys.path.insert(0, str(candidate))
            return candidate
    raise RuntimeError("Set PILOT04_VENDOR to the private pinned vendor directory")
