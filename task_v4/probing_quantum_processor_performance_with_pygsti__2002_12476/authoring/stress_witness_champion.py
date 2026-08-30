from collections import Counter
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[1] / "concept_2"
DESTINATION = ROOT / "adversary/generation_1"


def violation(score):
    values = []
    for scenario in score["scenarios"]:
        values.extend([.065 / max(scenario["heldout_abs_error"], 1e-15) - 1,
                       scenario["final_leakage"] / .01 - 1])
        for family in scenario["calibration"].values():
            values.extend([family["max_abs_error"] / .005 - 1, family["rms_error"] / .002 - 1])
    return float(max(values))


def scenarios(original, radius):
    records = copy.deepcopy(original)
    for scale in [.98, 1.02]:
        for signs in itertools.product([-1, 1], repeat=3):
            records.append(dict(name="independent_phase_" + str(len(records)), coupling_scale=scale,
                                phase_shift=[float(radius * sign) for sign in signs]))
    return records


def brief(score):
    failures = Counter()
    for failure in score["violations"]:
        failures[failure.split(": ", 1)[-1]] += 1
    return dict(core_score=score["core_score"], worst_family_score=score["worst_family_score"],
                passed=score["passed"], valid=score["valid"], violation=violation(score),
                maximum_final_leakage=max(record["final_leakage"] for record in score["scenarios"]),
                maximum_calibration_error=max(family["max_abs_error"] for record in score["scenarios"] for family in record["calibration"].values()),
                failure_root_counts=dict(failures))


def main():
    started = time.monotonic()
    DESTINATION.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("private_witness_checker", ROOT / "evaluator/evaluate.py")
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    checker.integrity_check()
    original_spec = copy.deepcopy(checker.SPEC)
    champion_path = ROOT / "champions/generation_1/witness.json"
    champion = checker.read_submission(champion_path)
    assert checker.score_witness(champion)["passed"]
    records = []
    chosen = None
    for radius in [.002, .004, .008, .012, .020, .030]:
        checker.SPEC = copy.deepcopy(original_spec)
        checker.SPEC["scenarios"] = scenarios(original_spec["scenarios"], radius)
        plain = checker.score_witness(champion)
        cache = {}

        def objective(scale):
            key = float(scale)
            if key not in cache:
                candidate = copy.deepcopy(champion)
                for row in candidate["gate_parameters"]:
                    row[1:] = [value * key for value in row[1:]]
                score = checker.score_witness(candidate)
                cache[key] = (violation(score), score)
            return cache[key][0]

        grid = np.linspace(.55, 1., 31)
        sampled = np.array([objective(scale) for scale in grid])
        for index in np.argsort(sampled)[:3]:
            lower = grid[max(0, int(index) - 1)]
            upper = grid[min(len(grid) - 1, int(index) + 1)]
            if lower < upper:
                minimize_scalar(objective, bounds=(lower, upper), method="bounded",
                                options=dict(xatol=1e-5, maxiter=28))
        best_scale = min(cache, key=lambda scale: cache[scale][0])
        record = dict(phase_radius=radius, scenarios=len(checker.SPEC["scenarios"]),
                      unmodified_champion=brief(plain), scalar_trials=len(cache), best_uniform_scale=best_scale,
                      best_uniform_scaling=brief(cache[best_scale][1]))
        records.append(record)
        (DESTINATION / "stress_progress.json").write_text(json.dumps(records, indent=2) + "\n")
        print(json.dumps(record), flush=True)
        if not plain["passed"] and cache[best_scale][0] > .03:
            chosen = copy.deepcopy(checker.SPEC)
            chosen.update(generation=1, independent_phase_radius=radius,
                          uncertainty_description="original five scenarios plus sixteen independent per-gate phase/coupling vertices")
            (DESTINATION / "selected_specification.json").write_text(json.dumps(chosen, indent=2) + "\n")
            break
    if chosen is None:
        raise RuntimeError("no nontrivial phase-uncertainty failure found in the bounded sweep")
    rng = np.random.default_rng(773144019)
    randomized = [dict(name="nominal", coupling_scale=1., phase_shift=0.)]
    for index in range(512):
        randomized.append(dict(name="private_random_" + str(index), coupling_scale=float(rng.uniform(.98, 1.02)),
                               phase_shift=rng.uniform(-chosen["independent_phase_radius"], chosen["independent_phase_radius"], 3).tolist()))
    checker.SPEC = copy.deepcopy(chosen)
    checker.SPEC["scenarios"] = randomized
    random_score = checker.score_witness(champion)
    result = dict(champion_sha256=hashlib.sha256(champion_path.read_bytes()).hexdigest(),
                  original_champion_passes=True, original_five_scenarios_retained=True,
                  radius_sweeps=records, selected_phase_radius=chosen["independent_phase_radius"],
                  broad_random_scenarios=len(randomized), broad_random_score=brief(random_score),
                  failure_mechanism="independent gate phase drift disrupts calibrated coherent leakage return; common-shift axes miss the failure",
                  scalar_search_is_empirical_not_global_proof=True, runtime_seconds=time.monotonic() - started)
    (DESTINATION / "champion_stress_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    (DESTINATION / "broad_random_details.json").write_text(json.dumps(random_score, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
