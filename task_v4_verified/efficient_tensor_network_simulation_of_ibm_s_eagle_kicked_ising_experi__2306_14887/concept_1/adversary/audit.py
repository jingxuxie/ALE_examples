import importlib.util
import itertools
import json
import math
from pathlib import Path
import random
import sys

import networkx as nx
import numpy as np
import opt_einsum as oe


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from contraction import assess, greedy

specification = importlib.util.spec_from_file_location("trusted_evaluator", ROOT / "evaluator" / "evaluate.py")
trusted = importlib.util.module_from_spec(specification)
specification.loader.exec_module(trusted)


def materialize(instance, plan, arrays):
    original_labels = [[index for index, edge in enumerate(instance["edges"]) if vertex in (edge["u"], edge["v"])]
                       for vertex in range(instance["n"])]
    total = 0.0
    for assignment in itertools.product(*(range(instance["edges"][index]["dim"]) for index in plan["slices"])):
        fixed = dict(zip(plan["slices"], assignment))
        live = {}
        for vertex, labels in enumerate(original_labels):
            selector = tuple(fixed.get(index, slice(None)) for index in labels)
            live[vertex] = (arrays[vertex][selector], [index for index in labels if index not in fixed])
        for step, (left, right) in enumerate(plan["merges"]):
            left_array, left_labels = live.pop(left)
            right_array, right_labels = live.pop(right)
            common = sorted(set(left_labels).intersection(right_labels))
            result = np.tensordot(left_array, right_array,
                                  axes=([left_labels.index(index) for index in common],
                                        [right_labels.index(index) for index in common]))
            result_labels = [index for index in left_labels + right_labels if index not in common]
            live[instance["n"] + step] = (result, result_labels)
        total += float(next(iter(live.values()))[0])
    return total


def main():
    rng = random.Random(932)
    numpy_rng = np.random.default_rng(451)
    comparisons = 0
    maximum_error = 0.0
    rejected = 0
    graphs = [nx.path_graph(5), nx.cycle_graph(6), nx.complete_bipartite_graph(2, 3), nx.star_graph(3)]
    for graph in graphs:
        instance = {"n": len(graph), "edges": [{"u": left, "v": right, "dim": rng.choice([2, 4])}
                     for left, right in graph.edges], "memory_elements": 2 ** 30}
        labels = [[index for index, edge in enumerate(instance["edges"]) if vertex in (edge["u"], edge["v"])]
                  for vertex in range(instance["n"])]
        arrays = [numpy_rng.normal(size=tuple(instance["edges"][index]["dim"] for index in indices)) for indices in labels]
        arguments = []
        for array, indices in zip(arrays, labels):
            arguments.extend([array, indices])
        exact = float(oe.contract(*arguments, [], optimize="optimal"))
        for repetition in range(10):
            slices = rng.sample(range(len(instance["edges"])), repetition % 3)
            plan = greedy(instance, slices, repetition, 2.0)
            fast = assess(instance, plan)
            independent = trusted.checked_cost(instance, plan)
            assert fast["work"] == independent["work"]
            assert fast["peak_elements"] == independent["peak_elements"]
            actual = materialize(instance, plan, arrays)
            error = abs(actual - exact) / max(1, abs(exact))
            assert error < 2e-12
            maximum_error = max(maximum_error, error)
            comparisons += 1
        invalid = [dict(plan, slices=[0, 0]), dict(plan, slices=[True]),
                   dict(plan, merges=plan["merges"][:-1]),
                   dict(plan, merges=[[0, 0]] + plan["merges"][1:]),
                   dict(plan, slices=[-1])]
        for bad_plan in invalid:
            try:
                trusted.checked_cost(instance, bad_plan)
            except ValueError:
                rejected += 1
            else:
                raise AssertionError("invalid plan accepted")
    payload = {"independent_cost_and_numeric_contraction_checks": comparisons,
               "maximum_relative_numeric_disagreement": maximum_error,
               "malformed_plans_rejected": rejected, "passed": True}
    (ROOT / "evaluator" / "hidden" / "audit.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
