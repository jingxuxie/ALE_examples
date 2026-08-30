import concurrent.futures
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import sys
import time

import networkx as nx


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from contraction import assess, baseline_plan


def instance(rows, columns, family, seed, cap_bits=24):
    rng = random.Random(seed)
    honeycomb = nx.hexagonal_lattice_graph(rows, columns)
    nodes = sorted(honeycomb.nodes)
    labels = {node: index for index, node in enumerate(nodes)}
    edges = []
    vertex_count = len(nodes)
    for left, right in sorted(honeycomb.edges):
        if family == "balanced":
            dimension = 16
        elif family == "directional":
            dimension = 64 if left[0] != right[0] else 4
        else:
            dimension = rng.choices([4, 16, 64], weights=[0.30, 0.45, 0.25])[0]
        edges.append({"u": labels[left], "v": vertex_count, "dim": dimension})
        edges.append({"u": vertex_count, "v": labels[right], "dim": dimension})
        vertex_count += 1
    for node in (nodes[0], nodes[-1]):
        if honeycomb.degree[node] < 3:
            edges.append({"u": labels[node], "v": vertex_count, "dim": 4})
            vertex_count += 1
    permutation = list(range(vertex_count))
    rng.shuffle(permutation)
    rng.shuffle(edges)
    for edge in edges:
        edge["u"], edge["v"] = permutation[edge["u"]], permutation[edge["v"]]
    return {"n": vertex_count, "edges": edges, "memory_elements": 1 << cap_bits}


def build_case(specification):
    case_id, rows, columns, family, seed, cap_bits = specification
    data = instance(rows, columns, family, seed, cap_bits)
    started = time.monotonic()
    baseline = baseline_plan(data)
    result = assess(data, baseline)
    print(case_id, data["n"], round(result["log2_work"], 3), round(time.monotonic() - started, 2), flush=True)
    return {"id": case_id, "family": family, "instance": data,
            "baseline_work": result["work"], "baseline_plan": baseline,
            "baseline_runtime_seconds": time.monotonic() - started}


def main():
    for directory in ("evaluator/hidden", "attempts", "champions", "adversary"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    families = ["balanced", "directional", "inhomogeneous"]
    public = [instance(rows, columns, family, 62000 + family_index * 20 + number, 24)
              for family_index, family in enumerate(families)
              for number, (rows, columns) in enumerate([(3, 3), (4, 4)])]
    (ROOT / "participant" / "input" / "examples.json").write_text(json.dumps(public, indent=2) + "\n")
    specifications = [(f"{family}_{number}", rows, columns, family,
                       901287 + family_index * 407 + number * 37, cap)
                      for family_index, family in enumerate(families)
                      for number, (rows, columns, cap) in enumerate([(3, 5, 24), (4, 4, 24), (4, 5, 26), (5, 6, 28)])]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        cases = list(executor.map(build_case, specifications))
    payload = {"schema_version": 1, "target": {"geometric_speedup": 4,
               "worst_family_speedup": 1.1, "maximum_case_regression": 1.05}, "cases": cases}
    (ROOT / "evaluator" / "hidden" / "challenge.json").write_text(json.dumps(payload, indent=2) + "\n")
    status = {"concept": 1, "mode": "A_baseline_improvement", "status": "built",
              "target_frozen_before_attempt": True, "target": payload["target"],
              "baseline": {"core_score": 1.0, "worst_family_score": 1.0},
              "solvability": "unknown", "ratchet_generations": 0}
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n")


if __name__ == "__main__":
    main()
