import collections
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import eigh, solve
from scipy.optimize import least_squares


PORTFOLIO = Path(__file__).resolve().parent
ROOT = PORTFOLIO.parents[1]
BUDGET = json.loads((PORTFOLIO / "budget.json").read_text())
DEADLINE = BUDGET["deadline_epoch"]
SEARCH_DEADLINE = DEADLINE - BUDGET["optimization_reserve_seconds"]
EDGES = [(row, column) for row in range(7) for column in range(row + 1, 7)]
FIELDS = ("virtual_hopping", "virtual_density")
BOUNDS = np.array([0.45] * 21 + [0.60] * 21)
PAIR_MASKS = [mask for mask in range(128) if mask.bit_count() == 2]
TRIPLE_MASKS = [mask for mask in range(128) if mask.bit_count() == 3]


def load_module(name, relative):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


MODEL = load_module("portfolio_public_model", "participant/workspace/model.py")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def encode(parameters):
    candidate = {"schema_version": 1}
    for field_index, field in enumerate(FIELDS):
        matrix = [[0.0] * 7 for row in range(7)]
        for edge_index, (row, column) in enumerate(EDGES):
            matrix[row][column] = matrix[column][row] = float(parameters[field_index * 21 + edge_index])
        candidate[field] = matrix
    return candidate


def decode(candidate):
    return np.array([candidate[field][row][column] for field in FIELDS for row, column in EDGES])


def sample(parameters, uniforms):
    lower = np.maximum(-BOUNDS, parameters - 0.001)
    upper = np.minimum(BOUNDS, parameters + 0.001)
    lower_derivative = (parameters - 0.001 > -BOUNDS).astype(float)
    upper_derivative = (parameters + 0.001 < BOUNDS).astype(float)
    return lower + uniforms * (upper - lower), lower_derivative + uniforms * (upper_derivative - lower_derivative)


class TimeLimit(Exception):
    pass


