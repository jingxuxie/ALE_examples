#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import time

import numpy as np


def feasible_values(generator, pair_count, counts):
    occupied_count = counts["1"] + counts["2"]
    extra_zeros = pair_count - 2 * occupied_count
    bars = sorted(generator.sample(range(extra_zeros + occupied_count - 1), occupied_count - 1))
    boundaries = [-1] + bars + [extra_zeros + occupied_count - 1]
    gaps = [boundaries[index + 1] - boundaries[index] + 1 for index in range(occupied_count)]
    weights = [1] * counts["1"] + [2] * counts["2"]
    generator.shuffle(weights)
    values = np.zeros(pair_count, dtype=np.int64)
    position = generator.randrange(pair_count)
    for gap, weight in zip(gaps, weights):
        values[position] = weight
        position = (position + gap) % pair_count
    return values


def exact_correlation(values):
    pair_count = len(values)
    return np.array([sum(int(values[slot]) * int(values[(slot + lag) % pair_count])
                         for slot in range(pair_count)) for lag in range(pair_count)], dtype=np.int64)


def swap_delta(values, source, destination, plus_indices, minus_indices):
    difference = int(values[destination] - values[source])
    delta = difference * (values[plus_indices[source]] + values[minus_indices[source]]
                          - values[plus_indices[destination]] - values[minus_indices[destination]])
    delta[0] += 2 * difference * difference
    delta[(destination - source) % len(values)] -= difference * difference
    delta[(source - destination) % len(values)] -= difference * difference
    return delta


def legal_swap(values, source, destination):
    source_value = int(values[source])
    destination_value = int(values[destination])
    values[source], values[destination] = destination_value, source_value
    affected = {source, (source - 1) % len(values), destination, (destination - 1) % len(values)}
    legal = all(not (values[slot] and values[(slot + 1) % len(values)]) for slot in affected)
    values[source], values[destination] = source_value, destination_value
    return legal


def search(target, seed, restarts, steps):
    started = time.perf_counter()
    generator = random.Random(seed)
    pair_count = target["pair_count"]
    expected = np.array(target["cyclic_autocorrelation"], dtype=np.int64)
    indices = np.arange(pair_count)
    plus_indices = (indices[:, None] + indices[None, :]) % pair_count
    minus_indices = (indices[:, None] - indices[None, :]) % pair_count
    best_values = None
    best_cost = None
    restart_records = []
    total_proposals = 0
    total_accepted = 0
    temperature_factor = math.exp(math.log(2.0 / 800.0) / max(steps - 1, 1))
    for restart in range(restarts):
        values = feasible_values(generator, pair_count, target["counts"])
        residual = exact_correlation(values) - expected
        cost = int(residual @ residual)
        initial_cost = cost
        if best_cost is None or cost < best_cost:
            best_values, best_cost = values.copy(), cost
        occupied = np.flatnonzero(values).tolist()
        temperature = 800.0
        accepted = 0
        legal_proposals = 0
        for iteration in range(steps):
            total_proposals += 1
            occupied_index = generator.randrange(len(occupied))
            source = occupied[occupied_index]
            destination = generator.randrange(pair_count)
            if values[source] != values[destination] and legal_swap(values, source, destination):
                legal_proposals += 1
                delta = swap_delta(values, source, destination, plus_indices, minus_indices)
                change = int(2 * (residual @ delta) + delta @ delta)
                if change <= 0 or generator.random() < math.exp(-change / temperature):
                    destination_empty = values[destination] == 0
                    values[source], values[destination] = values[destination], values[source]
                    if destination_empty:
                        occupied[occupied_index] = destination
                    residual += delta
                    cost += change
                    accepted += 1
                    total_accepted += 1
                    if cost < best_cost:
                        best_values, best_cost = values.copy(), cost
                    if best_cost == 0:
                        break
            temperature *= temperature_factor
        checked_residual = exact_correlation(values) - expected
        if not np.array_equal(residual, checked_residual):
            raise RuntimeError("incremental correlation drift")
        restart_records.append({"restart": restart, "initial_squared_error": initial_cost,
                                "final_squared_error": cost, "best_squared_error": best_cost,
                                "legal_proposals": legal_proposals, "accepted": accepted})
        if best_cost == 0:
            break
    final_residual = exact_correlation(best_values) - expected
    if int(final_residual @ final_residual) != best_cost:
        raise RuntimeError("best-artifact objective mismatch")
    result = {"schema_version": 1, "a": best_values.tolist()}
    metrics = {"algorithm": "count/spacing-preserving swap simulated annealing",
               "seed": seed, "requested_restarts": restarts, "steps_per_restart": steps,
               "proposals": total_proposals, "accepted": total_accepted,
               "squared_error": best_cost, "l1_error": int(np.abs(final_residual).sum()),
               "matched_lags": int(np.count_nonzero(final_residual == 0)),
               "found_exact_witness": best_cost == 0, "restart_records": restart_records,
               "search_runtime_seconds": time.perf_counter() - started}
    return result, metrics


def main():
    parser = argparse.ArgumentParser(description="Generate a static inverse-EEC design by bounded local search.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", type=Path,
                        default=Path(__file__).resolve().parents[1] / "input" / "target.json")
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--restarts", type=int, default=4)
    parser.add_argument("--steps", type=int, default=60000)
    arguments = parser.parse_args()
    if arguments.restarts < 1 or arguments.steps < 1:
        parser.error("restarts and steps must be positive")
    payload = arguments.target.read_bytes()
    target = json.loads(payload)
    if target["pair_count"] != 512 or target["counts"] != {"0": 416, "1": 64, "2": 32}:
        parser.error("unsupported target configuration")
    design, metrics = search(target, arguments.seed, arguments.restarts, arguments.steps)
    metrics["target_sha256"] = hashlib.sha256(payload).hexdigest()
    arguments.output.mkdir(parents=True, exist_ok=True)
    (arguments.output / "design.json").write_text(json.dumps(design, separators=(",", ":")) + "\n",
                                                 encoding="utf-8")
    (arguments.output / "search_report.json").write_text(json.dumps(metrics, indent=2) + "\n",
                                                        encoding="utf-8")
    print(json.dumps({key: value for key, value in metrics.items() if key != "restart_records"}))


if __name__ == "__main__":
    main()
