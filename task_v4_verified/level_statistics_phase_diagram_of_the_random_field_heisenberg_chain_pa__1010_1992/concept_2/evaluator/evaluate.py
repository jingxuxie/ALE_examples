import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import time

from check import evaluate_design


def expired(signum, frame):
    raise TimeoutError("Evaluation wall-time limit")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parent
    started = time.monotonic()
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(240)
    report = {"core_score": 0, "worst_family_score": 0, "valid": False, "passed": False,
              "evaluator_valid": True, "reason": "No valid design"}
    try:
        spec = json.loads((root / "hidden/spec.json").read_text())
        seed_path = root / "hidden/seeds.json"
        if hashlib.sha256(seed_path.read_bytes()).hexdigest() != spec["hidden_seeds_sha256"]:
            raise RuntimeError("Seed commitment mismatch")
        seed_document = json.loads(seed_path.read_text())
        design_path = arguments.submission / "design.json" if arguments.submission.is_dir() else arguments.submission
        if design_path.is_symlink() or design_path.stat().st_size > 100000:
            raise ValueError("Invalid design file")
        design = json.loads(design_path.read_text())
        report.update(evaluate_design(design, spec, seed_document["seeds"]))
    except (ValueError, TypeError, KeyError, FileNotFoundError) as error:
        report["reason"] = "Invalid submission: " + str(error)
    except Exception as error:
        report.update(evaluator_valid=False, reason=type(error).__name__ + ": " + str(error))
    finally:
        signal.alarm(0)
    elapsed = time.monotonic() - started
    memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    report["runtime_seconds"] = elapsed
    report["resource_score"] = float(elapsed <= 240 and memory <= 2048)
    report["resource"] = {"wall_limit_seconds": 240, "peak_rss_mb": memory, "memory_limit_mb": 2048, "threads": 1}
    report["passed"] = report["passed"] and bool(report["resource_score"])
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "families"}, allow_nan=False))


if __name__ == "__main__":
    main()
