import argparse
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh_tridiagonal, solve_banded
from scipy.optimize import minimize

from path_audit import EXPECTED_HASH, old

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
import reference

STATS = {"steps": 0, "dense_fallbacks": 0, "maximum_selected_modes": 0, "follow_calls": []}
DEADLINE = np.inf
RELAX_ITERATIONS = 1600


class BudgetExpired(Exception):
    pass


def band_solve(diagonal, offdiagonal, gradient):
    band = np.zeros((3, len(diagonal)))
    band[0, 1:] = offdiagonal
    band[1] = diagonal
    band[2, :-1] = offdiagonal
    return solve_banded((1, 1), band, gradient, check_finite=False)


def old_step(diagonal, offdiagonal, gradient):
    values, vectors = eigh_tridiagonal(diagonal, offdiagonal, check_finite=False)
    coefficient = -(vectors.T @ gradient) / np.maximum(np.abs(values), 1e-3)
    coefficient[0] *= -1
    return vectors @ coefficient


def structured_step(diagonal, offdiagonal, gradient):
    lowest = eigh_tridiagonal(diagonal, offdiagonal, select="i", select_range=(0, 1), eigvals_only=True, check_finite=False)
    if lowest[0] <= 1e-3:
        values, vectors = eigh_tridiagonal(diagonal, offdiagonal, select="v", select_range=(-np.inf, 1e-3), check_finite=False)
    else:
        values, vectors = eigh_tridiagonal(diagonal, offdiagonal, select="i", select_range=(0, 0), check_finite=False)
    STATS["steps"] += 1
    STATS["maximum_selected_modes"] = max(STATS["maximum_selected_modes"], len(values))
    if np.min(np.abs(values)) < 1e-8:
        STATS["dense_fallbacks"] += 1
        return lowest, old_step(diagonal, offdiagonal, gradient)
    step = -band_solve(diagonal, offdiagonal, gradient)
    coefficient = -1 / np.maximum(np.abs(values), 1e-3)
    coefficient[0] *= -1
    step += vectors @ ((coefficient + 1 / values) * (vectors.T @ gradient))
    return lowest, step


def follow_saddle(model, initial, maxiter=160):
    started = time.perf_counter()
    record = {"maxiter": maxiter, "start_energy": float(model.energy_gradient(initial)[0]), "converged": False}
    STATS["follow_calls"].append(record)
    angles = initial.copy()
    best = None
    try:
        for iteration in range(maxiter):
            if time.monotonic() > DEADLINE:
                raise BudgetExpired()
            energy, gradient = model.energy_gradient(angles)
            diagonal, offdiagonal = model.hessian(angles)
            values, step = structured_step(diagonal, offdiagonal, gradient)
            residual = np.max(np.abs(gradient))
            record.update(iterations=iteration + 1, residual=float(residual), lowest=values.tolist())
            if values[0] < -1e-8 and values[1] > 1e-9:
                if best is None or residual < best[0]:
                    best = (residual, angles.copy())
                if residual < 2e-11:
                    record["converged"] = True
                    return angles
            if residual < 1e-10 and values[0] > 0:
                return None
            largest = max(np.max(np.abs(step)) / 0.22, np.linalg.norm(step) / 0.65, 1.0)
            step /= largest
            if values[0] < 0 and values[1] > 0 and residual < 0.02:
                trial = angles + step
                for backtrack in range(8):
                    if np.linalg.norm(model.energy_gradient(trial)[1]) < np.linalg.norm(gradient):
                        break
                    step *= 0.5
                    trial = angles + step
                angles = trial
            else:
                angles += step
        if best is not None and best[0] < 2e-6:
            record["converged"] = True
            return best[1]
        return None
    finally:
        record["seconds"] = time.perf_counter() - started


def relax(model, initial):
    result = minimize(model.energy_gradient, initial, jac=True, method="L-BFGS-B", options={"gtol": 2e-10, "ftol": 1e-15, "maxiter": RELAX_ITERATIONS, "maxls": 30, "maxcor": 15})
    angles = result.x
    for iteration in range(8):
        _, gradient = model.energy_gradient(angles)
        if np.max(np.abs(gradient)) < 1e-10:
            break
        diagonal, offdiagonal = model.hessian(angles)
        values = eigh_tridiagonal(diagonal, offdiagonal, select="i", select_range=(0, 0), eigvals_only=True, check_finite=False)
        if values[0] <= 0:
            break
        step = band_solve(diagonal, offdiagonal, gradient)
        if np.max(np.abs(step)) > 0.1:
            break
        angles -= step
    return angles, {"lbfgs_iterations": int(result.nit), "lbfgs_message": str(result.message), "final_residual": float(np.max(np.abs(model.energy_gradient(angles)[1])))}


def connected(model, candidate):
    diagonal, offdiagonal = model.hessian(candidate)
    values, vectors = eigh_tridiagonal(diagonal, offdiagonal, select="i", select_range=(0, 1), check_finite=False)
    if values[0] >= 0 or values[1] <= 0:
        return {"connected": False, "reason": "planar_inertia"}
    unstable = vectors[:, 0]
    relaxed = [relax(model, candidate + sign * 0.12 * unstable) for sign in (-1, 1)]
    endpoints = [item[0] for item in relaxed]
    distances = np.array([[np.max(np.abs(old.wrap(endpoint - minimum))) for minimum in (model.start, model.finish)] for endpoint in endpoints])
    matched = bool(min(max(distances[0, 0], distances[1, 1]), max(distances[0, 1], distances[1, 0])) < 2e-3)
    return {"connected": matched, "endpoint_distances": distances.tolist(), "relaxations": [item[1] for item in relaxed]}


