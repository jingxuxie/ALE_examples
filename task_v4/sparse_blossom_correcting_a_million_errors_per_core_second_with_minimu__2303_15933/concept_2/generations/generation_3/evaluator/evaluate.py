import sys

sys.dont_write_bytecode = True

import argparse
import importlib.util
import json
from pathlib import Path
import resource
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", nargs="?")
    parser.add_argument("--submission", dest="named_submission")
    parser.add_argument("--output")
    parser.add_argument("--summary-only", action="store_true")
    arguments = parser.parse_args()
    started, cpu_started = time.monotonic(), time.process_time()
    source = Path(__file__).resolve().parent / "hidden/oracle.py"
    specification = importlib.util.spec_from_file_location("generation_three_trusted_oracle", source)
    oracle = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(oracle)
    try:
        submission = arguments.named_submission or arguments.submission
        if not submission or (arguments.submission and arguments.named_submission):
            raise ValueError("supply exactly one submission path")
        artifact = oracle.read_artifact(submission)
    except (ValueError, UnicodeError, OSError, OverflowError, RecursionError) as error:
        result = {"valid": False, "passed": False, "core_score": 0.0, "worst_scale_score": 0.0,
                  "worst_family_score": 0.0, "runtime_score": 0.0, "resource_score": 0.0,
                  "reason": "invalid_submission: " + str(error)}
    else:
        result = oracle.evaluate(artifact)
    result["evaluation_seconds"] = time.monotonic() - started
    result["evaluation_cpu_seconds"] = time.process_time() - cpu_started
    result["peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    result["resources"] = {"nominal_wall_allowance_seconds": 900, "memory_allowance_mib": 1024,
                           "internal_wall_watchdog": False, "runtime_scored": False,
                           "submission_code_executed": False, "native_threads": 1}
    if arguments.output:
        Path(arguments.output).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if arguments.summary_only:
        result = {key: value for key, value in result.items() if key != "groups"}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
