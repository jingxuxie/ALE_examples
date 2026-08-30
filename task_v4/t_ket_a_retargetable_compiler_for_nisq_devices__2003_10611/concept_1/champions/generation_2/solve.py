#!/usr/bin/env python3
import json
import os
import subprocess
import sys


def valid_route(instance, route):
    if not isinstance(route, dict) or not isinstance(route.get("operations"), list):
        return False
    operations = route["operations"]
    if len(operations) > 30000:
        return False
    count = instance["n"]
    positions = instance["initial"][:]
    occupants = [0] * count
    for logical, physical in enumerate(positions):
        occupants[physical] = logical
    edges = {tuple(sorted((first, second))) for first, second, _ in instance["edges"]}
    previous = [-1] * count
    predecessors = []
    for index, (first, second) in enumerate(instance["gates"]):
        predecessors.append((previous[first], previous[second]))
        previous[first] = previous[second] = index
    completed = {-1}
    for operation in operations:
        if not isinstance(operation, list) or not operation:
            return False
        if operation[0] == "swap" and len(operation) == 3:
            first, second = operation[1:]
            if type(first) is not int or type(second) is not int:
                return False
            if not (0 <= first < count and 0 <= second < count):
                return False
            if tuple(sorted((first, second))) not in edges:
                return False
            occupants[first], occupants[second] = occupants[second], occupants[first]
            positions[occupants[first]] = first
            positions[occupants[second]] = second
        elif operation[0] == "gate" and len(operation) == 2:
            index = operation[1]
            if type(index) is not int or not 0 <= index < len(instance["gates"]) or index in completed:
                return False
            if any(predecessor not in completed for predecessor in predecessors[index]):
                return False
            first, second = [positions[logical] for logical in instance["gates"][index]]
            if tuple(sorted((first, second))) not in edges:
                return False
            completed.add(index)
        else:
            return False
    return len(completed) == len(instance["gates"]) + 1


def safe_route(instance):
    count = instance["n"]
    adjacency = [[] for _ in range(count)]
    for first, second, _ in instance["edges"]:
        adjacency[first].append(second)
        adjacency[second].append(first)
    positions = instance["initial"][:]
    occupants = [0] * count
    for logical, physical in enumerate(positions):
        occupants[physical] = logical
    operations = []
    for index, (logical_first, logical_second) in enumerate(instance["gates"]):
        source, target = positions[logical_first], positions[logical_second]
        parents = [-1] * count
        parents[source] = source
        pending = [source]
        for current in pending:
            if parents[target] >= 0:
                break
            for neighbor in adjacency[current]:
                if parents[neighbor] < 0:
                    parents[neighbor] = current
                    pending.append(neighbor)
        path = [target]
        while path[-1] != source:
            path.append(parents[path[-1]])
        path.reverse()
        for first, second in zip(path[:-2], path[1:-1]):
            occupants[first], occupants[second] = occupants[second], occupants[first]
            positions[occupants[first]] = first
            positions[occupants[second]] = second
            operations.append(["swap", first, second])
        operations.append(["gate", index])
    return {"operations": operations}


def main():
    instance = json.load(sys.stdin)
    directory = os.path.dirname(os.path.abspath(__file__))
    executable = os.path.join(directory, "router")
    fields = [str(instance["n"]), str(len(instance["edges"])), str(len(instance["gates"]))]
    for first, second, weight in instance["edges"]:
        fields.extend((str(first), str(second), str(round(weight * 10000))))
    fields.extend(map(str, instance["initial"]))
    for first, second in instance["gates"]:
        fields.extend((str(first), str(second)))
    try:
        result = subprocess.run([executable], input=" ".join(fields), text=True,
                                stdout=subprocess.PIPE, check=True, timeout=9.8)
        route = json.loads(result.stdout)
        if not valid_route(instance, route):
            route = safe_route(instance)
    except (OSError, subprocess.SubprocessError, ValueError):
        route = safe_route(instance)
    json.dump(route, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
