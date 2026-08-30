"""Bounded private pool construction and isolated measurement; never activates a task."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import time


POOL = Path(__file__).resolve().parent
ROOT = POOL.parents[1]
sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import POLICY, accepted, metrics, run_candidate
import numpy as np


def cpu_usage():
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time() + children.ru_utime + children.ru_stime


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def remaining_budget(ceiling):
    remaining = ceiling - cpu_usage()
    soft = max(1, math.ceil(time.process_time() + max(0, remaining)))
    current_soft, current_hard = resource.getrlimit(resource.RLIMIT_CPU)
    if current_hard != resource.RLIM_INFINITY:
        soft = min(soft, current_hard - 1)
    resource.setrlimit(resource.RLIMIT_CPU, (soft, soft + 1))
    if remaining < 1:
        raise TimeoutError("aggregate CPU ceiling reached")
    return remaining


def cpu_expired(signum, frame):
    raise TimeoutError("aggregate CPU ceiling reached")


def measure(submission, specification, ceiling):
    directory = POOL / "cases" / specification["case_id"]
    certificate_path = directory / "certificate.json"
    result = {"case_id": specification["case_id"], "family": specification["family"],
              "profile": specification["profile"], "accepted": False,
              "in_original_parameter_contract": specification["profile"] == "original"}
    if not certificate_path.exists() or not json.loads(certificate_path.read_text())["valid"]:
        return dict(result, measurement_status="not_run_without_certified_reference")
    certificate = json.loads(certificate_path.read_text())
    if certificate["instance_sha256"] != fingerprint(directory / "instance.npz"):
        raise ValueError("instance changed since certification")
    if certificate["solution_sha256"] != fingerprint(directory / "reference.npz"):
        raise ValueError("reference changed since certification")
    if remaining_budget(ceiling) < 18:
        return dict(result, measurement_status="not_run_aggregate_cpu_reserve")
    with np.load(directory / "instance.npz", allow_pickle=False) as archive:
        instance = {key: archive[key] for key in archive.files}
    with np.load(directory / "reference.npz", allow_pickle=False) as archive:
        reference = archive["delta"]
    output, execution = run_candidate(submission, instance)
    result["execution"] = execution
    if output is None:
        return dict(result, measurement_status="resource_or_execution_failure")
    remaining_budget(ceiling)
    verification_started = time.process_time()
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        measured = metrics(instance, output["delta"], output["z"], reference)
    result["private_verification_cpu_seconds"] = time.process_time() - verification_started
    if not all(np.isfinite(value) for value in measured.values()):
        return dict(result, measurement_status="nonfinite_verification_metrics")
    result["quality"] = measured
    result["accepted"] = accepted(measured)
    result["measurement_status"] = "passed_same_resource_quality_gates" if result["accepted"] else "quality_failure"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluate-only", action="store_true")
    parser.add_argument("--submission", type=Path, default=ROOT / "champions")
    parser.add_argument("--report", default="champion_report.json")
    parser.add_argument("--cpu-ceiling", type=int, default=900)
    arguments = parser.parse_args()
    if Path(arguments.report).name != arguments.report:
        raise ValueError("report must be a plain filename inside the private pool")
    plan = json.loads((POOL / "plan.json").read_text())
    ceiling = min(arguments.cpu_ceiling, plan["aggregate_cpu_ceiling_seconds"])
    signal.signal(signal.SIGXCPU, cpu_expired)
    for name in ("jobs", "cases", "logs", "scratch"):
        (POOL / name).mkdir(exist_ok=True)
    tempfile.tempdir = str(POOL / "scratch")
    source_paths = [ROOT / "evaluator" / "evaluate.py", ROOT / "evaluator" / "launch.py",
                    ROOT / "evaluator" / "hidden" / "physics.py",
                    ROOT / "evaluator" / "hidden" / "reference_operator.py",
                    ROOT / "evaluator" / "hidden" / "build_suite.py",
                    ROOT / "champions" / "solve.py", ROOT / "champions" / "solver_core.py",
                    ROOT / "participant" / "input" / "eliashberg.py"]
    source_hashes = {str(path.relative_to(ROOT)): fingerprint(path) for path in source_paths}
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "active": False,
              "active_task_or_target_modified": False, "fresh_agent_launched": False,
              "pool_plan_sha256": fingerprint(POOL / "plan.json"), "source_sha256": source_hashes,
              "submission": str(arguments.submission.resolve()), "cpu_ceiling_seconds": ceiling,
              "candidate_resources": {key: POLICY[key] for key in ("cpu_seconds", "wall_seconds", "memory_mb", "threads")},
              "generation": [], "measurements": []}
    started = time.monotonic()
    try:
        for specification in plan["specifications"]:
            remaining = remaining_budget(ceiling)
            case_id = specification["case_id"]
            certificate_path = POOL / "cases" / case_id / "certificate.json"
            if not arguments.evaluate_only and not certificate_path.exists():
                case_limit = 90 if specification["profile"] == "original" else (150 if specification["n_freq"] == 4096 else 210)
                case_limit = min(case_limit, math.floor(remaining - 30))
                if case_limit < 10:
                    raise TimeoutError("insufficient CPU reserve for another reference")
                job = POOL / "jobs" / (case_id + ".json")
                job.write_text(json.dumps(specification, indent=2) + "\n")
                before = cpu_usage()
                command = [sys.executable, "-I", "-B", str(POOL / "worker.py"), "--job", str(job), "--cpu-seconds", str(case_limit)]
                with (POOL / "logs" / (case_id + ".log")).open("wb") as log:
                    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                               close_fds=True, start_new_session=True)
                    wall_timeout = False
                    try:
                        process.wait(timeout=2700)
                    except subprocess.TimeoutExpired:
                        wall_timeout = True
                    finally:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        process.wait()
                construction = {"case_id": case_id, "returncode": process.returncode,
                                "cpu_limit_seconds": case_limit, "wall_timeout": wall_timeout,
                                "parent_measured_worker_cpu_seconds": cpu_usage() - before}
                report["generation"].append(construction)
                print(json.dumps({"generation": construction}), flush=True)
            measured = measure(arguments.submission.resolve(), specification, ceiling)
            report["measurements"].append(measured)
            report["cpu_seconds_so_far"] = cpu_usage()
            (POOL / arguments.report).write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
            print(json.dumps({"measurement": measured, "aggregate_cpu_seconds": cpu_usage()}, allow_nan=False), flush=True)
    except TimeoutError as error:
        report["budget_stop"] = str(error)
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["aggregate_cpu_seconds"] = cpu_usage()
        report["wall_seconds"] = time.monotonic() - started
        report["source_hash_mismatches"] = [name for name, expected in source_hashes.items() if fingerprint(ROOT / name) != expected]
        for profile in ("original", "low_temperature"):
            selected = [item for item in report["measurements"] if item["profile"] == profile]
            report[profile + "_summary"] = {"case_records": len(selected),
                                           "measured_cases": sum("execution" in item for item in selected),
                                           "passed": sum(item["accepted"] for item in selected)}
        (POOL / arguments.report).write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        manifest = []
        for specification in plan["specifications"]:
            directory = POOL / "cases" / specification["case_id"]
            if (directory / "certificate.json").exists():
                certificate = json.loads((directory / "certificate.json").read_text())
                manifest.append(dict(specification, certified=certificate["valid"],
                                     instance="cases/" + specification["case_id"] + "/instance.npz",
                                     certificate="cases/" + specification["case_id"] + "/certificate.json",
                                     reference="cases/" + specification["case_id"] + "/reference.npz" if certificate["valid"] else None))
        if not arguments.evaluate_only:
            (POOL / "manifest.json").write_text(json.dumps({"active": False, "cases": manifest}, indent=2) + "\n")
        print(json.dumps({key: value for key, value in report.items() if key not in ("measurements", "generation", "source_sha256")}), flush=True)


if __name__ == "__main__":
    main()
