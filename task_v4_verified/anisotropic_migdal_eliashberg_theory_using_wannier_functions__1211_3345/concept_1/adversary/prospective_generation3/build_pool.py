"""Build at most four private prospective cases within 900 aggregate CPU seconds."""

import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True
import numpy as np

SIDECAR = Path(__file__).resolve().parent
ROOT = SIDECAR.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
import evaluate


def cpu():
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time() + children.ru_utime + children.ru_stime


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    started = cpu()
    started_wall = time.monotonic()
    plan = json.loads((SIDECAR / "plan.json").read_text())
    protocol = json.loads((SIDECAR / "protocol.json").read_text())
    (SIDECAR / "scratch").mkdir(exist_ok=True)
    (SIDECAR / "logs").mkdir(exist_ok=True)
    tempfile.tempdir = str(SIDECAR / "scratch")
    reports = []
    for index, specification in enumerate(plan["cases"]):
        remaining = plan["cpu_budget_seconds"] - (cpu() - started)
        if remaining < 150:
            break
        limit = min(specification["offline_cpu_limit"], int(remaining) - 75)
        command = [sys.executable, "-B", str(SIDECAR / "case_worker.py"), "--index", str(index), "--cpu-seconds", str(limit)]
        with (SIDECAR / "logs" / (specification["case_id"] + ".log")).open("wb") as log:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            timed_out = False
            try:
                process.wait(timeout=1800)
            except subprocess.TimeoutExpired:
                timed_out = True
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
        directory = SIDECAR / "cases" / specification["case_id"]
        report = {"case_id": specification["case_id"], "family": specification["family"],
                  "offline_worker_cpu_limit": limit, "offline_worker_returncode": process.returncode,
                  "offline_wall_timeout": timed_out, "reference_valid": False, "comparators": {}}
        certificate_path = directory / "certificate.json"
        if certificate_path.exists():
            certificate = json.loads(certificate_path.read_text())
            report["reference_valid"] = certificate["valid"]
            report["certificate"] = {key: certificate[key] for key in
                                     ("primary_all_frequency", "second_start_all_frequency", "offline_cpu_seconds")}
        if report["reference_valid"]:
            with np.load(directory / "instance.npz", allow_pickle=False) as archive:
                instance = {key: archive[key] for key in evaluate.INPUT_KEYS}
            with np.load(directory / "reference.npz", allow_pickle=False) as archive:
                reference = archive["delta"]
            for name in ("archived_v3", "threshold8192_control"):
                if plan["cpu_budget_seconds"] - (cpu() - started) < 40:
                    report["comparators"][name] = {"tested": False, "reason": "aggregate CPU reserve"}
                    continue
                output, execution = evaluate.run_candidate(SIDECAR / "comparators" / name, instance)
                result = {"tested": True, "accepted": False, "execution": execution}
                if output is not None:
                    result["quality"] = evaluate.metrics(instance, output["delta"], output["z"], reference)
                    result["accepted"] = evaluate.accepted(result["quality"])
                    np.savez_compressed(directory / (name + "_output.npz"), **output)
                report["comparators"][name] = result
        report["aggregate_cpu_seconds"] = cpu() - started
        reports.append(report)
        if directory.exists():
            save(directory / "measurement.json", report)
        save(SIDECAR / "progress.json", {"cases": reports, "aggregate_cpu_seconds": cpu() - started})
        print(json.dumps(report), flush=True)
    mismatches = [name for name, expected in protocol["active_sealed_files"].items()
                  if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    assert not mismatches, mismatches
    summary = {"prospective_only": True, "promoted_generation": False, "actual_v4_tested": False,
               "actual_v4_failure_claimed": False, "new_public_assets": False, "fresh_launch_performed": False,
               "certified_cases": sum(report["reference_valid"] for report in reports),
               "attempted_cases": len(reports), "cpu_budget_seconds": plan["cpu_budget_seconds"],
               "aggregate_cpu_seconds": cpu() - started, "wall_seconds": time.monotonic() - started_wall,
               "active_seal_unchanged": True, "active_sealed_files_verified": len(protocol["active_sealed_files"]),
               "case_reports": reports,
               "comparator_interpretation": "Both comparator codes use the same reduced-grid path for all these N>8192 cases. Results are private diagnostic controls, not evidence about actual v4.",
               "next_action": "If v4 fails, retain generation two and stop. Only if v4 passes may the parent evaluate its actual frozen submission on this pool for a possible final ratchet.",
               "offline_certificates_do_not_prove_same_budget_attainability": True}
    assert summary["aggregate_cpu_seconds"] < plan["cpu_budget_seconds"]
    save(SIDECAR / "summary.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "case_reports"}), flush=True)


if __name__ == "__main__":
    main()
