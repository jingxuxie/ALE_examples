import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import sys
import time

import numpy as np

from model import LOWER, SCALE, STATES, Model, experiment, fit_data


def information(predictions, gradients):
    whitened = gradients / np.sqrt(np.maximum(predictions[:, :, None], 1e-14))
    return np.einsum("eoi,eoj->eij", whitened, whitened, optimize=True)


def select_probe(modes, experiments, random, shots):
    candidates = []
    for index in range(240):
        duration = random.uniform(2.0, 5.8)
        if index < 20:
            duration = random.uniform(0.4, 2.0)
        phases = random.uniform(-np.pi, np.pi, 6)
        if index % 10 == 0:
            phases *= 0
        candidates.append(experiment(STATES[index % 20], duration, phases))
    scores = np.zeros(len(candidates))
    weights = np.exp(-0.5 * np.minimum(100, np.array([mode[1] - modes[0][1] for mode in modes])))
    weights /= weights.sum()
    for weight, mode in zip(weights, modes):
        predictions, gradients = Model(experiments).evaluate(mode[0])
        current = information(predictions, gradients).sum(axis=0) + np.eye(20) * 1e-5
        predictions, gradients = Model(candidates).evaluate(mode[0])
        prospective = information(predictions, gradients)
        covariance = np.linalg.inv(current[None, :, :] + prospective)
        scores += weight * np.trace(covariance, axis1=1, axis2=2) / shots
    return candidates[int(np.argmin(scores))]


def run_controller(query, config, diagnostic=False):
    started = time.process_time()
    random = np.random.default_rng(51923)
    schedule_random = np.random.default_rng(83471)
    experiments = []
    counts = []
    for preparation, duration in zip((21, 7), (1.1, 2.0)):
        if len(experiments) >= config["query_budget"]:
            break
        setting = experiment(preparation, duration, schedule_random.uniform(-1.6, 1.6, 6))
        experiments.append(setting)
        counts.append(query(setting))
    modes = []
    for attempt in range(12):
        initial = np.full(20, 0.5)
        if attempt in (1, 2):
            initial[6:11] = 0.2 if attempt == 1 else 0.8
        elif attempt > 2:
            initial[:14] = random.uniform(0.1, 0.9, 14)
            initial[14:] = modes[0][0][14:]
        fitted = fit_data(experiments, counts, initial, max_nfev=130)
        modes.append(fitted)
        modes.sort(key=lambda result: result[1])
        distinct = []
        for mode in modes:
            if not any(np.linalg.norm(mode[0] - previous[0]) < 0.05 for previous in distinct):
                distinct.append(mode)
        modes = distinct[:5]
        if time.process_time() - started > 25:
            break
    if diagnostic:
        print("initial", [round(mode[1], 3) for mode in modes], time.process_time() - started, file=sys.stderr, flush=True)
    while len(experiments) < config["query_budget"]:
        plausible = [mode for mode in modes if mode[1] < modes[0][1] + 12][:3]
        setting = select_probe(plausible, experiments, random, config["shots"])
        experiments.append(setting)
        counts.append(query(setting))
        results = [fit_data(experiments, counts, mode[0], max_nfev=150) for mode in modes]
        results.sort(key=lambda result: result[1])
        for attempt in range(12):
            initial = results[0][0].copy()
            if attempt % 3 == 0:
                initial[:14] = random.uniform(0.05, 0.95, 14)
            else:
                initial[:14] += random.normal(0, 0.12 if attempt % 3 == 1 else 0.3, 14)
            fitted = fit_data(experiments, counts, initial, max_nfev=130)
            results.append(fitted)
            results.sort(key=lambda result: result[1])
            if time.process_time() - started > 75:
                break
        modes = results[:3]
        if diagnostic:
            print("final", modes[0][1], "cpu", time.process_time() - started, "probe", setting, file=sys.stderr, flush=True)
    normalized, cost, evaluations = fit_data(experiments, counts, modes[0][0], max_nfev=180)
    return LOWER + SCALE * normalized


def main():
    start = json.loads(sys.stdin.readline())

    def query(setting):
        print(json.dumps(setting), flush=True)
        response = json.loads(sys.stdin.readline())
        return response["counts"]

    parameters = run_controller(query, start["config"], diagnostic=True)
    print(json.dumps({"type": "answer", "parameters": parameters.tolist()}), flush=True)


if __name__ == "__main__":
    main()
