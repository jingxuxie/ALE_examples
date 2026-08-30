import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import concurrent.futures
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
GENERATION = ROOT / "generations/generation_2"
module_spec = importlib.util.spec_from_file_location("frozen_physics", GENERATION / "evaluator/physics.py")
PHYSICS = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(PHYSICS)
SPEC = json.loads((GENERATION / "participant/input/spec.json").read_text())
CHAMPION = json.loads((ROOT / "champions/generation_2/witness.json").read_text())
SPINS = PHYSICS.enumerate_spins(16)
HALF = SPINS[::2]
LOWER = np.tril_indices(16, -1)
EDGES = PHYSICS.torus_edges()
CORES = sorted(os.sched_getaffinity(0))[:4]
LINEAR_MATRIX = np.zeros((15, 241))
for index, row in enumerate(LOWER[0]):
    LINEAR_MATRIX[row - 1, index] = 1
    LINEAR_MATRIX[row - 1, index + 120] = 1


def save(name, document):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def rescale(document, floor):
    result = json.loads(json.dumps(document))
    weights = np.asarray(result["weights"], dtype=float)
    bound = math.log((1 - floor) / floor) - 1e-9
    weights *= min(1.0, bound / np.abs(weights).sum(axis=1).max())
    result["weights"] = weights.tolist()
    return result


def exact_report(document, floor):
    report = PHYSICS.evaluate_document(document, SPEC)
    bound = math.log((1 - floor) / floor)
    norms = [math.fsum(abs(value) for value in row) for row in document["weights"]]
    report["audit_conditional_floor"] = floor
    report["audit_floor_satisfied"] = max(norms) <= bound
    report["passes_exploration_guard_and_original_gates"] = report["passed"] and report["audit_floor_satisfied"]
    return report


class Problem:
    def __init__(self, document, gradient_weight):
        self.document = document
        self.spins = HALF[:, document["order"]]
        self.energy = -sum(coupling * HALF[:, first] * HALF[:, second] for coupling, (first, second) in zip(document["bonds"], EDGES))
        distance = np.count_nonzero(HALF != document["pattern"], axis=1)
        self.sector = (np.minimum(distance, 16 - distance) <= document["radius"]).astype(float)
        self.gradient_weight = gradient_weight
        self.last = None
        self.calls = 0
        self.deadline = math.inf

    def calculate(self, parameters):
        if time.monotonic() >= self.deadline:
            raise TimeoutError("bounded local optimization ended")
        if self.last is not None and np.array_equal(parameters, self.last):
            return self.cached
        self.last = parameters.copy()
        self.calls += 1
        weights = np.zeros((16, 16))
        weights[LOWER] = parameters[:120] - parameters[120:240]
        beta = parameters[-1]
        logits = self.spins @ weights.T
        log_probability = -np.logaddexp(0, -self.spins * logits).sum(axis=1)
        probability = 2 * np.exp(log_probability)
        positive = expit(logits)
        residual = (self.spins + 1) / 2 - positive
        potential = beta * self.energy
        target = np.exp(-potential - logsumexp(-potential))
        reward = potential + log_probability
        centered = reward - probability @ reward
        mean_energy_q = float(probability @ self.energy)
        mean_energy_p = float(target @ self.energy)
        variance_energy_p = float(target @ (self.energy - mean_energy_p) ** 2)
        variance = float(probability @ centered ** 2)
        entropy = float(-probability @ log_probability)
        divergence = float(probability @ reward + logsumexp(-potential) + math.log(2))
        difference = beta * (mean_energy_q - mean_energy_p)
        proposal_mass = float(probability @ self.sector)
        target_mass = float(target @ self.sector)

        def derivative(coefficient, beta_derivative):
            matrix = (residual * (probability * coefficient)[:, None]).T @ self.spins
            lower = matrix[LOWER]
            return np.concatenate([lower, -lower, [beta_derivative]])

        gradient_divergence = derivative(centered, mean_energy_q - mean_energy_p)
        gradient_variance = derivative(centered ** 2 + 2 * centered, 2 * float((probability * centered) @ self.energy))
        objective = variance
        objective_gradient = gradient_variance
        if self.gradient_weight:
            lower_gradient = gradient_divergence[:120]
            direction = np.sign(lower_gradient) * np.maximum(np.abs(lower_gradient) - 0.0027, 0)
            direction_matrix = np.zeros((16, 16))
            direction_matrix[LOWER] = direction
            directional_logits = self.spins @ direction_matrix.T
            directional_score = (residual * directional_logits).sum(axis=1)
            hessian_action = ((residual * (probability * (centered + 1) * directional_score)[:, None]).T @ self.spins)[LOWER]
            hessian_action -= (((probability * centered)[:, None] * positive * (1 - positive) * directional_logits).T @ self.spins)[LOWER]
            energy_gradient = derivative(self.energy, 0)[:120]
            packed_action = np.concatenate([hessian_action, -hessian_action, [float(direction @ energy_gradient)]])
            objective += self.gradient_weight * float(direction @ direction)
            objective_gradient = objective_gradient + 2 * self.gradient_weight * packed_action
        entropy_gradient = derivative(-log_probability, 0)
        energy_gradient = derivative(potential, mean_energy_q - mean_energy_p + beta * variance_energy_p)
        proposal_gradient = derivative(self.sector, 0)
        target_gradient = np.zeros(241)
        target_gradient[-1] = -float((target * self.sector) @ (self.energy - mean_energy_p))
        constraints = np.asarray([entropy - 3.0001, divergence - 0.4001, 0.3199 - difference,
                                  0.3199 + difference, 0.0009999 - proposal_mass, target_mass - 0.350001])
        constraint_jacobian = np.asarray([entropy_gradient, gradient_divergence, -energy_gradient,
                                          energy_gradient, -proposal_gradient, target_gradient])
        metrics = {"entropy": entropy, "reverse_kl": divergence, "reward_variance": variance,
                   "gradient_infinity": float(np.abs(gradient_divergence[:120]).max()),
                   "energy_error_per_spin": abs(difference) / 16,
                   "target_sector_mass": target_mass, "proposal_sector_mass": proposal_mass}
        report = PHYSICS.gate_report(metrics, SPEC)
        report["metrics"] = metrics
        self.cached = objective, objective_gradient, constraints, constraint_jacobian, report, weights
        return self.cached


