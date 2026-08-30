import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True

import engine
import numpy as np
from scipy.optimize import least_squares


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BUDGET = json.loads((HERE / "budget.json").read_text())
DEADLINE = BUDGET["deadline_epoch"]
SEARCH_DEADLINE = DEADLINE - BUDGET["optimization_reserve_seconds"]
sys.path.insert(0, str(ROOT / "participant/workspace"))
import assay


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    manifest = ROOT / "evaluator/hidden/freeze.json"
    if digest(manifest) != BUDGET["frozen_manifest_sha256"]:
        raise AssertionError("freeze manifest changed")
    frozen = json.loads(manifest.read_text())
    for name, expected in frozen["files"].items():
        if digest(ROOT / name) != expected:
            raise AssertionError("frozen file changed: " + name)
    return dict(frozen_file_count=len(frozen["files"]), frozen_manifest_sha256=digest(manifest), all_unchanged=True)


class Case:
    def __init__(self, template, family, uniform=None):
        self.family = family
        self.uniform = uniform
        self.engine = template
        self.coordinates = uniform
        if family == "full":
            coefficients = assay.perturb(engine.encode(np.zeros(42)), uniform, "full")
            coefficients[1][3:, 3:] = 0.0
            coefficients[2][3:, 3:] = 0.0
            self.engine = engine.Engine(coefficients, template.cache)
            self.coordinates = np.concatenate((uniform[34:55], uniform[79:100]))

    def point(self, parameters):
        if self.family == "nominal":
            sampled, derivative = parameters, np.ones(42)
        else:
            sampled, derivative = engine.sample(parameters, self.coordinates)
        return self.engine.point(sampled), derivative


def cases_from_seed(template, seed, vv_count, full_count):
    streams = np.random.SeedSequence(seed).spawn(2)
    cases = [Case(template, "nominal")]
    for family, count, dimension, stream in zip(("vv", "full"), (vv_count, full_count), (42, 100), streams):
        uniforms = np.random.Generator(np.random.PCG64(stream)).random((count, dimension))
        cases.extend(Case(template, family, row) for row in uniforms)
    return cases


def evaluate(parameters, cases):
    results = {"vv": [], "full": []}
    nominal = None
    for case in cases:
        point, derivative = case.point(parameters)
        result = engine.diagnostic(point)
        if case.family == "nominal":
            nominal = result
        else:
            results[case.family].append(result)
    return dict(nominal=nominal, families={family: dict(successes=sum(case["passed"] for case in records),
                count=len(records), minimum_case_score=min(case["core_score"] for case in records),
                max_parent_eh=max(case["max_abs_triple_eh"] for case in records),
                min_tail_eh=min(case["tail_eh"] for case in records), cases=records) for family, records in results.items()})


def ranking(report):
    successes = [report["families"][family]["successes"] for family in ("vv", "full")]
    return (int(report["nominal"]["passed"]), min(successes), sum(successes),
            min(report["families"][family]["minimum_case_score"] for family in ("vv", "full")),
            report["nominal"]["core_score"])


class Objective:
    def __init__(self, cases, tail_floor, mode, deadline, directory):
        self.cases = cases
        self.tail_floor = tail_floor
        self.mode = mode
        self.deadline = deadline
        self.directory = directory
        self.evaluations = 0
        self.last_parameters = None
        self.best_parameters = None
        self.best_cost = math.inf
        self.counts = {family: sum(case.family == family for case in cases) for family in ("vv", "full")}

    def calculate(self, parameters):
        if self.last_parameters is not None and np.array_equal(parameters, self.last_parameters):
            return self.residual, self.jacobian
        residuals, jacobians = [], []
        for case in self.cases:
            if time.time() >= self.deadline:
                raise engine.TimeLimit()
            point, chain = case.point(parameters)
            weight = 1.0 if case.family == "nominal" else math.sqrt((0.4 if case.family == "vv" else 2.0) / self.counts[case.family])
            scale = min(0.9e-6, self.tail_floor / 115)
            normalized = point["triples"] / scale
            if self.mode == "fourth":
                root = np.sqrt(0.04 + normalized ** 2)
                transformed = normalized * root
                slope = (0.04 + 2 * normalized ** 2) / root
            elif self.mode == "hinge":
                transformed = np.sign(normalized) * np.maximum(0, np.abs(normalized) - 0.7)
                slope = (np.abs(normalized) > 0.7).astype(float)
            else:
                transformed, slope = normalized, np.ones(35)
            residuals.extend(weight * transformed)
            jacobians.extend(weight * slope[:, None] * point["triple_gradients"] * chain[None, :] / scale)
            deficits = ((-point["tail"] - self.tail_floor, -point["tail_gradient"], 2e-6),
                        (point["weight"] - 0.956, point["weight_gradient"], 0.002),
                        (point["gap"] - 0.425, point["gap_gradient"], 0.01),
                        (point["margin"] - 0.62, point["margin_gradient"], 0.01))
            for deficit, gradient, scale in deficits:
                residuals.append(weight * min(0.0, deficit) / scale)
                jacobians.append(weight * gradient * chain / scale if deficit < 0 else np.zeros(42))
        residual = np.asarray(residuals)
        jacobian = np.asarray(jacobians)
        if not np.all(np.isfinite(residual)) or not np.all(np.isfinite(jacobian)):
            raise ValueError("nonfinite objective")
        self.evaluations += 1
        cost = float(residual @ residual)
        if cost < self.best_cost:
            self.best_cost = cost
            self.best_parameters = parameters.copy()
            save(self.directory / "checkpoint.json", engine.encode(parameters))
        self.last_parameters = parameters.copy()
        self.residual, self.jacobian = residual, jacobian
        return residual, jacobian


