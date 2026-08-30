import functools
import hashlib
import importlib.util
import itertools
import json
import multiprocessing
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


sys.dont_write_bytecode = True
OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[2]
SOURCE = ROOT / "evaluator/evaluate.py"
LOADER = importlib.util.spec_from_file_location("authoritative_evaluator", SOURCE)
REFERENCE = importlib.util.module_from_spec(LOADER)
LOADER.loader.exec_module(REFERENCE)
SPEC = REFERENCE.SPEC
FAMILIES = REFERENCE.FAMILIES
CHAMPION_PATH = ROOT / "champions/generation_2/witness.json"
CHAMPION = json.loads(CHAMPION_PATH.read_text())
PARAMETERS = np.array(CHAMPION["gate_parameters"])
WORDS = sum(FAMILIES.values(), []) + [CHAMPION["circuit"]]
LABELS = np.full((len(WORDS), max(map(len, WORDS))), 3, dtype=int)
for index, word in enumerate(WORDS):
    LABELS[index, :len(word)] = ["IXY".index(symbol) for symbol in word]
PAULIS = np.array([[[1, 0], [0, 1]], [[0, 1], [1, 0]], [[0, -1j], [1j, 0]], [[1, 0], [0, -1]]], dtype=complex)
ROTATIONS = np.array([PAULIS[0], (PAULIS[0] - 1j * PAULIS[1]) / np.sqrt(2),
                      (PAULIS[0] - 1j * PAULIS[2]) / np.sqrt(2)])
METRIC_NAMES = ["calibration_max"] + ["rms_" + name for name in FAMILIES] + ["heldout_leakage", "heldout_gap"]
LIMITS = np.array([.005] + [.002] * len(FAMILIES) + [.01, .065])
STARTED = time.monotonic()
DEADLINE = STARTED + 480
LOCAL_CALLS = 0


