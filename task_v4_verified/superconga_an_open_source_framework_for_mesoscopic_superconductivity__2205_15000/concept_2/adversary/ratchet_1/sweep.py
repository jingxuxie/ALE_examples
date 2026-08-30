import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True

import numpy as np
from scipy.linalg import eigh, solve
from scipy.optimize import least_squares

from adapter import CONCEPT, ROOT, adaptation_diff, load_champion

sys.path.insert(0, str(CONCEPT / "participant" / "workspace"))
sys.path.insert(0, str(CONCEPT / "evaluator"))
from spectral import discrepancies, hamiltonian, load_problem, response, validate_design
from checker import independent_hamiltonian, independent_response


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def source_hashes():
    paths = list((CONCEPT / "champions" / "generation_1").glob("*"))
    paths += [path for folder in ("participant", "evaluator") for path in (CONCEPT / folder).rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    return {str(path.relative_to(CONCEPT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths) if path.is_file()}


def score(config, target, pattern):
    started = time.monotonic()
    observed = independent_response(config, pattern)
    result = discrepancies(config, observed, target)
    try:
        validate_design(config, pattern)
        result["valid"] = True
    except ValueError as error:
        result["valid"] = False
        result["invalid_reason"] = str(error)
    result["checker_seconds"] = time.monotonic() - started
    result["passed"] = bool(result["valid"] and result["core_score"] >= 0.96 and result["worst_family_score"] >= 0.94 and result["checker_seconds"] <= 120)
    return result


def cavity_pattern(config):
    width, height = config["width"], config["height"]
    occupied = {(column, 2) for column in range(2, width - 2)}
    occupied |= {(column, row) for column in (2, width - 3) for row in range(3, height - 2)}
    occupied |= {(3, 3), (width - 4, 3)}
    return np.array([int(tuple(coordinate) in occupied) for coordinate in config["candidates"]])


def verify_case(case_dir, config, pattern, target):
    started = time.monotonic()
    validate_design(config, pattern)
    independent = independent_response(config, pattern)
    check = {"target_checker_max_error": float(np.max(np.abs(independent - target)))}
    matrix = hamiltonian(config, pattern, config["conditions"][0])
    alternate = independent_hamiltonian(config, pattern, config["conditions"][0])
    check["matrix_max_error"] = float(np.max(np.abs(matrix - alternate)))
    check["hermiticity_max_error"] = float(np.max(np.abs(matrix - matrix.conj().T)))
    eigenvalues = eigh(matrix, eigvals_only=True, check_finite=False)
    check["particle_hole_max_error"] = float(np.max(np.abs(eigenvalues + eigenvalues[::-1])))
    positions = np.array([row * config["width"] + column for column, row in config["probes"]])
    right = np.eye(len(matrix), dtype=complex)[:, positions]
    energy_indices = np.linspace(0, len(config["energies"]) - 1, 5, dtype=int)
    resolvent_error = 0.0
    for energy_index in energy_indices:
        energy = config["energies"][energy_index]
        inverse_columns = solve((energy + 1j * config["broadening"]) * np.eye(len(matrix)) - matrix, right, check_finite=False)
        observed = -inverse_columns[positions, np.arange(len(positions))].imag / np.pi
        resolvent_error = max(resolvent_error, float(np.max(np.abs(observed - target[0, :, energy_index]))))
    check["direct_resolvent_max_error"] = resolvent_error
    optimize, continuation = load_champion(case_dir / "public", case_dir / "private")
    fit = optimize.SpectralFit()
    random = np.random.default_rng(119)
    continuous = random.uniform(0.1, 0.9, len(pattern))
    direction = random.normal(size=len(pattern))
    evaluation_start = time.monotonic()
    residual, jacobian = fit.evaluate(continuous)
    check["analytic_evaluation_seconds"] = time.monotonic() - evaluation_start
    check["adapted_forward_max_error"] = float(np.max(np.abs(fit.observed - response(config, continuous))))
    increment = 1e-7
    numerical = (fit.evaluate(continuous + increment * direction, False)[0] - fit.evaluate(continuous - increment * direction, False)[0]) / (2 * increment)
    check["jacobian_direction_relative_error"] = float(np.linalg.norm(numerical - jacobian @ direction) / np.linalg.norm(numerical))
    transformed = continuation.TransformedFit(fit, sigma=1.5, cumulative=1, binary=1)
    transformed_jacobian = transformed.jacobian(continuous)
    numerical = (transformed.residual(continuous + increment * direction) - transformed.residual(continuous - increment * direction)) / (2 * increment)
    check["continuation_jacobian_relative_error"] = float(np.linalg.norm(numerical - transformed_jacobian @ direction) / np.linalg.norm(numerical))
    check["witness_score"] = score(config, target, pattern)
    check["verification_seconds"] = time.monotonic() - started
    check["passed"] = bool(all(value < 1e-9 for key, value in check.items() if key.endswith("max_error")) and check["jacobian_direction_relative_error"] < 1e-5 and check["continuation_jacobian_relative_error"] < 1e-5 and check["witness_score"]["passed"])
    write_json(case_dir / "private" / "verification.json", check)
    if not check["passed"]:
        raise RuntimeError(f"Validation failed: {case_dir.name}: {check}")
    return check


def generate_case(specification):
    name, broadening, potential, width, original = specification
    config, original_target = load_problem(CONCEPT / "participant" / "input")
    if original:
        pattern = np.array(json.loads((CONCEPT / "champions" / "generation_1" / "design.json").read_text())["pattern"])
        target = original_target
    else:
        config.update(width=width, height=width, broadening=broadening, pin_potential=potential)
        config["candidates"] = [[column, row] for row in range(2, width - 2) for column in range(2, width - 2)]
        config["probes"] = [[0, 3], [0, width - 4], [width - 1, 2], [width - 1, width - 3], [3, 0], [width - 4, width - 1], [width // 2 - 1, width // 2 - 1], [width - 4, 4]]
        intervals = max(30, int(np.ceil(0.6 / (broadening / 2))))
        config["energies"] = np.linspace(-0.3, 0.3, intervals + 1).tolist()
        pattern = cavity_pattern(config)
        config["normal_site_count"] = int(pattern.sum())
        validate_design(config, pattern)
        target = response(config, pattern)
    case_dir = ROOT / "cases" / name
    (case_dir / "public" / "input").mkdir(parents=True, exist_ok=True)
    (case_dir / "private").mkdir(exist_ok=True)
    write_json(case_dir / "public" / "input" / "device.json", config)
    np.savez_compressed(case_dir / "public" / "input" / "target.npz", ldos=target)
    write_json(case_dir / "private" / "design.json", {"pattern": pattern.tolist()})
    verification = verify_case(case_dir, config, pattern, target)
    metadata = {"case": name, "broadening": config["broadening"], "pin_potential": config["pin_potential"], "width": config["width"], "candidate_count": len(pattern), "normal_site_count": int(pattern.sum()), "energy_count": len(config["energies"]), "energy_spacing": float(np.max(np.diff(config["energies"]))), "pattern_recipe": "preserved generation_1 control" if original else "open U cavity: bottom row y=2, x=2..W-3; arms x=2,W-3, y=3..H-3; inner corners (3,3),(W-4,3)", "verification": verification}
    write_json(case_dir / "private" / "metadata.json", metadata)
    return metadata


def run_fit(job):
    case, mode, seed, nfev = job
    case_dir = ROOT / "cases" / case
    output = case_dir / "runs" / f"{mode}_{seed}_{nfev}"
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "result.json"
    if report_path.exists():
        return json.loads(report_path.read_text())
    started = time.monotonic()
    optimize, continuation = load_champion(case_dir / "public", output)
    fit = optimize.SpectralFit()
    random = np.random.default_rng(seed)
    count = len(fit.config["candidates"])
    if mode == "direct":
        pattern = np.full(count, fit.config["normal_site_count"] / count) if seed == 0 else random.uniform(0.02, 0.73, count)
        stages = [(0, 0, 0)]
    else:
        pattern = np.full(count, fit.config["normal_site_count"] / count) + random.normal(0, 0.03, count)
        stages = {"smooth": [(3, 0, 0), (1.5, 0, 0), (0.6, 0, 0), (0, 0, 0)], "cdf": [(0, 1, 0), (1, 0, 0), (0, 0, 0)], "binary": [(1.5, 0, 0), (0.6, 0, 1), (0, 0, 2), (0, 0, 0)]}[mode]
    report = {"case": case, "mode": mode, "seed": seed, "max_nfev_per_stage": nfev, "stages": []}
    for stage_index, (sigma, cumulative, binary) in enumerate(stages):
        transformed = fit if mode == "direct" else continuation.TransformedFit(fit, sigma=sigma, cumulative=cumulative, binary=binary)
        stage_start = time.monotonic()
        cpu_start = time.process_time()
        result = least_squares(transformed.residual, np.clip(pattern, 1e-9, 1 - 1e-9), jac=transformed.jacobian, bounds=(0, 1), max_nfev=nfev, ftol=1e-9 if mode == "direct" else 1e-7, xtol=1e-9 if mode == "direct" else 1e-7, gtol=1e-8 if mode == "direct" else 1e-7)
        optimizer_seconds = time.monotonic() - stage_start
        optimizer_cpu_seconds = time.process_time() - cpu_start
        pattern = result.x
        projected = optimize.project(pattern)
        measured = score(fit.config, fit.target, projected)
        continuous_error = float(np.sqrt(np.mean(fit.residual(pattern) ** 2)))
        record = {"stage": stage_index, "sigma": sigma, "cumulative": cumulative, "binary_penalty": binary, "nfev": result.nfev, "njev": result.njev, "optimizer_seconds": optimizer_seconds, "optimizer_cpu_seconds": optimizer_cpu_seconds, "continuous_relative_rmse": continuous_error, "continuous_sum": float(pattern.sum()), "binary_distance": float(np.mean(np.minimum(pattern, 1 - pattern))), "solver_status": result.status, "score": measured, "pattern": projected.tolist()}
        np.savez_compressed(output / f"stage_{stage_index}.npz", continuous=pattern, pattern=projected)
        write_json(output / f"stage_{stage_index}.json", record)
        report["stages"].append(record)
        print(json.dumps({"event": "stage", "case": case, "mode": mode, "seed": seed, **{key: record[key] for key in ("stage", "nfev", "optimizer_seconds", "continuous_relative_rmse", "score")}}), flush=True)
    best = min(report["stages"], key=lambda entry: entry["score"]["relative_rmse"])
    valid_stages = [entry for entry in report["stages"] if entry["score"]["valid"]]
    report["best_spectral"] = best["score"]
    report["best_valid"] = min(valid_stages, key=lambda entry: entry["score"]["relative_rmse"])["score"] if valid_stages else None
    report["total_seconds"] = time.monotonic() - started
    write_json(report_path, report)
    return report


def summarize():
    rows = []
    for case_dir in sorted((ROOT / "cases").iterdir()):
        metadata = json.loads((case_dir / "private" / "metadata.json").read_text())
        runs = [json.loads(path.read_text()) for path in sorted((case_dir / "runs").glob("*/result.json"))]
        stages = [stage for run in runs for stage in run["stages"]]
        valid = [stage for stage in stages if stage["score"]["valid"]]
        rows.append({"case": case_dir.name, "broadening": metadata["broadening"], "pin_potential": metadata["pin_potential"], "width": metadata["width"], "energy_count": metadata["energy_count"], "completed_runs": len(runs), "completed_stages": len(stages), "total_nfev": sum(stage["nfev"] for stage in stages), "optimizer_seconds_sum": sum(stage["optimizer_seconds"] for stage in stages), "optimizer_cpu_seconds_sum": sum(stage["optimizer_cpu_seconds"] for stage in stages), "best_spectral": min(stages, key=lambda entry: entry["score"]["relative_rmse"])["score"] if stages else None, "best_valid": min(valid, key=lambda entry: entry["score"]["relative_rmse"])["score"] if valid else None, "passing_stages": sum(stage["score"]["passed"] for stage in stages), "witness_verified": metadata["verification"]["passed"]})
    write_json(ROOT / "summary.json", rows)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["generate", "run", "summary"])
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--modes", nargs="*", default=["direct"])
    parser.add_argument("--seeds", nargs="*", type=int, default=[0, 17, 71])
    parser.add_argument("--nfev", type=int, default=200)
    arguments = parser.parse_args()
    started = time.monotonic()
    os.nice(10)
    if arguments.action == "generate":
        write_json(ROOT / "original_hashes.json", source_hashes())
        cases = [("g1_control", 0.032, 1.65, 12, True)]
        for broadening in (0.04, 0.02, 0.008, 0.004):
            for potential in (1.65, 3.2, 6.0):
                cases.append((f"u12_eta{broadening:g}_v{potential:g}", broadening, potential, 12, False))
        cases.extend([("u14_eta0.008_v3.2", 0.008, 3.2, 14, False), ("u16_eta0.004_v6", 0.004, 6.0, 16, False)])
        with ProcessPoolExecutor(max_workers=min(arguments.workers, len(cases))) as executor:
            results = list(executor.map(generate_case, cases))
        write_json(ROOT / "manifest.json", {"cases": results, "generation_seconds": time.monotonic() - started, "core_target": 0.96, "worst_family_target": 0.94, "protocol": "3 independent direct starts, 200 nfev each; extend difficult finalists with original continuation schedules", "non_control_energy_resolution": "uniform [-0.3, 0.3] subgap window, step <= eta/2 (at least four samples per Lorentzian FWHM)", "generation_pilot": "A full [-0.9,0.9] band was verified before any fitting, then narrowed uniformly across all physical cases for the initial sidecar computational budget; no target selection based on optimizer results.", "private_pattern_policy": "deterministic open cavity, identical across 12-case eta/potential factorial; not selected by target fingerprint or optimization failure"})
        write_json(ROOT / "adaptations.json", adaptation_diff(ROOT / "cases" / "g1_control" / "public", ROOT))
    elif arguments.action == "run":
        cases = arguments.cases or sorted(path.name for path in (ROOT / "cases").iterdir())
        jobs = [(case, mode, seed, arguments.nfev) for case in cases for mode in arguments.modes for seed in arguments.seeds]
        with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
            futures = {executor.submit(run_fit, job): job for job in jobs}
            for future in as_completed(futures):
                result = future.result()
                print(json.dumps({"event": "finished", "case": result["case"], "mode": result["mode"], "seed": result["seed"], "score": result["best_spectral"], "seconds": result["total_seconds"]}), flush=True)
        write_json(ROOT / f"batch_{time.time_ns()}.json", {"jobs": jobs, "batch_wall_seconds": time.monotonic() - started})
    rows = summarize()
    write_json(ROOT / "hash_audit.json", {"unchanged": source_hashes() == json.loads((ROOT / "original_hashes.json").read_text()), "current": source_hashes()})
    print(json.dumps(rows, indent=2), flush=True)


if __name__ == "__main__":
    main()
