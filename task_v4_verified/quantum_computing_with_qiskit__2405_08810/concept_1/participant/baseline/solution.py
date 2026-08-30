import heapq
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from phase_model import check


def remote_sequence(path):
    if len(path) == 2:
        return [["cx", *path]]
    forward = list(zip(path[:-1], path[1:]))
    pairs = forward + forward[-2::-1] + forward[1:] + forward[-2:0:-1]
    return [["cx", control, target] for control, target in pairs]


def routes(instance):
    size = instance["n"]
    neighbors = [[] for unused in range(size)]
    weights = {}
    for control, target, weight, duration in instance["edges"]:
        neighbors[control].append((target, weight + 0.2 * duration))
        weights[control, target] = weight + 0.2 * duration
    sequences = {}
    costs = {}
    for source in range(size):
        queue = [(0, source, (source,))]
        distances = {}
        while queue:
            distance, current, path = heapq.heappop(queue)
            if current in distances:
                continue
            distances[current] = distance
            if current != source:
                sequence = remote_sequence(path)
                sequences[source, current] = sequence
                costs[source, current] = sum(weights[control, target] for kind, control, target in sequence)
            for neighbor, weight in neighbors[current]:
                if neighbor not in distances:
                    heapq.heappush(queue, (distance + weight, neighbor, path + (neighbor,)))
    return sequences, costs


def coordinates(rows, masks):
    pivots = {}
    for qubit, row in enumerate(rows):
        coefficients = 1 << qubit
        while row:
            pivot = row.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = row, coefficients
                break
            basis, mapped = pivots[pivot]
            row ^= basis
            coefficients ^= mapped
    result = []
    for mask in masks:
        coefficients = 0
        while mask:
            basis, mapped = pivots[mask.bit_length() - 1]
            mask ^= basis
            coefficients ^= mapped
        result.append(coefficients)
    return result


def dynamic_compile(instance, sequences, costs, seed):
    randomizer = random.Random(seed)
    size = instance["n"]
    rows = [1 << qubit for qubit in range(size)]
    remaining = dict(enumerate(instance["terms"]))
    operations = []
    history = []
    while remaining:
        present = {mask: qubit for qubit, mask in enumerate(rows)}
        for term, mask in list(remaining.items()):
            if mask in present:
                operations.append(["rz", present[mask], term])
                del remaining[term]
        if not remaining:
            break
        candidates = []
        transformed = coordinates(rows, list(remaining.values()))
        for (term, mask), coefficient in zip(remaining.items(), transformed):
            support = [qubit for qubit in range(size) if coefficient >> qubit & 1]
            for target in support:
                cost = sum(costs[control, target] for control in support if control != target)
                if seed:
                    cost *= randomizer.uniform(0.8, 1.25)
                candidates.append((cost, term, target, support))
        unused_cost, term, target, support = min(candidates)
        for control in support:
            if control != target:
                sequence = sequences[control, target]
                operations.extend(sequence)
                history.extend(sequence)
                for kind, native_control, native_target in sequence:
                    rows[native_target] ^= rows[native_control]
        operations.append(["rz", target, term])
        del remaining[term]
    operations.extend(reversed(history))
    return {"ops": operations}


def star_compile(instance, sequences, costs, seed):
    randomizer = random.Random(seed)
    size = instance["n"]
    groups = [[] for unused in range(size)]
    for term, mask in enumerate(instance["terms"]):
        support = [qubit for qubit in range(size) if mask >> qubit & 1]
        target = min(support, key=lambda qubit: sum(costs[control, qubit] for control in support if control != qubit) * randomizer.uniform(0.8, 1.2))
        groups[target].append((term, mask))
    operations = []
    for target, remaining in enumerate(groups):
        current = 1 << target
        while remaining:
            term, mask = min(remaining, key=lambda item: sum(costs[control, target] for control in range(size) if (current ^ item[1]) >> control & 1))
            difference = current ^ mask
            for control in range(size):
                if difference >> control & 1:
                    operations.extend(sequences[control, target])
            current = mask
            operations.append(["rz", target, term])
            remaining.remove((term, mask))
        difference = current ^ (1 << target)
        for control in range(size):
            if difference >> control & 1:
                operations.extend(sequences[control, target])
    return {"ops": operations}


def compile_circuit(instance):
    sequences, costs = routes(instance)
    candidates = [dynamic_compile(instance, sequences, costs, seed) for seed in (0, 17, 91)]
    candidates.extend(star_compile(instance, sequences, costs, seed) for seed in (0, 29))
    return min(candidates, key=lambda candidate: check(instance, candidate)["cost"])


def main():
    for line in sys.stdin:
        if line.strip():
            print(json.dumps(compile_circuit(json.loads(line)), separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