class Engine:
    def __init__(self):
        self.diagonalizations = 0
        self.points = 0
        self.cache = {}
        hopping, density = MODEL.decode_witness(encode(np.zeros(42)))
        for mask in [0] + [1 << index for index in range(7)] + PAIR_MASKS + TRIPLE_MASKS + [127]:
            occupation, (rows, columns, sources, destinations) = MODEL.topology(mask)
            base = MODEL.hamiltonian(mask, hopping, density)
            indices, derivatives = [], []
            for edge_index, (row, column) in enumerate(EDGES):
                if not (mask & (1 << row) and mask & (1 << column)):
                    continue
                derivative = np.zeros_like(base)
                selected = ((sources == row + 3) & (destinations == column + 3)) | ((sources == column + 3) & (destinations == row + 3))
                derivative[rows[selected], columns[selected]] = 1.0
                derivative[columns[selected], rows[selected]] = 1.0
                indices.extend((edge_index, 21 + edge_index))
                derivatives.extend((derivative, np.diag(occupation[:, row + 3] * occupation[:, column + 3])))
            self.cache[mask] = (base, np.array(indices, dtype=int), np.array(derivatives))
        self.reference = self.cache[0][0][0, 0]
        self.singles = {1 << index: eigh(self.cache[1 << index][0], eigvals_only=True, subset_by_index=(0, 0))[0] for index in range(7)}
        self.single_sum = math.fsum(value - self.reference for value in self.singles.values())

    def eigensystem(self, mask, parameters, full=False):
        base, indices, derivatives = self.cache[mask]
        matrix = base + np.einsum("a,aij->ij", parameters[indices], derivatives, optimize=False)
        values, vectors = eigh(matrix, subset_by_index=(0, 1 if full else 0), check_finite=False)
        self.diagonalizations += 1
        gradient = np.zeros(42)
        gradient[indices] = np.einsum("aij,i,j->a", derivatives, vectors[:, 0], vectors[:, 0], optimize=False)
        return values, vectors, gradient, matrix, indices, derivatives

    def point(self, parameters):
        self.points += 1
        pair_energies, pair_gradients, pair_increments = {}, {}, []
        for mask in PAIR_MASKS:
            values, vectors, gradient, matrix, indices, derivatives = self.eigensystem(mask, parameters)
            pair_energies[mask], pair_gradients[mask] = values[0], gradient
            pair_increments.append(values[0] - math.fsum(self.singles[1 << index] for index in range(7) if mask & (1 << index)) + self.reference)
        triples, triple_gradients = [], []
        for mask in TRIPLE_MASKS:
            values, vectors, gradient, matrix, indices, derivatives = self.eigensystem(mask, parameters)
            parents = [mask ^ (1 << index) for index in range(7) if mask & (1 << index)]
            triples.append(values[0] - math.fsum(pair_energies[parent] for parent in parents) + math.fsum(self.singles[1 << index] for index in range(7) if mask & (1 << index)) - self.reference)
            triple_gradients.append(gradient - sum((pair_gradients[parent] for parent in parents), np.zeros(42)))
        triples = np.array(triples)
        triple_gradients = np.array(triple_gradients)
        truncation = self.reference + self.single_sum + math.fsum(pair_increments) + math.fsum(triples)
        values, vectors, gradient, matrix, indices, derivatives = self.eigensystem(127, parameters, full=True)
        tail = float(values[0] - truncation)
        tail_gradient = gradient - sum(pair_gradients.values(), np.zeros(42)) - np.sum(triple_gradients, axis=0)
        weight = float(vectors[0, 0] ** 2)
        gap = float(values[1] - values[0])
        gap_gradient = np.zeros(42)
        gap_gradient[indices] = np.einsum("aij,i,j->a", derivatives, vectors[:, 1], vectors[:, 1], optimize=False)
        gap_gradient -= gradient
        weight_gradient = np.zeros(42)
        if weight < 0.962 and gap > 0.02:
            ground = vectors[:, 0]
            right = -(np.einsum("aij,j->ia", derivatives, ground, optimize=False) - np.outer(ground, gradient[indices]))
            response = solve(matrix - values[0] * np.eye(len(matrix)) + np.outer(ground, ground), right, assume_a="pos", check_finite=False)
            weight_gradient[indices] = 2 * ground[0] * response[0]
        diagonal_index = 1 + np.argmin(np.diag(matrix)[1:] - self.reference)
        margin = float(matrix[diagonal_index, diagonal_index] - self.reference)
        margin_gradient = np.zeros(42)
        margin_gradient[indices] = derivatives[:, diagonal_index, diagonal_index]
        return dict(triples=triples, triple_gradients=triple_gradients, tail=tail, tail_gradient=tail_gradient, weight=weight, weight_gradient=weight_gradient, gap=gap, gap_gradient=gap_gradient, margin=margin, margin_gradient=margin_gradient, energy=float(values[0]))


def diagnostic(point):
    parent = float(np.max(np.abs(point["triples"])))
    tail = abs(point["tail"])
    ratio = tail / max(parent, 1e-10)
    valid = point["weight"] >= 0.95 and point["gap"] >= 0.4 and point["margin"] >= 0.6
    passed = valid and parent <= 1e-6 and tail >= 50e-6 and ratio >= 100
    score = min(1.0, 1e-6 / max(parent, 1e-10), tail / 50e-6, ratio / 100) if valid else 0.0
    return dict(valid=valid, passed=passed, core_score=score, max_abs_triple_eh=parent, tail_eh=tail, signed_tail_eh=point["tail"], ratio=ratio, hf_weight=point["weight"], spectral_gap_eh=point["gap"], diagonal_margin_eh=point["margin"])


def validation(engine, parameters, uniforms):
    nominal = diagnostic(engine.point(parameters))
    cases = [diagnostic(engine.point(sample(parameters, row)[0])) for row in uniforms]
    return dict(nominal=nominal, successes=sum(case["passed"] for case in cases), cases=len(cases), success_fraction=sum(case["passed"] for case in cases) / len(cases), minimum_original_score=min(case["core_score"] for case in cases), maximum_parent_eh=max(case["max_abs_triple_eh"] for case in cases), minimum_tail_eh=min(case["tail_eh"] for case in cases))


