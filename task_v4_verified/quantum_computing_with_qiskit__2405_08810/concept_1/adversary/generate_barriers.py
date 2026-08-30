import json
from pathlib import Path
import random
import sys

from generate import generate_case, load_baseline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from phase_model import check


def cancel_commuting_inverses(operations):
    retained = []
    for operation in operations:
        kind, control, target = operation
        inverse = None
        for position in range(len(retained) - 1, -1, -1):
            previous_kind, previous_control, previous_target = retained[position]
            if (control, target) == (previous_control, previous_target):
                inverse = position
                break
            if control == previous_target or target == previous_control:
                break
        if inverse is None:
            retained.append(operation)
        else:
            retained.pop(inverse)
    return retained


def make_barrier(seed, family, size, layers, extra_terms):
    scaffold, unused = generate_case(seed, family, size, 24)
    randomizer = random.Random(seed ^ 0x7814AB9106)
    rows = [1 << qubit for qubit in range(size)]
    operations = []
    history = []
    previous = set()
    for layer in range(layers):
        available = list(scaffold["edges"])
        randomizer.shuffle(available)
        occupied = set()
        current = set()
        for control, target, weight, duration in available:
            if control in occupied or target in occupied or (control, target) in previous:
                continue
            occupied.update((control, target))
            current.add((control, target))
            rows[target] ^= rows[control]
            gate = ["cx", control, target]
            operations.append(gate)
            history.append(gate)
        previous = current
    history = cancel_commuting_inverses(history)
    operations = list(history)
    masks = list(rows)
    seen = set(masks)
    operations.extend(["rz", qubit, qubit] for qubit in range(size))
    while len(masks) < size + extra_terms:
        control, target, weight, duration = randomizer.choice(scaffold["edges"])
        rows[target] ^= rows[control]
        gate = ["cx", control, target]
        operations.append(gate)
        history.append(gate)
        if rows[target] not in seen:
            operations.append(["rz", target, len(masks)])
            masks.append(rows[target])
            seen.add(rows[target])
    operations.extend(reversed(history))
    order = list(range(len(masks)))
    randomizer.shuffle(order)
    remap = {original: index for index, original in enumerate(order)}
    operations = [[kind, first, remap[second] if kind == "rz" else second] for kind, first, second in operations]
    instance = {"n": size, "edges": scaffold["edges"], "terms": [masks[index] for index in order]}
    witness = {"ops": operations}
    check(instance, witness)
    return instance, witness


def main():
    baseline = load_baseline()
    destination = ROOT / "adversary" / "basis_barriers"
    destination.mkdir(exist_ok=True)
    cases = []
    witnesses = []
    for family_index, family in enumerate(("lattice", "bottleneck", "heterogeneous", "shared_dense")):
        for case_index in range(6):
            size = 24 if case_index % 2 == 0 else 28
            layers = (10, 14, 18)[case_index // 2]
            extra_terms = (0, 8, 16)[case_index % 3]
            seed = 0xFA961B44ACFE782 + 10939 * family_index + 17903 * case_index
            instance, witness = make_barrier(seed, family, size, layers, extra_terms)
            baseline_metrics = check(instance, baseline.compile_circuit(instance))
            witness_metrics = check(instance, witness)
            case_id = f"basis-{family}-{case_index}"
            cases.append({"id": case_id, "family": family, "input": instance, "baseline": baseline_metrics})
            witnesses.append({"id": case_id, "circuit": witness, "metrics": witness_metrics, "reduction": 1 - witness_metrics["cost"] / baseline_metrics["cost"], "seed": seed, "layers": layers, "extra_terms": extra_terms})
            print(case_id, baseline_metrics["cost"], witness_metrics["cost"], flush=True)
    (destination / "cases.json").write_text(json.dumps(cases, separators=(",", ":")) + "\n")
    (destination / "witnesses.json").write_text(json.dumps(witnesses, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
