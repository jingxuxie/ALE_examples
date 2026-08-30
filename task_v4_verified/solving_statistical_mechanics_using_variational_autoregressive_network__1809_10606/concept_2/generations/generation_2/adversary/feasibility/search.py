import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import concurrent.futures
import datetime
import hashlib
import importlib.util
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

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ORIGINAL = ROOT.parents[1]
MODULE_SPEC = importlib.util.spec_from_file_location("frozen_physics", ROOT / "evaluator/physics.py")
PHYSICS = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(PHYSICS)
SPEC = json.loads((ROOT / "participant/input/spec.json").read_text())
SPINS = PHYSICS.enumerate_spins(16)
EDGES = PHYSICS.torus_edges()
FEATURES = np.column_stack([SPINS[:, first] * SPINS[:, second] for first, second in EDGES])
LOWER = np.tril_indices(16, -1)
LIMIT = math.log(999) - 2e-10
CORES = sorted(os.sched_getaffinity(0))[:4]
STOP = None
ROW_CONSTRAINTS = np.zeros((15, 240))
for index, row in enumerate(LOWER[0]):
    ROW_CONSTRAINTS[row - 1, index] = 1
    ROW_CONSTRAINTS[row - 1, 120 + index] = 1
LINEAR = LinearConstraint(ROW_CONSTRAINTS, np.zeros(15), np.full(15, LIMIT))
BOUNDS = Bounds(np.zeros(240), np.full(240, LIMIT))


def save(name, document):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def normalize_rows(weights):
    result = np.tril(np.asarray(weights, dtype=float), -1).copy()
    for row in result:
        norm = math.fsum(abs(value) for value in row)
        if norm > LIMIT:
            row *= LIMIT / norm
    return result


class Model:
    def __init__(self, document):
        self.document = document
        self.ordered = SPINS[:, document["order"]]
        self.energy = -document["beta"] * (FEATURES @ np.asarray(document["bonds"], dtype=float))
        self.log_partition = float(logsumexp(-self.energy))
        self.log_target = -self.energy - self.log_partition
        self.target = np.exp(self.log_target)
        self.target_energy = float(self.target @ self.energy)
        distance = np.count_nonzero(SPINS != document["pattern"], axis=1)
        self.sector = (np.minimum(distance, 16 - distance) <= document["radius"]).astype(float)
        self.target_sector = float(self.target @ self.sector)

    def calculate(self, weights, penalty, variance_weight=0.0):
        logits = self.ordered @ weights.T
        log_probability = -np.logaddexp(0.0, -self.ordered * logits).sum(axis=1)
        probability = np.exp(log_probability)
        reward = self.energy + log_probability
        mean_reward = float(probability @ reward)
        centered = reward - mean_reward
        entropy = float(-probability @ log_probability)
        divergence = float(probability @ (log_probability - self.log_target))
        variance = float(probability @ centered ** 2)
        mass = float(probability @ self.sector)
        mean_energy = float(probability @ self.energy)
        energy_difference = (mean_energy - self.target_energy) / 16
        residual = (self.ordered + 1) / 2 - expit(logits)
        gradient_divergence = ((residual * (probability * centered)[:, None]).T @ self.ordered)[LOWER]
        coefficient = centered + penalty * self.sector
        loss = divergence + penalty * mass
        if variance_weight:
            coefficient = coefficient + variance_weight * (centered ** 2 + 2 * centered)
            loss += variance_weight * variance
        entropy_deficit = max(0.0, 3.015 - entropy)
        energy_excess = max(0.0, abs(energy_difference) - 0.018)
        if entropy_deficit:
            loss += 20 * entropy_deficit ** 2
            coefficient += 40 * entropy_deficit * log_probability
        if energy_excess:
            loss += 100 * energy_excess ** 2
            coefficient += 200 * energy_excess * np.sign(energy_difference) * self.energy / 16
        gradient = ((residual * (probability * coefficient)[:, None]).T @ self.ordered)[LOWER]
        metrics = {"entropy": entropy, "reverse_kl": divergence, "reward_variance": variance,
                   "gradient_infinity": float(np.max(np.abs(gradient_divergence))),
                   "energy_error_per_spin": abs(energy_difference),
                   "target_sector_mass": self.target_sector, "proposal_sector_mass": mass}
        report = PHYSICS.gate_report(metrics, SPEC)
        report["metrics"] = metrics
        return float(loss), gradient, report


