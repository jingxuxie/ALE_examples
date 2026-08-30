import importlib.util
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from phase_model import check


def generate_case(seed, family, size=None, terms_count=None):
    randomizer = random.Random(seed)
    size = size or randomizer.choice([16, 20, 24, 28])
    terms_count = terms_count or randomizer.randrange(42, 81)
    undirected = set()
    if family == "bottleneck":
        midpoint = size // 2
        for start, stop in ((0, midpoint), (midpoint, size)):
            for qubit in range(start, stop - 1):
                undirected.add((qubit, qubit + 1))
            for qubit in range(start, stop - 3):
                if randomizer.random() < 0.55:
                    undirected.add((qubit, qubit + 3))
        undirected.add((midpoint - 1, midpoint))
    elif family in ("lattice", "heterogeneous"):
        width = 4
        for qubit in range(size):
            if qubit % width < width - 1 and qubit + 1 < size:
                undirected.add((qubit, qubit + 1))
            if qubit + width < size:
                undirected.add((qubit, qubit + width))
    elif family == "shared_dense":
        for qubit in range(size):
            undirected.add(tuple(sorted((qubit, (qubit + 1) % size))))
        permutation = list(range(size))
        randomizer.shuffle(permutation)
        for first, second in zip(permutation[::2], permutation[1::2]):
            undirected.add(tuple(sorted((first, second))))
    else:
        raise ValueError("unknown family")
    relabeling = list(range(size))
    randomizer.shuffle(relabeling)
    edges = []
    for first, second in sorted(undirected):
        for control, target in ((first, second), (second, first)):
            weight = randomizer.randrange(1, 13) if family == "heterogeneous" else randomizer.randrange(1, 6)
            edges.append([relabeling[control], relabeling[target], weight, randomizer.randrange(1, 7)])
    rows = [1 << qubit for qubit in range(size)]
    history = []
    operations = []
    masks = []
    seen = set()
    previous = None
    burn_in = 2 * size if family == "shared_dense" else size // 3
    iterations = 0
    while len(masks) < terms_count:
        iterations += 1
        control, target, weight, duration = randomizer.choice(edges)
        if (control, target) == previous:
            continue
        previous = (control, target)
        rows[target] ^= rows[control]
        operation = ["cx", control, target]
        operations.append(operation)
        history.append(operation)
        mask = rows[target]
        if iterations > burn_in and mask.bit_count() >= 2 and mask not in seen and randomizer.random() < 0.72:
            operations.append(["rz", target, len(masks)])
            masks.append(mask)
            seen.add(mask)
    operations.extend(reversed(history))
    order = list(range(len(masks)))
    randomizer.shuffle(order)
    remap = {old: new for new, old in enumerate(order)}
    operations = [[kind, first, remap[second] if kind == "rz" else second] for kind, first, second in operations]
    workload = {"n": size, "edges": edges, "terms": [masks[index] for index in order]}
    planted = {"ops": operations}
    check(workload, planted)
    return workload, planted


def load_baseline():
    specification = importlib.util.spec_from_file_location("phase_baseline", ROOT / "participant" / "baseline" / "solution.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main():
    families = ["lattice", "bottleneck", "heterogeneous", "shared_dense"]
    hidden = ROOT / "evaluator" / "hidden"
    hidden.mkdir(parents=True, exist_ok=True)
    for directory in ("attempts", "champions"):
        (ROOT / directory).mkdir(exist_ok=True)
    baseline = load_baseline()
    cases = []
    evidence = []
    examples = []
    for family_index, family in enumerate(families):
        public, unused = generate_case(1109 + family_index * 211, family, size=16, terms_count=32)
        examples.append(public)
        for case_index in range(8):
            seed = 0x7C8F350D1B + family_index * 9901 + case_index * 7919
            workload, planted = generate_case(seed, family)
            baseline_circuit = baseline.compile_circuit(workload)
            baseline_metrics = check(workload, baseline_circuit)
            planted_metrics = check(workload, planted)
            case = {"id": f"{family}-{case_index}", "family": family, "input": workload, "baseline": baseline_metrics}
            cases.append(case)
            evidence.append({"id": case["id"], "seed": seed, "circuit": planted, "metrics": planted_metrics, "reduction": 1 - planted_metrics["cost"] / baseline_metrics["cost"]})
            print(case["id"], baseline_metrics["cost"], planted_metrics["cost"], flush=True)
    (hidden / "cases.json").write_text(json.dumps(cases, separators=(",", ":")) + "\n")
    (hidden / "generation_witnesses.json").write_text(json.dumps(evidence, separators=(",", ":")) + "\n")
    (ROOT / "participant" / "input" / "examples.jsonl").write_text("".join(json.dumps(example) + "\n" for example in examples))
    summary = {family: sum(item["reduction"] for item, case in zip(evidence, cases) if case["family"] == family) / 8 for family in families}
    (ROOT / "adversary" / "headroom.json").write_text(json.dumps({"family_planted_reductions": summary, "mean": sum(summary.values()) / len(summary), "qualification": "These concealed construction witnesses establish per-instance headroom, not a general compiler solution."}, indent=2) + "\n")
    (ROOT / "status.json").write_text(json.dumps({"concept": "hardware_aware_phase_compilation", "verification_mode": "A", "status": "built_pending_tournament", "target": {"core_score": 0.40, "worst_family_score": 0.25, "all_valid": True}, "ratchet_generations": 0, "solvability": "general_compiler_unknown"}, indent=2) + "\n")


if __name__ == "__main__":
    main()
