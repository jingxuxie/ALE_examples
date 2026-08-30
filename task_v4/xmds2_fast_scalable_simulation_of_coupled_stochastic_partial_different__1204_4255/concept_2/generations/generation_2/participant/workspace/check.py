import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import time
from pathlib import Path

from search_api import assess, certificate_screen, parse_submission, screen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--quick", action="store_true")
    modes.add_argument("--guards", action="store_true")
    parser.add_argument("--family", action="store_true")
    arguments = parser.parse_args()
    started = time.monotonic()
    try:
        parameters = parse_submission(Path(arguments.submission).read_text())
        if arguments.guards:
            result = {"screening_only": True, "guards_only": True, "family": certificate_screen(parameters, arguments.family)}
        elif arguments.quick:
            result = {"screening_only": True, "family": screen(parameters, arguments.family)}
        else:
            result = assess(parameters)
    except (ValueError, OSError, FloatingPointError, OverflowError, RecursionError) as error:
        result = {"core_score": 0.0, "worst_family_score": 0.0, "valid": False, "passed": False, "reason": str(error)[:200]}
    result["runtime_seconds"] = time.monotonic() - started
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