def initializer(event):
    global STOP
    STOP = event
    identity = multiprocessing.current_process()._identity[-1] - 1
    os.sched_setaffinity(0, [CORES[identity % len(CORES)]])


def trial(job):
    started = time.monotonic()
    deadline = min(job["deadline"], started + 110)
    document = job["document"]
    model = Model(document)
    weights = normalize_rows(document["weights"])
    packed = weights[LOWER]
    parameters = np.concatenate([np.maximum(packed, 0), np.maximum(-packed, 0)])
    best_score = -1.0
    best_document = None
    best_report = None
    best_parameters = parameters.copy()
    calls = 0
    stages = []
    current_variance_weight = 0.0

    def objective(values):
        nonlocal best_score, best_document, best_report, best_parameters, calls
        if time.monotonic() >= deadline or STOP.is_set():
            raise TimeoutError("private optimizer bound reached")
        current = np.zeros((16, 16))
        current[LOWER] = values[:120] - values[120:]
        loss, gradient, report = model.calculate(current, job["penalty"], current_variance_weight)
        calls += 1
        feasible = float(np.max(np.abs(current).sum(axis=1))) <= math.log(999) + 1e-10
        score = report["core_score"]
        if feasible and score > best_score:
            best_score = score
            best_document = dict(document, weights=normalize_rows(current).tolist())
            best_report = report
            best_parameters = values.copy()
        if feasible and report["passed"]:
            raise RuntimeError("candidate satisfies all metric gates")
        return loss, np.concatenate([gradient, -gradient])

    try:
        for variance_weight in job["stages"]:
            current_variance_weight = variance_weight
            result = minimize(objective, parameters, jac=True, method="SLSQP", bounds=BOUNDS,
                              constraints=[LINEAR], options={"maxiter": 110, "ftol": 2e-9, "disp": False})
            stages.append({"variance_weight": variance_weight, "success": bool(result.success),
                           "message": str(result.message), "iterations": int(result.nit), "loss": float(result.fun)})
            parameters = result.x
            if variance_weight == 0 and best_score > 0.6:
                parameters = best_parameters.copy()
    except (TimeoutError, RuntimeError) as error:
        stages.append({"termination": str(error)})
    if best_document is None:
        best_document = dict(document, weights=weights.tolist())
    official_math = PHYSICS.evaluate_document(best_document, SPEC)
    return {"trial_id": job["trial_id"], "best_document": best_document, "report": official_math,
            "elapsed_seconds": time.monotonic() - started, "function_calls": calls, "stages": stages,
            "penalty": job["penalty"], "initialization": job["initialization"],
            "non_root_weights": sum(abs(best_document["weights"][row][column]) > 1e-6 for row in range(16) for column in range(1, row))}


