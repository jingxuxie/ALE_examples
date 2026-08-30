import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from prototype import circuits, encode, operators, simulate


def score_population(parameters, encoded):
    residual, leakage = simulate(parameters, encoded)
    return np.abs(residual) - 3 * np.maximum(leakage - .007, 0)


def circuit_search(parameters, word, generator, rounds=100, population=1024):
    encoded = generator.integers(0, 3, (population, 64))
    encoded[:population // 2] = encode([word])
    best_score = -np.inf
    best_word = word
    for generation in range(rounds):
        scores = score_population(parameters, encoded)
        order = np.argsort(scores)
        if scores[order[-1]] > best_score:
            best_score = float(scores[order[-1]])
            best_word = "".join("IXY"[index] for index in encoded[order[-1]])
        elite = encoded[order[-128:]]
        encoded = elite[generator.integers(0, len(elite), population)].copy()
        for mutation in range(1 if generation > rounds // 2 else 3):
            locations = generator.integers(0, 64, population)
            encoded[np.arange(population), locations] = generator.integers(0, 3, population)
        encoded[:len(elite)] = elite
    return best_word


def parameter_search(parameters, word, calibration):
    scale = np.tile([1., .01, .01, .01, .01], 3)
    encoded = encode([word])
    both = np.concatenate([calibration, np.pad(encoded, ((0, 0), (0, calibration.shape[1] - 64)), constant_values=3)])
    last_parameters = None
    last_data = None

    def data(candidate):
        nonlocal last_parameters, last_data
        if last_parameters is None or not np.array_equal(candidate, last_parameters):
            last_parameters = candidate.copy()
            last_data = simulate(candidate * scale, both)
        return last_data

    def loss(candidate):
        residual, leakage = data(candidate)
        return -10 * abs(residual[-1])

    def constraint(candidate):
        residual, leakage = data(candidate)
        return np.concatenate([(.005 - residual[:-1]) / .005,
                               (.005 + residual[:-1]) / .005,
                               [(.007 - leakage[-1]) / .007],
                               (.04 - np.linalg.norm((candidate * scale).reshape(3, 5)[:, 1:], axis=1)) / .04])

    result = minimize(loss, parameters / scale, method="SLSQP", constraints={"type": "ineq", "fun": constraint},
                      bounds=[(-np.pi, np.pi), (-3., 3.), (-3., 3.), (-3., 3.), (-3., 3.)] * 3,
                      options={"maxiter": 300, "ftol": 1e-9, "eps": 1e-5})
    candidate = result.x * scale
    for iteration in range(10):
        residual, leakage = simulate(candidate, both)
        factor = min(1., np.sqrt(.00499 / max(abs(residual[:-1]))), np.sqrt(.00699 / max(leakage[-1], 1e-20)))
        candidate.reshape(3, 5)[:, 1:] *= factor
        if factor == 1.:
            break
    return candidate, bool(result.success)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restarts", type=int, default=8)
    parser.add_argument("--cycles", type=int, default=3)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    samples = json.loads((root / "prototype_results.json").read_text())
    samples.sort(key=lambda sample: sample["heldout"], reverse=True)
    calibration = encode(sum(circuits().values(), []))
    generator = np.random.default_rng(809173)
    start = time.monotonic()
    records = []
    for trial in range(args.restarts):
        seed = samples[trial % len(samples)]
        parameters = np.array(seed["parameters"])
        word = seed["circuit"]
        for cycle in range(args.cycles):
            word = circuit_search(parameters, word, generator)
            parameters, success = parameter_search(parameters, word, calibration)
            residual, leakage = simulate(parameters, calibration)
            heldout, held_leakage = simulate(parameters, encode([word]))
            record = {"trial": trial, "cycle": cycle, "parameters": parameters.tolist(), "circuit": word,
                      "calibration_max": float(max(abs(residual))),
                      "calibration_rms": float(np.sqrt(np.mean(residual ** 2))),
                      "heldout": float(abs(heldout[0])), "final_leakage": float(held_leakage[0]),
                      "success": success, "runtime": time.monotonic() - start}
            records.append(record)
            print(json.dumps(record), flush=True)
            (root / "joint_scaled_results.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
