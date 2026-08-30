import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import concurrent.futures
import datetime
import hashlib
import json
import math
import multiprocessing
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, minimize
from scipy.special import expit, logsumexp

import kernel

HERE = Path(__file__).resolve().parent
CORES = sorted(os.sched_getaffinity(0))[:4]
STOP = None
ROW_MATRIX = np.zeros((15, 241))
for coordinate, row in enumerate(kernel.LOWER[0]):
    ROW_MATRIX[row - 1, coordinate] = 1
    ROW_MATRIX[row - 1, 120 + coordinate] = 1
COUNTS = ((kernel.SPINS + 1) / 2).sum(axis=1)
HALF_IDS = np.arange(0, 65536, 2, dtype=np.uint32)


def save(name, document):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def transform(values):
    result = np.asarray(values, dtype=float).copy()
    stride = 1
    while stride < len(result):
        blocks = result.reshape(-1, 2, stride)
        first, second = blocks[:, 0].copy(), blocks[:, 1].copy()
        blocks[:, 0], blocks[:, 1] = first + second, first - second
        stride *= 2
    return result


KERNELS = {radius: transform((np.minimum(COUNTS, 16 - COUNTS) <= radius).astype(float)) for radius in (2, 3, 4)}


def sector_arrays(half_probability):
    full = np.empty(65536)
    full[::2] = half_probability / 2
    full[1::2] = half_probability[::-1] / 2
    transformed = transform(full)
    return {radius: transform(transformed * values) / 65536 for radius, values in KERNELS.items()}


def choose_sector(target_arrays, proposal_arrays):
    best = None
    for radius in (2, 3, 4):
        eligible = target_arrays[radius] >= 0.350001
        if not np.any(eligible):
            continue
        identifiers = np.flatnonzero(eligible)
        identifier = int(identifiers[np.argmin(proposal_arrays[radius][identifiers])])
        mass = float(max(0.0, proposal_arrays[radius][identifier]))
        candidate = (mass, -float(target_arrays[radius][identifier]), radius, identifier)
        if best is None or candidate < best:
            best = candidate
    return best


def ground_components(energy):
    identifiers = HALF_IDS[energy == energy.min()]
    index = {int(identifier): position for position, identifier in enumerate(identifiers)}
    parents = list(range(len(identifiers)))

    def representative(position):
        while parents[position] != position:
            parents[position] = parents[parents[position]]
            position = parents[position]
        return position

    for position, identifier in enumerate(identifiers):
        for site in range(16):
            neighbor = int(identifier) ^ (1 << site)
            if neighbor & 1:
                neighbor ^= 65535
            other = index.get(neighbor)
            if other is not None:
                parents[representative(other)] = representative(position)
    components = {}
    for position, identifier in enumerate(identifiers):
        components.setdefault(representative(position), []).append(int(identifier))
    return sorted(components.values(), key=len, reverse=True)


def canonical_bonds(bonds):
    neighbors = [[] for site in range(16)]
    for coupling, (first, second) in zip(bonds, kernel.EDGES):
        neighbors[first].append((second, coupling))
        neighbors[second].append((first, coupling))
    gauge = [0] * 16
    gauge[0] = 1
    queue = [0]
    for site in queue:
        for neighbor, coupling in neighbors[site]:
            if not gauge[neighbor]:
                gauge[neighbor] = gauge[site] * coupling
                queue.append(neighbor)
    return tuple(int(coupling * gauge[first] * gauge[second]) for coupling, (first, second) in zip(bonds, kernel.EDGES))


