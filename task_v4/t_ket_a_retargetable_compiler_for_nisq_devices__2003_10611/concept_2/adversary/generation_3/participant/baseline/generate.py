import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "input"))

from router import hardware
from validation import InvalidWitness, validate


def inverse_candidate(seed, graph="grid16", gate_count=96, swap_count=24):
    generator = random.Random(seed)
    count, edges = hardware(graph)
    occupants = list(range(count))
    position = list(range(count))
    gates, operations = [], []
    previous = [-1] * count
    coverage = [0] * count
    pair_counts = Counter()
    swap_slots = Counter(generator.randrange(gate_count) for _ in range(swap_count))
    for index in range(gate_count):
        for _ in range(swap_slots[index]):
            left, right = generator.choice(edges)
            first, second = occupants[left], occupants[right]
            occupants[left], occupants[right] = second, first
            position[first], position[second] = right, left
            operations.append(["swap", left, right])
        allowed = []
        for left, right in edges:
            first, second = occupants[left], occupants[right]
            pair = tuple(sorted((first, second)))
            if previous[first] == previous[second] and previous[first] != -1:
                continue
            if pair_counts[pair] >= 8:
                continue
            weight = 1.0 / (1 + coverage[first] + coverage[second]) ** 2
            allowed.append(((left, right), weight))
        if not allowed:
            raise InvalidWitness("generator exhausted admissible gates")
        left, right = generator.choices([edge for edge, _ in allowed],
                                         weights=[weight for _, weight in allowed])[0]
        if generator.random() < 0.5:
            left, right = right, left
        first, second = occupants[left], occupants[right]
        gates.append([first, second])
        operations.append(["gate", index, left, right])
        previous[first] = previous[second] = index
        coverage[first] += 1
        coverage[second] += 1
        pair_counts[tuple(sorted((first, second)))] += 1
    return {"version": 1, "hardware": graph, "gates": gates,
            "route": operations, "final_mapping": position}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    for seed in range(1000):
        witness = inverse_candidate(seed)
        try:
            validate(witness)
        except InvalidWitness:
            continue
        arguments.output.write_text(json.dumps(witness, indent=2) + "\n")
        print(json.dumps({"seed": seed, "output": str(arguments.output)}))
        return
    raise RuntimeError("could not generate a valid baseline")


if __name__ == "__main__":
    main()
