"""Evaluate data only; never import or execute participant code."""

import os
import sys

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
for thread_variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[thread_variable] = "1"

import argparse
import hashlib
import importlib.util
import json
import time
from pathlib import Path


PRIVATE_DIRECTORY = Path(__file__).resolve().parent


def _load_private(filename, name, expected_digest):
    source = PRIVATE_DIRECTORY / filename
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected_digest:
        raise RuntimeError("evaluator integrity check failed: " + filename)
    specification = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def evaluate(path):
    started = time.process_time()
    result = {
        "core_score": 0.0,
        "worst_family_score": 0.0,
        "runtime_score": 0.0,
        "passed": False,
        "valid": False,
        "evidence_valid": False,
        "reason": "not evaluated",
    }
    try:
        manifest = json.loads((PRIVATE_DIRECTORY / "frozen_manifest.json").read_text(encoding="utf-8"))
        checker = _load_private("exact_checker.py", "concept2_private_checker", manifest["exact_checker_sha256"])
        guard = _load_private("_frozen_guard.py", "concept2_private_guard", manifest["guard_sha256"])
        try:
            checked = checker.check_file(path)
        except checker.InvalidSubmission as error:
            result["reason"] = str(error)
            return result
        result["valid"] = True
        result["evidence_valid"] = checked["evidence_valid"]
        result["exact_rayleigh"] = str(checked["rayleigh"])
        result["exact_minimum_principal_minor"] = str(checked["minimum_principal_minor"])
        result["degree"] = checked["degree"]
        result["guard_sha256"] = manifest["guard_sha256"]
        if not checked["evidence_valid"]:
            result["reason"] = "admissible data, but exact normalized Rayleigh quotient is not at most -1e-7"
            return result
        coefficients = [[[float(entry) for entry in row] for row in matrix] for matrix in checked["coefficients"]]
        reports = guard.screen_all(coefficients)
        result["guard_profiles"] = reports
        accepted = sum(report["accepted"] for report in reports)
        result["core_score"] = accepted / len(guard.PROFILES)
        result["worst_family_score"] = float(accepted == len(guard.PROFILES))
        result["passed"] = accepted == len(guard.PROFILES)
        result["reason"] = "accepted exact false-acceptance witness" if result["passed"] else "exact negative evidence is valid, but the numerical guard detects it"
        return result
    except Exception as error:
        result.update(core_score=0.0, worst_family_score=0.0, runtime_score=0.0, passed=False, reason="evaluator failure (fail closed): " + type(error).__name__)
        return result
    finally:
        elapsed = time.process_time() - started
        result["cpu_seconds"] = elapsed
        result["runtime_score"] = min(1.0, 3.0 / max(elapsed, 1e-9)) if result["passed"] else 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("witness", nargs="?", default="participant/workspace/witness.json")
    parser.add_argument("--output")
    arguments = parser.parse_args()
    result = evaluate(arguments.witness)
    text = json.dumps(result, sort_keys=True, allow_nan=False) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
