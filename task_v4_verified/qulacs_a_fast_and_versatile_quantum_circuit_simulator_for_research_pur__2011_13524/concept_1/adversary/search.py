import argparse
import importlib.util
import json
import math
from pathlib import Path
import random
import time


ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    specification = importlib.util.spec_from_file_location(name, file)
    loaded = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(loaded)
    return loaded


BASELINE = load("original_baseline", ROOT / "participant/baseline/solution.py")
MODEL = load("original_model", ROOT / "participant/workspace/model.py")


def closure_order(case, seed, exponent):
    rng = random.Random(seed)
    gates = case["gates"]
    masks = [sum(1 << qubit for qubit in gate["qubits"]) for gate in gates]
    kinds = [{"dense": 1, "diagonal": 2, "permutation": 4}[gate["kind"]] for gate in gates]
    parents = MODEL.predecessors(case)
    children = [[] for _ in gates]
    for index, dependencies in enumerate(parents):
        for parent in dependencies:
            children[parent].append(index)
    done = set()
    order = []
    epochs = sorted({gate["epoch"] for gate in gates})
    for epoch in epochs:
        members = {index for index, gate in enumerate(gates) if gate["epoch"] == epoch}
        ready = {index for index in members if parents[index] <= done}
        while ready:
            seeds = sorted(ready)
            rng.shuffle(seeds)
            candidates = {masks[index] for index in seeds}
            for first in seeds[:14]:
                support = masks[first]
                for second in seeds[:18]:
                    expanded = support | masks[second]
                    if expanded.bit_count() <= case["max_block_qubits"]:
                        candidates.add(expanded)
                        if rng.random() < 0.35:
                            support = expanded
            winner = None
            for support in candidates:
                active = {index for index in ready if masks[index] & ~support == 0}
                chosen = []
                chosen_set = set()
                union = 0
                kind_mask = 0
                while active and len(chosen) < case["max_block_operations"]:
                    index = min(active)
                    active.remove(index)
                    chosen.append(index)
                    chosen_set.add(index)
                    union |= masks[index]
                    kind_mask |= kinds[index]
                    for child in children[index]:
                        if gates[child]["epoch"] == epoch and not masks[child] & ~support and parents[child] <= done | chosen_set:
                            active.add(child)
                if not chosen:
                    continue
                cost = BASELINE.cost_from_stats(case, union, kind_mask, len(chosen))
                metric = cost / len(chosen) ** exponent
                key = (metric, -len(chosen), chosen[0])
                if winner is None or key < winner[0]:
                    winner = (key, chosen)
            selected = winner[1]
            done.update(selected)
            order.extend(selected)
            ready.difference_update(selected)
            for index in selected:
                for child in children[index]:
                    if child not in done and gates[child]["epoch"] == epoch and parents[child] <= done:
                        ready.add(child)
    return order


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", type=int, default=6)
    parser.add_argument("--output", type=Path, default=ROOT / "adversary/portfolio_search.json")
    args = parser.parse_args()
    entries = json.loads((ROOT / "evaluator/hidden/cases.json").read_text())
    results = []
    started = time.monotonic()
    for case_number, entry in enumerate(entries):
        case = entry["case"]
        best_cost = entry["baseline_cost"]
        best_schedule = entry["baseline_schedule"]
        best_variant = None
        for variant in range(args.variants):
            order = closure_order(case, case_number * 97 + variant, [0.8, 1.0, 1.2][variant % 3])
            cost, blocks = BASELINE.partition(case, order)
            verified = MODEL.validate_and_cost(case, blocks)
            if abs(cost - verified) > 1e-6 * max(1, cost):
                raise RuntimeError("Cost implementation disagrees")
            if cost < best_cost:
                best_cost, best_schedule, best_variant = cost, blocks, variant
        result = {"id": case["id"], "family": entry["family"], "speedup": entry["baseline_cost"] / best_cost,
                  "cost": best_cost, "variant": best_variant, "schedule": best_schedule}
        results.append(result)
        families = {}
        for row in results:
            families.setdefault(row["family"], []).append(row["speedup"])
        means = {family: math.exp(sum(map(math.log, values)) / len(values)) for family, values in families.items()}
        report = {"kind": "privileged_offline_search_not_a_time_compliant_submission", "completed_cases": len(results),
                  "variants_per_case": args.variants, "elapsed_seconds": time.monotonic() - started,
                  "core_score": math.exp(sum(math.log(row["speedup"]) for row in results) / len(results)),
                  "worst_family_score": min(means.values()), "family_scores": means, "cases": results}
        args.output.write_text(json.dumps(report, indent=2))
        print(case_number, entry["family"], result["speedup"], flush=True)


if __name__ == "__main__":
    main()
