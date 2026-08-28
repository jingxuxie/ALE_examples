"""Bounded author-side performance evidence, never a participant launcher."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PILOT = HERE.parents[2]
GIB = 1024 ** 3


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path).resolve()
    if not path.is_relative_to(HERE):
        raise ValueError("All sidecar writes must remain in performance/")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def event(kind, **values):
    record = {"event": kind, "unix_seconds": time.time(), **values}
    with (HERE / "events.jsonl").open("a") as handle:
        handle.write(json.dumps(record, allow_nan=False) + "\n")
    print(json.dumps(record, allow_nan=False), flush=True)


def pin():
    allowed = sorted(os.sched_getaffinity(0))
    selected = allowed[-2:]
    os.sched_setaffinity(0, selected)
    return {"inherited_affinity": allowed, "effective_affinity": sorted(os.sched_getaffinity(0))}


def physics_module():
    sys.path.insert(0, str(PILOT / "participant" / "workspace"))
    import physics
    return physics


def resources():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {"cpu_seconds": usage.ru_utime + usage.ru_stime, "peak_rss_kib": usage.ru_maxrss, "affinity": sorted(os.sched_getaffinity(0)), "address_space_limit_bytes": resource.getrlimit(resource.RLIMIT_AS)[0]}


def worker(arguments):
    pin()
    limit = (6 if arguments.mode == "dense" else 2) * GIB
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    resource.setrlimit(resource.RLIMIT_CPU, (1200, 1201))
    physics = physics_module()
    import numpy as np
    import scipy
    from threadpoolctl import threadpool_info, threadpool_limits
    request = load(HERE / "request.json")
    scenarios = load(HERE / "scenarios.json")
    masks = physics.geometry_arrays(request, load(arguments.geometry)["geometry"])
    started = time.monotonic()
    record = {"status": "starting", "mode": arguments.mode, "scenario_index": arguments.scenario, "scenario": scenarios[arguments.scenario], "numpy_version": np.__version__, "scipy_version": scipy.__version__, "threadpools": threadpool_info(), **resources()}
    save(arguments.output, record)
    try:
        with threadpool_limits(limits=1):
            build_started = time.monotonic()
            model = physics.ForwardModel(request, masks, scenarios[arguments.scenario])
            record.update(dimension=model.dimension, model_build_seconds=time.monotonic() - build_started)
            if arguments.mode == "dense":
                record.update(status="building_dense_matrix", variant=arguments.variant)
                save(arguments.output, record)
                dense = model.hamiltonian(0.0).toarray(order="F")
                record.update(status="eigensolver_running", dense_bytes=dense.nbytes, fortran_contiguous=bool(dense.flags.f_contiguous), dtype=str(dense.dtype), **resources())
                save(arguments.output, record)
                kernel_started = time.monotonic()
                if arguments.variant == "numpy_full_eigh":
                    energies, vectors = np.linalg.eigh(dense)
                    record["eigenvector_bytes"] = vectors.nbytes
                else:
                    center = model.dimension // 2
                    energies = scipy.linalg.eigh(dense, eigvals_only=True, overwrite_a=True, check_finite=False, driver="evr", subset_by_index=(center - 4, center + 3))
                record.update(status="completed", eigensolver_call_seconds=time.monotonic() - kernel_started, minimum_absolute_energy_mev=float(np.min(np.abs(energies))))
            else:
                topology_started = time.monotonic()
                invariant = model.topological_invariant()
                record.update(status="sampling", class_d_invariant=invariant, topology_seconds=time.monotonic() - topology_started, momenta_rad=[], gaps_mev=[], eigensolver_seconds=[])
                save(arguments.output, record)
                for momentum in np.linspace(0, np.pi, 51):
                    kernel_started = time.monotonic()
                    energies, _ = model.low_energy(float(momentum))
                    record["eigensolver_seconds"].append(time.monotonic() - kernel_started)
                    record["momenta_rad"].append(float(momentum))
                    record["gaps_mev"].append(float(np.min(np.abs(energies))))
                    record.update(elapsed_seconds=time.monotonic() - started, **resources())
                    if len(record["gaps_mev"]) % 5 == 0:
                        save(arguments.output, record)
                record.update(status="completed", gap_mev=min(record["gaps_mev"]), eigensolver_total_seconds=sum(record["eigensolver_seconds"]))
    except Exception as error:
        record.update(status="allocation_failure" if isinstance(error, MemoryError) else "exception", error_type=type(error).__name__, error=str(error))
        if "kernel_started" in locals():
            record["eigensolver_call_seconds_before_error"] = time.monotonic() - kernel_started
    record.update(elapsed_seconds=time.monotonic() - started, **resources())
    save(arguments.output, record)


def spawn(mode, geometry, output, scenario=0, variant=""):
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--mode", mode, "--geometry", str(geometry), "--output", str(output), "--scenario", str(scenario)]
    if variant:
        command.extend(("--variant", variant))
    log = Path(output).with_suffix(".stderr.log").open("w")
    process = subprocess.Popen(command, cwd=HERE, env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    log.close()
    return process


def terminate(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)


def dense_probes(baseline, in_place_seconds):
    results = []
    for variant, budget in (("numpy_full_eigh", 30), ("scipy_inplace_subset_evr", in_place_seconds)):
        output = HERE / f"dense_{variant}.json"
        started = time.monotonic()
        process = spawn("dense", baseline, output, variant=variant)
        event("dense_start", variant=variant, wall_budget_seconds=budget, pid=process.pid)
        while process.poll() is None and time.monotonic() - started < budget:
            time.sleep(0.2)
        expired = process.poll() is None
        terminate(process)
        record = load(output) if output.exists() else {"status": "no_worker_report"}
        if expired:
            record.update(status="wall_timeout", stage_at_timeout=record.get("status"), wall_budget_seconds=budget)
        record.update(observed_wall_seconds=time.monotonic() - started, returncode=process.returncode)
        save(output, record)
        results.append(record)
        event("dense_finish", variant=variant, status=record["status"], seconds=record["observed_wall_seconds"], error=record.get("error"))
    return results


def shape(request, amplitude, width):
    import numpy as np
    grid = request["grid"]
    columns = np.arange(grid["nx"])
    positions = (np.arange(grid["ny"]) - (grid["ny"] - 1) / 2) * grid["spacing_nm"]
    center = -amplitude + 4 * amplitude * np.minimum(columns, grid["nx"] - columns) / grid["nx"]
    vertical_width = width * math.sqrt(1 + (4 * amplitude / grid["period_nm"]) ** 2)
    return {"sc_top": positions[:, None] >= center[None, :] + vertical_width / 2, "sc_bottom": positions[:, None] <= center[None, :] - vertical_width / 2}


def evaluate(geometry, index, deadline):
    active = {}
    records = {}
    next_scenario = 0
    try:
        while len(records) < 3:
            if time.monotonic() >= deadline:
                return {"complete": False, "reason": "wall_budget_exhausted", "completed_scenarios": records}
            while len(active) < 2 and next_scenario < 3:
                output = HERE / f"candidate_{index:03d}_scenario_{next_scenario}.json"
                process = spawn("forward", geometry, output, scenario=next_scenario)
                active[next_scenario] = (process, output)
                event("scenario_start", candidate=index, scenario=next_scenario, pid=process.pid)
                next_scenario += 1
            for scenario, (process, output) in list(active.items()):
                if process.poll() is not None:
                    record = load(output) if output.exists() else {"status": "no_worker_report"}
                    record["returncode"] = process.returncode
                    records[scenario] = record
                    del active[scenario]
                    event("scenario_finish", candidate=index, scenario=scenario, status=record["status"], gap_mev=record.get("gap_mev"), elapsed_seconds=record.get("elapsed_seconds"))
            time.sleep(0.15)
    finally:
        for process, output in active.values():
            terminate(process)
            if output.exists():
                record = load(output)
                record.update(status="wall_timeout", stage_at_timeout=record.get("status"), returncode=process.returncode)
                save(output, record)
    ordered = [records[scenario] for scenario in range(3)]
    complete = all(record.get("status") == "completed" and len(record.get("gaps_mev", [])) == 51 for record in ordered)
    feasible = complete and all(record["class_d_invariant"] == -1 and record["gap_mev"] > 1e-5 for record in ordered)
    robust_gap = None
    if complete:
        gaps = [record["gap_mev"] for record in ordered]
        robust_gap = 0.5 * sum(gaps) / len(gaps) + 0.5 * min(gaps)
    return {"complete": complete, "physical_feasibility": feasible, "robust_gap_mev": robust_gap, "measurements": ordered}


def direct_search(request, wall_seconds):
    physics = physics_module()
    started = time.monotonic()
    initial_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    deadline = started + wall_seconds
    center = (100.0, 200.0)
    step = 40.0
    tried = set()
    history = []
    best = None
    candidate_index = 0
    pending = [center]
    while time.monotonic() < deadline:
        if not pending:
            amplitude, width = center
            neighbors = [(amplitude, max(100.0, width - step)), (amplitude, min(280.0, width + step)), (min(260.0, amplitude + step), width), (max(0.0, amplitude - step), width)]
            pending = [parameters for parameters in neighbors if parameters not in tried]
            if not pending:
                step /= 2
                if step < 10:
                    break
                continue
        parameters = pending.pop(0)
        if parameters in tried:
            continue
        tried.add(parameters)
        masks = shape(request, *parameters)
        geometry_status = physics.feasibility(request, masks)
        record = {"index": candidate_index, "amplitude_nm": parameters[0], "perpendicular_width_nm": parameters[1], "geometry": geometry_status, "started_at_seconds": time.monotonic() - started}
        if not geometry_status["valid"]:
            record.update(complete=False, reason="manufacturing_infeasible")
            history.append(record)
            event("candidate_rejected", **record)
            candidate_index += 1
            continue
        path = HERE / f"candidate_{candidate_index:03d}.json"
        result = {"schema_version": 1, "request_id": request["request_id"], "geometry": physics.geometry_json(masks)}
        save(path, result)
        event("candidate_start", **record)
        measured = evaluate(path, candidate_index, deadline)
        record.update(measured, finished_at_seconds=time.monotonic() - started)
        history.append(record)
        if measured.get("physical_feasibility") and (best is None or measured["robust_gap_mev"] > best["robust_gap_mev"] + 1e-8):
            best = {"candidate_index": candidate_index, "parameters": list(parameters), "robust_gap_mev": measured["robust_gap_mev"], "measurements": measured["measurements"], "geometry": geometry_status}
            save(HERE / "best_result.json", result)
            save(HERE / "best_so_far.json", best)
            center = parameters
            pending = []
            event("best_updated", candidate=candidate_index, parameters=parameters, robust_gap_mev=best["robust_gap_mev"])
        save(HERE / "direct_history.json", history)
        event("candidate_finish", candidate=candidate_index, complete=measured["complete"], physical_feasibility=measured.get("physical_feasibility"), robust_gap_mev=measured.get("robust_gap_mev"), elapsed_seconds=record["finished_at_seconds"])
        candidate_index += 1
        if not measured["complete"]:
            break
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    report = {"method": "two-parameter first-improvement coordinate search with fresh direct forward solves", "wall_budget_seconds": wall_seconds, "wall_seconds": time.monotonic() - started, "numeric_child_cpu_seconds": usage.ru_utime + usage.ru_stime - initial_usage.ru_utime - initial_usage.ru_stime, "affinity": sorted(os.sched_getaffinity(0)), "blas_threads": 1, "max_concurrent_numeric_workers": 2, "worker_address_space_limit_gib": 2, "parent_address_space_limit_gib": 1, "termination": "wall_budget_exhausted" if time.monotonic() >= deadline else "stopped_or_coordinate_stencil_exhausted", "started_candidates": candidate_index, "completed_full_candidates": sum(bool(row.get("complete")) for row in history), "best": best, "optimizer_or_strong_geometry_read": False, "exact_private_scenarios_given_to_baseline": True}
    save(HERE / "direct_report.json", report)
    return report


def run(arguments):
    started = time.monotonic()
    affinity = pin()
    memory = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(("MemTotal:", "MemAvailable:")):
            name, quantity, _ = line.split()
            memory[name.rstrip(":")] = int(quantity) * 1024
    if memory.get("MemAvailable", 0) < 12 * GIB:
        raise RuntimeError("Insufficient host headroom for safely running the 6 GiB dense probe")
    case = PILOT / "private" / "challenge_pool" / "matched_1300"
    request = load(case / "request.json")
    save(HERE / "request.json", request)
    save(HERE / "scenarios.json", load(case / "scenarios.json"))
    physics = physics_module()
    baseline = physics.geometry_arrays(request, request["baseline_geometry"])
    assert physics.geometry_digest(baseline) == physics.geometry_digest(shape(request, 100.0, 200.0))
    baseline_path = HERE / "baseline_result.json"
    save(baseline_path, {"schema_version": 1, "request_id": request["request_id"], "geometry": physics.geometry_json(baseline)})
    environment = {**affinity, "host_memory": memory, "python": sys.version, "python_executable": sys.executable, "forward_model_sha256": hashlib.sha256((PILOT / "participant" / "workspace" / "physics.py").read_bytes()).hexdigest(), "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "start_unix_seconds": time.time(), "cpu_pinning_policy": "last two inherited allowed CPUs", "blas_threads": 1, "writes_confined_to": str(HERE)}
    save(HERE / "environment.json", environment)
    event("run_start", affinity=affinity["effective_affinity"], direct_wall_budget_seconds=arguments.wall_seconds)
    dense = [load(HERE / f"dense_{variant}.json") for variant in ("numpy_full_eigh", "scipy_inplace_subset_evr")] if arguments.skip_dense else dense_probes(baseline_path, arguments.dense_seconds)
    resource.setrlimit(resource.RLIMIT_AS, (GIB, 6 * GIB))
    direct = direct_search(request, arguments.wall_seconds)
    calibration = load(PILOT / "private" / "reference" / "matched_1300_calibration.json")
    weak_gap = calibration["weak"]["robust_gap_mev"]
    strong_gap = calibration["strong"]["robust_gap_mev"]
    best_gap = direct["best"]["robust_gap_mev"] if direct["best"] else None
    score = None if best_gap is None else (best_gap - weak_gap) / (strong_gap - weak_gap)
    costs = [sum(row["eigensolver_seconds"]) for candidate in load(HERE / "direct_history.json") for row in candidate.get("measurements", []) if row.get("status") == "completed"]
    summary = {"complete": True, "request_id": request["request_id"], "dimension": 15860, "dense_probes": dense, "direct_wall_seconds": direct["wall_seconds"], "direct_numeric_cpu_seconds": direct["numeric_child_cpu_seconds"], "direct_completed_full_candidates": direct["completed_full_candidates"], "weak_reference_robust_gap_mev": weak_gap, "strong_reference_robust_gap_mev": strong_gap, "direct_best_robust_gap_mev": best_gap, "direct_best_normalized_core": score, "direct_reached_or_exceeded_strong": score is not None and score >= 1 - 1e-8, "scope_of_core_comparison": "one representative family only; no claim about aggregate three-family core", "reference_read_after_search": True, "affinity": affinity["effective_affinity"], "total_wall_seconds": time.monotonic() - started, "estimates_only": {"median_51_momentum_kernel_seconds": None if not costs else sorted(costs)[len(costs) // 2], "full_grid_candidate_count_if_amplitude_0_to_260_and_width_100_to_280_at_20nm": 140, "grid_cost_note": "140 candidate count is combinatorial, not an executed exhaustive optimization; feasibility may prune candidates and runtimes depend on shape."}, "limits": ["A single generic direct baseline is not a proof that all direct methods fail.", "The in-place dense timeout is only the explicitly recorded probe deadline, not a witnessed 1200-second timeout.", "Exact held-out scenarios were supplied to the naive search, an advantage over the participant contract.", "Incomplete candidates are never used as best-so-far results."]}
    save(HERE / "summary.json", summary)
    event("run_finish", direct_normalized_core=score, reached_strong=summary["direct_reached_or_exceeded_strong"], total_wall_seconds=summary["total_wall_seconds"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("run", "dense", "forward"), default="run")
    parser.add_argument("--wall-seconds", type=float, default=1200)
    parser.add_argument("--dense-seconds", type=float, default=60)
    parser.add_argument("--skip-dense", action="store_true")
    parser.add_argument("--geometry", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--scenario", type=int, default=0)
    parser.add_argument("--variant", default="numpy_full_eigh")
    arguments = parser.parse_args()
    if arguments.mode == "run":
        run(arguments)
    else:
        worker(arguments)


if __name__ == "__main__":
    main()