class Objective:
    def __init__(self, engine, uniforms, sign, tail_floor, mode, deadline, directory):
        self.engine, self.uniforms, self.sign, self.tail_floor, self.mode = engine, uniforms, sign, tail_floor, mode
        self.deadline, self.directory = deadline, directory
        self.last_parameters = None
        self.evaluations = 0
        self.best_cost = math.inf
        self.best_parameters = None

    def calculate(self, parameters):
        if self.last_parameters is not None and np.array_equal(parameters, self.last_parameters):
            return self.last_residual, self.last_jacobian
        residuals, jacobians = [], []
        for case_index in range(len(self.uniforms) + 1):
            if time.time() >= self.deadline:
                raise TimeLimit()
            perturbed, chain = (parameters, np.ones(42)) if case_index == 0 else sample(parameters, self.uniforms[case_index - 1])
            point = self.engine.point(perturbed)
            weight = 2.0 if case_index == 0 else 1 / math.sqrt(len(self.uniforms))
            scaled = point["triples"] / 1e-6
            if self.mode == "fourth_power":
                root = np.sqrt(0.04 + scaled ** 2)
                transformed, slope = scaled * root, (0.04 + 2 * scaled ** 2) / root
            elif self.mode == "hinge":
                transformed = np.sign(scaled) * np.maximum(0, np.abs(scaled) - 0.25)
                slope = (np.abs(scaled) > 0.25).astype(float)
            else:
                transformed, slope = scaled, np.ones(35)
            residuals.extend(weight * transformed)
            jacobians.extend(weight * slope[:, None] * point["triple_gradients"] * chain[None, :] / 1e-6)
            deficits = ((self.sign * point["tail"] - self.tail_floor, self.sign * point["tail_gradient"], 2e-6), (point["weight"] - 0.958, point["weight_gradient"], 0.002), (point["gap"] - 0.43, point["gap_gradient"], 0.01), (point["margin"] - 0.62, point["margin_gradient"], 0.01))
            for deficit, gradient, scale in deficits:
                residuals.append(weight * min(0.0, deficit) / scale)
                jacobians.append(weight * gradient * chain / scale if deficit < 0 else np.zeros(42))
        self.evaluations += 1
        residual, jacobian = np.array(residuals), np.array(jacobians)
        cost = float(np.dot(residual, residual))
        if cost < self.best_cost:
            self.best_cost, self.best_parameters = cost, parameters.copy()
            save(self.directory / "checkpoint.json", encode(parameters))
        self.last_parameters = parameters.copy()
        self.last_residual, self.last_jacobian = residual, jacobian
        return residual, jacobian

    def fun(self, parameters):
        return self.calculate(parameters)[0]

    def jac(self, parameters):
        return self.calculate(parameters)[1]