def validate_step():
    records = []
    for directory in [ROOT.parent / "N40", ROOT / "interface/N128"]:
        case = json.loads((directory / "case.json").read_text())
        model = old.SpinModel(case)
        planar = old.PlanarModel(model, model.plane())
        with np.load(directory / "reference.npz", allow_pickle=False) as archive:
            saddle = planar.angles(archive["saddle"])
        generator = np.random.default_rng(731901)
        for name, angles in [("minimum", planar.start), ("perturbed_saddle", saddle + generator.normal(0, 0.03, planar.count)), ("coherent_midpoint", 0.5 * (planar.start + planar.finish)), ("random_angles", generator.normal(0, 1, planar.count))]:
            gradient = planar.energy_gradient(angles)[1]
            diagonal, offdiagonal = planar.hessian(angles)
            exact = old_step(diagonal, offdiagonal, gradient)
            _, structured = structured_step(diagonal, offdiagonal, gradient)
            error = float(np.max(np.abs(exact - structured)))
            relative = error / max(1.0, float(np.max(np.abs(exact))))
            if relative > 1e-7:
                raise RuntimeError(f"structured step mismatch {name}: {relative}")
            records.append({"case_id": case["case_id"], "state": name, "max_absolute_step_error": error, "relative_step_error": relative})
    reference.write_json(ROOT / "structured_step_validation.json", records)


def profile(directory, images, directions, budget):
    global DEADLINE
    started = time.perf_counter()
    DEADLINE = time.monotonic() + budget
    STATS.update(steps=0, dense_fallbacks=0, maximum_selected_modes=0, follow_calls=[])
    case = json.loads((directory / "case.json").read_text())
    with np.load(directory / "reference.npz", allow_pickle=False) as archive:
        target = {name: archive[name].copy() for name in archive.files}
    model = old.SpinModel(case)
    planar = old.PlanarModel(model, model.plane())
    candidates = []
    traces = []
    original_follow = old.follow_saddle
    old.follow_saddle = follow_saddle
    timed_out = False
    try:
        for direction in directions:
            branch_started = time.perf_counter()
            found, path = old.string_search(planar, old.initial_path(planar, direction, images), DEADLINE)
            traces.append({"direction": direction, "seconds": time.perf_counter() - branch_started, "candidates": len(found), "final_peak_index": int(np.argmax(planar.energy_gradient(path)[0]))})
            for angles in found:
                if all(np.max(np.abs(old.wrap(angles - other))) > 1e-4 for other in candidates):
                    candidates.append(angles)
            if time.monotonic() > DEADLINE:
                timed_out = True
                break
    except BudgetExpired:
        timed_out = True
    finally:
        old.follow_saddle = original_follow
    candidates.sort(key=lambda angles: float(planar.energy_gradient(angles)[0]))
    accepted = None
    checks = []
    for angles in candidates:
        if time.monotonic() > DEADLINE:
            timed_out = True
            break
        spins = planar.spins(angles)
        info = reference.diagnose(case, spins)
        values = info["eigenvalues"]
        if values[0] < -1e-7 and values[1] > 1e-8:
            barrier = float(np.sum(reference.energy_gradient(case, spins)[0] - reference.energy_gradient(case, np.asarray(case["minimum_a"]))[0]))
            minimum_values = reference.diagnose(case, np.asarray(case["minimum_a"]))["eigenvalues"]
            log_factor = float(0.5 * (np.log(minimum_values).sum() - np.log(values[1:]).sum()))
            check = {"residual_meV": info["residual_meV"], "negative_modes": int(np.sum(values < -1e-6)), "zero_modes": int(np.sum(np.abs(values) <= 1e-6)), "barrier_meV": barrier, "barrier_error_meV": abs(barrier - float(target["barrier_meV"])), "spectrum_error_meV": float(np.max(np.abs(values - target["eigenvalues_saddle_meV"]))), "log_omega0_error": abs(log_factor - float(target["log_omega0"])), "connectivity": connected(planar, angles)}
            checks.append(check)
            if check["connectivity"]["connected"]:
                accepted = check
                break
    result = {"case_id": case["case_id"], "n_spins": case["n_spins"], "images": images, "directions": directions, "relax_iteration_limit": RELAX_ITERATIONS, "seconds": time.perf_counter() - started, "budget_seconds": budget, "timed_out": timed_out, "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "branch_traces": traces, "stats": STATS, "candidate_checks": checks, "accepted": accepted, "immutable_solver_sha256": EXPECTED_HASH, "method": "Private diagnostic: unchanged string and path initialization, same eigenvector-following step via tridiagonal solve plus selected-mode correction; connectivity Newton solves and full tangent spectra use banded structure. No trusted saddle is supplied to search; reference data are used only afterward for assessment. Not a new native reference or an isolated submission evaluation."}
    suffix = "_".join(str(direction) for direction in directions)
    reference.write_json(ROOT / "structured_profiles" / f"{case['case_id']}_images{images}_directions{suffix}_relax{RELAX_ITERATIONS}.json", result)
    print(json.dumps({name: result[name] for name in ["case_id", "images", "directions", "seconds", "timed_out", "accepted"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", type=Path)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--images", type=int, default=45)
    parser.add_argument("--directions", type=int, nargs="+", default=[0, 1, -1])
    parser.add_argument("--budget", type=float, default=90)
    parser.add_argument("--relax-iterations", type=int, default=1600)
    arguments = parser.parse_args()
    RELAX_ITERATIONS = arguments.relax_iterations
    if arguments.validate:
        validate_step()
    if arguments.directory:
        profile(arguments.directory.resolve(), arguments.images, arguments.directions, arguments.budget)
