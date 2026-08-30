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
    weights = [1] * counts["1"] + [2] * counts["2"]
    generator.shuffle(weights)
    values = np.zeros(pair_count, dtype=np.int64)
    position = generator.randrange(pair_count)
    for index, weight in enumerate(weights):
        values[position] = weight
        position = (position + boundaries[index + 1] - boundaries[index] + 1) % pair_count
    return values


def exact_correlation(values):
    positions = np.flatnonzero(values)
    weights = values[positions]
    result = np.zeros(len(values), dtype=np.int64)
    for source, source_weight in zip(positions, weights):
        result[(positions - source) % len(values)] += source_weight * weights
    return result


def swap_delta(doubled, source, destination, pair_count):
    difference = int(doubled[destination] - doubled[source])
    delta = difference * (doubled[source:source + pair_count] + doubled[source + pair_count:source:-1]
                          - doubled[destination:destination + pair_count]
                          - doubled[destination + pair_count:destination:-1])
    delta[0] += 2 * difference * difference
    delta[(destination - source) % pair_count] -= difference * difference
    delta[(source - destination) % pair_count] -= difference * difference
    return delta


def legal_swap(values, source, destination):
    source_value, destination_value = int(values[source]), int(values[destination])
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
    best_values, best_cost = None, None
    proposals, total_accepted = 0, 0
    restart_records = []
    initial_temperature = 800.0 * pair_count / 512
    final_temperature = 2.0 * pair_count / 512
    factor = math.exp(math.log(final_temperature / initial_temperature) / max(steps - 1, 1))
    for restart in range(restarts):
        values = feasible_values(generator, pair_count, target["counts"])
        doubled = np.tile(values, 2)
        residual = exact_correlation(values) - expected
        cost = int(residual @ residual)
        initial_cost = cost
        if best_cost is None or cost < best_cost:
            best_values, best_cost = values.copy(), cost
        occupied = np.flatnonzero(values).tolist()
        temperature = initial_temperature
        accepted = 0
        for iteration in range(steps):
            proposals += 1
            occupied_index = generator.randrange(len(occupied))
            source = occupied[occupied_index]
            destination = generator.randrange(pair_count)
            if values[source] != values[destination] and legal_swap(values, source, destination):
                delta = swap_delta(doubled, source, destination, pair_count)
                change = int(2 * (residual @ delta) + delta @ delta)
                if change <= 0 or generator.random() < math.exp(-change / temperature):
                    destination_empty = values[destination] == 0
                    values[source], values[destination] = values[destination], values[source]
                    doubled[source] = doubled[source + pair_count] = values[source]
                    doubled[destination] = doubled[destination + pair_count] = values[destination]
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
            temperature *= factor
        if not np.array_equal(residual, exact_correlation(values) - expected):
            raise RuntimeError("incremental correlation drift")
        restart_records.append({"restart": restart, "initial_squared_error": initial_cost,
                                "final_squared_error": cost, "best_squared_error": best_cost, "accepted": accepted})
        if best_cost == 0:
            break
    residual = exact_correlation(best_values) - expected
    if int(residual @ residual) != best_cost:
        raise RuntimeError("best-artifact objective mismatch")
    metrics = {"algorithm": "count/spacing-preserving swap simulated annealing", "seed": seed,
               "pair_count": pair_count, "requested_restarts": restarts, "steps_per_restart": steps,
               "proposals": proposals, "accepted": total_accepted, "squared_error": best_cost,
               "l1_error": int(np.abs(residual).sum()), "matched_lags": int(np.count_nonzero(residual == 0)),
               "eec_l1_error": float(np.abs(residual).sum() / target["energy_integer_sum"] ** 2),
               "initial_temperature": initial_temperature, "final_temperature": final_temperature,
               "working_storage": "linear in pair_count; no quadratic index tables",
               "found_exact_witness": best_cost == 0, "restart_records": restart_records,
               "search_runtime_seconds": time.perf_counter() - started}
    return {"schema_version": 1, "a": best_values.tolist()}, metrics


def main():
    parser = argparse.ArgumentParser(description="Generate static JSON by bounded, size-parameterized local search.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", type=Path, default=Path(__file__).resolve().parents[1] / "input" / "target.json")
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--restarts", type=int, default=4)
    parser.add_argument("--steps", type=int, default=60000)
    arguments = parser.parse_args()
    if arguments.restarts < 1 or arguments.steps < 1:
        parser.error("restarts and steps must be positive")
    payload = arguments.target.read_bytes()
    target = json.loads(payload)
    design, metrics = search(target, arguments.seed, arguments.restarts, arguments.steps)
    metrics["target_sha256"] = hashlib.sha256(payload).hexdigest()
    arguments.output.mkdir(parents=True, exist_ok=True)
    (arguments.output / "design.json").write_text(json.dumps(design, separators=(",", ":")) + "\n")
    (arguments.output / "search_report.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps({key: value for key, value in metrics.items() if key != "restart_records"}))


if __name__ == "__main__":
    main()
