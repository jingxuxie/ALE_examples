import argparse
import json
import time
from pathlib import Path


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def finite(value):
    raise ValueError("nonfinite JSON number")


def affine(expression, values, depths):
    if type(expression) is not list or any(type(reference) is not int for reference in expression):
        raise ValueError("affine expressions require integer lists")
    if expression != sorted(set(expression)) or any(reference < 0 or reference >= len(values) for reference in expression):
        raise ValueError("unordered, repeated or unavailable reference")
    value = 0
    depth = 0
    for reference in expression:
        value ^= values[reference]
        depth = max(depth, depths[reference])
    return value, depth


def check(instance, circuit):
    if type(circuit) is not dict or set(circuit) != {"id", "gates", "outputs"}:
        raise ValueError("invalid circuit schema")
    gates, outputs = circuit["gates"], circuit["outputs"]
    if type(gates) is not list or len(gates) > 50000 or type(outputs) is not list or len(outputs) != instance["m"]:
        raise ValueError("invalid gate or output count")
    rows = 1 << instance["n"]
    values = [(1 << rows) - 1]
    values.extend(sum(((address >> bit) & 1) << address for address in range(rows)) for bit in range(instance["n"]))
    depths = [0] * len(values)
    affine_size = 0
    for gate in gates:
        if type(gate) is not dict or set(gate) != {"left", "right"}:
            raise ValueError("invalid product schema")
        left, left_depth = affine(gate["left"], values, depths)
        right, right_depth = affine(gate["right"], values, depths)
        values.append(left & right)
        depths.append(1 + max(left_depth, right_depth))
        affine_size += len(gate["left"]) + len(gate["right"])
    actual = []
    for expression in outputs:
        value, depth = affine(expression, values, depths)
        actual.append(value)
        affine_size += len(expression)
    expected = [sum(((row >> bit) & 1) << address for address, row in enumerate(instance["table"])) for bit in range(instance["m"])]
    wrong_rows = 0
    for actual_column, expected_column in zip(actual, expected):
        wrong_rows |= actual_column ^ expected_column
    exact = wrong_rows == 0
    usage = {"and": len(gates), "depth": max(depths), "affine": affine_size,
             "ancilla": len(gates) + 2 if gates else 0}
    within = all(usage[key] <= instance["caps"][key] for key in usage)
    return {"id": instance["id"], "family": instance["family"], "exact": exact,
            "row_accuracy": 1 - wrong_rows.bit_count() / rows, "within_caps": within,
            "passed": exact and within, "usage": usage, "caps": instance["caps"],
            "clean_lift_toffolis": 2 * len(gates)}


def evaluate(suite, submission):
    started = time.monotonic()
    try:
        artifact = submission / "circuits.json"
        if artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size > 8 * 1024**2:
            raise ValueError("missing, linked or oversized circuits.json")
        data = json.loads(artifact.read_text(), object_pairs_hook=unique, parse_constant=finite)
        if type(data) is not dict or set(data) != {"circuits"} or type(data["circuits"]) is not list:
            raise ValueError("invalid artifact schema")
        circuits = data["circuits"]
        if any(type(circuit) is not dict or type(circuit.get("id")) is not str for circuit in circuits):
            raise ValueError("invalid circuit IDs")
        by_id = {circuit["id"]: circuit for circuit in circuits}
        instances = suite["instances"]
        if len(by_id) != len(circuits) or set(by_id) != {instance["id"] for instance in instances}:
            raise ValueError("duplicate, missing or extra circuit IDs")
        records = [check(instance, by_id[instance["id"]]) for instance in instances]
        families = {record["family"] for record in records}
        family_scores = {family: sum(record["passed"] for record in records if record["family"] == family) / sum(record["family"] == family for record in records) for family in families}
        passed = all(record["passed"] for record in records)
        return {"core_score": sum(record["passed"] for record in records) / len(records),
                "worst_family_score": min(family_scores.values()), "family_scores": family_scores,
                "correctness_score": sum(record["exact"] for record in records) / len(records),
                "resource_score": sum(record["within_caps"] for record in records) / len(records),
                "runtime_seconds": time.monotonic() - started, "valid": passed, "passed": passed,
                "reason": "all exact resource-bounded witnesses verified" if passed else "truth-table or resource requirements unmet", "instances": records}
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
        return {"core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0,
                "runtime_seconds": time.monotonic() - started, "valid": False, "passed": False, "reason": str(error)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = evaluate(json.loads((args.input / "suite.json").read_text()), args.submission)
    text = json.dumps(result, indent=2)
    if args.report:
        args.report.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