def optimize(job):
    os.sched_setaffinity(0, [CORES[job["index"] % len(CORES)]])
    started = time.monotonic()
    document = job["document"]
    floor = job["floor"]
    bound = math.log((1 - floor) / floor) - 1e-9
    packed = np.asarray(document["weights"])[LOWER]
    initial = np.concatenate([np.maximum(packed, 0), np.maximum(-packed, 0), [document["beta"]]])
    problem = Problem(document, job["gradient_weight"])
    problem.deadline = min(job["deadline"], started + 115)
    best_document = document
    best_report = exact_report(document, floor)
    best_score = best_report["core_score"]

    def objective(parameters):
        nonlocal best_document, best_report, best_score
        loss, gradient, constraints, jacobian, report, weights = problem.calculate(parameters)
        norm = float(np.max(np.abs(weights).sum(axis=1)))
        if norm <= bound + 1e-9 and report["core_score"] > best_score:
            candidate = dict(document, beta=float(parameters[-1]), weights=weights.tolist())
            for row in candidate["weights"]:
                row_norm = math.fsum(abs(value) for value in row)
                if row_norm > bound:
                    row[:] = [value * bound / row_norm for value in row]
            checked = exact_report(candidate, floor)
            best_score = checked["core_score"]
            best_document = candidate
            best_report = checked
            if checked["passes_exploration_guard_and_original_gates"]:
                raise RuntimeError("guard-passing candidate found")
        return loss, gradient

    try:
        result = minimize(objective, initial, jac=True, method="SLSQP",
                          bounds=Bounds(np.r_[np.zeros(240), 1], np.r_[np.full(240, bound), 3]),
                          constraints=[LinearConstraint(LINEAR_MATRIX, np.zeros(15), np.full(15, bound)),
                                       {"type": "ineq", "fun": lambda parameters: problem.calculate(parameters)[2],
                                        "jac": lambda parameters: problem.calculate(parameters)[3]}],
                          options={"maxiter": 300, "ftol": 1e-10, "disp": False})
        termination = str(result.message)
        converged = bool(result.success)
    except (TimeoutError, RuntimeError) as error:
        termination = str(error)
        converged = False
    return {"index": job["index"], "floor": floor, "gradient_penalty_weight": job["gradient_weight"],
            "elapsed_seconds": time.monotonic() - started, "calls": problem.calls,
            "optimizer_converged": converged, "termination": termination,
            "witness": best_document, "report": best_report}


