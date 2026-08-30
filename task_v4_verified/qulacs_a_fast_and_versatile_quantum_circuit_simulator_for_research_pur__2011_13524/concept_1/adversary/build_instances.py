import importlib.util
import json
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[1]


def generate(seed, family, scale=1):
    rng = random.Random(seed)
    qubit_count = rng.choice([12, 16, 20, 24])
    gates = []
    epochs = rng.choice([1, 2, 3])
    depth = int(rng.randint(12, 22) * scale)
    for epoch in range(epochs):
        if family == "modular":
            modules = [list(range(start, min(start + 4, qubit_count))) for start in range(0, qubit_count, 4)]
            for layer in range(depth):
                shuffled = list(modules)
                rng.shuffle(shuffled)
                for module in shuffled:
                    for repeat in range(rng.randint(2, 4)):
                        support = rng.sample(module, rng.choice([1, 1, 2]))
                        gates.append({"qubits": support, "kind": rng.choice(["dense", "dense", "diagonal"]), "epoch": epoch})
                if layer % 5 == 4:
                    for start in range(3, qubit_count - 1, 4):
                        gates.append({"qubits": [start, start + 1], "kind": "dense", "epoch": epoch})
        elif family == "nearest_neighbor":
            for layer in range(depth):
                for qubit in rng.sample(range(qubit_count), qubit_count):
                    gates.append({"qubits": [qubit], "kind": "dense", "epoch": epoch})
                for qubit in range(layer % 2, qubit_count - 1, 2):
                    gates.append({"qubits": [qubit, qubit + 1], "kind": rng.choice(["permutation", "diagonal"]), "epoch": epoch})
        elif family == "wide_frontier":
            for layer in range(depth):
                for qubit in rng.sample(range(qubit_count), qubit_count):
                    gates.append({"qubits": [qubit], "kind": rng.choice(["dense", "diagonal", "permutation"]), "epoch": epoch})
                for repeat in range(max(1, qubit_count // 6)):
                    gates.append({"qubits": rng.sample(range(qubit_count), 2), "kind": "dense", "epoch": epoch})
        elif family == "diagonal_heavy":
            for layer in range(depth):
                for repeat in range(qubit_count):
                    width = rng.choice([1, 2, 2, 3])
                    gates.append({"qubits": rng.sample(range(qubit_count), width), "kind": "diagonal", "epoch": epoch})
                for qubit in rng.sample(range(qubit_count), max(1, qubit_count // 5)):
                    gates.append({"qubits": [qubit], "kind": "dense", "epoch": epoch})
        else:
            for layer in range(depth):
                offset = (layer // 3) % 4
                windows = [list(range(start, min(start + 4, qubit_count))) for start in range(offset, qubit_count, 4)]
                for repeat in range(5):
                    rng.shuffle(windows)
                    for window in windows:
                        width = min(len(window), rng.choice([1, 2]))
                        gates.append({"qubits": rng.sample(window, width), "kind": rng.choice(["dense", "diagonal"]), "epoch": epoch})
    gates = gates[:1500]
    return {
        "id": f"c{rng.getrandbits(48):012x}",
        "n_qubits": qubit_count,
        "gates": gates,
        "max_block_qubits": rng.choice([3, 4, 5, 6]),
        "max_block_operations": rng.choice([12, 24, 40]),
        "repetitions": rng.choice([1, 4, 16, 64, 128]),
        "hardware": {"launch": rng.choice([0.5, 2.0, 6.0]), "memory": rng.choice([6.0, 12.0, 24.0]),
                     "compute": rng.choice([0.12, 0.25, 0.5]), "build": rng.choice([0.002, 0.02, 0.10]),
                     "stride_penalty": rng.choice([0.0, 0.04, 0.08]), "cache_qubits": 4}
    }


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    baseline = load_module("baseline", ROOT / "participant/baseline/solution.py")
    model = load_module("costmodel", ROOT / "participant/workspace/model.py")
    families = ["modular", "nearest_neighbor", "wide_frontier", "diagonal_heavy", "shifting_locality"]
    hidden = []
    examples = []
    for family_index, family in enumerate(families):
        examples.append(generate(910 + family_index, family, 0.5))
        for member in range(5):
            case = generate(507001 + family_index * 131 + member * 17, family)
            blocks = baseline.plan(case)
            baseline_cost = model.validate_and_cost(case, blocks)
            hidden.append({"case": case, "family": family, "baseline_cost": baseline_cost, "baseline_schedule": blocks})
    (ROOT / "evaluator/hidden").mkdir(parents=True, exist_ok=True)
    (ROOT / "evaluator/hidden/cases.json").write_text(json.dumps(hidden, indent=2))
    (ROOT / "participant/input/examples.json").write_text(json.dumps({"cases": examples}, indent=2))
    baseline_report = {"core_score": 1.0, "worst_family_score": 1.0, "passed": False, "valid": True,
                       "reason": "Supplied seven-schedule planner defines normalization; target is 1.20.",
                       "costs": {entry["case"]["id"]: entry["baseline_cost"] for entry in hidden}}
    (ROOT / "adversary/baseline_costs.json").write_text(json.dumps(baseline_report, indent=2))


if __name__ == "__main__":
    main()
