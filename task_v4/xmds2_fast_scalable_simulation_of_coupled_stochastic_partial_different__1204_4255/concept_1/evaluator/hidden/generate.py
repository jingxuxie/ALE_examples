import argparse
import importlib.util
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from model import check

FAMILIES = ["shared_bases", "layout_pressure", "unequal_fields", "version_epochs", "mixed_anisotropy"]


def instance(seed, family, dimensions=None):
    rng = random.Random(seed)
    dimensions = dimensions or rng.choice([4, 5, 6])
    count = rng.choice([2, 3, 4])
    sizes = [rng.choice([1, 2, 3, 4]) if family == "unequal_fields" else rng.choice([1, 1, 2]) for field in range(count)]
    capacity = max(sizes) + rng.randint(2, 5)
    base = [rng.randint(8, 28) for axis in range(dimensions)]
    if family in ("shared_bases", "mixed_anisotropy"):
        for axis in rng.sample(range(dimensions), dimensions // 2):
            base[axis] *= rng.randint(6, 14)
    axis_cost = [[[int(base[axis] * rng.uniform(0.7, 1.4)) + 1 for direction in range(2)] for axis in range(dimensions)] for layout in range(dimensions)]
    transpose_cost = [[0 if source == destination else rng.randint(30, 150) * (4 if family == "layout_pressure" else 1) for destination in range(dimensions)] for source in range(dimensions)]
    motifs = []
    for field in range(count):
        anchor = rng.randrange(1, 1 << dimensions)
        masks = [anchor ^ (1 << axis) for axis in rng.sample(range(dimensions), min(3, dimensions))]
        masks.extend([anchor, (1 << dimensions) - 1, 0])
        motifs.append([(mask, rng.randrange(dimensions)) for mask in masks])
    requests = []
    length = rng.randint(45, 85)
    for position in range(length):
        field = (position // rng.randint(2, 5)) % count if family == "shared_bases" else rng.randrange(count)
        mask, layout = rng.choice(motifs[field])
        if family == "layout_pressure":
            mask = motifs[field][position % 3][0]
            layout = (position // 3 + field) % dimensions
        if family == "mixed_anisotropy" and rng.random() < 0.16:
            mask, layout = rng.randrange(1 << dimensions), rng.randrange(dimensions)
        updates = []
        if family == "version_epochs" and position % rng.choice([7, 11, 13]) == 0 and position > 0:
            updates = rng.sample(range(count), rng.randint(1, count))
        elif family != "shared_bases" and rng.random() < 0.025:
            updates = [rng.randrange(count)]
        requests.append({"field": field, "mask": mask, "layout": layout, "updates": updates})
    return {"dimensions": dimensions, "sizes": sizes, "capacity": capacity, "axis_cost": axis_cost, "transpose_cost": transpose_cost, "requests": requests}


def main():
    spec = importlib.util.spec_from_file_location("baseline", ROOT / "participant" / "baseline" / "solve.py")
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    hidden = []
    public = []
    for family_number, family in enumerate(FAMILIES):
        for sample in range(6):
            seed = 42551204 + family_number * 1000 + sample
            case = instance(seed, family)
            result = check(case, baseline.plan(case))
            hidden.append({"id": f"{family}-{sample}", "family": family, "seed": seed, "instance": case, "baseline": result})
        for sample in range(2):
            public.append(instance(91234 + family_number * 100 + sample, family, dimensions=4))
    (ROOT / "evaluator" / "hidden" / "cases.json").write_text(json.dumps(hidden, separators=(",", ":")) + "\n")
    (ROOT / "participant" / "input" / "examples.jsonl").write_text("".join(json.dumps(case, separators=(",", ":")) + "\n" for case in public))
    print(json.dumps({"hidden_cases": len(hidden), "public_cases": len(public), "baseline_cost": sum(case["baseline"]["cost"] for case in hidden)}))


if __name__ == "__main__":
    main()
