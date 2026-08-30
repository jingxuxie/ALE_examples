import argparse
import ctypes
import json
import math
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parents[1] / "participant"
sys.path.insert(0, str(PARTICIPANT / "input"))
from router import hardware, relabelings, route, settings, transform
from validation import InvalidWitness, validate
from benchmark import evaluate_witness


def integers(values):
    values = list(values)
    return (ctypes.c_int * len(values))(*values)


class FastRouter:
    def __init__(self, graph):
        self.graph = graph
        self.count, self.edges = hardware(graph)
        self.library = ctypes.CDLL(str(ROOT / "router_fast.so"))
        self.library.setup.argtypes = [ctypes.c_int] + [ctypes.POINTER(ctypes.c_int)] * 3
        self.library.evaluate.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int),
                                         ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        physicals, ranks = [], []
        for name, logical, physical in relabelings(16):
            physicals.extend(physical)
            ordered = sorted(range(len(self.edges)), key=lambda index: tuple(sorted(
                physical[node] for node in self.edges[index])))
            for tie in range(3):
                ranked = ordered[:]
                if tie == 1:
                    random.Random(1729).shuffle(ranked)
                elif tie == 2:
                    ranked.reverse()
                rank = [0] * len(self.edges)
                for index, edge in enumerate(ranked):
                    rank[edge] = index
                ranks.extend(rank)
        self.library.setup(len(self.edges), integers(node for edge in self.edges for node in edge),
                           integers(physicals), integers(ranks))
        self.setting_ids = [family * 18 + variant for family in (0, 1, 2, 4, 5)
                            for variant in range(18)]

    def evaluate(self, gates, ids=None):
        ids = self.setting_ids if ids is None else ids
        output = integers([0] * len(ids))
        self.library.evaluate(len(gates), integers(node for gate in gates for node in gate),
                              len(ids), integers(ids), output)
        return list(output)


def schedule_witness(graph, schedule):
    occupants = list(range(16))
    position = list(range(16))
    gates, operations = [], []
    for kind, left, right in schedule:
        if kind == "swap":
            first, second = occupants[left], occupants[right]
            occupants[left], occupants[right] = second, first
            position[first], position[second] = right, left
            operations.append([kind, left, right])
        else:
            gates.append([occupants[left], occupants[right]])
            operations.append(["gate", len(gates) - 1, left, right])
    return {"version": 1, "hardware": graph, "gates": gates, "route": operations,
            "final_mapping": position}


def random_schedule(generator, edges, gate_count, swaps, style):
    if style == "initial":
        slots = Counter({0: swaps})
    elif style == "phases":
        phase_count = generator.randint(2, 4)
        slots = Counter(generator.randrange(phase_count) * gate_count // phase_count
                        for index in range(swaps))
    elif style == "early":
        slots = Counter(generator.randrange(max(1, gate_count // 4)) for index in range(swaps))
    else:
        slots = Counter(generator.randrange(gate_count) for index in range(swaps))
    schedule = []
    occupants = list(range(16))
    previous = [-1] * 16
    coverage = [0] * 16
    pairs = Counter()
    last_swap = None
    for index in range(gate_count):
        for unused in range(slots[index]):
            allowed = [edge for edge in edges if edge != last_swap]
            left, right = generator.choice(allowed)
            occupants[left], occupants[right] = occupants[right], occupants[left]
            schedule.append(("swap", left, right))
            last_swap = (left, right)
        allowed, weights = [], []
        for left, right in edges:
            first, second = occupants[left], occupants[right]
            pair = tuple(sorted((first, second)))
            if previous[first] == previous[second] and previous[first] >= 0:
                continue
            if pairs[pair] >= 8:
                continue
            allowed.append((left, right))
            weights.append(1.0 / (1 + coverage[first] + coverage[second]) ** 2)
        if not allowed:
            return None
        left, right = generator.choices(allowed, weights)[0]
        first, second = occupants[left], occupants[right]
        previous[first] = previous[second] = index
        coverage[first] += 1
        coverage[second] += 1
        pairs[tuple(sorted((first, second)))] += 1
        schedule.append(("gate", left, right))
    return schedule


def objective(counts, swaps, gate_count):
    threshold = max(2.5 * swaps, swaps + 16, 1.35 * swaps + gate_count * 0.35 / 3)
    ordered = sorted(counts)
    return ordered[0] / threshold + sum(min(value, threshold) for value in ordered[:12]) / (1200 * threshold)


def validate_fast(graph, samples):
    fast = FastRouter(graph)
    generator = random.Random(9927)
    tested = 0
    started = time.monotonic()
    while tested < samples:
        schedule = random_schedule(generator, fast.edges, 96, 12, "initial")
        witness = schedule_witness(graph, schedule)
        try:
            validate(witness)
        except InvalidWitness:
            continue
        values = fast.evaluate(witness["gates"], list(range(108)))
        expected = []
        for name, logical, physical in relabelings(16):
            gates, edges, initial = transform(witness["gates"], fast.edges, logical, physical)
            for setting in settings():
                expected.append(route(gates, 16, edges, initial, setting)["swaps"])
        mismatches = [(index, actual, correct) for index, (actual, correct)
                      in enumerate(zip(values, expected)) if actual != correct]
        print("compare", graph, tested, "min", min(values), "mismatches", mismatches, flush=True)
        if mismatches:
            (ROOT / "mismatch.json").write_text(json.dumps(witness))
            raise RuntimeError("fast router mismatch")
        tested += 1
    print("verified", tested * 108, "routes in", time.monotonic() - started, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", default="ring16")
    parser.add_argument("--check", type=int, default=0)
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--gates", type=int, default=80)
    parser.add_argument("--swaps", type=int, default=8)
    parser.add_argument("--style", default="initial")
    parser.add_argument("--tag", default="search")
    arguments = parser.parse_args()
    if arguments.check:
        validate_fast(arguments.graph, arguments.check)
        return
    fast = FastRouter(arguments.graph)
    generator = random.Random(arguments.seed)
    started = time.monotonic()
    best_score = -1
    count = valid = 0
    while time.monotonic() - started < arguments.seconds:
        count += 1
        schedule = random_schedule(generator, fast.edges, arguments.gates, arguments.swaps, arguments.style)
        if schedule is None:
            continue
        witness = schedule_witness(arguments.graph, schedule)
        try:
            validate(witness)
        except InvalidWitness:
            continue
        valid += 1
        counts = fast.evaluate(witness["gates"])
        score = objective(counts, arguments.swaps, arguments.gates)
        if score > best_score:
            best_score = score
            (ROOT / (arguments.tag + ".json")).write_text(json.dumps(witness, indent=2) + "\n")
            print("best", count, valid, "score", round(score, 5), "min", min(counts),
                  "families", [min(counts[index:index+18]) for index in range(0, 90, 18)],
                  "mean", round(sum(counts)/len(counts), 2), "time", round(time.monotonic()-started, 1), flush=True)
    print("done", arguments.tag, count, valid, "best", best_score, flush=True)


if __name__ == "__main__":
    main()