def save(name, data):
    temporary = OUTPUT / (name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temporary.replace(OUTPUT / name)


def scenario(normalized):
    normalized = np.asarray(normalized)
    return {"phase_shift": (.008 * normalized[:3]).tolist(), "coupling_scale": float(1 + .02 * normalized[3])}


def physical_batch(normalized, parameters=PARAMETERS):
    normalized = np.asarray(normalized).reshape(-1, 4)
    strengths, scale_indices = np.unique(1 + .02 * normalized[:, 3], return_inverse=True)
    phases = .008 * normalized[:, :3]
    hamiltonians = np.zeros((3, 3, 3), dtype=complex)
    hamiltonians[:, 0, 2] = parameters[:, 1] + 1j * parameters[:, 2]
    hamiltonians[:, 1, 2] = parameters[:, 3] + 1j * parameters[:, 4]
    hamiltonians[:, 2, :2] = hamiltonians[:, :2, 2].conj()
    radii = np.linalg.norm(parameters[:, 1:], axis=1)
    radii_scaled = strengths[:, None] * radii[None, :]
    first_coefficient = strengths[:, None] * np.sinc(radii_scaled / np.pi)
    second_coefficient = .5 * strengths[:, None] ** 2 * np.sinc(radii_scaled / (2 * np.pi)) ** 2
    mixing = np.eye(3) - 1j * first_coefficient[:, :, None, None] * hamiltonians[None]
    mixing -= second_coefficient[:, :, None, None] * (hamiltonians @ hamiltonians)[None]
    nominal = np.zeros((3, 3, 3), dtype=complex)
    nominal[:, :2, :2] = ROTATIONS
    nominal[:, 2, 2] = np.exp(-1j * parameters[:, 0])
    base = np.tile(np.eye(3, dtype=complex), (len(strengths), 4, 1, 1))
    base[:, :3] = mixing @ nominal[None]
    first = base[:, :3, :2, :2]
    second = np.zeros_like(first)
    second[:, :, 1, :] = base[:, :3, 2, :2]
    images = first[:, :, None] @ PAULIS[None, None] @ first.conj().swapaxes(-1, -2)[:, :, None]
    images += second[:, :, None] @ PAULIS[None, None] @ second.conj().swapaxes(-1, -2)[:, :, None]
    transfers = np.tile(np.eye(4), (len(strengths), 4, 1, 1))
    transfers[:, :3] = (np.einsum("aij,sgbji->sgab", PAULIS, images) / 2).real
    unitaries = base[scale_indices].copy()
    unitaries[:, :3, :, 2] *= np.exp(-1j * phases)[:, :, None]
    states = np.zeros((len(normalized), len(WORDS), 3), dtype=complex)
    states[:, :, 0] = 1
    bloch = np.tile([1., 0., 0., 1.], (len(strengths), len(WORDS), 1))
    for column in LABELS.T:
        states = (unitaries[:, column] @ states[..., None])[..., 0]
        bloch = (transfers[:, column] @ bloch[..., None])[..., 0]
    truth = .005 + .99 * abs(states[:, :, 0]) ** 2
    prediction = .005 + .99 * (bloch[:, :, 0] + bloch[:, :, 3]) / 2
    prediction = prediction[scale_indices]
    return truth - prediction, abs(states[:, :, 2]) ** 2


def metric_values(residual, leakage):
    errors = abs(residual)
    values = [np.max(errors[:, :-1], axis=1)]
    offset = 0
    for family in FAMILIES.values():
        values.append(np.sqrt(np.mean(errors[:, offset:offset + len(family)] ** 2, axis=1)))
        offset += len(family)
    values.extend([leakage[:, -1], errors[:, -1]])
    return np.array(values).T


def violations(metrics):
    scores = metrics / LIMITS - 1
    scores[:, -1] *= -1
    return scores


def batch(normalized):
    return metric_values(*physical_batch(normalized))


def independent(normalized, parameters=PARAMETERS):
    normalized = np.asarray(normalized)
    if np.max(abs(normalized)) > 1 + 1e-12:
        raise ValueError("candidate lies outside the frozen continuous box")
    transformed = np.array(parameters).copy()
    transformed[:, 0] += .008 * normalized[:3]
    transformed[:, 1:] *= 1 + .02 * normalized[3]
    truth, prediction, leakage = REFERENCE.simulate(transformed, WORDS)
    residual = truth - prediction
    metrics = metric_values(residual[None], leakage[None])[0]
    differences = metrics - LIMITS
    differences[-1] *= -1
    maximum_index = int(np.argmax(abs(residual[:-1])))
    return {"scenario": scenario(normalized), "normalized_coordinates": normalized.tolist(),
            "metrics": dict(zip(METRIC_NAMES, metrics.tolist())),
            "normalized_violations": dict(zip(METRIC_NAMES, violations(metrics[None])[0].tolist())),
            "absolute_excess": dict(zip(METRIC_NAMES, differences.tolist())),
            "violated_metrics": [name for name, difference in zip(METRIC_NAMES, differences) if difference > SPEC["numerical_tolerance"]],
            "worst_calibration_circuit": WORDS[maximum_index],
            "worst_calibration_signed_error": float(residual[maximum_index]),
            "heldout_signed_error": float(residual[-1]),
            "heldout_truth": float(truth[-1]), "heldout_prediction": float(prediction[-1])}


def initialize_worker():
    try:
        identity = multiprocessing.current_process()._identity[0]
        cores = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {cores[-1 - (identity - 1) % min(4, len(cores))]})
    except (AttributeError, OSError, IndexError):
        pass


@functools.lru_cache(maxsize=1024)
def local_metrics(coordinates):
    global LOCAL_CALLS
    if time.monotonic() > DEADLINE:
        raise TimeoutError("bounded search limit")
    LOCAL_CALLS += 1
    return batch(np.array(coordinates)[None])[0]


