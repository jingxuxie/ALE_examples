"""Bounded private measurement; submitted modules never enter this process."""

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
SIDECAR = Path(__file__).resolve().parent
ROOT = SIDECAR.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
import evaluate
import numpy as np


def cpu():
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time() + child.ru_utime + child.ru_stime


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def self_check(source):
    with tempfile.TemporaryDirectory(prefix="self_check_", dir=SIDECAR / "scratch") as temporary:
        scratch = Path(temporary)
        with np.load(source, allow_pickle=False) as archive:
            instance = {key: archive[key] for key in evaluate.INPUT_KEYS}
        np.savez(scratch / "input.npz", **instance)
        command = [sys.executable, "-I", "-B", str(ROOT / "evaluator" / "launch.py"),
                   "--shared-runner", str(evaluate.RUNNER), "--submission", str(SIDECAR / "candidate_1"),
                   "--participant", str(ROOT / "participant"), "--input", str(scratch / "input.npz"),
                   "--output", str(scratch / "output.npz"), "--scratch", str(scratch),
                   "--entry", "self_check.py", "--cpu-seconds", "12", "--memory-mb", "2048"]
        started = cpu()
        with (scratch / "log.txt").open("wb") as log:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                     start_new_session=True, close_fds=True)
            try:
                child.wait(timeout=1800)
            finally:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
        output = scratch / "output.npz"
        assert child.returncode == 0, (scratch / "log.txt").read_text()
        assert not output.is_symlink() and output.resolve().is_relative_to(scratch.resolve())
        evaluate.read_output(output, instance["initial_delta"].shape)
        return {"public_example": source.name, "passed": True, "cpu_seconds": cpu() - started}


def main():
    start = cpu()
    started_wall = time.monotonic()
    protocol = json.loads((SIDECAR / "protocol.json").read_text())
    (SIDECAR / "scratch").mkdir(exist_ok=True)
    tempfile.tempdir = str(SIDECAR / "scratch")
    checks = [self_check(ROOT / "participant" / "input" / "examples" / name)
              for name in ("critical.npz", "low_temperature_4096.npz")]
    save(SIDECAR / "self_check_report.json", checks)
    print(json.dumps({"self_checks": checks}), flush=True)
    reports = {}
    passing = None
    for name in ("candidate_1", "candidate_2"):
        if cpu() - start > protocol["cpu_budget_seconds_total"] - 400:
            break
        report = evaluate.evaluate(SIDECAR / name)
        reports[name] = report
        save(SIDECAR / (name + "_report.json"), report)
        print(json.dumps({"candidate": name, "passed": report["passed"], "core_score": report["core_score"],
                          "worst_family_score": report["worst_family_score"], "aggregate_cpu_seconds": cpu() - start}), flush=True)
        if report["passed"]:
            passing = name
            break
    repeat = None
    if passing and cpu() - start <= protocol["cpu_budget_seconds_total"] - 400:
        repeat = evaluate.evaluate(SIDECAR / passing)
        save(SIDECAR / (passing + "_repeat_report.json"), repeat)
    diagnostic = None
    if not passing and "candidate_2" in reports and cpu() - start <= protocol["cpu_budget_seconds_total"] - 150:
        case_id = "case_16"
        with np.load(evaluate.HIDDEN / "cases" / (case_id + ".npz"), allow_pickle=False) as archive:
            instance = {key: archive[key] for key in evaluate.INPUT_KEYS}
        with np.load(evaluate.HIDDEN / "references" / (case_id + ".npz"), allow_pickle=False) as archive:
            reference = archive["delta"]
        result, execution = evaluate.run_candidate(SIDECAR / "candidate_2", instance, cpu_seconds=90)
        diagnostic = {"case_id": case_id, "extended_offline_execution": execution,
                      "not_a_12_cpu_witness": True}
        if result is not None:
            diagnostic["quality"] = evaluate.metrics(instance, result["delta"], result["z"], reference)
        save(SIDECAR / "extended_diagnostic.json", diagnostic)
    mismatches = [name for name, expected in protocol["active_sealed_files"].items()
                  if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    assert not mismatches, mismatches
    summary = {"passing_candidate": passing, "repeat_passed": None if repeat is None else repeat["passed"],
               "same_budget_attainability": "verified" if passing else "unknown",
               "candidates_evaluated": list(reports), "aggregate_cpu_seconds": cpu() - start,
               "wall_seconds": time.monotonic() - started_wall,
               "budget_seconds": protocol["cpu_budget_seconds_total"], "active_seal_unchanged": True,
               "fresh_trial_touched": False, "extended_diagnostic_is_joint_witness": False,
               "scores": {name: {key: report[key] for key in ("core_score", "worst_family_score", "passed", "runtime")}
                          for name, report in reports.items()}}
    assert summary["aggregate_cpu_seconds"] <= protocol["cpu_budget_seconds_total"]
    save(SIDECAR / "summary.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