def make_job(index, seed_document, generator, deadline):
    document = json.loads(json.dumps(seed_document))
    original_order = document["order"]
    original_weights = np.asarray(document["weights"], dtype=float)
    root = original_order[0]
    free = [original_order[position] for position in range(1, 16) if not np.any(original_weights[position])]
    fixed = [site for site in original_order if site not in free and site != root]
    relative = np.zeros(16)
    relative[root] = 1
    for position, site in enumerate(original_order):
        if position and site not in free:
            relative[site] = np.sign(original_weights[position, 0])
    mode = index % 5
    if mode in (0, 1):
        order = [root] + fixed + free
        if mode == 1:
            generator.shuffle(fixed)
            generator.shuffle(free)
            order = [root] + fixed + free
    elif mode == 2:
        remainder = fixed + free
        generator.shuffle(remainder)
        order = [root] + remainder
    elif mode == 3:
        order = [root] + free + fixed
    else:
        generator.shuffle(fixed)
        order = [root] + fixed[:5] + free[:2] + fixed[5:] + free[2:]
    beta_choices = [1.2, 1.35, 1.5, 1.6, 1.8, 2.0]
    document["beta"] = beta_choices[(index // 5) % len(beta_choices)]
    document["order"] = [int(site) for site in order]
    coupling_matrix = np.zeros((16, 16))
    for coupling, (first, second) in zip(document["bonds"], EDGES):
        coupling_matrix[first, second] = coupling
        coupling_matrix[second, first] = coupling
    weights = np.zeros((16, 16))
    for position, site in enumerate(order[1:], start=1):
        if site not in free:
            weights[position, 0] = LIMIT * relative[site]
        if site in free:
            for previous, neighbor in enumerate(order[:position]):
                weights[position, previous] += 2 * document["beta"] * coupling_matrix[site, neighbor]
            weights[position, 0] -= sum(weights[position, previous] * relative[neighbor] for previous, neighbor in enumerate(order[:position]))
        elif mode in (2, 3, 4):
            for previous, neighbor in enumerate(order[:position]):
                if neighbor in free:
                    weights[position, previous] += 1.5 * document["beta"] * coupling_matrix[site, neighbor]
    if index >= 10:
        weights += np.tril(generator.normal(0, 0.025, (16, 16)), -1)
    document["weights"] = normalize_rows(weights).tolist()
    return {"trial_id": index, "document": document, "penalty": [10.0, 20.0, 30.0][(index // 2) % 3],
            "stages": [0.0, 0.3, 1.0], "initialization": mode, "deadline": deadline}


def gradient_checks(document):
    model = Model(document)
    weights = 0.7 * np.asarray(document["weights"], dtype=float)
    weights[15, 3] = 0.13
    weights[14, 2] = -0.11
    checks = []
    for penalty, variance_weight in ((20.0, 0.0), (0.0, 0.7)):
        loss, gradient, report = model.calculate(weights, penalty, variance_weight)
        for row, column in ((15, 3), (14, 2), (5, 1), (4, 0)):
            positive = weights.copy()
            negative = weights.copy()
            positive[row, column] += 1e-5
            negative[row, column] -= 1e-5
            upper = model.calculate(positive, penalty, variance_weight)[0]
            lower = model.calculate(negative, penalty, variance_weight)[0]
            coordinate = int(np.flatnonzero((LOWER[0] == row) & (LOWER[1] == column))[0])
            error = abs((upper - lower) / 2e-5 - gradient[coordinate])
            checks.append({"penalty": penalty, "variance_weight": variance_weight, "row": row, "column": column, "absolute_error": float(error)})
    assert max(check["absolute_error"] for check in checks) < 2e-7
    save("gradient_checks.json", {"passed": True, "checks": checks})


def official_evaluate(directory, output):
    command = [sys.executable, "-B", str(ROOT / "evaluator/evaluate.py"), "--submission", str(directory), "--output", str(output)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=130)
    if result.returncode:
        raise RuntimeError(result.stderr + result.stdout)
    return json.loads(output.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=900)
    parser.add_argument("--seed", type=int, default=202608282055)
    arguments = parser.parse_args()
    if not 1 <= arguments.seconds <= 1100:
        raise ValueError("search bound must leave time for final official verification")
    os.sched_setaffinity(0, CORES)
    started = time.monotonic()
    deadline = started + arguments.seconds
    baseline = json.loads((ROOT / "participant/baseline/witness.json").read_text())
    other = json.loads((ORIGINAL / "adversary/search_run/witness.json").read_text())
    other["weights"] = normalize_rows(other["weights"]).tolist()
    manifest = json.loads((ROOT / "adversary/release_manifest.json").read_text())
    before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in manifest["sha256"]}
    save("best/witness.json", baseline)
    best = official_evaluate(HERE / "best", HERE / "best/official_report.json")
    gradient_checks(baseline)
    generator = np.random.default_rng(arguments.seed)
    state = {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "seed": arguments.seed,
             "time_budget_seconds": arguments.seconds, "completed_trials": 0, "submitted_trials": 0,
             "best_score": best["core_score"], "passing_witness_found": bool(best["passed"]),
             "achievability": "unknown", "cpu_affinity": CORES, "workers": len(CORES),
             "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             "method": "full triangular constrained exact KL + missed-sector penalty, with optional variance refinement and varied causal orders",
             "no_ongoing_fresh_submission_read": True, "no_frozen_status_or_target_edits": True}
    save("run.json", state)
    context = multiprocessing.get_context("fork")
    event = context.Event()
    pool = concurrent.futures.ProcessPoolExecutor(max_workers=len(CORES), mp_context=context, initializer=initializer, initargs=(event,))
    pending = {}
    all_results = []
    index = 0
    try:
        while time.monotonic() < deadline and not state["passing_witness_found"]:
            while len(pending) < len(CORES) and time.monotonic() < deadline:
                seed_document = baseline if index % 4 != 3 else other
                job = make_job(index, seed_document, generator, deadline)
                future = pool.submit(trial, job)
                pending[future] = index
                index += 1
                state["submitted_trials"] = index
            completed, unused = concurrent.futures.wait(pending, timeout=1.0, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in completed:
                trial_id = pending.pop(future)
                try:
                    result = future.result()
                except Exception as error:
                    all_results.append({"trial_id": trial_id, "error": type(error).__name__ + ": " + str(error)})
                    continue
                state["completed_trials"] += 1
                report = result.pop("report")
                document = result.pop("best_document")
                result.update(score=report["core_score"], passed=report["passed"], metrics=report["metrics"])
                all_results.append(result)
                save(f"trials/{trial_id:04d}/witness.json", document)
                save(f"trials/{trial_id:04d}/exact_report.json", report)
                if report["core_score"] > state["best_score"] or report["passed"]:
                    save("best/witness.json", document)
                    best = official_evaluate(HERE / "best", HERE / "best/official_report.json")
                    state.update(best_score=best["core_score"], best_trial=trial_id,
                                 passing_witness_found=bool(best["passed"]),
                                 achievability="witnessed" if best["passed"] else "unknown",
                                 best_non_root_weights=result["non_root_weights"])
                    print(json.dumps({"elapsed_seconds": time.monotonic() - started, "trial_id": trial_id,
                                      "official_passed": best["passed"], "score": best["core_score"],
                                      "non_root_weights": result["non_root_weights"], "metrics": best["metrics"]}), flush=True)
                state["elapsed_seconds"] = time.monotonic() - started
                save("run.json", state)
                save("trials.json", all_results)
                if state["passing_witness_found"]:
                    event.set()
                    break
    finally:
        event.set()
        pool.shutdown(wait=True, cancel_futures=True)
        for future, trial_id in pending.items():
            if future.cancelled():
                continue
            try:
                result = future.result()
            except Exception as error:
                all_results.append({"trial_id": trial_id, "error": type(error).__name__ + ": " + str(error)})
                continue
            report = result.pop("report")
            document = result.pop("best_document")
            result.update(score=report["core_score"], passed=report["passed"], metrics=report["metrics"])
            all_results.append(result)
            save(f"trials/{trial_id:04d}/witness.json", document)
            save(f"trials/{trial_id:04d}/exact_report.json", report)
            state["completed_trials"] += 1
            if report["core_score"] > state["best_score"]:
                save("best/witness.json", document)
                best = official_evaluate(HERE / "best", HERE / "best/official_report.json")
                state.update(best_score=best["core_score"], best_trial=trial_id,
                             passing_witness_found=bool(best["passed"]),
                             achievability="witnessed" if best["passed"] else "unknown",
                             best_non_root_weights=result["non_root_weights"])
        best = official_evaluate(HERE / "best", HERE / "best/official_report.json")
        state.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     elapsed_seconds=time.monotonic() - started, termination="passing witness" if best["passed"] else "time budget exhausted",
                     passing_witness_found=bool(best["passed"]), achievability="witnessed" if best["passed"] else "unknown",
                     frozen_file_changes=[name for name, digest in before.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest])
        save("run.json", state)
        save("trials.json", all_results)
        print(json.dumps(state, indent=2), flush=True)


if __name__ == "__main__":
    main()
