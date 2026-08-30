import heapq
import importlib.util
import json
import math
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from model import baseline_order, graph_arrays, improvement, metrics


def make_case(seed, family, scale=1):
    rng = random.Random(seed)
    edges = []
    count = 0
    if family == "modular":
        groups = 18 * scale
        span = 18
        count = groups * span
        for group in range(groups):
            start = group * span
            for offset in range(span - 1):
                edges.append([start + offset, start + offset + 1, rng.choice([4, 8, 16, 32])])
            for left in range(span - 3):
                for right in rng.sample(range(left + 2, span), min(2, span - left - 2)):
                    if rng.random() < 0.38:
                        edges.append([start + left, start + right, rng.choice([8, 16, 32, 64])])
            if group and rng.random() < 0.5:
                predecessor = rng.randrange(group)
                edges.append([predecessor * span + rng.randrange(12, span), start + rng.randrange(5), 2])
    elif family == "wavefront":
        side = 20 * scale
        count = side * side
        for row in range(side):
            for column in range(side):
                source = row * side + column
                if row + 1 < side:
                    edges.append([source, source + side, 2 ** rng.randrange(2, 7)])
                if column + 1 < side:
                    edges.append([source, source + 1, 2 ** rng.randrange(2, 7)])
                if column + 2 < side and row + 1 < side and rng.random() < 0.15:
                    edges.append([source, source + side + 2, rng.choice([2, 4, 8])])
    elif family == "reconvergent":
        count = 2
        def branch(source, destination, depth):
            nonlocal count
            if depth == 0:
                edges.append([source, destination, 2 ** rng.randrange(2, 8)])
                return
            children = rng.randint(2, 4)
            for _ in range(children):
                entry, exit_node = count, count + 1
                count += 2
                width = 2 ** rng.randrange(2, 7)
                edges.extend([[source, entry, width], [exit_node, destination, width]])
                branch(entry, exit_node, depth - 1)
        branch(0, 1, 4 + (scale > 1))
    elif family == "heterogeneous":
        count = 420 * scale
        for node in range(count - 1):
            stop = min(count, node + rng.choice([12, 30, 80]))
            for destination in rng.sample(range(node + 1, stop), min(rng.randint(1, 3), stop - node - 1)):
                edges.append([node, destination, 2 ** rng.randrange(1, 8)])
    else:
        raise ValueError(family)
    nodes = [{"duration": 2 ** rng.randrange(0, 7), "workspace": rng.choice([0, 4, 8, 16, 32, 64, 128])} for _ in range(count)]
    permutation = list(range(count))
    rng.shuffle(permutation)
    shuffled = [None] * count
    for node, new_index in zip(nodes, permutation):
        shuffled[new_index] = node
    relabeled_edges = [[permutation[source], permutation[destination], width] for source, destination, width in edges]
    return {"id": f"{family}_{seed}", "family": family, "nodes": shuffled, "edges": relabeled_edges}


def portfolio(case, seed, trials=120):
    rng = random.Random(seed)
    successors, predecessors, incoming, outgoing, indegree = graph_arrays(case)
    base_order = baseline_order(case)
    before = metrics(case, base_order)
    best_order = base_order
    best_score = 1.0
    count = len(indegree)
    descendants = [0] * count
    critical = [0] * count
    for node in reversed(base_order):
        descendants[node] = 1 + sum(descendants[successor] for successor in set(successors[node]))
        critical[node] = case["nodes"][node]["duration"] + max([critical[successor] for successor in successors[node]] or [0])
    for trial in range(trials):
        degree = indegree.copy()
        ready = [node for node, value in enumerate(degree) if not value]
        coefficients = [rng.uniform(-2, 2) for _ in range(6)]
        jitter = [rng.gauss(0, 1) for _ in range(count)]
        order = []
        live = 0
        current_peak = 0
        preferred = set()
        while ready:
            def priority(node):
                data = case["nodes"][node]
                delta = outgoing[node] - incoming[node]
                footprint = live + max(0, delta) + data["workspace"]
                unlocked = sum(incoming[child] for child in set(successors[node]) if degree[child] == successors[node].count(child))
                static = (coefficients[0] * delta + coefficients[1] * data["workspace"] +
                          coefficients[2] * math.log2(descendants[node] + 1) * 16 +
                          coefficients[3] * math.log2(critical[node] + 1) * 16 +
                          coefficients[4] * unlocked + coefficients[5] * jitter[node] * 32)
                if trial % 4 == 0:
                    return (max(current_peak, footprint), static)
                if trial % 4 == 1:
                    return (0 if node in preferred else 1, static)
                if trial % 4 == 2:
                    return (0 if incoming[node] else 1, static)
                return (static, node)
            node = min(ready, key=priority)
            ready.remove(node)
            order.append(node)
            current_peak = max(current_peak, live + max(0, outgoing[node] - incoming[node]) + case["nodes"][node]["workspace"])
            live += outgoing[node] - incoming[node]
            preferred = set(successors[node])
            for successor in successors[node]:
                degree[successor] -= 1
                if not degree[successor]:
                    ready.append(successor)
        after = metrics(case, order)
        score = improvement(before, after)
        if after["peak"] * 20 <= before["peak"] * 21 and score > best_score:
            best_order, best_score = order, score
    return best_order, best_score


def main():
    cases = []
    schedules = {}
    baseline_schedules = {}
    baseline_metrics = {}
    search_log = []
    for family_index, family in enumerate(["modular", "wavefront", "reconvergent", "heterogeneous"]):
        pool = []
        for offset in range(7):
            seed = 240904643 + family_index * 1000 + offset
            case = make_case(seed, family)
            order, score = portfolio(case, seed ^ 782391, trials=72)
            search_log.append({"seed": seed, "family": family, "best_ratio": score, "nodes": len(case["nodes"])})
            pool.append((score, case, order))
            print(family, offset, len(case["nodes"]), round(score, 4), flush=True)
        pool.sort(key=lambda item: item[0], reverse=True)
        for score, case, order in pool[:4]:
            cases.append(case)
            schedules[case["id"]] = order
            baseline_schedules[case["id"]] = baseline_order(case)
            baseline_metrics[case["id"]] = metrics(case, baseline_schedules[case["id"]])
    workload_text = json.dumps({"cases": cases}, separators=(",", ":"))
    (ROOT / "participant" / "input" / "workloads.json").write_text(workload_text)
    (ROOT / "evaluator" / "hidden" / "workloads.json").write_text(workload_text)
    for path in [ROOT / "participant" / "baseline" / "metrics.json", ROOT / "evaluator" / "hidden" / "baseline_metrics.json"]:
        path.write_text(json.dumps(baseline_metrics, indent=2))
    (ROOT / "participant" / "baseline" / "schedules.json").write_text(json.dumps({"schedules": baseline_schedules}))
    destination = ROOT / "adversary" / "portfolio_witness"
    destination.mkdir(exist_ok=True)
    (destination / "schedules.json").write_text(json.dumps({"schedules": schedules}))
    (ROOT / "adversary" / "initial_search.json").write_text(json.dumps(search_log, indent=2))


if __name__ == "__main__":
    main()
