import argparse
import heapq
import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from model import GeneralModel


def integer_projection(model, point, generator, deadline, randomized):
    lower = np.floor(point + 1e-6).astype(int)
    upper = np.ceil(point - 1e-6).astype(int)
    indices = np.flatnonzero(lower != upper)
    matrix = model.full_constraint[:, indices]
    target = model.integer_target - model.full_constraint @ lower
    objective = 1 - 2 * (point[indices] - lower[indices])
    if randomized:
        objective += generator.normal(0, 0.7, len(indices))
    serial = itertools.count()
    queue = []
    solved_nodes = 0

    def enqueue(bounds):
        nonlocal solved_nodes
        if time.perf_counter() >= deadline:
            return
        result = linprog(objective, A_eq=matrix, b_eq=target, bounds=bounds, method="highs",
                         options={"time_limit": max(0.1, deadline - time.perf_counter())})
        solved_nodes += 1
        if result.success:
            heapq.heappush(queue, (float(result.fun), next(serial), bounds, result.x))

    enqueue([(0, 1)] * len(indices))
    while queue and time.perf_counter() < deadline and solved_nodes < 4000:
        _, _, bounds, relaxed = heapq.heappop(queue)
        fractional = abs(relaxed - np.rint(relaxed))
        if np.max(fractional, initial=0) < 1e-7:
            counts = lower.copy()
            counts[indices] += np.rint(relaxed).astype(int)
            if not np.array_equal(model.full_constraint @ counts, model.integer_target):
                raise AssertionError("Integer projection violated an exact linear constraint")
            return counts, solved_nodes
        variable = int(np.argmax(fractional))
        for value in (0, 1):
            child = list(bounds)
            child[variable] = (value, value)
            enqueue(child)
    return None, solved_nodes


def family_repairs(model, counts, quadratic, family, target, gradient, keep=32):
    gates = range(24) if family == "single" else range(24, 32)
    moves = [np.zeros(192, dtype=int)]
    for first_gate, second_gate in itertools.combinations(gates, 2):
        if set(model.supports[first_gate]) != set(model.supports[second_gate]):
            continue
        for first_label, second_label in itertools.combinations(model.supports[first_gate], 2):
            for amount in (-2, -1, 1, 2):
                change = np.zeros(192, dtype=int)
                change[model.lookup[first_gate, first_label]] = amount
                change[model.lookup[first_gate, second_label]] = -amount
                change[model.lookup[second_gate, first_label]] = -amount
                change[model.lookup[second_gate, second_label]] = amount
                candidate = counts + change
                if np.all(candidate >= model.lower) and np.all(candidate <= model.upper):
                    moves.append(change)
    moves = np.array(moves)
    products = moves @ quadratic
    deltas = 2 * products @ counts + np.sum(products * moves, axis=1)
    pair_deltas = deltas[:, None] + deltas[None, :] + 2 * products @ moves.T
    wanted = target - int(counts @ quadratic @ counts)
    found = {}
    for first_index, second_index in np.argwhere(pair_deltas == wanted):
        if first_index > second_index:
            continue
        change = moves[first_index] + moves[second_index]
        candidate = counts + change
        if np.any(candidate < model.lower) or np.any(candidate > model.upper):
            continue
        key = tuple(int(value) for value in change)
        if key not in found:
            found[key] = (float(gradient @ change / 60), change)
    ordered = sorted(found.values(), key=lambda entry: entry[0])[:keep]
    return ordered, {"moves": len(moves), "exact_repairs": len(found), "kept": len(ordered),
                     "initial_overlap": int(counts @ quadratic @ counts), "target": target}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=900)
    arguments = parser.parse_args()
    started = time.perf_counter()
    deadline = started + arguments.seconds
    model = GeneralModel()
    source_path = Path(__file__).with_name("pair_search.json")
    source = json.loads(source_path.read_text())["result"]
    starts = sorted((run for run in source["runs"] if run["success"]), key=lambda run: -run["metrics"]["bias"])
    single_quadratic = model.quadratic.copy()
    single_quadratic[72:, :] = 0
    single_quadratic[:, 72:] = 0
    cx_quadratic = (model.quadratic - single_quadratic) // 2
    generator = np.random.default_rng(239)
    seen_projections = set()
    records = []
    best_metrics = None
    total_nodes = 0
    evaluations = 0
    for attempt in range(1000):
        if time.perf_counter() >= deadline:
            break
        start = starts[attempt % min(3, len(starts))]
        point = 60 * np.array(start["conditional"])
        counts, nodes = integer_projection(model, point, generator, deadline, randomized=attempt >= 3)
        total_nodes += nodes
        if counts is None:
            continue
        key = tuple(int(value) for value in counts)
        if key in seen_projections:
            continue
        seen_projections.add(key)
        gradient = model.run(point / 60, gradient=True)[1]
        single_options, single_stats = family_repairs(model, counts, single_quadratic, "single", 28800, gradient)
        cx_options, cx_stats = family_repairs(model, counts, cx_quadratic, "cx", 1920, gradient)
        record = {"attempt": attempt, "continuous_start": start["start"], "lp_nodes": nodes,
                  "single_repairs": single_stats, "cx_repairs": cx_stats}
        records.append(record)
        print(json.dumps(record), flush=True)
        combinations = sorted(((single_cost + cx_cost, single_change, cx_change)
                              for single_cost, single_change in single_options
                              for cx_cost, cx_change in cx_options), key=lambda entry: entry[0])
        for _, single_change, cx_change in combinations[:256]:
            if time.perf_counter() >= deadline:
                break
            candidate = counts + single_change + cx_change
            if not np.array_equal(model.full_constraint @ candidate, model.integer_target):
                raise AssertionError("Family repairs changed the global mean")
            if int(candidate @ single_quadratic @ candidate) != 28800 or int(candidate @ cx_quadratic @ candidate) != 1920:
                raise AssertionError("Integer pair calibration is not exact")
            metrics = model.run(candidate / 60)
            evaluations += 1
            if best_metrics is None or metrics["bias"] > best_metrics["bias"]:
                best_metrics = {name: value for name, value in metrics.items() if name != "polarizations"}
            if metrics["bias"] >= 0.0239 and metrics["max_residual"] <= 0.004 and metrics["end_signal"] >= 0.005:
                result = {"found": True, "elapsed_seconds": time.perf_counter() - started,
                          "deadline_seconds": arguments.seconds, "source": str(source_path),
                          "source_start": start["start"], "lp_nodes": total_nodes,
                          "integer_projections": len(seen_projections), "exact_candidate_evaluations": evaluations,
                          "metrics": {name: value for name, value in metrics.items() if name != "polarizations"},
                          "family_calibrations": model.family_calibrations(candidate),
                          "witness": model.encode(candidate), "progress": records}
                print("FINAL_JSON " + json.dumps(result), flush=True)
                return
    result = {"found": False, "elapsed_seconds": time.perf_counter() - started,
              "deadline_seconds": arguments.seconds, "lp_nodes": total_nodes,
              "integer_projections": len(seen_projections), "exact_candidate_evaluations": evaluations,
              "best_metrics": best_metrics, "progress": records}
    print("FINAL_JSON " + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
