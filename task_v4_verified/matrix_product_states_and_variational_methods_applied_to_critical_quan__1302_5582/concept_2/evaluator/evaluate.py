import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent / "hidden"))
from trusted_physics import CONTRACT_VERSION, check


def timeout_handler(signum, frame):
    raise TimeoutError("checker exceeded 120 seconds")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output")
    arguments = parser.parse_args()
    started = time.monotonic()
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(120)
    try:
        artifact = Path(arguments.submission) / "state.npz"
        if artifact.is_symlink():
            raise ValueError("the tensor must be a submitted regular file, not an external symlink")
        result = check(artifact)
    except Exception as error:
        result = {"core_score": 0.0, "worst_family_score": 0.0, "valid": False, "passed": False, "reason": type(error).__name__ + ": " + str(error)}
    finally:
        signal.alarm(0)
    elapsed = time.monotonic() - started
    result.update({"verification_mode": "C_witness_construction", "runtime_seconds": elapsed, "resource_score": float(elapsed <= 120), "contract_version": CONTRACT_VERSION})
    serialized = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(serialized)
    print(serialized, end="")


if __name__ == "__main__":
    main()