def main():
    engine = Engine()
    starts = {name: decode(json.loads((ROOT / ("adversary/" + filename)).read_text())) for name, filename in (("author", "known_witness.json"), ("v1", "v1_witness.json"))}
    point = engine.point(starts["author"])
    public = MODEL.compute(encode(starts["author"]), complete=False)
    energy_error = abs(point["energy"] - public["full_energy_eh"])
    increment_error = max(abs(point["triples"][index] - public["increments_eh"][str(mask)]) for index, mask in enumerate(TRIPLE_MASKS))
    gradient_errors = []
    for coordinate in (2, 13, 27):
        step = np.zeros(42)
        step[coordinate] = 2e-5
        upper, lower = engine.point(starts["author"] + step), engine.point(starts["author"] - step)
        finite_difference = (upper["triples"] - lower["triples"]) / (4e-5)
        gradient_errors.append(float(np.max(np.abs(finite_difference - point["triple_gradients"][:, coordinate]))))
    assert energy_error < 2e-11 and increment_error < 2e-11 and max(gradient_errors) < 2e-7
    save(PORTFOLIO / "engine_checks.json", dict(energy_error_eh=energy_error, increment_error_eh=increment_error, gradient_max_errors=gradient_errors, passed=True))
    selection_seed = 20260828711
    selection_uniforms = np.random.default_rng(selection_seed).random((64, 42))
    candidates, runs = [], []
    for name, parameters in starts.items():
        stats = validation(engine, parameters, selection_uniforms)
        path = PORTFOLIO / (name + "_start.json")
        save(path, encode(parameters))
        candidates.append(dict(name=name + "_start", path=str(path.relative_to(ROOT)), parameters=parameters, validation=stats))
    configurations = [("author", "squared", 120e-6, 16), ("v1", "squared", 105e-6, 16), ("author", "fourth_power", 160e-6, 24), ("best", "fourth_power", 110e-6, 32), ("best", "hinge", 110e-6, 32), ("best", "fourth_power", 110e-6, 48)]
    rank = lambda candidate: (candidate["validation"]["nominal"]["passed"], candidate["validation"]["successes"], candidate["validation"]["minimum_original_score"])
    for run_index, (start_name, mode, floor, count) in enumerate(configurations):
        remaining = SEARCH_DEADLINE - time.time()
        if remaining < 20:
            break
        parameters = max(candidates, key=rank)["parameters"].copy() if start_name == "best" else starts[start_name].copy()
        sign = -1 if engine.point(parameters)["tail"] < 0 else 1
        seed = 20260829000 + run_index
        uniforms = np.random.default_rng(seed).random((count, 42))
        directory = PORTFOLIO / ("run_" + str(run_index).zfill(2))
        directory.mkdir(exist_ok=True)
        run_deadline = min(SEARCH_DEADLINE, time.time() + remaining / (len(configurations) - run_index))
        objective = Objective(engine, uniforms, sign, floor, mode, run_deadline, directory)
        started = time.time()
        try:
            result = least_squares(objective.fun, np.clip(parameters, -BOUNDS + 1e-12, BOUNDS - 1e-12), jac=objective.jac, bounds=(-BOUNDS, BOUNDS), max_nfev=140, x_scale="jac", ftol=2e-7, xtol=1e-9, gtol=1e-6)
            termination = str(result.message)
        except TimeLimit:
            termination = "allocated search time reached"
        if objective.best_parameters is not None:
            parameters = objective.best_parameters
        stats = validation(engine, parameters, selection_uniforms)
        save(directory / "witness.json", encode(parameters))
        run = dict(run_index=run_index, start=start_name, mode=mode, tail_floor_eh=floor, tail_sign=sign, training_seed=seed, training_cases=count, objective_evaluations=objective.evaluations, best_cost=objective.best_cost if math.isfinite(objective.best_cost) else None, elapsed_seconds=time.time() - started, termination=termination, validation=stats)
        save(directory / "training_report.json", run)
        runs.append(run)
        candidates.append(dict(name=directory.name, path=str((directory / "witness.json").relative_to(ROOT)), parameters=parameters, validation=stats))
        print(json.dumps(dict(run=run_index, evaluations=objective.evaluations, nominal_passed=stats["nominal"]["passed"], selection_successes=stats["successes"], selection_cases=64, elapsed_seconds=run["elapsed_seconds"], remaining_seconds=DEADLINE - time.time())), flush=True)
    ranked = sorted(candidates, key=rank, reverse=True)
    selected, seen = [], set()
    for candidate in ranked:
        payload = (ROOT / candidate["path"]).read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest not in seen:
            selected.append(dict(name=candidate["name"], path=candidate["path"], sha256=digest, independent_selection=candidate["validation"]))
            seen.add(digest)
        if len(selected) == 3:
            break
    selection = dict(selection_seed=selection_seed, selection_cases=64, hidden_uniforms_used_for_optimization=False, official_reports_consulted_during_optimization=False, selected_before_any_new_official_evaluation=True, selected=selected, runs=runs, engine_points=engine.points, diagonalizations=engine.diagonalizations, objective_evaluations=sum(run["objective_evaluations"] for run in runs))
    save(PORTFOLIO / "preheldout_selection.json", selection)
    print("Portfolio committed; optimization is finished before heldout evaluation.", flush=True)
    wrapper = load_module("frozen_official_evaluator", "evaluator/evaluate.py")
    verifier = load_module("frozen_additional_noise_verifier", "evaluator/hidden/assay_worker.py")
    official, additional = [], []
    for candidate_index, candidate in enumerate(selected):
        if DEADLINE - time.time() < 35:
            break
        report = wrapper.evaluate(ROOT / candidate["path"])
        report_path = PORTFOLIO / ("official_" + candidate["name"] + ".json")
        save(report_path, report)
        record = dict(candidate=candidate, report=str(report_path.relative_to(ROOT)), result=report)
        official.append(record)
        print(json.dumps(dict(candidate=candidate["name"], official_passed=report["passed"], successes=report.get("perturbed_assay", {}).get("successes"), core_score=report["core_score"])), flush=True)
        if report["passed"]:
            witness = json.loads((ROOT / candidate["path"]).read_text())
            extra_seed = 202608299001 + candidate_index
            uniforms = np.random.default_rng(extra_seed).random((512, 42))
            cases = []
            for row in uniforms:
                if DEADLINE - time.time() < 8:
                    break
                cases.append(verifier.evaluate_case(verifier.perturb(witness, row)))
            successes = sum(case["passed"] for case in cases)
            extra = dict(candidate=candidate["name"], seed=extra_seed, requested_cases=512, completed_cases=len(cases), successes=successes, success_fraction=successes / len(cases) if cases else None, numerical_valid=all(case["numerical_valid"] for case in cases), failure_counts_nonexclusive=dict(collections.Counter(group + "." + key for case in cases for group in ("admissibility", "witness_checks") for key, passed in case.get(group, {}).items() if not passed)), metric_ranges={field: {"min": min(case["metrics"][field] for case in cases), "max": max(case["metrics"][field] for case in cases)} for field in verifier.METRIC_FIELDS} if cases else {}, independent_of_training_selection_and_official=True, claim="finite additional-noise validation only, not universal or population robustness")
            save(PORTFOLIO / ("additional_" + candidate["name"] + ".json"), extra)
            additional.append(extra)
    best = max(official, key=lambda record: (record["result"]["passed"], record["result"]["core_score"])) if official else None
    if best:
        save(PORTFOLIO / "best_witness.json", json.loads((ROOT / best["candidate"]["path"]).read_text()))
        save(PORTFOLIO / "best_official_report.json", best["result"])
    manifest = json.loads((ROOT / "evaluator/hidden/freeze.json").read_text())
    changed = [relative for relative, expected in manifest["files"].items() if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected]
    assert not changed, changed
    passed = any(record["result"]["passed"] for record in official)
    summary = dict(status="complete", privileged_only=True, started_at_utc=BUDGET["started_at_utc"], elapsed_seconds=time.time() - BUDGET["start_epoch"], budget_seconds=900, optimization_runs=len(runs), objective_evaluations=selection["objective_evaluations"], engine_points=engine.points, diagonalizations=engine.diagonalizations, saved_candidates=len(candidates), official_evaluations=len(official), official_results=[dict(candidate=record["candidate"]["name"], passed=record["result"]["passed"], valid=record["result"]["valid"], core_score=record["result"]["core_score"], worst_family_score=record["result"]["worst_family_score"], successes=record["result"].get("perturbed_assay", {}).get("successes"), report=record["report"]) for record in official], known_robust_passing_witness=passed, solvability="demonstrated for frozen finite assay" if passed else "unknown; bounded unsuccessful portfolio does not imply impossibility", best_witness="adversary/portfolio/best_witness.json" if best else None, best_report="adversary/portfolio/best_official_report.json" if best else None, additional_noise_validation=additional, frozen_files_unchanged=True, hidden_pool_used_for_optimization=False, no_refit_after_official_evaluation=True, fresh_agents_launched=0)
    save(PORTFOLIO / "summary.json", summary)
    save(ROOT / "adversary/portfolio_report.json", summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
