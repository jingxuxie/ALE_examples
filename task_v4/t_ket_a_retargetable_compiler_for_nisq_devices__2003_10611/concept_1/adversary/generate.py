import importlib.util
import json
from pathlib import Path
import random
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "baseline"))
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from solve import solve
from routing import validate


def generate(family, seed, identifier):
    generator = random.Random(seed)
    if family in ("chain", "ring"):
        count = generator.choice([12, 16, 20, 24])
        edges = [(index, index + 1) for index in range(count - 1)]
        if family == "ring":
            edges.append((0, count - 1))
    elif family == "grid":
        rows, columns = generator.choice([(3, 4), (4, 4), (4, 5), (4, 6)])
        count = rows * columns
        edges = [(row * columns + column, row * columns + column + 1) for row in range(rows) for column in range(columns - 1)]
        edges += [(row * columns + column, (row + 1) * columns + column) for row in range(rows - 1) for column in range(columns)]
    elif family == "ladder":
        width = generator.choice([6, 8, 10, 12])
        count = 2 * width
        edges = [(index, index + 1) for index in range(width - 1)]
        edges += [(width + index, width + index + 1) for index in range(width - 1)]
        edges += [(index, width + index) for index in range(width)]
    elif family == "tree":
        count = generator.choice([15, 19, 23, 27])
        edges = [(index, (index - 1) // 2) for index in range(1, count)]
    else:
        module = generator.choice([4, 5, 6, 7])
        count = 4 * module
        edges = []
        for block in range(4):
            base = block * module
            edges += [(base + index, base + (index + 1) % module) for index in range(module)]
            if module >= 5:
                edges.append((base, base + module // 2))
        edges += [(module - 1, module), (2 * module - 1, 2 * module), (3 * module - 1, 3 * module)]
    relabel = list(range(count))
    generator.shuffle(relabel)
    weighted = [[relabel[first], relabel[second], round(generator.uniform(0.45, 2.8), 4)] for first, second in edges]
    initial = list(range(count))
    generator.shuffle(initial)
    wanted = generator.choice([96, 120, 144, 180, 216, 240])
    pattern = generator.randrange(4)
    gates = []
    labels = list(range(count))
    generator.shuffle(labels)
    while len(gates) < wanted:
        if pattern == 0:
            generator.shuffle(labels)
            gates.extend([labels[index], labels[index + 1]] for index in range(0, count - 1, 2))
        elif pattern == 1:
            offset = generator.randrange(1, max(2, count // 3))
            gates.extend([labels[index], labels[(index + offset) % count]] for index in range(count))
            if generator.random() < 0.35:
                generator.shuffle(labels)
        elif pattern == 2:
            hubs = generator.sample(range(count), 2)
            for logical in generator.sample(range(count), count):
                hub = hubs[logical % 2]
                if hub != logical:
                    gates.append([hub, logical])
        else:
            for first, second in generator.sample(edges, len(edges)):
                gates.append([labels[first], labels[second]])
            for _ in range(max(1, count // 5)):
                first, second = generator.sample(range(count), 2)
                labels[first], labels[second] = labels[second], labels[first]
    return {"id": identifier, "family": family, "n": count, "edges": weighted,
            "initial": initial, "gates": gates[:wanted]}


def main():
    families = ["chain", "ring", "grid", "ladder", "tree", "modular"]
    public = []
    hidden = []
    for family_index, family in enumerate(families):
        for case_index in range(2):
            public.append(generate(family, 3127 + 47 * family_index + case_index, f"public_{family}_{case_index}"))
        for case_index in range(6):
            hidden.append(generate(family, 8301941 + 997 * family_index + case_index * 131, f"heldout_{family}_{case_index}"))
    for case in public:
        (ROOT / "participant" / "input" / (case["id"] + ".json")).write_text(json.dumps(case, indent=2) + "\n")
    (ROOT / "evaluator" / "hidden" / "cases.json").write_text(json.dumps(hidden, indent=2) + "\n")
    baseline = {}
    for case in hidden + public:
        started = time.monotonic()
        answer = solve(case)
        metrics = validate(case, answer)
        metrics["seconds"] = time.monotonic() - started
        baseline[case["id"]] = metrics
        print(case["id"], round(metrics["cost"], 3), round(metrics["seconds"], 3), flush=True)
    manifest = {"generation": 1, "frozen_before_fresh_attempt": True,
                "core_target": 0.15, "worst_family_target": 0.08, "case_seconds": 8,
                "suite_seconds": 240, "baseline": baseline}
    (ROOT / "evaluator" / "hidden" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    summary = {case["id"]: baseline[case["id"]] for case in public}
    (ROOT / "participant" / "input" / "baseline_scores.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
