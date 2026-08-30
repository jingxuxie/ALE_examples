import copy
import math
import random
import time

import numpy as np

from core import LOCAL_WORDS, circuit_weights, score_metrics, summarize


def grid_edges(rows, columns, offset=0):
    edges = []
    for row in range(rows):
        for column in range(columns):
            qubit = offset + row * columns + column
            if row + 1 < rows:
                edges.append([qubit, qubit + columns])
            if column + 1 < columns:
                edges.append([qubit, qubit + 1])
    return edges


def hardware():
    return [
        {"id": "ladder16", "n": 16, "edges": grid_edges(2, 8),
         "description": "Open 2 by 8 ladder; row-major labels."},
        {"id": "grid20", "n": 20, "edges": grid_edges(4, 5),
         "description": "Open 4 by 5 rectangular grid; row-major labels."},
        {"id": "bridge18", "n": 18,
         "edges": grid_edges(3, 3) + grid_edges(3, 3, 9) + [[4, 13]],
         "description": "Two open 3 by 3 grids, labels 0..8 and 9..17, linked only at their centers 4--13."},
    ]


def matching(family, rng, maximum=None):
    best = []
    for _ in range(5):
        shuffled = list(family["edges"])
        rng.shuffle(shuffled)
        occupied = set()
        selected = []
        for first, second in shuffled:
            if first not in occupied and second not in occupied:
                selected.append([first, second] if rng.randrange(2) else [second, first])
                occupied.update((first, second))
        if len(selected) > len(best):
            best = selected
    if maximum is not None and len(best) > maximum:
        rng.shuffle(best)
        best = best[:maximum]
    return best


def random_layers(family, rng):
    layers = [{"local": [rng.choice(LOCAL_WORDS) for _ in range(family["n"])],
               "cx": matching(family, rng)} for _ in range(family["max_rounds"])]
    excess = sum(len(layer["cx"]) for layer in layers) - family["max_cx"]
    while excess > 0:
        layer = rng.choice(layers)
        if layer["cx"]:
            del layer["cx"][rng.randrange(len(layer["cx"]))]
            excess -= 1
    return layers


def mutate(layers, family, rng):
    child = [{"local": layer["local"][:], "cx": [gate[:] for gate in layer["cx"]]} for layer in layers]
    layer_index = rng.randrange(len(child))
    layer = child[layer_index]
    choice = rng.random()
    if choice < 0.65:
        for _ in range(1 if rng.random() < 0.8 else rng.randint(2, 5)):
            qubit = rng.randrange(family["n"])
            layer["local"][qubit] = rng.choice(LOCAL_WORDS)
    elif choice < 0.82 and layer["cx"]:
        rng.choice(layer["cx"]).reverse()
    elif choice < 0.96:
        elsewhere = sum(len(entry["cx"]) for index, entry in enumerate(child) if index != layer_index)
        layer["cx"] = matching(family, rng, family["max_cx"] - elsewhere)
    elif len(child) > 1:
        second_index = rng.randrange(len(child))
        child[layer_index], child[second_index] = child[second_index], child[layer_index]
    return child


def energy(weights, targets):
    value = 0.0
    for strata in weights:
        for name, samples in zip(("single", "double"), strata):
            deficits = np.maximum(0, targets["min_" + name] - samples.astype(float))
            value += float((deficits * deficits).sum())
            value += 0.035 * float(np.exp(-0.8 * (samples.astype(float) - targets["min_" + name])).sum())
            mean_gap = max(0.0, targets["mean_" + name + "_milli"] / 1000 - float(samples.mean()))
            value += 20.0 * mean_gap * mean_gap
    return value


def search(family, seed, iterations, checkpoint=None):
    rng = random.Random(seed)
    started = time.perf_counter()
    targets = family["targets"]
    best = None
    best_energy = math.inf
    pool = []
    accepted = 0
    first_pass = None
    for iteration in range(iterations):
        if iteration < 32 or iteration % 1200 == 0:
            candidate = random_layers(family, rng)
        else:
            parent = rng.choice(pool[:min(len(pool), 12)])[1]
            candidate = mutate(parent, family, rng)
        weights = circuit_weights(family["n"], candidate)
        candidate_energy = energy(weights, targets)
        if not pool or candidate_energy < pool[-1][0] or (iteration % 80 == 0):
            pool.append((candidate_energy, candidate))
            pool.sort(key=lambda entry: entry[0])
            pool = pool[:24]
            accepted += 1
        if candidate_energy < best_energy:
            best_energy = candidate_energy
            metrics = summarize(family["n"], weights)
            score, failed = score_metrics(metrics, targets)
            best = {"family": family["id"], "layers": copy.deepcopy(candidate)}
            if not failed and first_pass is None:
                first_pass = iteration + 1
            if checkpoint is not None:
                checkpoint(best, metrics, iteration + 1, score, first_pass)
        if first_pass is not None and iteration >= first_pass + 1500:
            break
    metrics = summarize(family["n"], circuit_weights(family["n"], best["layers"]))
    score, failed = score_metrics(metrics, targets)
    return best, {"seed": str(seed), "iterations": iteration + 1, "accepted": accepted,
                  "runtime_seconds": time.perf_counter() - started, "energy": best_energy,
                  "core_score": score, "failed": failed, "first_pass_iteration": first_pass,
                  "metrics": metrics}