def build_pool(generator, deadline):
    started = time.monotonic()
    pool = []
    models = []
    seen = set()
    attempts = 0
    stop = min(deadline - 120, started + 100)
    while time.monotonic() < stop and len(pool) < 56 and attempts < 6000:
        attempts += 1
        bonds = canonical_bonds(generator.choice([-1, 1], size=32).tolist())
        if bonds in seen:
            continue
        seen.add(bonds)
        frustration = kernel.PHYSICS.frustrated_plaquettes(bonds)
        if not 4 <= frustration <= 12:
            continue
        energy = -(kernel.FEATURES @ np.asarray(bonds))
        ground = np.flatnonzero(energy == energy.min())
        if len(ground) < 8:
            continue
        beta = float(generator.choice([1.0, 1.1, 1.2, 1.35]))
        target = np.exp(-beta * energy - logsumexp(-beta * energy))
        entropy = float(-target @ np.log(target) + math.log(2))
        if entropy < 3.25:
            continue
        target_arrays = sector_arrays(target)
        if max(float(values.max()) for values in target_arrays.values()) < 0.350001:
            continue
        components = ground_components(energy)
        basins = []
        for component in components[:5]:
            if len(component) < 3:
                continue
            mask = np.zeros(32768, dtype=bool)
            for identifier in component:
                mask[identifier // 2] = True
                for site in range(16):
                    neighbor = identifier ^ (1 << site)
                    if neighbor & 1:
                        neighbor ^= 65535
                    mask[neighbor // 2] = True
            basins.append((mask, {"type": "ground_component_plus_single_flips", "component_identifiers": component}))
        for position in generator.choice(ground, size=min(5, len(ground)), replace=False):
            distances = np.count_nonzero(kernel.HALF != kernel.HALF[position], axis=1)
            for radius in (2, 3):
                mask = np.minimum(distances, 16 - distances) <= radius
                basins.append((mask, {"type": "antipodal_low_energy_ball", "center_identifier": int(HALF_IDS[position]), "radius": radius}))
        accepted = 0
        for mask, description in basins:
            mass = float(target[mask].sum())
            if not 1e-4 < mass < 0.68:
                continue
            conditional = np.where(mask, target / mass, 0.0)
            nonzero = conditional > 0
            conditional_entropy = float(-conditional[nonzero] @ np.log(conditional[nonzero]) + math.log(2))
            if conditional_entropy < 3.08:
                continue
            proposal_arrays = sector_arrays(conditional)
            chosen = choose_sector(target_arrays, proposal_arrays)
            if chosen is None or chosen[0] > 0.0003:
                continue
            proposal_mass, negative_target_mass, radius, identifier = chosen
            pool.append({"pool_id": len(pool), "model_id": len(models), "bonds": list(bonds), "beta": beta,
                         "pattern": kernel.SPINS[identifier].astype(int).tolist(), "radius": radius,
                         "training_half_indices": np.flatnonzero(mask).tolist(), "basin": description,
                         "training_target_mass": mass, "training_entropy": conditional_entropy,
                         "target_sector_mass": -negative_target_mass, "training_sector_mass": proposal_mass,
                         "frustrated_plaquettes": frustration})
            accepted += 1
            if accepted >= 2 or len(pool) >= 56:
                break
        if accepted:
            models.append({"model_id": len(models), "bonds": list(bonds), "beta": beta, "entropy": entropy,
                           "frustrated_plaquettes": frustration, "ground_degeneracy": 2 * len(ground),
                           "antipodal_ground_component_sizes": [2 * len(component) for component in components], "basins": accepted})
            save("basin_pool.json", pool)
            save("models.json", models)
    diagnostics = {"random_draws": attempts, "distinct_gauge_classes_drawn": len(seen), "accepted_models": len(models),
                   "accepted_basins": len(pool), "elapsed_seconds": time.monotonic() - started}
    save("pool_generation.json", diagnostics)
    print(json.dumps({"pool": diagnostics}), flush=True)
    return pool


def order_for(variant, generator):
    if variant % 5 == 0:
        return list(range(16))
    if variant % 5 == 1:
        return [4 * row + column for column in range(4) for row in range(4)]
    neighbors = [set() for site in range(16)]
    for first, second in kernel.EDGES:
        neighbors[first].add(second)
        neighbors[second].add(first)
    if variant % 5 == 2:
        remaining = set(range(16))
        eliminated = []
        while remaining:
            costs = {}
            for site in remaining:
                adjacent = neighbors[site] & remaining
                missing = sum(second not in neighbors[first] for first in adjacent for second in adjacent if first < second)
                costs[site] = (missing, len(adjacent), float(generator.random()))
            site = min(remaining, key=costs.get)
            adjacent = neighbors[site] & remaining
            for first in adjacent:
                neighbors[first].update(adjacent - {first})
            remaining.remove(site)
            eliminated.append(site)
        return eliminated[::-1]
    if variant % 5 == 3:
        first = int(generator.integers(16))
        order = [first]
        visited = {first}
        for site in order:
            adjacent = list(neighbors[site] - visited)
            generator.shuffle(adjacent)
            for neighbor in adjacent:
                if neighbor not in visited:
                    visited.add(neighbor)
                    order.append(neighbor)
        return order
    return generator.permutation(16).tolist()


def fit_rows(blueprint, order, deadline):
    indices = np.asarray(blueprint["training_half_indices"], dtype=int)
    spins = kernel.HALF[indices][:, order]
    energy = -(kernel.FEATURES[indices] @ np.asarray(blueprint["bonds"]))
    probability = np.exp(-blueprint["beta"] * energy - logsumexp(-blueprint["beta"] * energy))
    weights = np.zeros((16, 16))
    diagnostics = []
    for position in range(1, 16):
        previous = spins[:, :position]
        labels = (spins[:, position] + 1) / 2

        def objective(parameters):
            if time.monotonic() >= deadline or STOP.is_set():
                raise TimeoutError("row-fit time budget")
            row = parameters[:position] - parameters[position:]
            logits = previous @ row
            loss = float(probability @ (np.logaddexp(0, logits) - labels * logits))
            gradient = previous.T @ (probability * (expit(logits) - labels))
            return loss, np.r_[gradient, -gradient]

        result = minimize(objective, np.zeros(2 * position), jac=True, method="SLSQP",
                          bounds=Bounds(np.zeros(2 * position), np.full(2 * position, kernel.BOUND)),
                          constraints=[LinearConstraint(np.ones((1, 2 * position)), 0, kernel.BOUND)],
                          options={"maxiter": 90, "ftol": 2e-10, "disp": False})
        row = result.x[:position] - result.x[position:]
        norm = math.fsum(abs(value) for value in row)
        if norm > kernel.BOUND:
            row *= kernel.BOUND / norm
        weights[position, :position] = row
        loss, packed_gradient = objective(np.r_[np.maximum(row, 0), np.maximum(-row, 0)])
        gradient = packed_gradient[:position]
        gap = float(gradient @ row + kernel.BOUND * np.max(np.abs(gradient)))
        diagnostics.append({"row": position, "success": bool(result.success), "iterations": int(result.nit), "convex_duality_gap_bound": max(0.0, gap)})
    return weights, diagnostics


def initialize(event):
    global STOP
    STOP = event
    worker = multiprocessing.current_process()._identity[-1] - 1
    os.sched_setaffinity(0, [CORES[worker % len(CORES)]])


def run_job(job):
    started = time.monotonic()
    deadline = min(job["deadline"], started + 85)
    blueprint = job["blueprint"]
    weights, fit_diagnostics = fit_rows(blueprint, job["order"], deadline)
    document = {"schema_version": 1, "bonds": blueprint["bonds"], "beta": blueprint["beta"], "order": job["order"],
                "weights": weights.tolist(), "pattern": blueprint["pattern"], "radius": blueprint["radius"]}
    energy = -(kernel.FEATURES @ np.asarray(document["bonds"]))
    target = np.exp(-document["beta"] * energy - logsumexp(-document["beta"] * energy))
    ordered = kernel.HALF[:, document["order"]]
    logits = ordered @ weights.T
    probability = 2 * np.exp(-np.logaddexp(0, -ordered * logits).sum(axis=1))
    selected = choose_sector(sector_arrays(target), sector_arrays(probability))
    if selected is not None:
        document["radius"] = selected[2]
        document["pattern"] = kernel.SPINS[selected[3]].astype(int).tolist()
    fitted_document = json.loads(json.dumps(document))
    fitted_report = kernel.PHYSICS.evaluate_document(document, kernel.SPEC)
    best_document = json.loads(json.dumps(document))
    best_score = fitted_report["core_score"]
    best_fast_report = fitted_report
    packed = weights[kernel.LOWER]
    parameters = np.r_[np.maximum(packed, 0), np.maximum(-packed, 0), document["beta"]]
    gradient_weight = 100 if job["mode"] == 2 else 0
    problem = kernel.Problem(document, gradient_weight)
    problem.deadline = deadline
    phases = []
    active_phase = "variance"
    final_parameters = parameters.copy()

    def objective(values):
        nonlocal best_document, best_score, best_fast_report, final_parameters
        if STOP.is_set():
            raise TimeoutError("portfolio stopped")
        loss, gradient, constraints, jacobian, report, current = problem.calculate(values)
        final_parameters = values.copy()
        if np.max(np.abs(current).sum(axis=1)) <= math.log(99) and report["core_score"] > best_score:
            best_score = report["core_score"]
            best_document = dict(document, beta=float(values[-1]), weights=current.tolist())
            best_fast_report = report
        if report["passed"] and np.max(np.abs(current).sum(axis=1)) <= math.log(99):
            raise RuntimeError("candidate meets every gate")
        if active_phase == "kl-sector":
            return report["metrics"]["reverse_kl"] + 20 * report["metrics"]["proposal_sector_mass"] + 0.2 * loss, jacobian[1] - 20 * jacobian[4] + 0.2 * gradient
        return loss, gradient

    phase_names = ["kl-sector", "variance"] if job["mode"] == 1 else ["variance"]
    try:
        for active_phase in phase_names:
            result = minimize(objective, parameters, jac=True, method="SLSQP",
                              bounds=Bounds(np.r_[np.zeros(240), 1], np.r_[np.full(240, kernel.BOUND), 3]),
                              constraints=[LinearConstraint(ROW_MATRIX, np.zeros(15), np.full(15, kernel.BOUND)),
                                           {"type": "ineq", "fun": lambda values: problem.calculate(values)[2],
                                            "jac": lambda values: problem.calculate(values)[3]}],
                              options={"maxiter": 100 if active_phase == "kl-sector" else 200, "ftol": 1e-10, "disp": False})
            phases.append({"phase": active_phase, "success": bool(result.success), "iterations": int(result.nit), "message": str(result.message), "objective": float(result.fun)})
            parameters = result.x
            final_parameters = result.x
    except (TimeoutError, RuntimeError) as error:
        phases.append({"termination": str(error)})
    final_weights = np.zeros((16, 16))
    final_weights[kernel.LOWER] = final_parameters[:120] - final_parameters[120:240]
    for row in final_weights:
        norm = math.fsum(abs(value) for value in row)
        if norm > kernel.BOUND:
            row *= kernel.BOUND / norm
    final_document = dict(document, beta=float(np.clip(final_parameters[-1], 1, 3)), weights=final_weights.tolist())
    final_report = kernel.PHYSICS.evaluate_document(final_document, kernel.SPEC)
    best_report = kernel.PHYSICS.evaluate_document(best_document, kernel.SPEC)
    if final_report["core_score"] > best_report["core_score"]:
        best_document, best_report = final_document, final_report
    return {"trial_id": job["trial_id"], "pool_id": blueprint["pool_id"], "model_id": blueprint["model_id"],
            "order": job["order"], "mode": job["mode"], "elapsed_seconds": time.monotonic() - started,
            "fitting": fit_diagnostics, "optimizer_calls": problem.calls, "phases": phases,
            "fitted_witness": fitted_document, "fitted_report": fitted_report,
            "best_witness": best_document, "best_report": best_report,
            "final_witness": final_document, "final_report": final_report}


def official(directory):
    output = directory / "official_report.json"
    completed = subprocess.run([sys.executable, "-B", str(kernel.ROOT / "evaluator/evaluate.py"), "--submission", str(directory), "--output", str(output)], capture_output=True, text=True, timeout=125)
    if completed.returncode:
        raise RuntimeError(completed.stdout + completed.stderr)
    return json.loads(output.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deadline-utc", required=True)
    parser.add_argument("--seed", type=int, default=202608282118)
    arguments = parser.parse_args()
    started = time.monotonic()
    ending = datetime.datetime.fromisoformat(arguments.deadline_utc)
    remaining = max(0.0, (ending - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
    deadline = started + min(remaining, 1100)
    os.sched_setaffinity(0, CORES)
    baseline = json.loads((kernel.ROOT / "participant/baseline/witness.json").read_text())
    save("best/witness.json", baseline)
    best = official(HERE / "best")
    manifest = json.loads((kernel.ROOT / "adversary/release_manifest.json").read_text())
    before = {name: hashlib.sha256((kernel.ROOT / name).read_bytes()).hexdigest() for name in manifest["sha256"]}
    state = {"seed": arguments.seed, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "deadline_utc": arguments.deadline_utc, "remaining_seconds_at_start": remaining, "workers": len(CORES),
             "method": "distinct binary disorder; exact antipodal basins; bounded convex weighted row fits; coupled constrained refinement",
             "completed_trials": 0, "submitted_trials": 0, "best_score": best["core_score"],
             "passing_witness_found": False, "achievability": "unknown", "cpu_affinity": CORES,
             "source_sha256": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in ("portfolio.py", "kernel.py")},
             "no_fresh_attempt_reads": True, "no_frozen_edits": True}
    save("run.json", state)
    generator = np.random.default_rng(arguments.seed)
    blueprints = build_pool(generator, deadline)
    save("basin_pool.json", blueprints)
    ledger = []
    if blueprints:
        context = multiprocessing.get_context("fork")
        event = context.Event()
        pool = concurrent.futures.ProcessPoolExecutor(max_workers=len(CORES), mp_context=context, initializer=initialize, initargs=(event,))
        pending = {}
        trial_id = 0

        def retain(result):
            nonlocal best
            document = result.pop("best_witness")
            report = result.pop("best_report")
            identifier = result["trial_id"]
            for label in ("fitted", "final"):
                save(f"trials/{identifier:04d}/{label}_witness.json", result.pop(label + "_witness"))
                save(f"trials/{identifier:04d}/{label}_report.json", result.pop(label + "_report"))
            save(f"trials/{identifier:04d}/witness.json", document)
            save(f"trials/{identifier:04d}/exact_report.json", report)
            result.update(score=report["core_score"], passed=report["passed"], metrics=report["metrics"])
            ledger.append(result)
            state["completed_trials"] += 1
            if report["core_score"] > state["best_score"] or report["passed"]:
                save("best/witness.json", document)
                best = official(HERE / "best")
                state.update(best_score=best["core_score"], best_trial=identifier,
                             passing_witness_found=bool(best["passed"]), achievability="witnessed" if best["passed"] else "unknown")
                print(json.dumps({"elapsed_seconds": time.monotonic() - started, "trial_id": identifier, "model_id": result["model_id"], "score": best["core_score"], "official_passed": best["passed"], "metrics": best["metrics"]}), flush=True)
            state["elapsed_seconds"] = time.monotonic() - started
            save("trials.json", ledger)
            save("run.json", state)

        try:
            while time.monotonic() < deadline and not state["passing_witness_found"]:
                while len(pending) < len(CORES) and time.monotonic() < deadline:
                    blueprint = blueprints[trial_id % len(blueprints)]
                    variant = (trial_id // len(blueprints) + trial_id) % 5
                    job = {"trial_id": trial_id, "blueprint": blueprint, "order": order_for(variant, generator), "mode": trial_id % 3, "deadline": deadline}
                    save(f"trials/{trial_id:04d}/job.json", job)
                    pending[pool.submit(run_job, job)] = trial_id
                    trial_id += 1
                    state["submitted_trials"] = trial_id
                finished, unused = concurrent.futures.wait(pending, timeout=1, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in finished:
                    identifier = pending.pop(future)
                    try:
                        retain(future.result())
                    except Exception as error:
                        ledger.append({"trial_id": identifier, "error": type(error).__name__ + ": " + str(error)})
                        save("trials.json", ledger)
                    if state["passing_witness_found"]:
                        event.set()
                        break
        finally:
            event.set()
            pool.shutdown(wait=True, cancel_futures=True)
            for future, identifier in pending.items():
                if not future.cancelled():
                    try:
                        retain(future.result())
                    except Exception as error:
                        ledger.append({"trial_id": identifier, "error": type(error).__name__ + ": " + str(error)})
    best = official(HERE / "best")
    state.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - started,
                 termination="passing witness" if best["passed"] else "bounded portfolio complete without passing witness",
                 passing_witness_found=bool(best["passed"]), achievability="witnessed" if best["passed"] else "unknown",
                 distinct_models_refined=len({row["model_id"] for row in ledger if "model_id" in row}),
                 frozen_file_changes=[name for name, digest in before.items() if hashlib.sha256((kernel.ROOT / name).read_bytes()).hexdigest() != digest])
    save("run.json", state)
    save("trials.json", ledger)
    print(json.dumps(state, indent=2), flush=True)


if __name__ == "__main__":
    main()
