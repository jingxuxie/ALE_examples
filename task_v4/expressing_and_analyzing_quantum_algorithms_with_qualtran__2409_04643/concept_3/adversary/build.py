import copy
import importlib.util
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
import verify

spec = importlib.util.spec_from_file_location("baseline", ROOT / "participant" / "baseline" / "solve.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def xor_forms(forms):
    references = set()
    for form in forms:
        references.symmetric_difference_update(form)
    return sorted(references)


def make_circuit(seed, width, outputs, family):
    rng = random.Random(seed)
    gates = []
    if family == "reconvergent":
        previous = []
        for layer in range(4):
            current = []
            for _ in range(outputs + 1):
                operands = []
                for _ in range(2):
                    references = rng.sample(range(1, width + 1), rng.randint(3, width - 1))
                    if previous:
                        references += rng.sample(previous, rng.randint(1, min(4, len(previous))))
                    if rng.random() < 0.5:
                        references += [0]
                    operands.append(sorted(references))
                current.append(width + 1 + len(gates))
                gates.append({"left": operands[0], "right": operands[1]})
            previous = current
        expressions = []
        for index in range(outputs):
            expressions.append(sorted([previous[index], previous[-1]] + rng.sample(range(1, width + 1), 3)))
    else:
        states = [[index + 1] for index in range(width)]
        for _ in range(4 * width):
            source, destination = rng.sample(range(width), 2)
            states[destination] = xor_forms([states[destination], states[source]])
        split = width // 2
        left, right = states[:split], states[split:]
        for _ in range(5):
            changed = []
            for state in left:
                operands = [xor_forms(rng.sample(right, rng.randint(2, min(4, len(right))))) for _ in range(2)]
                if operands[0] == operands[1]:
                    operands[1] = xor_forms([operands[1], [0]])
                reference = width + 1 + len(gates)
                gates.append({"left": operands[0], "right": operands[1]})
                changed.append(xor_forms([state, [reference]]))
            left, right = right, changed
        states = left + right
        expressions = [xor_forms(rng.sample(states, rng.randint(2, min(5, len(states))))) for _ in range(outputs)]
    return {"id": f"{family}_{width}", "gates": gates, "outputs": expressions}


def rows(circuit, width):
    table = []
    for address in range(1 << width):
        values = [1] + [(address >> bit) & 1 for bit in range(width)]
        for gate in circuit["gates"]:
            operands = [sum(values[reference] for reference in gate[key]) % 2 for key in ("left", "right")]
            values.append(operands[0] * operands[1])
        table.append(sum((sum(values[reference] for reference in expression) % 2) << bit for bit, expression in enumerate(circuit["outputs"])))
    return table


def structure(table, width, output_width):
    coefficients = table.copy()
    for bit in range(width):
        for mask in range(1 << width):
            if mask & (1 << bit):
                coefficients[mask] ^= coefficients[mask ^ (1 << bit)]
    min_degree = width
    for combination in range(1, 1 << output_width):
        degree = max([mask.bit_count() for mask, value in enumerate(coefficients) if (value & combination).bit_count() % 2] or [0])
        min_degree = min(min_degree, degree)
    active_inputs = sum(any(table[address] != table[address ^ (1 << bit)] for address in range(1 << width)) for bit in range(width))
    return min_degree, active_inputs


def main():
    instances, circuits, baselines, provenance = [], [], [], []
    for family_index, family in enumerate(("reconvergent", "affine_feedback")):
        for index, (width, output_width) in enumerate(((10, 4), (11, 6), (12, 8))):
            for trial in range(100):
                seed = 240904643 + 10000 * family_index + index * 100 + trial
                circuit = make_circuit(seed, width, output_width, family)
                table = rows(circuit, width)
                min_degree, active = structure(table, width, output_width)
                if min_degree >= 3 and active == width:
                    break
            else:
                raise RuntimeError("curation failed")
            instance = {"id": circuit["id"], "family": family, "n": width, "m": output_width,
                        "table": table, "caps": {"and": 50000, "depth": 100, "affine": 1000000, "ancilla": 50002}}
            usage = verify.check(instance, circuit)["usage"]
            instance["caps"] = {"and": usage["and"] + 2, "depth": usage["depth"],
                                "affine": math.ceil(1.20 * usage["affine"]), "ancilla": usage["and"] + 4}
            simple = baseline.synthesize(instance)
            baseline_report = verify.check(instance, simple)
            assert baseline_report["exact"] and not baseline_report["within_caps"]
            assert len(simple["gates"]) >= 8 * instance["caps"]["and"]
            assert verify.check(instance, circuit)["passed"]
            instances.append(instance)
            circuits.append(circuit)
            baselines.append(simple)
            provenance.append({"id": circuit["id"], "seed": seed, "minimum_output_combination_degree": min_degree,
                               "active_input_bits": active, "private_usage": usage,
                               "baseline_and": len(simple["gates"]), "caps": instance["caps"]})
            print(provenance[-1], flush=True)
    suite = {"instances": instances}
    for path in (ROOT / "participant/input/suite.json", ROOT / "evaluator/hidden/suite.json"):
        path.write_text(json.dumps(suite, separators=(",", ":")))
    witness_dir = ROOT / "adversary/private_witness"
    witness_dir.mkdir(exist_ok=True)
    (witness_dir / "circuits.json").write_text(json.dumps({"circuits": circuits}))
    (ROOT / "participant/baseline/circuits.json").write_text(json.dumps({"circuits": baselines}))
    (ROOT / "adversary/provenance.json").write_text(json.dumps(provenance, indent=2))
    witness_report = verify.evaluate(suite, witness_dir)
    baseline_report = verify.evaluate(suite, ROOT / "participant/baseline")
    assert witness_report["passed"] and baseline_report["correctness_score"] == 1 and not baseline_report["passed"]
    (ROOT / "adversary/private_witness_score.json").write_text(json.dumps(witness_report, indent=2))
    (ROOT / "evaluator/hidden/baseline_score.json").write_text(json.dumps(baseline_report, indent=2))
    checks = 0
    for instance, circuit in zip(instances, circuits):
        wrong = copy.deepcopy(circuit)
        wrong["outputs"][0] = xor_forms([wrong["outputs"][0], [0]])
        assert not verify.check(instance, wrong)["exact"]
        for invalid in ([True], [width + len(circuit["gates"]) + 100], [0, 0], [-1]):
            wrong = copy.deepcopy(circuit)
            wrong["outputs"][0] = invalid
            try:
                verify.check(instance, wrong)
            except ValueError:
                checks += 1
            else:
                raise AssertionError("invalid reference accepted")
        checks += 1
    (ROOT / "adversary/selftest.json").write_text(json.dumps({"passed": True, "negative_checks": checks,
        "positive_full_row_checks": sum(1 << instance["n"] for instance in instances),
        "independent_methods": ["row-by-row generator", "packed-bit verifier", "shared ANF baseline"]}, indent=2))


if __name__ == "__main__":
    main()