def main():
    REFERENCE.integrity_check()
    assert SPEC["independent_phase_radius"] == .008
    assert LIMITS.tolist() == [.005] + [.002] * 7 + [.01, .065]
    protected = [SOURCE, ROOT / "evaluator/hidden/specification.json", ROOT / "evaluator/hidden/calibration.json", CHAMPION_PATH]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    champion_score = REFERENCE.evaluate(CHAMPION_PATH)
    assert champion_score["passed"]
    save("champion_21_scenario_evaluation.json", champion_score)
    generator = np.random.default_rng(264161)
    cross_points = np.vstack([np.zeros((1, 4)), np.array(list(itertools.product([-1., 1.], repeat=4))), generator.uniform(-1, 1, (20, 4))])
    fast_residual, fast_leakage = physical_batch(cross_points)
    maximum_disagreement = 0.
    for index, point in enumerate(cross_points):
        transformed = PARAMETERS.copy()
        transformed[:, 0] += .008 * point[:3]
        transformed[:, 1:] *= 1 + .02 * point[3]
        truth, prediction, leakage = REFERENCE.simulate(transformed, WORDS)
        maximum_disagreement = max(maximum_disagreement, float(np.max(abs(fast_residual[index] - (truth - prediction)))),
                                   float(np.max(abs(fast_leakage[index] - leakage))))
    assert maximum_disagreement < 3e-12
    save("simulator_audit.json", {"passed": True, "maximum_disagreement": maximum_disagreement,
                                  "scenario_count": len(cross_points), "circuits_per_scenario": len(WORDS)})
    grid = np.array(list(itertools.product(np.linspace(-1., 1., 9), repeat=4)))
    interior = np.array(list(itertools.product(np.linspace(-.875, .875, 8), repeat=4)))
    random_points = generator.uniform(-1, 1, (8192, 4))
    points = np.concatenate([grid, interior, random_points])
    chunks = [points[start:start + 96] for start in range(0, len(points), 96)]
    with multiprocessing.Pool(4, initializer=initialize_worker) as pool:
        metrics = np.concatenate(pool.map(batch, chunks))
    np.savez_compressed(OUTPUT / "sampled_scenarios.npz", normalized_coordinates=points, metrics=metrics)
    scores = violations(metrics)
    extrema = {}
    seeds = {}
    for metric, name in enumerate(METRIC_NAMES):
        order = np.argsort(-scores[:, metric])
        top = int(order[0])
        extrema[name] = independent(points[top])
        selected = []
        for index in order:
            if all(np.linalg.norm(points[index] - previous) > .18 for previous in selected):
                selected.append(points[index])
            if len(selected) >= 6:
                break
        seeds[name] = selected
    save("grid_random_extrema.json", extrema)
    print(json.dumps({"stage": "grid_random", "seconds": time.monotonic() - STARTED,
                      "regular_grid_scenarios": len(grid), "interior_grid_scenarios": len(interior),
                      "random_scenarios": len(random_points),
                      "worst_normalized_violations": {name: extrema[name]["normalized_violations"][name] for name in METRIC_NAMES}}), flush=True)
    optimizations = []
    try:
        for metric, name in enumerate(METRIC_NAMES):
            def objective(coordinates):
                values = local_metrics(tuple(coordinates))
                score = values[metric] / LIMITS[metric] - 1
                if metric == len(METRIC_NAMES) - 1:
                    score *= -1
                return -score
            for index, seed in enumerate(seeds[name]):
                method = "Powell" if index == 5 else "L-BFGS-B"
                options = {"maxiter": 100, "ftol": 1e-12}
                if method == "L-BFGS-B":
                    options.update({"gtol": 1e-8, "eps": 2e-5, "maxls": 30})
                result = minimize(objective, seed, method=method, bounds=[(-1., 1.)] * 4, options=options)
                coordinates = np.clip(result.x, -1, 1)
                reproduced = independent(coordinates)
                if reproduced["normalized_violations"][name] > extrema[name]["normalized_violations"][name]:
                    extrema[name] = reproduced
                record = {"metric": name, "seed": index, "method": method, "success": bool(result.success),
                          "function_evaluations": int(result.nfev), "coordinates": coordinates.tolist(),
                          "normalized_violation": reproduced["normalized_violations"][name]}
                optimizations.append(record)
                save("local_optimization_log.json", optimizations)
            print(json.dumps({"stage": "optimized", "metric": name, "normalized_violation": extrema[name]["normalized_violations"][name],
                              "seconds": time.monotonic() - STARTED}), flush=True)
    except TimeoutError:
        print("local_search_budget_exhausted", flush=True)
    save("optimized_extrema.json", extrema)
    rounding = []
    worst_points = [np.array(record["normalized_coordinates"]) for record in extrema.values()]
    worst_points += [np.zeros(4), *np.array(list(itertools.product([-1., 1.], repeat=4)))]
    for digits in [16, 14, 12, 10, 8, 6, 4]:
        rounded = np.round(PARAMETERS, digits)
        changed = np.max(abs(rounded - PARAMETERS))
        evaluated = [independent(point, rounded) for point in worst_points]
        rounding.append({"decimal_digits": digits, "maximum_parameter_change": float(changed),
                         "violated_metrics": sorted(set(name for record in evaluated for name in record["violated_metrics"])),
                         "maximum_normalized_violation": max(max(record["normalized_violations"].values()) for record in evaluated),
                         "counts_as_fixed_champion_counterexample": False})
    save("rounding_stability.json", {"cases": rounding, "explanation": "Rounding alters the submitted nominal processor and is tested separately; it cannot justify a successor for the exact fixed champion."})
    failures = []
    for name, record in extrema.items():
        if record["absolute_excess"][name] > SPEC["numerical_tolerance"]:
            failures.append({"metric": name, **record})
    clusters = []
    for record in failures:
        if record["metric"] == "heldout_leakage":
            cause = "Interior or face leakage recoherence maximum missed by enumerated vertices"
        elif record["metric"] == "heldout_gap":
            cause = "Interior or face held-out prediction-gap minimum missed by enumerated vertices"
        elif record["metric"].startswith("rms_"):
            cause = "Calibration-family RMS maximum inside the uncertainty box rather than at tested vertices"
        else:
            cause = "Individual calibration residual maximum inside the uncertainty box rather than at tested vertices"
        clusters.append({"root_cause_candidate": cause, "metric": record["metric"],
                         "scenario": record["scenario"], "absolute_excess": record["absolute_excess"][record["metric"]],
                         "normalized_violation": record["normalized_violations"][record["metric"]],
                         "calibration_circuit": record["worst_calibration_circuit"] if "calibration" in record["metric"] else None})
    unchanged = all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected for path, expected in hashes.items())
    assert unchanged
    report = {"completed_at_utc": datetime.now(timezone.utc).isoformat(), "runtime_seconds": time.monotonic() - STARTED,
              "frozen_box": {"independent_phase_radius": .008, "common_coupling_scale": [.98, 1.02]},
              "thresholds_unchanged": True, "regular_grid_scenarios": len(grid), "interior_grid_scenarios": len(interior),
              "random_scenarios": len(random_points), "total_grid_random_scenarios": len(points),
              "local_optimizer_runs": len(optimizations), "local_scenario_evaluations": LOCAL_CALLS,
              "local_evaluation_count_definition": "Simulator cache misses during local optimization; revisits after cache eviction may be counted again.",
              "independently_reproduced_failures": failures, "failure_clusters": clusters,
              "has_genuine_continuous_box_failure": bool(failures),
              "successor_justified_by_this_search": bool(failures),
              "decision": "A continuous-box counterexample is reproduced; main must judge scientific magnitude and successor design." if failures else "Solved champion; no justified successor found within this unchanged uncertainty box.",
              "numerical_stability": {"simulator_maximum_disagreement": maximum_disagreement,
                                      "rounding_results_separate_from_fixed_champion_search": True},
              "source_hashes": hashes, "protected_assets_unchanged": unchanged,
              "active_attempts_inspected": False,
              "worst_metrics": {name: {"value": extrema[name]["metrics"][name], "absolute_excess": extrema[name]["absolute_excess"][name],
                                        "scenario": extrema[name]["scenario"]} for name in METRIC_NAMES}}
    save("final_report.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
