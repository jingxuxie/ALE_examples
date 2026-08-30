import argparse
from collections import deque
import json
from pathlib import Path
import sys


PARTICIPANT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PARTICIPANT_ROOT / "workspace"))
import checker


def shortest_path(neighbors, source, destination):
    parents = {source: None}
    queue = deque([source])
    while queue:
        current = queue.popleft()
        if current == destination:
            path = []
            while current is not None:
                path.append(current)
                current = parents[current]
            return list(reversed(path))
        for neighbor in neighbors[current]:
            if neighbor not in parents:
                parents[neighbor] = current
                queue.append(neighbor)
    raise ValueError("Disconnected hardware.")


def routed_cx(neighbors, control, target):
    path = shortest_path(neighbors, control, target)
    swaps = list(zip(path[:-2], path[1:-1]))
    gates = []
    for first, second in swaps:
        gates.extend(([first, second], [second, first], [first, second]))
    gates.append([path[-2], path[-1]])
    for first, second in reversed(swaps):
        gates.extend(([first, second], [second, first], [first, second]))
    return gates


def synthesize(target):
    qubit_count = target["n_qubits"]
    rows = checker.matrix_rows(target["matrix"])
    elimination = []
    for column in range(qubit_count):
        if not ((rows[column] >> column) & 1):
            pivot = next(position for position in range(column + 1, qubit_count) if (rows[position] >> column) & 1)
            rows[column] ^= rows[pivot]
            elimination.append([pivot, column])
        for destination in range(qubit_count):
            if destination != column and ((rows[destination] >> column) & 1):
                rows[destination] ^= rows[column]
                elimination.append([column, destination])
    if rows != [1 << qubit for qubit in range(qubit_count)]:
        raise ValueError("Gaussian elimination failed.")
    neighbors = [[] for qubit in range(qubit_count)]
    for control, destination, duration in target["native_cx"]:
        neighbors[control].append(destination)
    neighbors = [sorted(adjacent) for adjacent in neighbors]
    gates = []
    for control, destination in reversed(elimination):
        gates.extend(routed_cx(neighbors, control, destination))
    return gates


def main():
    parser = argparse.ArgumentParser(description="Weak exact Gaussian-elimination baseline with explicit native SWAP routing.")
    parser.add_argument("--input", type=Path, default=PARTICIPANT_ROOT / "input" / "instances.json")
    parser.add_argument("--output", type=Path, default=Path("solution.json"))
    arguments = parser.parse_args()
    suite = checker.validate_instances(checker.load_json_file(arguments.input))
    solution = {"schema_version": 1, "circuits": {target["name"]: synthesize(target) for target in suite["targets"]}}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(solution, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    report = checker.evaluate_document(solution, suite)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["valid"] and all(result["correct"] for result in report["per_target"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
