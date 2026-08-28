import copy
import itertools
import json
import math
import os
from pathlib import Path
import sys
import time
import warnings

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np
from scipy.optimize import least_squares, linprog

from source_io import cell_value, read_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT.parent.parent / "authoring"))
from isolated_eval import run_solver
sys.path.insert(0, str(ROOT / "private"))
from scoring import score


def dual_check(objective, matrix, limits, equality, proof):
    primal = np.asarray(proof["primal"])
    dual = np.asarray(proof["inequality_dual"])
    multiplier = proof["equality_dual"]
    slack = objective - matrix.T @ dual - equality * multiplier
    errors = [
        max(0.0, -float(primal.min())), max(0.0, float((matrix @ primal - limits).max())),
        abs(float(equality @ primal) - 1), max(0.0, float(dual.max())),
        max(0.0, -float(slack.min())), abs(float(objective @ primal - limits @ dual - multiplier)),
    ]
    assert max(errors) < 2e-7, errors
    return max(errors)


def numerical_checks(entries):
    worst_dual_error, worst_fit_error, worst_lp_error = 0.0, 0.0, 0.0
    independent_lp_count = 0
    for entry in entries:
        case, truth = entry["case"], entry["reference"]
        for track in case["tracks"]:
            times = np.asarray(track["time_ms"])
            calibration = track["calibration"]
            basis = (1 - np.exp(-times / calibration["decay_ms"]) * np.cos(
                2 * np.pi * times / calibration["period_ms"] + calibration["phase_rad"]
            )) / 2
            fit = least_squares(lambda parameters: (
                parameters[0] + parameters[1] * basis - track["signal"]
            ) / track["sigma"], [0.0, 0.5], method="lm", ftol=1e-12, xtol=1e-12, gtol=1e-12)
            expected = truth["fits"][track["id"]]
            discrepancy = float(np.max(np.abs(fit.x - [expected["offset"], expected["amplitude"]])))
            worst_fit_error = max(worst_fit_error, discrepancy)
            assert discrepancy < 1e-6
        matrix = np.asarray([row["response"] for row in case["occupation"]["observations"]], dtype=float)
        assert np.array_equal(matrix, truth["matrix"])
        centers, radii = np.asarray(truth["centers"]), np.asarray(truth["radii"])
        size = matrix.shape[1]
        inequalities = np.vstack([matrix, -matrix])
        inflation_matrix = np.column_stack([inequalities, -np.concatenate([radii, radii])])
        inflation_limits = np.concatenate([centers + radii, radii - centers])
        worst_dual_error = max(worst_dual_error, dual_check(
            np.r_[np.zeros(size), 1.0], inflation_matrix, inflation_limits,
            np.r_[np.ones(size), 0.0], truth["certificates"]["inflation"],
        ))
        enlarged = radii * (1 + truth["inflation"] + case["occupation"]["feasibility_pad"])
        limits = np.concatenate([centers + enlarged, enlarged - centers])
        for target in case["occupation"]["targets"]:
            for direction, name in [(1, "lower"), (-1, "upper")]:
                objective = direction * np.asarray(target["coefficients"], dtype=float)
                proof = truth["certificates"]["targets"][target["id"]][name]
                worst_dual_error = max(worst_dual_error, dual_check(objective, inequalities, limits, np.ones(size), proof))
                if entry["source"]["ramp_time_ms"] == 60 and target["id"] in ["p010", "gauge_valid"]:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", DeprecationWarning)
                        independent = linprog(objective, A_ub=inequalities, b_ub=limits,
                                              A_eq=np.ones((1, size)), b_eq=[1.0], bounds=(0, None),
                                              method="revised simplex", options={"tol": 1e-10})
                    assert independent.success, independent.message
                    discrepancy = abs(float(independent.fun - objective @ proof["primal"]))
                    assert discrepancy < 2e-7, discrepancy
                    worst_lp_error = max(worst_lp_error, discrepancy)
                    independent_lp_count += 1
    return {"max_dual_certificate_error": worst_dual_error, "max_independent_fit_error": worst_fit_error,
            "max_independent_lp_error": worst_lp_error, "independent_lp_endpoint_checks": independent_lp_count}


