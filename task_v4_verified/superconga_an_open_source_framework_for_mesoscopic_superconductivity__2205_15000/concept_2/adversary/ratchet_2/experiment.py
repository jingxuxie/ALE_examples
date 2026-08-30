import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time

sys.dont_write_bytecode = True

import numpy as np
from scipy.linalg import eigh, solve
from scipy.ndimage import gaussian_filter, label

from adapter import CHAMPION, CONCEPT, ROOT, load_champion

sys.path.insert(0, str(CHAMPION / "participant" / "workspace"))
sys.path.insert(0, str(CHAMPION / "evaluator"))
from spectral import discrepancies, hamiltonian, load_problem, response, validate_design
from checker import independent_hamiltonian, independent_response


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def source_hashes():
    paths = []
    for folder in (CONCEPT / "participant", CONCEPT / "evaluator", CHAMPION):
        paths.extend(path for path in folder.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    return {str(path.relative_to(CONCEPT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(set(paths))}


def audit():
    original = json.loads((ROOT / "protected_hashes.json").read_text())
    current = source_hashes()
    changed = [name for name, expected in original.items() if current.get(name) != expected]
    result = {"unchanged": not changed, "changed": changed, "protected_file_count": len(original), "concurrently_added_files": sorted(set(current) - set(original))}
    write_json(ROOT / "hash_audit.json", result)
    if changed:
        raise RuntimeError("Protected files changed: " + repr(changed))
    return result


def score(config, target, pattern):
    started = time.monotonic()
    result = discrepancies(config, independent_response(config, pattern), target)
    try:
        validate_design(config, pattern)
        result["valid"] = True
    except ValueError as error:
        result["valid"] = False
        result["invalid_reason"] = str(error)
    result["checker_seconds"] = time.monotonic() - started
    result["passed"] = bool(result["valid"] and result["core_score"] >= 0.96 and result["worst_family_score"] >= 0.94 and result["checker_seconds"] <= 120)
    return result


def candidate_coordinates(width):
    coordinates = [[column, row] for row in range(2, width - 2) for column in range(2, width - 2)]
    if len(coordinates) % 8:
        coordinates = [coordinate for coordinate in coordinates if not (coordinate[0] in (2, width - 3) and coordinate[1] in (2, width - 3))]
    return coordinates


def physical_pattern(config):
    width = config["width"]
    candidates = config["candidates"]
    for trial in range(10000):
        random = np.random.default_rng(823701 + trial)
        field = gaussian_filter(random.normal(size=(20, 20)), 0.65, mode="reflect")
        offset = (20 - width) // 2
        values = np.array([field[row + offset, column + offset] for column, row in candidates])
        pattern = np.zeros(len(candidates), dtype=int)
        pattern[np.argsort(values)[-config["normal_site_count"]:]] = 1
        try:
            validate_design(config, pattern)
            return pattern, trial
        except ValueError:
            continue
    raise RuntimeError("No fabrication-feasible mask")


def verify(case_dir, config, target, pattern):
    started = time.monotonic()
    matrix = hamiltonian(config, pattern, config["conditions"][0])
    alternate = independent_hamiltonian(config, pattern, config["conditions"][0])
    eigenvalues = eigh(matrix, eigvals_only=True, check_finite=False)
    result = {"matrix_max_error": float(np.max(np.abs(matrix - alternate))), "hermiticity_max_error": float(np.max(np.abs(matrix - matrix.conj().T))), "particle_hole_max_error": float(np.max(np.abs(eigenvalues + eigenvalues[::-1]))), "checker_target_max_error": float(np.max(np.abs(independent_response(config, pattern) - target))), "witness_score": score(config, target, pattern)}
    positions = np.array([row * config["width"] + column for column, row in config["probes"]])
    probes = np.eye(len(matrix), dtype=complex)[:, positions]
    energy_indices = sorted(set([0, len(config["energies"]) // 2, len(config["energies"]) - 1, int(np.argmax(np.max(target[0], axis=0)))]))
    errors = []
    for energy_index in energy_indices:
        columns = solve((config["energies"][energy_index] + 1j * config["broadening"]) * np.eye(len(matrix)) - matrix, probes, check_finite=False)
        observed = -columns[positions, np.arange(len(positions))].imag / np.pi
        errors.append(float(np.max(np.abs(observed - target[0, :, energy_index]))))
    result["direct_resolvent_max_error"] = max(errors)
    optimize, continuation, discrete = load_champion(case_dir / "public", case_dir / "private")
    model = optimize.Model()
    random = np.random.default_rng(315)
    continuous = random.uniform(0.05, 0.85, len(pattern))
    direction = random.normal(size=len(pattern))
    direction /= np.linalg.norm(direction)
    result["mode_gradient_relative_errors"] = {}
    for mode in ("linear", "log", "sqrt"):
        clock = time.monotonic()
        cpu = time.process_time()
        loss, gradient = model.evaluate(continuous, mode=mode)
        if mode == "linear":
            result["gradient_evaluation_seconds"] = time.monotonic() - clock
            result["gradient_cpu_seconds"] = time.process_time() - cpu
        step = 1e-6
        numerical = (model.evaluate(continuous + step * direction, False, mode=mode)[0] - model.evaluate(continuous - step * direction, False, mode=mode)[0]) / (2 * step)
        result["mode_gradient_relative_errors"][mode] = float(abs(numerical - gradient @ direction) / max(1e-9, abs(numerical)))
    result["adapted_forward_max_error"] = float(np.max(np.abs(model.evaluate(continuous, False)[1] - response(config, continuous))))
    result["verification_seconds"] = time.monotonic() - started
    result["passed"] = bool(result["witness_score"]["passed"] and all(value < 1e-8 for name, value in result.items() if name.endswith("max_error")) and max(result["mode_gradient_relative_errors"].values()) < 2e-4)
    write_json(case_dir / "private" / "verification.json", result)
    if not result["passed"]:
        raise RuntimeError(f"Verification failed for {case_dir.name}: {result}")
    return result


def generate_case(specification):
    width, potential, broadening, control = specification
    config, original = load_problem(CHAMPION / "participant" / "input")
    case = "generation_2_control" if control else f"islands{width}_v{potential:g}_eta{broadening:g}"
    case_dir = ROOT / "cases" / case
    (case_dir / "public" / "input").mkdir(parents=True, exist_ok=True)
    (case_dir / "private").mkdir(exist_ok=True)
    if control:
        pattern = np.array(json.loads((CHAMPION / "design.json").read_text())["pattern"])
        target = original
        trial = None
    else:
        candidates = candidate_coordinates(width)
        config.update(width=width, height=width, candidates=candidates, normal_site_count=3 * len(candidates) // 8, pin_potential=potential, broadening=broadening)
        config["probes"] = [[0, 3], [0, width - 4], [width - 1, 2], [width - 1, width - 3], [3, 0], [width - 4, width - 1], [width // 2 - 1, width // 2 - 1], [width - 4, 4]]
        intervals = int(np.ceil(0.6 / (broadening / 2)))
        config["energies"] = np.linspace(-0.3, 0.3, intervals + 1).tolist()
        pattern, trial = physical_pattern(config)
        target = response(config, pattern)
    write_json(case_dir / "public" / "input" / "device.json", config)
    np.savez_compressed(case_dir / "public" / "input" / "target.npz", ldos=target)
    write_json(case_dir / "private" / "design.json", {"pattern": pattern.tolist()})
    verification = verify(case_dir, config, target, pattern)
    normal = np.zeros((width, width), dtype=int)
    for occupied, (column, row) in zip(pattern, config["candidates"]):
        normal[row, column] = occupied
    metadata = {"case": case, "width": width, "candidate_count": len(pattern), "normal_site_count": int(pattern.sum()), "normal_fraction": float(pattern.mean()), "pin_potential": config["pin_potential"], "broadening": config["broadening"], "energy_count": len(config["energies"]), "max_energy_spacing": float(np.max(np.diff(config["energies"]))), "normal_components": int(label(normal)[1]), "pattern_trial": trial, "pattern_policy": "First fabrication-feasible thresholded correlated field (sigma=.65 lattice units, seed=823701+trial); no optimizer-dependent witness selection; same witness across V/eta for each geometry.", "candidate_policy": "Interior margin two; when necessary hold the four interior corners superconducting so candidate count is divisible by eight and normal fraction is EXACTLY 3/8.", "verification": verification}
    write_json(case_dir / "private" / "metadata.json", metadata)
    return metadata


def run_continuation(job):
    case, seed, iterations = job
    case_dir = ROOT / "cases" / case
    output = case_dir / "runs" / f"continuation_{seed}_{iterations}"
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "result.json"
    if destination.exists():
        return json.loads(destination.read_text())
    optimize, continuation, discrete = load_champion(case_dir / "public", output, iterations)
    config, target = optimize.CONFIG, optimize.TARGET
    original_minimize = continuation.minimize
    original_stdout = sys.stdout
    records = []
    started = time.monotonic()
    cpu_started = time.process_time()
    stage_index = 0

    def instrumented_minimize(objective, initial, *arguments, **keywords):
        nonlocal stage_index
        clock, cpu = time.monotonic(), time.process_time()
        result = original_minimize(objective, initial, *arguments, **keywords)
        wall, cpu_seconds = time.monotonic() - clock, time.process_time() - cpu
        continuous = np.clip(result.x, 0, 1)
        binary = np.zeros(len(continuous), dtype=int)
        binary[np.argsort(continuous)[-config["normal_site_count"]:]] = 1
        measured = score(config, target, binary)
        record = {"stage": stage_index, "penalty_weight": [.02, .1, .3, 1., 3., 10.][stage_index], "mode": ["linear", "log", "sqrt"][seed % 3], "nit": int(result.nit), "nfev": int(result.nfev), "njev": int(result.njev), "solver_success": bool(result.success), "solver_message": str(result.message), "optimizer_seconds": wall, "optimizer_cpu_seconds": cpu_seconds, "penalized_mode_loss": float(result.fun), "sum": float(continuous.sum()), "fractional": float(np.mean(continuous * (1 - continuous))), "score": measured, "pattern": binary.tolist()}
        write_json(output / f"stage_{stage_index}.json", record)
        np.savez_compressed(output / f"stage_{stage_index}.npz", continuous=continuous, pattern=binary)
        records.append(record)
        print(json.dumps({"event": "stage", "case": case, "seed": seed, "iterations": iterations, "stage": stage_index, "seconds": wall, "score": measured}), file=original_stdout, flush=True)
        stage_index += 1
        return result

    continuation.minimize = instrumented_minimize
    try:
        continuation.worker(seed)
    finally:
        redirected = sys.stdout
        sys.stdout = original_stdout
        if redirected is not original_stdout:
            redirected.close()
    valid = [entry for entry in records if entry["score"]["valid"]]
    report = {"case": case, "seed": seed, "maxiter_per_stage": iterations, "complete_six_stages": len(records) == 6, "best_spectral": min(records, key=lambda entry: entry["score"]["relative_rmse"])["score"], "best_valid": min(valid, key=lambda entry: entry["score"]["relative_rmse"])["score"] if valid else None, "stages": records, "total_seconds": time.monotonic() - started, "total_cpu_seconds": time.process_time() - cpu_started, "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
    write_json(destination, report)
    return report


def run_auxiliary(job):
    case, seed, method = job
    case_dir = ROOT / "cases" / case
    output = case_dir / "runs" / f"{method}_{seed}"
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "result.json"
    if destination.exists():
        return json.loads(destination.read_text())
    optimize, continuation, discrete = load_champion(case_dir / "public", output)
    original_stdout = sys.stdout
    records = []
    started, cpu_started = time.monotonic(), time.process_time()
    calls = []

    def instrument_solver(solver):
        def wrapped(*arguments, **keywords):
            clock, cpu = time.monotonic(), time.process_time()
            result = solver(*arguments, **keywords)
            calls.append({"nfev": int(result.nfev), "njev": int(result.njev), "nit": int(result.nit) if hasattr(result, "nit") else None, "solver_success": bool(result.success), "solver_message": str(result.message), "optimizer_seconds": time.monotonic() - clock, "optimizer_cpu_seconds": time.process_time() - cpu})
            return result
        return wrapped

    optimize.minimize = instrument_solver(optimize.minimize)
    optimize.least_squares = instrument_solver(optimize.least_squares)
    try:
        with (output / "optimizer.log").open("w", buffering=1) as logfile:
            sys.stdout = logfile
            if method == "lbfgs_then_ls":
                mode = "linear" if seed < 3 else "log" if seed < 6 else "sqrt"
                optimize.run(seed, 450, mode, 0, budget_weight=1., binary_weight=0.)
                evaluations = [(seed, "L-BFGS-B", 450)]
            else:
                evaluations = []
            if method == "lbfgs_then_ls":
                optimize.run_least_squares(seed + 100, 300, "linear", 0, start_file=str(output / f"result_{seed}.npz"), budget_weight=10., binary_weight=1.)
                evaluations.append((seed + 100, "warm_least_squares", 300))
            else:
                optimize.run_least_squares(seed, 350, "linear", 0, budget_weight=10., binary_weight=1.)
                evaluations.append((seed, "cold_least_squares", 350))
    finally:
        sys.stdout = original_stdout
    for stage, (result_seed, algorithm, budget) in enumerate(evaluations):
        with np.load(output / f"result_{result_seed}.npz") as arrays:
            continuous, binary = arrays["pattern"], arrays["binary"]
        record = {"stage": stage, "algorithm": algorithm, "iteration_budget": budget, **calls[stage], "sum": float(continuous.sum()), "fractional": float(np.mean(continuous * (1 - continuous))), "score": score(optimize.CONFIG, optimize.TARGET, binary), "pattern": binary.tolist()}
        write_json(output / f"stage_{stage}.json", record)
        np.savez_compressed(output / f"stage_{stage}.npz", continuous=continuous, pattern=binary)
        records.append(record)
    valid = [entry for entry in records if entry["score"]["valid"]]
    report = {"case": case, "seed": seed, "method": method, "maxiter_per_stage": 0, "complete_six_stages": False, "best_spectral": min(records, key=lambda entry: entry["score"]["relative_rmse"])["score"], "best_valid": min(valid, key=lambda entry: entry["score"]["relative_rmse"])["score"] if valid else None, "stages": records, "total_seconds": time.monotonic() - started, "total_cpu_seconds": time.process_time() - cpu_started, "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
    write_json(destination, report)
    return report


def summarize():
    rows = []
    for case_dir in sorted((ROOT / "cases").iterdir()):
        metadata = json.loads((case_dir / "private" / "metadata.json").read_text())
        records = [json.loads(path.read_text()) for path in (case_dir / "runs").glob("*/result.json")]
        stages = [json.loads(path.read_text()) for path in (case_dir / "runs").glob("*/stage_*.json")]
        valid = [entry for entry in stages if entry["score"]["valid"]]
        full = [record for record in records if record["maxiter_per_stage"] == 250 and record["complete_six_stages"]]
        rows.append({"case": case_dir.name, "width": metadata["width"], "candidate_count": metadata["candidate_count"], "normal_site_count": metadata["normal_site_count"], "normal_fraction": metadata["normal_fraction"], "normal_components": metadata["normal_components"], "pin_potential": metadata["pin_potential"], "broadening": metadata["broadening"], "verified": metadata["verification"]["passed"], "completed_runs": len(records), "full_strength_completed_seeds": sorted(record["seed"] for record in full), "scored_stages": len(stages), "nfev": sum(entry["nfev"] for entry in stages), "optimizer_seconds_sum": sum(entry["optimizer_seconds"] for entry in stages), "optimizer_cpu_seconds_sum": sum(entry["optimizer_cpu_seconds"] for entry in stages), "best_spectral": min(stages, key=lambda entry: entry["score"]["relative_rmse"])["score"] if stages else None, "best_valid": min(valid, key=lambda entry: entry["score"]["relative_rmse"])["score"] if valid else None, "passing_stages": sum(entry["score"]["passed"] for entry in stages), "max_worker_rss_mib": max([record["peak_rss_mib"] for record in records], default=0)})
    write_json(ROOT / "summary.json", rows)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["generate", "run", "auxiliary", "summary"])
    parser.add_argument("--workers", type=int, default=48)
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--seeds", nargs="*", type=int, default=[0, 1, 2])
    parser.add_argument("--seed-count", type=int)
    parser.add_argument("--iterations", type=int, default=80)
    arguments = parser.parse_args()
    os.nice(10)
    started = time.monotonic()
    if arguments.action == "generate":
        write_json(ROOT / "protected_hashes.json", source_hashes())
        specifications = [(12, 6, .02, True)] + [(width, potential, broadening, False) for width in (14, 16, 18, 20) for potential in (3.2, 6) for broadening in (.01, .02)] + [(12, 6, broadening, False) for broadening in (.01, .02)]
        with ProcessPoolExecutor(max_workers=min(len(specifications), arguments.workers)) as executor:
            results = list(executor.map(generate_case, specifications))
        write_json(ROOT / "manifest.json", {"cases": results, "generation_seconds": time.monotonic() - started, "core_target": .96, "worst_family_target": .94, "primary_full_portfolio_case": "islands16_v6_eta0.01", "primary_selection_policy": "Predeclared moderate-size many-inclusion primary before any fitting; broad results and full 48-seed test determine whether it survives.", "screen": "Seeds 0,1,2; all six original stages, maxiter=80 per stage; NOT a full-strength hardness test.", "full_portfolio": "Original maxiter=250, all six stages and all seeds 0..47, linear/log/sqrt modes, exact count constraint; no witness starts."})
        write_json(ROOT / "adaptations.json", {"provenance": "Generation_2 fresh-agent research snapshots, identical to preserved top-level algorithm files. The generation_2 final submission retained design.json, construction sources, and research outputs; generation_1 alone cleaned down to design.json.", "source_files": [str((CHAMPION / "research" / name).relative_to(CONCEPT)) for name in ("optimize.py", "continuation.py", "discrete.py")], "changes": ["64 -> candidate COUNT and 24 -> config BUDGET only for design dimensions/budget; original main executor max_workers=24 retained", ".375 -> BUDGET/COUNT", "Explicit case ASSETS override, output isolation, archived official forward model", "Discrete low-rank swap onsite literal 6 -> config pin_potential", "Stage maxiter parameter: 80 for labeled screening, original 250 for full-strength tests", "Instrumentation wraps scipy minimize but does not change objective, exact equality, gradients, bounds, penalty sequence, ftol, initialization, or seed mapping"], "successful_original_seed": 7, "successful_original_stage": 1, "original_schedule": [.02, .1, .3, 1., 3., 10.], "original_iteration_limit": 250, "original_seed_count": 48})
    elif arguments.action in ("run", "auxiliary"):
        cases = arguments.cases or [path.name for path in sorted((ROOT / "cases").iterdir()) if path.name != "generation_2_control"]
        seeds = list(range(arguments.seed_count)) if arguments.seed_count is not None else arguments.seeds
        jobs = [(case, seed, arguments.iterations) for case in cases for seed in seeds] if arguments.action == "run" else [(case, seed, "lbfgs_then_ls" if seed < 8 else "cold_ls") for case in cases for seed in range(16)]
        runner = run_continuation if arguments.action == "run" else run_auxiliary
        with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
            futures = {executor.submit(runner, job): job for job in jobs}
            for future in as_completed(futures):
                result = future.result()
                print(json.dumps({"event": "finished", "case": result["case"], "seed": result["seed"], "best": result["best_spectral"], "seconds": result["total_seconds"]}), flush=True)
        write_json(ROOT / f"batch_{time.time_ns()}.json", {"jobs": jobs, "batch_wall_seconds": time.monotonic() - started})
    print(json.dumps(summarize(), indent=2), flush=True)
    audit()


if __name__ == "__main__":
    main()
