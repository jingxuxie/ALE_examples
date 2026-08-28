import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

import numpy as np


def limits():
    os.setsid()
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})


def sandbox_command(participant, solver, destination):
    command = ["bwrap", "--unshare-user", "--unshare-pid", "--unshare-net", "--die-with-parent"]
    for system_path in ["/usr", "/lib", "/lib64", "/bin", "/etc"]:
        command += ["--ro-bind", system_path, system_path]
    command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    command += ["--ro-bind", str(participant), str(participant), "--bind", str(solver.parent), str(solver.parent)]
    timer = "import os,sys,time; print('__BENCHMARK_START__ '+str(time.monotonic()),flush=True); os.execv(sys.executable,[sys.executable]+sys.argv[1:])"
    command += ["--chdir", str(solver.parent), sys.executable, "-c", timer, str(solver), "--input", str(destination / "job.json"), "--output", str(destination / "result.json")]
    return command


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def discrepancy(prediction, reference):
    prediction = np.asarray(prediction, dtype=float)
    reference = np.asarray(reference, dtype=float)
    if prediction.shape != reference.shape or not np.all(np.isfinite(prediction)):
        return float("inf")
    denominator = float(np.sum(np.abs(reference)))
    if denominator == 0:
        denominator = 1.0
    return float(np.sum(np.abs(prediction - reference))) / denominator


def branch_name(kind, query):
    if kind == "weighted":
        return kind + "/" + query["algorithm"] + "/" + ("weighted" if query["kappa"] != 1 else "unit") + "/" + ("high_order" if query["order"] >= 6 else "low_order")
    if kind == "fractional":
        region = "subunit" if query["nu"] < 1 else "integer" if query["nu"] == int(query["nu"]) else "superunit"
        return kind + "/" + region + "/" + ("high_resolution" if query["nsub"] >= 14 else "low_resolution")
    if kind == "resolved":
        powers = [query.get("nu1", 1), query.get("nu2", 1), query.get("nu3", 1)]
        return kind + "/order" + str(query["order"]) + "/" + ("nonlinear" if any(power != 1 for power in powers) else "linear")
    return kind + "/" + query["geometry"] + "/" + query["observable"]


