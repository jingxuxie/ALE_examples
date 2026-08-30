import importlib.util
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("baseline", ROOT / "participant/baseline/solver.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def orthogonal(generator, dimension):
    matrix, triangular = np.linalg.qr(generator.normal(size=(dimension, dimension)))
    return matrix @ np.diag(np.where(np.diag(triangular) >= 0, 1, -1))


def make_case(seed, family, dimension, rank, identifier):
    generator = np.random.default_rng(seed)
    one_body = np.diag(generator.uniform(-1, 1, dimension))
    for site in range(dimension):
        neighbor = (site + 1) % dimension
        one_body[site, neighbor] = one_body[neighbor, site] = generator.uniform(-0.9, -0.2)
    local = np.zeros((rank, dimension, dimension))
    for factor in range(rank):
        center = (factor * 3 + factor // 3) % dimension
        width = {"bond_charge": 2, "overlapping_clusters": 3, "multiscale": 4}[family]
        sites = [(center + offset) % dimension for offset in range(width)]
        for component in range(2):
            vector = np.zeros(dimension)
            vector[sites] = generator.uniform(-0.65, 0.65, width)
            vector[center] += generator.uniform(0.8, 1.4)
            local[factor] += np.outer(vector, vector)
        if family == "multiscale":
            diffuse = generator.normal(size=dimension)
            diffuse /= np.linalg.norm(diffuse)
            local[factor] += generator.uniform(0.05, 0.15) * np.outer(diffuse, diffuse)
        local[factor] *= generator.uniform(0.6, 1.4)
    orbital = orthogonal(generator, dimension)
    auxiliary = orthogonal(generator, rank)
    factors = np.einsum("ab,pi,bij,qj->apq", auxiliary, orbital, local, orbital, optimize=True)
    case = {"id": identifier, "family": family, "one_body": (orbital @ one_body @ orbital.T).tolist(), "factors": factors.tolist()}
    starter = baseline.solve(case)
    base_cost = baseline.cost(np.asarray(case["one_body"]), factors, np.asarray(starter["orbital"]), np.asarray(starter["auxiliary"]))
    case["baseline_cost"] = base_cost
    private = {"id": identifier, "orbital": orbital.tolist(), "auxiliary": auxiliary.T.tolist()}
    private_cost = baseline.cost(np.asarray(case["one_body"]), factors, orbital, auxiliary.T)
    return case, private, {"id": identifier, "family": family, "baseline_cost": base_cost, "private_cost": private_cost, "reduction": 1 - private_cost / base_cost}


def main():
    families = ["bond_charge", "overlapping_clusters", "multiscale"]
    for directory in ["participant/input", "evaluator/hidden", "attempts", "champions"]:
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    summary = {}
    for split, count, offset in [("public", 12, 281037), ("hidden", 18, 730128)]:
        cases, solutions, records = [], [], []
        for index in range(count):
            dimension = [10, 12, 14, 16][(index // 3) % 4]
            rank = dimension - 2
            case, solution, record = make_case(offset + 101 * index, families[index % 3], dimension, rank, f"{split}_{index:03d}")
            cases.append(case)
            solutions.append(solution)
            records.append(record)
        destination = ROOT / ("participant/input/examples.json" if split == "public" else "evaluator/hidden/cases.json")
        destination.write_text(json.dumps({"cases": cases, "seconds_per_case": 10}, allow_nan=False))
        witness_dir = ROOT / "adversary" / (split + "_planted")
        witness_dir.mkdir(exist_ok=True)
        (witness_dir / "solution.json").write_text(json.dumps({"solutions": solutions}, allow_nan=False))
        by_family = defaultdict(list)
        for record in records:
            by_family[record["family"]].append(record["private_cost"] / record["baseline_cost"])
        reduction = lambda values: 1 - math.exp(np.log(values).mean())
        summary[split] = {"cases": records, "core_score": reduction([record["private_cost"] / record["baseline_cost"] for record in records]), "family_scores": {family: reduction(values) for family, values in by_family.items()}}
    (ROOT / "adversary/generation_report.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({split: {key: value for key, value in report.items() if key != "cases"} for split, report in summary.items()}, indent=2))


if __name__ == "__main__":
    main()