def main():
    started = time.monotonic()
    deadline = started + 245
    os.sched_setaffinity(0, CORES)
    original = exact_report(CHAMPION, 0.001)
    score = json.loads((ROOT / "champions/generation_2/official_score.json").read_text())
    assert all(abs(original["metrics"][name] - score["metrics"][name]) < 1e-10 for name in original["gates"])
    save("original_crosscheck.json", original)
    floors = []
    jobs = []
    for floor in (0.003, 0.01, 0.03, 0.05):
        document = rescale(CHAMPION, floor)
        problem = Problem(document, 0)
        ordered = HALF[:, document["order"]]
        logits = ordered @ np.asarray(document["weights"]).T
        log_probability = -np.logaddexp(0, -ordered * logits).sum(axis=1)
        probability = 2 * np.exp(log_probability)
        centered_energy = problem.energy - probability @ problem.energy
        centered_log = log_probability - probability @ log_probability
        variance_energy = float(probability @ centered_energy ** 2)
        covariance = float(probability @ (centered_energy * centered_log))
        beta = float(np.clip(-covariance / variance_energy, 1, 3))
        minimum = dict(document, beta=beta)
        record = {"floor": floor, "at_original_beta": exact_report(document, floor),
                  "continuous_variance_minimizer_beta": beta, "at_continuous_variance_minimum": exact_report(minimum, floor),
                  "variance_quadratic_coefficients": [float(probability @ centered_log ** 2), 2 * covariance, variance_energy]}
        floors.append(record)
        jobs.append({"index": len(jobs), "floor": floor, "document": minimum, "gradient_weight": 0, "deadline": deadline})
    extra = rescale(CHAMPION, 0.01)
    jobs.insert(2, {"index": 4, "floor": 0.01, "document": extra, "gradient_weight": 100, "deadline": deadline})
    save("scalar_floor_profiles.json", floors)
    print(json.dumps({"scalar_floor_profiles": [{"floor": row["floor"], "minimum_variance": row["at_continuous_variance_minimum"]["metrics"]["reward_variance"], "beta": row["continuous_variance_minimizer_beta"], "passed": row["at_continuous_variance_minimum"]["passes_exploration_guard_and_original_gates"]} for row in floors]}), flush=True)
    test_problem = Problem(rescale(CHAMPION, 0.01), 100)
    packed = np.asarray(rescale(CHAMPION, 0.01)["weights"])[LOWER]
    parameters = np.r_[np.maximum(packed, 0), np.maximum(-packed, 0), CHAMPION["beta"]]
    analytical = test_problem.calculate(parameters)[1]
    errors = []
    for coordinate in (0, 37, 121, 180, 240):
        plus = parameters.copy()
        minus = parameters.copy()
        plus[coordinate] += 1e-5
        minus[coordinate] -= 1e-5
        numerical = (test_problem.calculate(plus)[0] - test_problem.calculate(minus)[0]) / 2e-5
        errors.append(abs(float(analytical[coordinate] - numerical)))
    assert max(errors) < 2e-6
    save("gradient_checks.json", {"maximum_absolute_error": max(errors), "passed": True, "coordinates": [0, 37, 121, 180, 240]})
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context("fork")) as pool:
        futures = {pool.submit(optimize, job): job for job in jobs}
        continuation_sent = False
        while futures:
            finished, unused = concurrent.futures.wait(futures, timeout=1, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in finished:
                job = futures.pop(future)
                try:
                    result = future.result()
                except Exception as error:
                    results.append({"index": job["index"], "floor": job["floor"], "error": type(error).__name__ + ": " + str(error)})
                    continue
                witness = result.pop("witness")
                save(f"optimization_{job['index']}/witness.json", witness)
                save(f"optimization_{job['index']}/report.json", result)
                results.append(result)
                print(json.dumps({"optimization": job["index"], "floor": job["floor"], "score": result["report"]["core_score"], "passed_guard": result["report"]["passes_exploration_guard_and_original_gates"], "metrics": result["report"]["metrics"]}), flush=True)
                if job["floor"] == 0.003 and not continuation_sent and time.monotonic() + 15 < deadline:
                    continuation = {"index": 5, "floor": 0.01, "document": rescale(witness, 0.01), "gradient_weight": 0, "deadline": deadline}
                    futures[pool.submit(optimize, continuation)] = continuation
                    continuation_sent = True
                save("optimization_summary.json", results)
    summary = {"original_generation_2_still_passes": original["passed"],
               "elapsed_seconds": time.monotonic() - started, "floors": floors, "optimizations": results,
               "any_0_01_guard_passing_witness": any(row.get("floor") == 0.01 and row.get("report", {}).get("passes_exploration_guard_and_original_gates", False) for row in results),
               "general_0_01_attainability": "unknown unless a listed guard-passing witness exists",
               "scope": "completed champion, scalar and fully coupled local reoptimization; no global impossibility claim"}
    save("summary.json", summary)
    print(json.dumps({"completed": True, "elapsed_seconds": summary["elapsed_seconds"], "any_0_01_guard_passing_witness": summary["any_0_01_guard_passing_witness"]}), flush=True)


if __name__ == "__main__":
    main()
