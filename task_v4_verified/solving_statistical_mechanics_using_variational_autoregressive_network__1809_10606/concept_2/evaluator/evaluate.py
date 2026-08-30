import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
TRUSTED = ROOT / "evaluator"
sys.path[:] = [str(TRUSTED)] + [entry for entry in sys.path if entry and Path(entry).resolve().is_relative_to(Path(sys.base_prefix).resolve())]


def timeout_handler(signum, frame):
    raise TimeoutError("evaluator resource deadline exceeded")


def limit_resources(spec):
    memory_bytes = spec["evaluator_address_space_mib"] * 1024 ** 2
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    if hard != resource.RLIM_INFINITY:
        memory_bytes = min(memory_bytes, hard)
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, hard))
    soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
    cpu_seconds = spec["evaluator_cpu_seconds"]
    if hard != resource.RLIM_INFINITY:
        cpu_seconds = min(cpu_seconds, hard)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, hard))
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.signal(signal.SIGXCPU, timeout_handler)
    signal.alarm(spec["evaluator_wall_seconds"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    started = time.monotonic()
    report = {"core_score": 0.0, "worst_score": 0.0, "worst_family_score": 0.0,
              "resource_score": 0.0, "valid": False, "evaluator_valid": False,
              "passed": False, "reason": "evaluation did not complete"}
    spec = None
    try:
        spec_content = (ROOT / "participant" / "input" / "spec.json").read_bytes()
        spec = json.loads(spec_content)
        freeze = json.loads((TRUSTED / "freeze.json").read_text())
        if hashlib.sha256(spec_content).hexdigest() != freeze["spec_sha256"]:
            raise RuntimeError("frozen specification hash mismatch")
        for filename, digest in freeze["trusted_sha256"].items():
            if hashlib.sha256((TRUSTED / filename).read_bytes()).hexdigest() != digest:
                raise RuntimeError("trusted evaluator hash mismatch: " + filename)
        report["benchmark_id"] = spec["benchmark_id"]
        report["spec_sha256"] = freeze["spec_sha256"]
        limit_resources(spec)
        from physics import InvalidWitness, evaluate_document, read_witness
        try:
            document, content = read_witness(arguments.submission, spec)
            report["submission_sha256"] = hashlib.sha256(content).hexdigest()
            report.update(evaluate_document(document, spec))
        except InvalidWitness as error:
            report.update(evaluator_valid=True, reason="invalid witness: " + str(error))
    except Exception as error:
        report.update(core_score=0.0, worst_score=0.0, worst_family_score=0.0,
                      passed=False, evaluator_valid=False,
                      reason="evaluator error: " + type(error).__name__ + ": " + str(error))
    finally:
        signal.alarm(0)
    elapsed = time.monotonic() - started
    usage = resource.getrusage(resource.RUSAGE_SELF)
    within_limits = spec is not None and elapsed <= spec["evaluator_wall_seconds"] and usage.ru_utime + usage.ru_stime <= spec["evaluator_cpu_seconds"]
    report["resource_score"] = float(report["evaluator_valid"] and within_limits)
    if not within_limits:
        report.update(passed=False, reason=report["reason"] + "; resource limit exceeded")
    report["runtime_seconds"] = elapsed
    report["resource"] = {"wall_seconds": elapsed, "user_cpu_seconds": usage.ru_utime,
                          "system_cpu_seconds": usage.ru_stime, "peak_rss_mib": usage.ru_maxrss / 1024.0,
                          "threads": 1, "address_space_limit_mib": None if spec is None else spec["evaluator_address_space_mib"],
                          "wall_limit_seconds": None if spec is None else spec["evaluator_wall_seconds"],
                          "cpu_limit_seconds": None if spec is None else spec["evaluator_cpu_seconds"]}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("core_score", "worst_score", "resource_score", "valid", "evaluator_valid", "passed", "reason")}))


if __name__ == "__main__":
    main()