def evaluate_case(private, case, solver, run_root, reference_mode=False):
    case_dir = private / "challenge_pool" / case["id"]
    destination = run_root / case["id"]
    destination.mkdir(parents=True, exist_ok=True)
    job = json.loads((case_dir / "job.json").read_text())
    data_source = (case_dir / job["events_file"]).resolve()
    if not reference_mode:
        shutil.copyfile(data_source, destination / "events.txt")
        job["events_file"] = "events.txt"
        (destination / "job.json").write_text(json.dumps(job))
    reference_record = json.loads((private / "reference" / (case["id"] + ".json")).read_text())
    timeout = float(case.get("timeout_seconds", max(60, 5 * reference_record["wall_seconds"] + 20)))
    if reference_mode:
        submitted = {"histograms": reference_record["histograms"], "claims": {"method": "stored privileged reference"}}
        wall = reference_record["wall_seconds"]
        status = "reference"
        stderr = ""
        maxrss = reference_record.get("maxrss_kb", 0)
        overhead = 0.0
        cpu_seconds = None
    else:
        environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp", "LANG": "C.UTF-8", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "PYTHONHASHSEED": "0"}
        begin = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        with (destination / "stdout.log").open("w") as stdout, (destination / "stderr.log").open("w") as error_file:
            process = subprocess.Popen(
                sandbox_command(private.parent / "participant", solver, destination),
                cwd=solver.parent, stdout=stdout, stderr=error_file, env=environment, preexec_fn=limits,
            )
            try:
                returncode = process.wait(timeout=timeout + 60)
                status = "ok" if returncode == 0 else "exit_" + str(returncode)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                status = "timeout"
        end = time.monotonic()
        wall = end - begin
        overhead = 0.0
        with (destination / "stdout.log").open() as timer_stream:
            first_line = timer_stream.readline()
        if first_line.startswith("__BENCHMARK_START__ "):
            child_begin = float(first_line.split()[1])
            if begin <= child_begin <= end:
                overhead = child_begin - begin
                wall = end - child_begin
        if wall > timeout and status == "ok":
            status = "timeout"
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        maxrss = after.ru_maxrss
        cpu_seconds = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
        stderr = (destination / "stderr.log").read_text()[-3000:]
        try:
            submitted = json.loads((destination / "result.json").read_text()) if status == "ok" else {}
        except (ValueError, OSError):
            submitted = {}
            status = "invalid_json"
    quality = []
    errors = []
    claims = submitted.get("claims", {})
    proposed = submitted.get("histograms", [])
    for index, target in enumerate(reference_record["histograms"]):
        error = discrepancy(proposed[index], target) if index < len(proposed) else float("inf")
        weak = reference_record["weak_histograms"][index]
        weak_error = discrepancy(weak, target)
        scale = max(0.0005, 0.025 * weak_error)
        ratio = error / scale
        if not math.isfinite(ratio):
            value = 0.0
        elif ratio > 1:
            inverse = ratio ** -1.25
            value = inverse / (1.0 + inverse)
        else:
            value = 1.0 / (1.0 + ratio ** 1.25)
        quality.append(value)
        errors.append({"relative_l1": error if math.isfinite(error) else None, "weak_relative_l1": weak_error, "scale": scale})
    runtime_scale = 20 + 12 * reference_record["wall_seconds"]
    runtime_score = 1.0 / (1.0 + (wall / runtime_scale) ** 2)
    core = float(np.mean(quality)) if quality else 0.0
    return {
        "id": case["id"], "family": case["family"], "split": case["split"], "status": status,
        "core_score": core, "runtime_score": runtime_score, "score": core * runtime_score,
        "query_scores": quality, "errors": errors, "wall_seconds": wall,
        "branches": [branch_name(job["kind"], query) for query in job["queries"]],
        "reference_wall_seconds": reference_record["wall_seconds"], "timeout_seconds": timeout,
        "peak_child_rss_kb": maxrss, "claims": claims, "stderr_tail": stderr,
        "sandbox_setup_seconds_excluded": overhead, "child_cpu_seconds": cpu_seconds,
        "data_sha256": digest(data_source),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solver", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--split", default="pilot")
    parser.add_argument("--case")
    parser.add_argument("--reference", action="store_true")
    parser.add_argument("--private", type=Path, default=Path(__file__).resolve().parent)
    arguments = parser.parse_args()
    private = arguments.private.resolve()
    manifest = json.loads((private / "challenge_pool" / "manifest.json").read_text())
    cases = [case for case in manifest["cases"] if (arguments.split == "all" or case["split"] == arguments.split) and (not arguments.case or case["id"] == arguments.case)]
    if not cases:
        raise ValueError("No evaluation cases selected")
    solver = arguments.solver.resolve() if arguments.solver else None
    if not arguments.reference and (solver is None or not solver.is_file()):
        raise ValueError("A solve.py submission is required")
    run_root = (solver.parent if solver else private / "reference") / ("evaluation_" + arguments.report.stem)
    run_root.mkdir(parents=True, exist_ok=True)
    results = []
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    for case in cases:
        result = evaluate_case(private, case, solver, run_root, arguments.reference)
        results.append(result)
        print(json.dumps({key: result[key] for key in ["id", "status", "core_score", "score", "wall_seconds"]}), flush=True)
        arguments.report.with_suffix(".partial.json").write_text(json.dumps(results, indent=2))
    families = {}
    for result in results:
        families.setdefault("data/" + result["family"], []).append(result["score"])
        for branch, score in zip(result["branches"], result["query_scores"]):
            families.setdefault("branch/" + branch, []).append(score * result["runtime_score"])
            families.setdefault("joint/" + result["family"] + "/" + branch, []).append(score * result["runtime_score"])
    family_scores = {key: float(np.mean(values)) for key, values in families.items()}
    report = {
        "mean_core_score": float(np.mean([result["core_score"] for result in results])),
        "mean_score": float(np.mean([result["score"] for result in results])),
        "worst_family_score": min(family_scores.values()), "family_scores": family_scores,
        "consistency": {"finite_and_valid_cases": sum(result["status"] in ["ok", "reference"] for result in results), "total_cases": len(results), "claims_are_not_used_for_credit": True},
        "cases": results,
    }
    arguments.report.write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
