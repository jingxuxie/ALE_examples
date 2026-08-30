import argparse
from collections import deque
import json
from pathlib import Path


def shortest_path(adjacency, start, finish):
    queue = deque([start])
    parents = {start: None}
    while queue:
        current = queue.popleft()
        if current == finish:
            path = []
            while current is not None:
                path.append(current)
                current = parents[current]
            return path[::-1]
        for neighbor in adjacency[current]:
            if neighbor not in parents:
                parents[neighbor] = current
                queue.append(neighbor)
    raise ValueError("disconnected architecture")


def remote_cnot(adjacency, control, target):
    path = shortest_path(adjacency, control, target)
    swaps = list(zip(path[:-2], path[1:-1]))
    gates = []
    for first, second in swaps:
        gates.extend([[first, second], [second, first], [first, second]])
    gates.append([path[-2], path[-1]])
    for first, second in reversed(swaps):
        gates.extend([[first, second], [second, first], [first, second]])
    return gates


def synthesize_case(case, include_parities=True):
    size = case["n"]
    adjacency = [[] for _ in range(size)]
    for first, second in case["edges"]:
        adjacency[first].append(second)
        adjacency[second].append(first)
    for neighbors in adjacency:
        neighbors.sort()
    routed = {
        (control, target): remote_cnot(adjacency, control, target)
        for control in range(size)
        for target in range(size)
        if control != target
    }
    gates = []
    if include_parities:
        for mask in case["required_parities"]:
            support = [wire for wire in range(size) if (mask >> wire) & 1]
            target = support[0]
            compute = []
            for control in support[1:]:
                compute.extend(routed[control, target])
            gates.extend(compute)
            gates.extend(reversed(compute))
    rows = case["target_rows"][:]
    elimination = []

    def add(control, target):
        rows[target] ^= rows[control]
        elimination.append((control, target))

    for column in range(size):
        pivot = next(row for row in range(column, size) if (rows[row] >> column) & 1)
        if pivot != column:
            add(pivot, column)
            add(column, pivot)
            add(pivot, column)
        for row in range(size):
            if row != column and (rows[row] >> column) & 1:
                add(column, row)
    if rows != [1 << wire for wire in range(size)]:
        raise ValueError("noninvertible target")
    for control, target in reversed(elimination):
        gates.extend(routed[control, target])
    return gates


def synthesize(suite):
    return {
        "schema_version": 1,
        "circuits": {
            case["id"]: synthesize_case(case) for case in suite["instances"]
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parents[1] / "input" / "instances.json")
    parser.add_argument("--output", type=Path, default=Path("submission/witness.json"))
    arguments = parser.parse_args()
    witness = synthesize(json.loads(arguments.input.read_text()))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(witness, separators=(",", ":")) + "\n")
    print(json.dumps({"output": str(arguments.output), "counts": {name: len(gates) for name, gates in witness["circuits"].items()}}))


if __name__ == "__main__":
    main()
