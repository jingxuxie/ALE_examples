"""Run the frozen evaluator for all three preregistered ratchet cases."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
PRIVATE = HERE.parent
RUNS = PRIVATE / "reference_runs"
EVALUATOR = PRIVATE / "evaluator.py"
ASSIGNMENTS = {
    "lower_offset": list(range(64, 70)),
    "central_offset": list(range(72, 78)),
    "high_density": list(range(80, 86)),
}
THREAD_VARIABLES = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
for variable in THREAD_VARIABLES:
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    if not any(path.resolve().is_relative_to(root) for root in (HERE, RUNS)):
        raise ValueError("Writes must stay in ratchet reference or reference_runs")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluator_module():
    specification = importlib.util.spec_from_file_location("frozen_ratchet_evaluator", EVALUATOR)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def inspect_inputs():
    evaluator = evaluator_module()
    source = read(HERE / "source_manifest.json")
    actual = {path.name for path in (PRIVATE / "challenge_pool").iterdir() if path.is_dir()}
    if actual != set(ASSIGNMENTS) or set(source["cases"]) != set(ASSIGNMENTS):
        raise ValueError("The preregistered case set is not exactly the expected three cases")
    protected = [EVALUATOR, HERE / "physics.py", HERE / "source_manifest.json"]
    cases = []
    for case, cpus in ASSIGNMENTS.items():
        directory = PRIVATE / "challenge_pool" / case
        request_path = directory / "request.json"
        scenario_path = directory / "scenarios.json"
        request, scenarios = read(request_path), read(scenario_path)
        strong_path = HERE / f"{request['request_id']}.json"
        strong = evaluator.load_result(request, strong_path)
        weak = evaluator.geometry_arrays(request, request["baseline_geometry"])
        checks = {
            "request_id_matches": request["request_id"] == case,
            "preregistered_request_hash_matches": sha256(request_path) == source["cases"][case]["request_sha256"],
            "exposed_points_equal_frozen_scenarios": request["operating_points"] == scenarios == source["cases"][case]["operating_points"],
            "exact_three_points": len(scenarios) == 3,
            "dimension_25608": 4 * request["grid"]["nx"] * request["grid"]["ny"] == 25608,
            "strong_matches_source_digest": evaluator.geometry_digest(strong) == source["strong_geometry_sha256"],
        }
        protected.extend((request_path, scenario_path, strong_path))
        cases.append({
            "case": case, "cpu_set": cpus, "scenarios": scenarios, "checks": checks,
            "weak_geometry": evaluator.feasibility(request, weak), "strong_geometry": evaluator.feasibility(request, strong),
            "weak_geometry_sha256": evaluator.geometry_digest(weak), "strong_geometry_sha256": evaluator.geometry_digest(strong),
            "fingerprint": evaluator.fingerprint(request, scenarios, strong),
        })
    manifest = {
        "created_utc": stamp(), "case_selection_frozen": True, "case_order": list(ASSIGNMENTS),
        "source_manifest": source, "cases": cases,
        "protected_sha256": {str(path.relative_to(PRIVATE)): sha256(path) for path in protected},
        "runner_sha256": sha256(Path(__file__)),
        "preexisting_calibration_artifacts": sorted(path.name for path in HERE.glob("*_calibration.json")),
        "preexisting_measurement_artifacts": sorted(path.name for path in HERE.glob("*_measurements.json")),
        "inputs_verified": all(all(case["checks"].values()) for case in cases),
    }
    save(HERE / "calibration_run_manifest.json", manifest)
    if not manifest["inputs_verified"]:
        raise ValueError("Frozen-case or source fingerprint verification failed; no changes or replacements made")
    return manifest


def setup_child(cpus):
    os.sched_setaffinity(0, cpus)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024 ** 3, 4 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (900, 901))


def process_snapshot(root_pid):
    pending = [root_pid]
    records = []
    while pending:
        pid = pending.pop()
        directory = Path("/proc") / str(pid)
        try:
            children = (directory / "task" / str(pid) / "children").read_text().split()
            pending.extend(map(int, children))
            status = {}
            for line in (directory / "status").read_text().splitlines():
                key, _, value = line.partition(":")
                if key in ("Name", "State", "Threads", "VmRSS", "Cpus_allowed_list"):
                    status[key] = value.strip()
            records.append({"pid": pid, "affinity": sorted(os.sched_getaffinity(pid)), **status})
        except (FileNotFoundError, ProcessLookupError):
            continue
    return records


def terminate_all(active):
    for entry in active.values():
        if entry["process"].poll() is None:
            os.killpg(entry["process"].pid, signal.SIGTERM)
    until = time.monotonic() + 1.0
    while any(entry["process"].poll() is None for entry in active.values()) and time.monotonic() < until:
        time.sleep(0.05)
    for entry in active.values():
        process = entry["process"]
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wall-seconds", type=float, default=900.0)
    arguments = parser.parse_args()
    if not 0 < arguments.wall_seconds <= 900:
        parser.error("The numerical wall cap must be at most 900 seconds")
    if (HERE / "calibration_runtime.json").exists():
        parser.error("Existing bounded calibration run detected; refusing to overwrite it")
    allowed = os.sched_getaffinity(0)
    if any(not set(cpus).issubset(allowed) for cpus in ASSIGNMENTS.values()):
        parser.error("Requested CPU sets unavailable; no substitute CPUs will be used")
    os.sched_setaffinity(0, {69})
    manifest = inspect_inputs()
    RUNS.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    runtime = {
        "started_utc": stamp(), "started_monotonic": started, "deadline_monotonic": started + arguments.wall_seconds,
        "numeric_wall_budget_seconds": arguments.wall_seconds, "workers_per_case": 3, "max_concurrent_workers": 9,
        "cpu_assignments": ASSIGNMENTS, "controller_affinity": sorted(os.sched_getaffinity(0)),
        "blas_threads_per_worker": 1, "thread_environment": {name: os.environ[name] for name in THREAD_VARIABLES},
        "address_space_limit_gib_per_process": 4, "case_selection_frozen": True, "commands": {},
    }
    save(HERE / "calibration_runtime.json", runtime)
    active = {}
    timed_out = []
    last_snapshot = -30.0
    error = None
    try:
        for case, cpus in ASSIGNMENTS.items():
            command = [sys.executable, "-B", "-u", "evaluator.py", "--calibrate", "--case", case, "--workers", "3", "--output", f"reference_runs/{case}.json"]
            log = open(RUNS / f"{case}.log", "w", encoding="utf-8")
            process = subprocess.Popen(command, cwd=PRIVATE, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=lambda selected=cpus: setup_child(selected))
            active[case] = {"process": process, "log": log, "finished_seconds": None}
            runtime["commands"][case] = {"command": command, "cwd": str(PRIVATE), "pid": process.pid, "cpu_set": cpus}
            print(json.dumps({"event": "case_started", "case": case, "cpu_set": cpus, "pid": process.pid}), flush=True)
        save(HERE / "calibration_runtime.json", runtime)
        while any(entry["process"].poll() is None for entry in active.values()) and time.monotonic() < runtime["deadline_monotonic"]:
            elapsed = time.monotonic() - started
            for entry in active.values():
                if entry["process"].poll() is not None and entry["finished_seconds"] is None:
                    entry["finished_seconds"] = elapsed
            if elapsed - last_snapshot >= 30:
                snapshot = {"elapsed_seconds": elapsed, "cases": {case: process_snapshot(entry["process"].pid) for case, entry in active.items()}}
                with open(RUNS / "resource_snapshots.jsonl", "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(snapshot) + "\n")
                last_snapshot = elapsed
            time.sleep(0.5)
        timed_out = [case for case, entry in active.items() if entry["process"].poll() is None]
    except Exception as caught:
        error = repr(caught)
    finally:
        terminate_all(active)
        for entry in active.values():
            entry["log"].close()
    ended = time.monotonic() - started
    result = {
        "finished_utc": stamp(), "numeric_wall_seconds": ended, "numeric_wall_budget_seconds": arguments.wall_seconds,
        "timed_out_cases": timed_out, "error": error, "incomplete_is_failure": False,
        "protected_inputs_unchanged": all(sha256(PRIVATE / name) == digest for name, digest in manifest["protected_sha256"].items()),
        "cases": {case: {"returncode": entry["process"].returncode, "wall_seconds": entry["finished_seconds"] or ended, "timed_out": case in timed_out, "output_exists": (RUNS / f"{case}.json").exists()} for case, entry in active.items()},
    }
    save(HERE / "calibration_execution.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
