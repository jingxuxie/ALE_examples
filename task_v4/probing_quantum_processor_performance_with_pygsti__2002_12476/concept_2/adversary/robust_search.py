import argparse
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


ROOT = Path(__file__).resolve().parents[1]
IMPORT = importlib.util.spec_from_file_location("public_screen", ROOT / "participant/workspace/screen.py")
SCREEN = importlib.util.module_from_spec(IMPORT)
IMPORT.loader.exec_module(SCREEN)
SCALE = np.tile([1., .01, .01, .01, .01], 3)


def data(parameters, encoded, scenarios=SCREEN.SPEC["scenarios"]):
    results = []
    for scenario in scenarios:
        transformed = np.array(parameters).reshape(3, 5).copy()
        transformed[:, 0] += scenario["phase_shift"]
        transformed[:, 1:] *= scenario["coupling_scale"]
        truth, prediction, leakage = SCREEN.probabilities(transformed, encoded)
        results.append((truth - prediction, leakage))
    return results


def circuit_search(parameters, word, generator, rounds=150, population=1024):
    encoded = generator.integers(0, 3, (population, 64))
    encoded[:population // 2] = SCREEN.encode([word])
    best_score = -np.inf
    best_word = word
    for generation in range(rounds):
        results = data(parameters, encoded, SCREEN.SPEC["scenarios"][:3])
        scores = np.min([abs(result[0]) for result in results], axis=0)
        scores -= 5 * np.maximum(np.max([result[1] for result in results], axis=0) - .0095, 0)
        for gate in range(3):
            scores -= np.maximum(4 - np.sum(encoded == gate, axis=1), 0)
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


def parameter_search(parameters, word):
    words = sum(SCREEN.FAMILIES.values(), []) + [word]
    encoded = SCREEN.encode(words)
    last_parameters = None
    last_data = None

    def evaluate(candidate):
        nonlocal last_parameters, last_data
        if last_parameters is None or not np.array_equal(candidate, last_parameters):
            last_parameters = candidate.copy()
            last_data = data(candidate * SCALE, encoded)
        return last_data

    def loss(candidate):
        results = evaluate(candidate)
        return -10 * min(abs(residual[-1]) for residual, leakage in results)

    def constraint(candidate):
        constraints = []
        for residual, leakage in evaluate(candidate):
            constraints.extend([(.00498 - residual[:-1]) / .005, (.00498 + residual[:-1]) / .005,
                                [(.0098 - leakage[-1]) / .01]])
            offset = 0
            for family in SCREEN.FAMILIES.values():
                rms = np.sqrt(np.mean(residual[offset:offset + len(family)] ** 2))
                constraints.append([(.00199 - rms) / .002])
                offset += len(family)
        constraints.append((.0399 - np.linalg.norm((candidate * SCALE).reshape(3, 5)[:, 1:], axis=1)) / .04)
        return np.concatenate(constraints)

    result = minimize(loss, np.array(parameters).ravel() / SCALE, method="SLSQP",
                      constraints={"type": "ineq", "fun": constraint},
                      bounds=[(-np.pi, np.pi), (-4., 4.), (-4., 4.), (-4., 4.), (-4., 4.)] * 3,
                      options={"maxiter": 180, "ftol": 1e-8, "eps": 1e-5})
    candidate = result.x * SCALE
    for iteration in range(20):
        witness = {"version": 1, "gate_parameters": candidate.reshape(3, 5).tolist(), "circuit": word}
        measured = SCREEN.measure(witness)
        if measured["calibration_accepted"] and max(record["final_leakage"] for record in measured["scenarios"]) <= .01:
            return candidate, measured, bool(result.success)
        candidate.reshape(3, 5)[:, 1:] *= .98
    return candidate, SCREEN.measure(witness), bool(result.success)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restarts", type=int, default=6)
    parser.add_argument("--cycles", type=int, default=6)
    args = parser.parse_args()
    samples = json.loads((ROOT / "adversary/joint_scaled_results.json").read_text())
    samples.sort(key=lambda sample: sample["heldout"], reverse=True)
    seeds = []
    seen = set()
    for sample in samples:
        if sample["trial"] not in seen:
            seeds.append(sample)
            seen.add(sample["trial"])
    generator = np.random.default_rng(618641)
    start = time.monotonic()
    records = []
    best_score = 0.
    for restart in range(args.restarts):
        sample = seeds[restart % len(seeds)]
        parameters = np.array(sample["parameters"])
        word = sample["circuit"]
        for cycle in range(args.cycles):
            if cycle:
                word = circuit_search(parameters, word, generator)
            parameters, measured, success = parameter_search(parameters, word)
            witness = {"version": 1, "gate_parameters": parameters.reshape(3, 5).tolist(), "circuit": word}
            record = {"restart": restart, "cycle": cycle, "solver_success": success,
                      "core_score": measured["core_score"], "worst_family_score": measured["worst_family_score"],
                      "calibration_accepted": measured["calibration_accepted"], "passed": measured["passed"],
                      "runtime_seconds": time.monotonic() - start}
            records.append(record)
            print(json.dumps(record), flush=True)
            (ROOT / "adversary/robust_search_results.json").write_text(json.dumps(records, indent=2) + "\n")
            if measured["calibration_accepted"] and measured["worst_family_score"] > best_score:
                best_score = measured["worst_family_score"]
                (ROOT / "adversary/private_best_witness.json").write_text(json.dumps(witness, indent=2) + "\n")
                (ROOT / "adversary/private_best_public_result.json").write_text(json.dumps(measured, indent=2) + "\n")


if __name__ == "__main__":
    main()
