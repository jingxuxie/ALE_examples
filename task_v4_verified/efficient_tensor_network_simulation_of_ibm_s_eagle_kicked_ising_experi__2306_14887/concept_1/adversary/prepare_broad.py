import concurrent.futures
import json
from pathlib import Path
import random
import sys

import networkx as nx


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from contraction import assess, baseline_plan


def build(specification):
    case_id, rows, columns, family, periodic, bits, seed = specification
    generator = random.Random(seed)
    graph = nx.hexagonal_lattice_graph(rows, columns, periodic=periodic)
    labels = {node: index for index, node in enumerate(sorted(graph.nodes))}
    edges = []
    count = len(labels)
    for left, right in sorted(graph.edges):
        if family == "balanced":
            dimension = 16
        elif family == "directional":
            dimension = 64 if left[0] != right[0] else 4
        else:
            dimension = generator.choices([4, 16, 64], weights=[0.3, 0.45, 0.25])[0]
        edges.extend([{"u": labels[left], "v": count, "dim": dimension},
                      {"u": count, "v": labels[right], "dim": dimension}])
        count += 1
    permutation = list(range(count))
    generator.shuffle(permutation)
    generator.shuffle(edges)
    for edge in edges:
        edge["u"], edge["v"] = permutation[edge["u"]], permutation[edge["v"]]
    instance = {"n": count, "edges": edges, "memory_elements": 1 << bits}
    plan = baseline_plan(instance)
    metrics = assess(instance, plan)
    result = {"id": case_id, "family": family, "periodic": periodic, "memory_bits": bits,
              "instance": instance, "baseline_work": metrics["work"], "baseline_plan": plan}
    print(case_id, count, round(metrics["log2_work"], 3), flush=True)
    return result


if __name__ == "__main__":
    specifications = []
    for periodic in (False, True):
        for family_index, family in enumerate(("balanced", "directional", "inhomogeneous")):
            for shape_index, (rows, columns, bits) in enumerate(((3, 4, 20), (4, 4, 22), (5, 4, 24), (5, 6, 24))):
                case_id = f"{'periodic' if periodic else 'open'}_{family}_{shape_index}"
                specifications.append((case_id, rows, columns, family, periodic, bits,
                                       681883 + 12345 * periodic + 513 * family_index + 391 * shape_index))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        cases = list(pool.map(build, specifications))
    payload = {"purpose": "private post-champion stress pool; not part of the first fixed target",
               "scientific_axes": ["resident-memory pressure", "bond anisotropy", "periodic heavy-hex cells"],
               "cases": cases}
    (ROOT / "adversary" / "broad_challenge.json").write_text(json.dumps(payload, indent=2) + "\n")
