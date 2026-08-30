import json
import sys
import time
from pathlib import Path

STARTED = time.monotonic()

import numpy as np
from scipy.optimize import least_squares


INPUT_DIRECTORY = Path("/task/input") if Path("/task/input/model.py").exists() else Path(__file__).resolve().parents[1] / "input"
sys.path.insert(0, str(INPUT_DIRECTORY))
from model import BOUNDS, compile_experiments, probabilities


def fixed_schedule():
    calibration = [
        (["X+", "X+"], "IX"), (["X+", "X-"], "IX"),
        (["X+", "X+"], "XI"), (["X-", "X+"], "XI"),
        (["X+", "X+"], "XX"), (["X-", "X+"], "XX"),
        (["Z+", "Z+"], "ZZ"), (["Z-", "Z+"], "ZZ"),
    ] * 2
    schedule = [{"type": "experiment", "prep": prep, "measure": measure, "time": 0.0, "shots": 128} for prep, measure in calibration]
    times = [0.10, 0.19, 0.34, 0.58, 0.97, 1.53, 2.39, 3.71, 5.63, 8.17, 11.77]
    settings = [([control, target], "I" + axis) for control in ("Z+", "Z-") for target in ("X+", "Z+") for axis in "XYZ"]
    settings += [(["X+", target], axis + "I") for target in ("X+", "Z+") for axis in "XY"]
    for duration in times:
        schedule.extend({"type": "experiment", "prep": prep, "measure": measure, "time": duration, "shots": 128} for prep, measure in settings)
    return schedule


def fit_parameters(experiments, counts, deadline):
    batch = compile_experiments(experiments)
    shots = np.array([experiment["shots"] for experiment in experiments])
    transformed = np.arcsin(np.sqrt((np.asarray(counts) + 0.375) / (shots + 0.75)))
    weights = 2 * np.sqrt(shots)
    early_mask = batch.times <= 0.97
    early_batch = batch.subset(early_mask)

    def residual(parameters, selected_batch, selected_target, selected_weights):
        if time.monotonic() > deadline:
            raise TimeoutError("baseline fit time reserve")
        prediction = probabilities(parameters, selected_batch)
        return selected_weights * (np.arcsin(np.sqrt(np.clip(prediction, 1e-9, 1 - 1e-9))) - selected_target)

    rng = np.random.default_rng(1729)
    starts = []
    for start_index in range(12):
        initial = rng.uniform(BOUNDS[:, 0], BOUNDS[:, 1])
        initial[5:] = [0.92, 0.90, 0.0, 0.035]
        try:
            fit = least_squares(residual, initial, args=(early_batch, transformed[early_mask], weights[early_mask]),
                                bounds=(BOUNDS[:, 0], BOUNDS[:, 1]), max_nfev=95, ftol=2e-5, xtol=2e-5, gtol=2e-5)
        except TimeoutError:
            break
        starts.append((float(np.dot(fit.fun, fit.fun)), fit.x))
        if time.monotonic() > deadline - 3:
            break
    starts.sort(key=lambda item: item[0])
    if not starts:
        return np.array([0, 0, 0, 0, 0, 0.92, 0.90, 0, 0.035])
    best = (float("inf"), starts[0][1])
    for cost, initial in starts[:3]:
        try:
            fit = least_squares(residual, initial, args=(batch, transformed, weights), bounds=(BOUNDS[:, 0], BOUNDS[:, 1]),
                                max_nfev=140, ftol=1e-7, xtol=1e-7, gtol=1e-7)
        except TimeoutError:
            break
        full_cost = float(np.dot(fit.fun, fit.fun))
        if full_cost < best[0]:
            best = (full_cost, fit.x)
        if time.monotonic() > deadline:
            break
    return best[1]


def main():
    greeting = json.loads(sys.stdin.readline())
    if greeting.get("type") != "start":
        raise ValueError("expected start")
    experiments = fixed_schedule()
    counts = []
    for experiment in experiments:
        print(json.dumps(experiment), flush=True)
        response = json.loads(sys.stdin.readline())
        if response.get("type") != "result":
            raise ValueError("expected result")
        counts.append(response["plus"])
    parameters = fit_parameters(experiments, counts, STARTED + 12)
    print(json.dumps({"type": "estimate", "omega": parameters[:5].tolist(), "nuisance": parameters[5:].tolist()}), flush=True)


if __name__ == "__main__":
    main()
