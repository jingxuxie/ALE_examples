import argparse
import hashlib
import json
import math
import os
import resource
import stat
import subprocess
import sys
import time
from pathlib import Path


HIDDEN = Path(__file__).resolve().parent / "hidden"


def failure(reason):
    return {"core_score": 0.0, "worst_family_score": 0.0, "valid": False, "passed": False, "reason": reason[:240]}


def read_submission(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        information = os.fstat(descriptor)
        if not stat.S_ISREG(information.st_mode):
            raise ValueError("submission must be a regular file")
        if information.st_size > 16384:
            raise ValueError("submission exceeds 16384 bytes")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read(16385)
        if len(content) > 16384:
            raise ValueError("submission exceeds 16384 bytes")
        return content.decode("utf-8")
    finally:
        os.close(descriptor)


def finite_tree(value):
    if isinstance(value, float):
        return math.isfinite(value) and abs(value) <= 1e12
    if isinstance(value, list):
        return all(finite_tree(item) for item in value)
    if isinstance(value, dict):
        return all(finite_tree(item) for item in value.values())
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output")
    arguments = parser.parse_args()
    started = time.monotonic()
    submission_hash = None
    try:
        content = read_submission(arguments.submission)
        submission_hash = hashlib.sha256(content.encode()).hexdigest()
        environment = {
            "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        process = subprocess.run(
            ["/usr/bin/python3", "-I", "-B", str(HIDDEN / "runner.py")],
            input=content, text=True, capture_output=True, cwd=HIDDEN,
            env=environment, timeout=660,
        )
        if process.returncode != 0:
            result = failure("evaluator_resource_or_worker_failure")
        else:
            result = json.loads(process.stdout)
            if not finite_tree(result) or not 0 <= result["core_score"] <= 1 or not 0 <= result["worst_family_score"] <= 1:
                result = failure("nonfinite_or_unbounded_evaluator_result")
    except subprocess.TimeoutExpired:
        result = failure("evaluation_wall_time_limit")
    except (OSError, ValueError, OverflowError, RecursionError, KeyError, TypeError) as error:
        result = failure("invalid_submission_or_result: " + str(error))
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    result["runtime_seconds"] = time.monotonic() - started
    result["resource"] = {
        "cpu_seconds": usage.ru_utime + usage.ru_stime, "max_rss_mb": usage.ru_maxrss / 1024,
        "wall_limit_seconds": 660, "cpu_limit_seconds": 400,
        "address_space_limit_mb": 1536, "threads": 1,
    }
    result["submission_sha256"] = submission_hash
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        try:
            destination = Path(arguments.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text)
        except OSError as error:
            print("could not save optional output: " + str(error), file=sys.stderr)
    print(text, end="")


if __name__ == "__main__":
    main()