def analytical_invariant():
    states = list(itertools.product([0, 2], [0, 1], [0, 2]))
    time_ms = [0.0, 1.8, 3.6, 5.4, 7.2, 9.0]
    signal = [0.03 + 0.4 * (1 - math.exp(-moment / 96) * math.cos(2 * math.pi * moment / 7.2)) / 2 for moment in time_ms]
    target = [int(middle == 0 and left + right == 2) for left, middle, right in states]
    case = {
        "case_id": "independent_analytical_frechet", "family": "analytical_test_only",
        "tracks": [{"id": "analytic", "time_ms": time_ms, "signal": signal, "sigma": [0.01] * len(time_ms),
                    "query_time_ms": [2.7], "calibration": {"period_ms": 7.2, "decay_ms": 96.0, "phase_rad": 0.0}}],
        "occupation": {
            "states": states, "feasibility_pad": 1e-8,
            "observations": [
                {"id": "matter", "response": [middle for left, middle, right in states], "center": 0.0, "radius": 1e-9},
                {"id": "left", "response": [left / 2 for left, middle, right in states], "center": 0.5, "radius": 1e-9},
                {"id": "right", "response": [right / 2 for left, middle, right in states], "center": 0.5, "radius": 1e-9},
            ],
            "targets": [{"id": "gauge_valid", "coefficients": target}],
        },
    }
    answers = []
    for correlated in [False, True]:
        variant = copy.deepcopy(case)
        if correlated:
            variant["occupation"]["observations"].append({
                "id": "xor", "response": target, "center": 0.6, "radius": 1e-9,
            })
        execution = run_solver(ROOT / "private" / "reference" / "strong", ROOT / "participant", variant, timeout=120, memory_gib=6)
        assert execution["ok"], execution
        answer = execution["result"]
        fits = answer["fits"]["analytic"]
        assert abs(fits["offset"] - 0.03) < 1e-10
        assert abs(fits["amplitude"] - 0.4) < 1e-10
        expected = [0.6, 0.6] if correlated else [0.0, 1.0]
        assert np.max(np.abs(np.asarray(answer["bounds"]["gauge_valid"]) - expected)) < 1e-7
        answers.append({"correlated": correlated, "expected": expected, "observed": answer["bounds"]["gauge_valid"], "seconds": execution["seconds"]})
    return answers


def source_checks(entries):
    source = ROOT / "private" / "reference" / "source"
    published = read_workbook(source / "fig4.xlsx")["Violation of Gauss law"]
    violations = {}
    for number in published:
        moment, value = [cell_value(published, number, column) for column in ["A", "B"]]
        if isinstance(moment, (int, float)) and isinstance(value, (int, float)):
            violations[int(moment)] = value
    checks, heldout_checks = [], []
    for entry in entries:
        if entry["case"]["family"] not in ["projected", "leakage"]:
            continue
        moment = entry["source"]["ramp_time_ms"]
        lower, upper = entry["reference"]["bounds"]["gauge_valid"]
        checks.append({"case_id": entry["case"]["case_id"], "published_violation": violations[moment],
                       "conditional_violation_interval": [1 - upper, 1 - lower],
                       "contains_published_point": 1 - upper - 1e-7 <= violations[moment] <= 1 - lower + 1e-7})
        if entry["case"]["family"] == "projected":
            for identifier, heldout in entry["source"]["heldout_readout"].items():
                residual = np.asarray(entry["reference"]["fits"][identifier]["prediction"]) - heldout["signal"]
                heldout_checks.append({"ramp_time_ms": moment, "track": identifier,
                                       "rmse": float(np.sqrt(np.mean(residual ** 2))),
                                       "standardized_rmse": float(np.sqrt(np.mean((residual / heldout["sigma"]) ** 2)))})
    split_response = [[0, 0.5, 1, 0.5], [0.5, 0.5, 0.5, 0.5], [1, 0.5, 0, 0], [0.5, 0.5, 0, 0]]
    slack = []
    for left, middle, right in itertools.product(range(4), repeat=3):
        bound = split_response[left][right] + int(middle == 1 and left == 0) + int(middle == 1 and right == 0)
        bound -= (left % 2 + right % 2) / 2 + middle / 2 + 1.5 * (middle % 2)
        indicator = int((left, middle, right) in [(0, 0, 2), (2, 0, 0)])
        slack.append(indicator - bound)
    assert min(slack) >= 0
    return {"published_cross_checks": checks, "heldout_readout_checks": heldout_checks,
            "source_inequality_min_slack_all_64_states": min(slack)}


def bottleneck_checks(entries):
    checks = []
    for entry in entries:
        case, truth = entry["case"], entry["reference"]
        answer = {"fits": truth["fits"], "inflation": truth["inflation"], "bounds": truth["bounds"],
                  "witnesses": {target["id"]: {
                      name: truth["certificates"]["targets"][target["id"]][name]["primal"]
                      for name in ["lower", "upper"]} for target in case["occupation"]["targets"]}}
        bad_fit = copy.deepcopy(answer)
        for fitted in bad_fit["fits"].values():
            fitted["amplitude"] += 0.2
        bad_certificate = copy.deepcopy(answer)
        bad_certificate["witnesses"]["gauge_valid"]["lower"] = [
            2 * value for value in bad_certificate["witnesses"]["gauge_valid"]["lower"]
        ]
        fit_score = score(case, truth, bad_fit)["components"]
        certificate_score = score(case, truth, bad_certificate)["components"]
        assert fit_score["readout"] < 0.99 and fit_score["certificate"] > 0.999999
        assert certificate_score["certificate"] < 0.99 and certificate_score["readout"] > 0.999999
        checks.append({"case_id": case["case_id"], "fit_only_corruption": fit_score,
                       "certificate_only_corruption": certificate_score})
    return checks


def main():
    started = time.monotonic()
    entries = []
    for split in ["screening", "challenge"]:
        entries.extend(json.loads((ROOT / "private" / "challenge_pool" / f"{split}.json").read_text())["cases"])
    report = numerical_checks(entries)
    report.update(source_checks(entries))
    report["independent_bottleneck_checks"] = bottleneck_checks(entries)
    report["analytical_invariant"] = analytical_invariant()
    report["confirmation_evaluated"] = False
    report["seconds"] = time.monotonic() - started
    destination = ROOT / "private" / "reference" / "validation" / "independent_checks.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, allow_nan=False))


if __name__ == "__main__":
    main()
