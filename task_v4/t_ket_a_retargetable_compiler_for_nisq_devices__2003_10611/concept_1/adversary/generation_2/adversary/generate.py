import argparse
import collections
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import sys
import time


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ("chain", "ring", "grid", "ladder", "tree", "modular")
ORIGINAL_SHA256 = "944d86402ef50921f7c8aa4b047c71734dce5e8dad7ce29e5712c7bb7dc03fd3"


def module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(loaded)
    return loaded


BASELINE = module("g2_reference", ROOT / "participant/baseline/solve.py")
CHECKER = module("g2_checker", ROOT / "evaluator/routing.py")


def architecture(family, generator):
    if family in ("chain", "ring"):
        count = generator.choice((16, 20, 24, 28))
        edges = [(index, index + 1) for index in range(count - 1)]
        if family == "ring":
            edges.append((count - 1, 0))
    elif family == "grid":
        rows, columns = generator.choice(((4, 4), (4, 5), (4, 6)))
        count = rows * columns
        edges = [(row * columns + column, row * columns + column + 1)
                 for row in range(rows) for column in range(columns - 1)]
        edges += [(row * columns + column, (row + 1) * columns + column)
                  for row in range(rows - 1) for column in range(columns)]
    elif family == "ladder":
        width = generator.choice((8, 10, 12, 14))
        count = 2 * width
        edges = [(index, index + 1) for index in range(width - 1)]
        edges += [(width + index, width + index + 1) for index in range(width - 1)]
        edges += [(index, width + index) for index in range(width)]
    elif family == "tree":
        count = 28
        edges = [(index, (index - 1) // 2) for index in range(1, count)]
    else:
        width = generator.choice((5, 6, 7))
        count = 4 * width
        edges = []
        for block in range(4):
            base = block * width
            edges.extend((base + index, base + (index + 1) % width) for index in range(width))
            edges.append((base, base + width // 2))
        edges.extend((block * width - 1, block * width) for block in range(1, 4))
    return count, edges


def path_edges(path):
    return {tuple(sorted(edge)) for edge in zip(path, path[1:])}


def paths(adjacency, length, generator, limit=2400):
    result = []
    starts = list(range(len(adjacency)))
    generator.shuffle(starts)
    neighbors = [list(values) for values in adjacency]
    for values in neighbors:
        generator.shuffle(values)

    def extend(path):
        if len(result) >= limit:
            return
        if len(path) == length:
            result.append(tuple(path))
            return
        for neighbor in neighbors[path[-1]]:
            if neighbor not in path:
                extend(path + [neighbor])

    for start in starts:
        extend([start])
        if len(result) >= limit:
            break
    return result


def find_regions(count, edges, generator):
    adjacency = [[] for _ in range(count)]
    for first, second in edges:
        adjacency[first].append(second)
        adjacency[second].append(first)
    distances = []
    for source in range(count):
        distance = [count + 1] * count
        distance[source] = 0
        pending = collections.deque([source])
        while pending:
            current = pending.popleft()
            for neighbor in adjacency[current]:
                if distance[neighbor] > distance[current] + 1:
                    distance[neighbor] = distance[current] + 1
                    pending.append(neighbor)
        distances.append(distance)
    source_first = [(path, path_edges(path)) for path in paths(adjacency, 5, generator)]
    source_second = [(path, path_edges(path)) for path in paths(adjacency, 4, generator)]
    destinations = paths(adjacency, 9, generator)
    generator.shuffle(destinations)
    choices = []
    for destination in destinations[:250]:
        forbidden = path_edges(destination)
        first = [(sum(distances[source][target] for source, target in zip(path, destination[:5])), path)
                 for path, selected in source_first if not selected & forbidden]
        second = [(sum(distances[source][target] for source, target in zip(path, destination[5:])), path)
                  for path, selected in source_second if not selected & forbidden]
        for first_cost, first_path in sorted(first)[:12]:
            for second_cost, second_path in sorted(second)[:20]:
                if not set(first_path) & set(second_path):
                    choices.append((first_cost + second_cost, first_path, second_path, destination))
                    break
    if not choices:
        return None
    choices.sort()
    return generator.choice(choices[:min(6, len(choices))])[1:]


def tree_route(count, edges, initial, goals, generator):
    weights = {tuple(sorted((first, second))): weight for first, second, weight in edges}
    desired = {physical: logical for logical, physical in goals.items()}
    best = None
    for trial in range(24):
        parents = list(range(count))

        def component(vertex):
            while parents[vertex] != vertex:
                vertex = parents[vertex]
            return vertex

        tree = [set() for _ in range(count)]
        selected = sorted(edges, key=lambda edge: edge[2] * (1 + generator.random() * (0.05 if trial == 0 else 2.0)))
        for first, second, _ in selected:
            first_root, second_root = component(first), component(second)
            if first_root != second_root:
                parents[first_root] = second_root
                tree[first].add(second)
                tree[second].add(first)
        positions = initial[:]
        occupants = [0] * count
        for logical, physical in enumerate(positions):
            occupants[physical] = logical
        active = set(range(count))
        operations = []
        work = 0.0
        while len(active) > 1:
            choices = []
            for leaf in active:
                if len(tree[leaf] & active) != 1:
                    continue
                predecessor = {leaf: None}
                pending = collections.deque([leaf])
                while pending:
                    current = pending.popleft()
                    for neighbor in tree[current] & active:
                        if neighbor not in predecessor:
                            predecessor[neighbor] = current
                            pending.append(neighbor)
                sources = [positions[desired[leaf]]] if leaf in desired else [
                    physical for physical in active if occupants[physical] not in goals]
                for source in sources:
                    path = [source]
                    while path[-1] != leaf:
                        path.append(predecessor[path[-1]])
                    cost = sum(3 * weights[tuple(sorted(edge))] for edge in zip(path, path[1:]))
                    priority = cost * (1 + generator.random() * (0.0 if trial == 0 else 0.5))
                    choices.append((priority, cost, leaf, path))
            _, cost, leaf, path = min(choices)
            for first, second in zip(path, path[1:]):
                operations.append(["swap", first, second])
                occupants[first], occupants[second] = occupants[second], occupants[first]
                positions[occupants[first]] = first
                positions[occupants[second]] = second
            work += cost
            active.remove(leaf)
        if any(positions[logical] != physical for logical, physical in goals.items()):
            raise ValueError("partial token routing failed")
        if best is None or work < best[0]:
            best = (work, operations, positions, occupants)
    return best


def construct(family, seed, identifier):
    generator = random.Random(seed)
    count, graph = architecture(family, generator)
    regions = find_regions(count, graph, generator)
    if regions is None:
        return None
    first_path, second_path, destination = regions
    expensive = path_edges(first_path) | path_edges(second_path)
    cheap = path_edges(destination)
    edges = [[first, second, round(generator.uniform(2.68, 2.8) if tuple(sorted((first, second))) in expensive
                                    else generator.uniform(0.45, 0.51) if tuple(sorted((first, second))) in cheap
                                    else generator.uniform(0.46, 0.8), 4)] for first, second in graph]
    initial = list(range(count))
    generator.shuffle(initial)
    occupants = [0] * count
    for logical, physical in enumerate(initial):
        occupants[physical] = logical
    logical_order = [occupants[physical] for physical in first_path + second_path]
    goals = dict(zip(logical_order, destination))
    _, operations, positions, occupants = tree_route(count, edges, initial, goals, generator)
    gates = []
    phases = []
    total = generator.choice((216, 228, 240))
    native_count = total - 24
    native_lengths = [native_count // 4] * 4
    native_lengths[-1] += native_count - sum(native_lengths)

    def burst(physical_path, length, kind):
        start = len(gates)
        interactions = [(physical_path[index], physical_path[index + 1]) for index in range(3)]
        previous = None
        while len(gates) < start + length:
            selected = interactions[:]
            generator.shuffle(selected)
            for first, second in selected:
                if len(gates) >= start + length:
                    break
                if (first, second) == previous:
                    continue
                pair = [occupants[first], occupants[second]]
                if generator.random() < 0.5:
                    pair.reverse()
                operations.append(["gate", len(gates)])
                gates.append(pair)
                previous = (first, second)
        phases.append({"start": start, "end": len(gates), "kind": kind,
                       "logical_wires": sorted({logical for pair in gates[start:] for logical in pair})})

    for window, length in zip((destination[:4], destination[1:5], destination[5:9], destination[1:5]), native_lengths):
        burst(window, length, "coupled_dominant")
    for offset in (4, 5):
        first, second = destination[offset], destination[offset + 1]
        operations.append(["swap", first, second])
        occupants[first], occupants[second] = occupants[second], occupants[first]
        positions[occupants[first]] = first
        positions[occupants[second]] = second
        burst(destination[3:7] if offset == 4 else destination[4:8], 12, "coupled_overlap")
    relabel = list(range(count))
    generator.shuffle(relabel)
    case = {"id": identifier, "family": family, "n": count,
            "edges": [[relabel[first], relabel[second], weight] for first, second, weight in edges],
            "initial": [relabel[physical] for physical in initial], "gates": gates}
    witness = {"operations": [[operation[0], relabel[operation[1]], relabel[operation[2]]]
                               if operation[0] == "swap" else operation for operation in operations]}
    metrics = CHECKER.validate(case, witness)
    reference_answer = BASELINE.solve(case)
    reference = CHECKER.validate(case, reference_answer)
    improvement = 1 - metrics["cost"] / reference["cost"]
    initial_weights = {tuple(sorted((first, second))): weight for first, second, weight in case["edges"]}
    prefix_work = sum(initial_weights[tuple(sorted((case["initial"][first], case["initial"][second])))]
                      for first, second in gates[:native_count])
    metadata = {"seed": seed, "phases": phases, "active_wires": sorted(set(logical_order)),
                "native_prefix_gates": native_count, "native_prefix_work": prefix_work,
                "champion_prefix_improvement_upper_bound": 1 - prefix_work / reference["cost"],
                "witness_metrics": metrics, "baseline_metrics": reference,
                "witness_improvement": improvement,
                "distinct_interactions": len({tuple(sorted(pair)) for pair in gates})}
    if improvement < 0.50 or metadata["champion_prefix_improvement_upper_bound"] >= 0.30:
        return None
    if metadata["distinct_interactions"] < 10:
        return None
    return case, witness, reference_answer, metadata


def main():
    started = time.monotonic()
    if hashlib.sha256((ROOT / "participant/baseline/solve.py").read_bytes()).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("reference router is not the original baseline")
    targets = json.loads((ROOT / "targets.json").read_text())
    if (targets["core_target"], targets["worst_family_target"], targets["case_seconds"], targets["suite_seconds"]) != (0.4, 0.3, 12, 360):
        raise ValueError("fixed prelaunch contract changed")
    hidden = ROOT / "evaluator/hidden"
    hidden.mkdir(exist_ok=True)
    certificates = {}
    baseline = {}
    design = {}
    private_cases = []
    public_scores = {}
    search_counts = {}
    for family_index, family in enumerate(FAMILIES):
        for index in range(8):
            split = "public" if index < 2 else "hidden"
            identifier = f"{split}_g2_{family}_{index if split == 'public' else index - 2}"
            for trial in range(150):
                seed = 209748361 + family_index * 10000019 + index * 104729 + trial * 7919
                result = construct(family, seed, identifier)
                if result is not None:
                    break
            else:
                raise RuntimeError(f"no certificate-feasible coupled instance for {identifier}")
            case, witness, reference, metadata = result
            certificates[identifier] = {"case": case, "answer": witness, "baseline_answer": reference}
            baseline[identifier] = metadata["baseline_metrics"]
            design[identifier] = metadata
            search_counts[identifier] = trial + 1
            if split == "public":
                (ROOT / "participant/input" / f"{identifier}.json").write_text(json.dumps(case, indent=2) + "\n")
                public_scores[identifier] = baseline[identifier]
            else:
                private_cases.append(case)
            print(json.dumps({"id": identifier, "trials": trial + 1, "n": case["n"], "gates": len(case["gates"]),
                              "certificate_improvement": metadata["witness_improvement"],
                              "champion_quality_upper_bound": metadata["champion_prefix_improvement_upper_bound"]}), flush=True)
            (hidden / "certificates.json").write_text(json.dumps(certificates) + "\n")
            (ROOT / "adversary/design.json").write_text(json.dumps(design, indent=2) + "\n")
    manifest = {**targets, "baseline": baseline, "generation": 2, "frozen_before_fresh_launch": True,
                "minimum_certificate_improvement": min(record["witness_improvement"] for record in design.values()),
                "baseline_sha256": ORIGINAL_SHA256}
    (hidden / "cases.json").write_text(json.dumps(private_cases, indent=2) + "\n")
    (hidden / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "participant/input/baseline_scores.json").write_text(json.dumps(public_scores, indent=2) + "\n")
    (ROOT / "adversary/generation_report.json").write_text(json.dumps({"public": 12, "hidden": 36,
        "search_counts": search_counts, "wall_seconds": time.monotonic() - started,
        "quality_targets_not_retuned": True, "minimum_certificate_improvement": manifest["minimum_certificate_improvement"]}, indent=2) + "\n")


if __name__ == "__main__":
    main()