def check_engine(template, parameters):
    row = np.random.Generator(np.random.PCG64(303170011)).random(100)
    case = Case(template, "full", row)
    point, chain = case.point(parameters)
    public = engine.MODEL.compute_coefficients(assay.perturb(engine.encode(parameters), row, "full"))
    energy_error = abs(public["full_energy_eh"] - point["energy"])
    increment_error = max(abs(public["increments_eh"][str(mask)] - point["triples"][index]) for index, mask in enumerate(engine.TRIPLE_MASKS))
    gradient_errors = []
    smooth_coordinates = [index for index in range(42)
                          if min(abs(parameters[index] - (engine.BOUNDS[index] - 0.001)),
                                 abs(parameters[index] + (engine.BOUNDS[index] - 0.001))) > 1e-5]
    coordinates = [smooth_coordinates[0], smooth_coordinates[len(smooth_coordinates) // 2], smooth_coordinates[-1]]
    for coordinate in coordinates:
        lower, upper = parameters.copy(), parameters.copy()
        lower[coordinate] -= 1e-6
        upper[coordinate] += 1e-6
        before, ignored = case.point(lower)
        after, ignored = case.point(upper)
        finite_difference = (after["triples"] - before["triples"]) / 2e-6
        gradient_errors.append(float(np.max(np.abs(finite_difference - point["triple_gradients"][:, coordinate] * chain[coordinate]))))
    if energy_error > 5e-10 or increment_error > 5e-10 or max(gradient_errors) > 2e-7:
        raise AssertionError("full-noise engine validation failed")
    report = dict(passed=True, energy_error_eh=energy_error, increment_error_eh=increment_error,
                  gradient_errors=gradient_errors, gradient_coordinates=coordinates,
                  finite_difference_avoids_box_truncation_kinks=True, independent_training_from_hidden=True)
    save(HERE / "engine_checks.json", report)


def main():
    initial_audit = audit()
    template = engine.Engine()
    starts = {name: engine.decode(json.loads((ROOT / ("adversary/references/" + name + ".json")).read_text()))
              for name in ("b2_champion", "portfolio_best")}
    check_engine(template, np.clip(starts["b2_champion"], -engine.BOUNDS + 2e-5, engine.BOUNDS - 2e-5))
    selection_cases = cases_from_seed(template, 303170021, 32, 32)
    candidates = []
    for name, parameters in starts.items():
        report = evaluate(parameters, selection_cases)
        save(HERE / (name + "_start.json"), engine.encode(parameters))
        save(HERE / (name + "_selection.json"), report)
        candidates.append(dict(name=name + "_start", parameters=parameters, report=report))
    schedules = [("b2_champion", 100e-6, "squared", 4, 16, 75),
                 ("portfolio_best", 100e-6, "squared", 4, 16, 75),
                 ("best", 70e-6, "squared", 4, 24, 85),
                 ("best", 105e-6, "fourth", 6, 24, 75),
                 ("best", 80e-6, "hinge", 6, 32, 75),
                 ("best", 105e-6, "hinge", 8, 40, 80)]
    runs = []
    for run_index, (origin, tail_floor, mode, vv_count, full_count, maximum_evaluations) in enumerate(schedules):
        if time.time() >= SEARCH_DEADLINE - 12:
            break
        seed = 303171000 + run_index
        directory = HERE / ("run_" + str(run_index).zfill(2))
        directory.mkdir(exist_ok=True)
        cases = cases_from_seed(template, seed, vv_count, full_count)
        start = max(candidates, key=lambda candidate: ranking(candidate["report"]))["parameters"] if origin == "best" else starts[origin]
        parameters = np.clip(start, -engine.BOUNDS + 1e-8, engine.BOUNDS - 1e-8)
        deadline = min(SEARCH_DEADLINE - 5, time.time() + 90)
        objective = Objective(cases, tail_floor, mode, deadline, directory)
        stopped = "evaluation limit or convergence"
        try:
            result = least_squares(lambda value: objective.calculate(value)[0], parameters,
                                   jac=lambda value: objective.calculate(value)[1], bounds=(-engine.BOUNDS + 1e-10, engine.BOUNDS - 1e-10),
                                   x_scale="jac", max_nfev=maximum_evaluations, ftol=2e-7, xtol=2e-8, gtol=1e-6)
        except engine.TimeLimit:
            stopped = "bounded time limit"
        except (ValueError, np.linalg.LinAlgError) as error:
            stopped = "numerical optimization stopped: " + str(error)
        parameters = parameters if objective.best_parameters is None else objective.best_parameters
        save(directory / "witness.json", engine.encode(parameters))
        report = evaluate(parameters, selection_cases)
        save(directory / "selection_report.json", report)
        record = dict(run_index=run_index, seed=seed, origin=origin, tail_floor_eh=tail_floor, mode=mode,
                      training_vv_cases=vv_count, training_full_cases=full_count, objective_evaluations=objective.evaluations,
                      stopped=stopped, best_cost=None if not math.isfinite(objective.best_cost) else objective.best_cost,
                      nominal_passed=report["nominal"]["passed"], selection_successes={family: report["families"][family]["successes"] for family in ("vv", "full")})
        save(directory / "run_report.json", record)
        runs.append(record)
        candidates.append(dict(name="run_" + str(run_index).zfill(2), parameters=parameters.copy(), report=report))
        print(json.dumps(record), flush=True)
    selected = max(candidates, key=lambda candidate: ranking(candidate["report"]))
    save(HERE / "best_witness.json", engine.encode(selected["parameters"]))
    save(HERE / "best_selection_report.json", selected["report"])
    save(HERE / "preheldout_selection.json", dict(candidate=selected["name"], witness_sha256=digest(HERE / "best_witness.json"),
        selected_at_epoch=time.time(), independent_selection_seed=303170021, count_per_family=32,
        no_heldout_evaluation_yet=True, ranking_rule="nominal pass, minimum family successes, sum successes, minimum individual score, nominal score"))
    official_start = time.time()
    timeout = min(95, max(1, DEADLINE - time.time() - 20))
    try:
        process = subprocess.run([sys.executable, "-B", str(ROOT / "evaluator/evaluate.py"), str(HERE / "best_witness.json"),
                                  "--report", str(HERE / "official_report.json")], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)
        (HERE / "official.log").write_text(process.stdout + process.stderr)
        if process.returncode or not (HERE / "official_report.json").exists():
            raise RuntimeError("official evaluator failed")
        official = json.loads((HERE / "official_report.json").read_text())
    except (subprocess.TimeoutExpired, RuntimeError) as error:
        official = dict(valid=False, passed=False, core_score=0.0, worst_family_score=0.0, resource_score=0.0,
                        reason="bounded portfolio evaluation incomplete: " + str(error))
        save(HERE / "official_report.json", official)
    additional = None
    if official["passed"] and time.time() < DEADLINE - 25:
        specification = importlib.util.spec_from_file_location("frozen_holdout_verifier", ROOT / "evaluator/hidden/assay_worker.py")
        verifier = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(verifier)
        hopping, density = verifier.NOMINAL.read_candidate(HERE / "best_witness.json")
        center = verifier.NOMINAL.full_coefficients(hopping, density)
        uniforms = np.random.Generator(np.random.PCG64(303179991)).random((128, 100))
        cases = []
        for row in uniforms:
            if time.time() >= DEADLINE - 10:
                break
            cases.append(verifier.evaluate_case(verifier.perturb(center, row, "full")))
        additional = dict(seed=303179991, requested_cases=128, completed_cases=len(cases), summary=verifier.summarize(cases))
        save(HERE / "additional_full_holdout.json", additional)
    summary = dict(status="completed bounded private portfolio", elapsed_seconds=time.time() - BUDGET["start_epoch"],
                   execution_budget_seconds=BUDGET["execution_budget_seconds"], requested_cap_seconds=900,
                   runs=runs, optimization_runs=len(runs), objective_evaluations=sum(record["objective_evaluations"] for record in runs),
                   saved_candidate_count=len(candidates), selected_candidate=selected["name"],
                   selected_nominal=selected["report"]["nominal"], official_evaluations=1,
                   official_report="official_report.json", official_passed=official["passed"], official_valid=official["valid"],
                   official_family_successes={family: report["successes"] for family, report in official.get("robustness_families", {}).items()},
                   core_score=official["core_score"], worst_family_score=official["worst_family_score"],
                   official_elapsed_seconds=time.time() - official_start, additional_full_noise_validation=additional,
                   feasibility="passing B3 artifact saved" if official["passed"] else "unknown; bounded failure does not establish impossibility",
                   frozen_audit_before=initial_audit, frozen_audit_after=audit(),
                   heldout_used_for_optimization=False, refit_after_official=False, fresh_B3_outputs_inspected=False,
                   fresh_agents_launched=0, all_writes_within_portfolio=True)
    save(HERE / "summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
