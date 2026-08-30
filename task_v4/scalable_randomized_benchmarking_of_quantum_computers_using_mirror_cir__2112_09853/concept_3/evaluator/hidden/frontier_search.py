import argparse
import copy
import hashlib
import json
import math
import random
import secrets
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from core import circuit_weights, score_metrics, summarize
from design import energy, mutate, random_layers


def compact(weights):
    return [int(samples.min()) for strata in weights for samples in strata], [float(samples.mean()) for strata in weights for samples in strata]


def worker(family, initial, seed, iterations, root):
    rng = random.Random(seed)
    started = time.perf_counter()
    targets = family["targets"]
    chains = []
    best_energy = math.inf
    best_score_key = (-1,)
    best_circuit = None
    history = []
    temperatures = (0.0, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0, 1.5)
    for index, temperature in enumerate(temperatures):
        layers = copy.deepcopy(initial) if index < 6 else random_layers(family, rng)
        for _ in range(index * 2):
            layers = mutate(layers, family, rng)
        weights = circuit_weights(family["n"], layers)
        chains.append([energy(weights, targets), layers, temperature])
    for iteration in range(iterations):
        chain_index = iteration % len(chains)
        old_energy, parent, temperature = chains[chain_index]
        candidate = mutate(parent, family, rng)
        if rng.random() < 0.03:
            for _ in range(rng.randint(1, 7)):
                candidate = mutate(candidate, family, rng)
        weights = circuit_weights(family["n"], candidate)
        loss = energy(weights, targets)
        if loss <= old_energy or (temperature > 0 and rng.random() < math.exp(min(0.0, (old_energy - loss) / temperature))):
            chains[chain_index] = [loss, candidate, temperature]
        if loss < best_energy:
            best_energy = loss
            best_energy_circuit = copy.deepcopy(candidate)
        minima, means = compact(weights)
        ratios = [minima[index] / targets["min_single" if index % 2 == 0 else "min_double"] for index in range(4)]
        ratios += [means[index] * 1000 / targets["mean_single_milli" if index % 2 == 0 else "mean_double_milli"] for index in range(4)]
        key = (min(ratios), sum(minima), min(means[::2]), min(means[1::2]), -loss)
        if key > best_score_key:
            best_score_key = key
            best_circuit = copy.deepcopy(candidate)
            history.append({"iteration": iteration + 1, "seconds": time.perf_counter() - started,
                            "minima": minima, "means": means, "score": key[0], "energy": loss})
        if (iteration + 1) % 20000 == 0:
            record = {"family": family["id"], "iteration": iteration + 1,
                      "seconds": time.perf_counter() - started, "best": history[-1], "energy": best_energy}
            print(json.dumps(record), flush=True)
            Path(root, "evaluator/hidden", family["id"] + "_hard_progress.json").write_text(json.dumps(record, indent=2) + "\n")
            Path(root, "evaluator/hidden", family["id"] + "_hard_best.json").write_text(json.dumps({"family": family["id"], "layers": best_circuit}, indent=2) + "\n")
            worst = max(range(len(chains)), key=lambda index: chains[index][0])
            replacement = copy.deepcopy(best_energy_circuit)
            for _ in range(rng.randint(5, 20)):
                replacement = mutate(replacement, family, rng)
            chains[worst][:2] = [energy(circuit_weights(family["n"], replacement), targets), replacement]
    metrics = summarize(family["n"], circuit_weights(family["n"], best_circuit))
    report = {"seed": str(seed), "iterations": iterations, "runtime_seconds": time.perf_counter() - started,
              "metrics": metrics, "history": history, "best_energy": best_energy,
              "target_score": score_metrics(metrics, targets)[0]}
    return {"family": family["id"], "layers": best_circuit}, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=400000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    provisional = json.loads((root / "evaluator/hidden/provisional_spec.json").read_text())
    initial = json.loads((root / "champions/calibration_witness.json").read_text())
    families = provisional["families"]
    for family, minima, means in zip(families, ((8, 6), (9, 6), (8, 6)), ((11300,11800),(13000,14300),(12400,13100))):
        family["targets"] = {"min_single": minima[0], "min_double": minima[1],
                             "mean_single_milli": means[0], "mean_double_milli": means[1]}
    seeds = [secrets.randbits(128) for family in families]
    (root / "evaluator/hidden/hard_seeds.json").write_text(json.dumps({"seeds": list(map(str, seeds)),
        "sha256": [hashlib.sha256(str(seed).encode()).hexdigest() for seed in seeds]}, indent=2) + "\n")
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(worker, family, circuit["layers"], seed, args.iterations, str(root))
                   for family, circuit, seed in zip(families, initial["circuits"], seeds)]
        results = [future.result() for future in futures]
    (root / "evaluator/hidden/hard_calibration.json").write_text(json.dumps({"families": families,
        "results": [result[1] for result in results]}, indent=2) + "\n")
    (root / "evaluator/hidden/hard_artifact.json").write_text(json.dumps({"schema_version": 1,
        "circuits": [result[0] for result in results]}, indent=2) + "\n")


if __name__ == "__main__":
    main()
