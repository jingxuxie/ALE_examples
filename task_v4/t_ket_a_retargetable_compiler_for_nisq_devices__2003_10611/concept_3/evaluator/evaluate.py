import argparse
import hashlib
import json
import os
from pathlib import Path
import stat


ROOT = Path(__file__).resolve().parent
MAX_BYTES = 8 * 1024 * 1024
MAX_GATES = 50000


class InvalidWitness(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidWitness("duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_constant(value):
    raise InvalidWitness("nonfinite JSON constant: " + value)


def parse_json(data):
    return json.loads(data, object_pairs_hook=unique_object, parse_constant=reject_constant)


def load_suite():
    data = (ROOT / "hidden" / "frozen_instances.json").read_bytes()
    freeze = json.loads((ROOT / "hidden" / "freeze.json").read_text())
    if hashlib.sha256(data).hexdigest() != freeze["instances_sha256"]:
        raise RuntimeError("trusted frozen instance digest mismatch")
    return parse_json(data.decode("utf-8"))


def read_witness(solution_dir):
    source = Path(solution_dir).absolute()
    if source.is_symlink():
        raise InvalidWitness("symlink submission root is forbidden")
    if source.is_dir():
        nested = source / "submission"
        if nested.is_symlink():
            raise InvalidWitness("symlink submission directory is forbidden")
        source = nested / "witness.json" if nested.is_dir() else source / "witness.json"
    descriptor = os.open(source, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        information = os.fstat(stream.fileno())
        if not stat.S_ISREG(information.st_mode):
            raise InvalidWitness("witness must be a regular file")
        if information.st_size > MAX_BYTES:
            raise InvalidWitness("witness exceeds 8 MiB")
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise InvalidWitness("witness exceeds 8 MiB")
    return parse_json(data.decode("utf-8"))


def validate_shape(witness, suite):
    if type(witness) is not dict or set(witness) != {"schema_version", "circuits"}:
        raise InvalidWitness("top-level keys must be schema_version and circuits")
    if type(witness["schema_version"]) is not int or witness["schema_version"] != 1:
        raise InvalidWitness("schema_version must be integer 1")
    circuits = witness["circuits"]
    expected = {case["id"] for case in suite["instances"]}
    if type(circuits) is not dict or set(circuits) != expected:
        raise InvalidWitness("circuits must contain exactly all six instance IDs")
    for case in suite["instances"]:
        gates = circuits[case["id"]]
        if type(gates) is not list or len(gates) > MAX_GATES:
            raise InvalidWitness(case["id"] + ": circuit must be an array of at most 50000 gates")
        for index, gate in enumerate(gates):
            if type(gate) is not list or len(gate) != 2 or any(type(wire) is not int for wire in gate):
                raise InvalidWitness(f"{case['id']}: gate {index} must be two integer indices")
            if gate[0] == gate[1] or any(wire < 0 or wire >= case["n"] for wire in gate):
                raise InvalidWitness(f"{case['id']}: gate {index} has invalid endpoints")


def replay_case(case, gates):
    size = case["n"]
    rows = [1 << wire for wire in range(size)]
    clocks = [0] * size
    missing = set(case["required_parities"]) - set(rows)
    edges = {tuple(sorted(edge)) for edge in case["edges"]}
    illegal = None
    for index, (control, target) in enumerate(gates):
        if tuple(sorted((control, target))) not in edges:
            illegal = index
            break
        rows[target] ^= rows[control]
        missing.discard(rows[target])
        level = 1 + max(clocks[control], clocks[target])
        clocks[control] = level
        clocks[target] = level
    count = len(gates)
    depth = max(clocks)
    target_matches = illegal is None and rows == case["target_rows"]
    valid = illegal is None and target_matches and not missing
    count_ok = count <= case["max_cnots"]
    depth_ok = illegal is None and depth <= case["max_depth"]
    passed = bool(valid and count_ok and depth_ok)
    reasons = []
    if illegal is not None:
        reasons.append(f"non-native edge at gate {illegal}")
    if not target_matches:
        reasons.append("target matrix mismatch")
    if missing:
        reasons.append(f"{len(missing)} required parities not visited")
    if not count_ok:
        reasons.append("CNOT count budget exceeded")
    if illegal is None and not depth_ok:
        reasons.append("depth budget exceeded")
    efficiency = 0.0
    if valid:
        efficiency = (min(1.0, case["max_cnots"] / max(1, count)) + min(1.0, case["max_depth"] / max(1, depth))) / 2
    return {
        "id": case["id"],
        "family": case["family"],
        "valid": bool(valid),
        "passed": passed,
        "reason": "; ".join(reasons) if reasons else "ok",
        "cnots": count,
        "depth": depth if illegal is None else None,
        "max_cnots": case["max_cnots"],
        "max_depth": case["max_depth"],
        "count_ok": count_ok,
        "depth_ok": depth_ok,
        "target_matches": target_matches,
        "missing_parities": sorted(missing),
        "resource_score": efficiency,
    }


def failure(reason):
    return {"core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0, "passed": False, "valid": False, "reason": reason, "cases": []}


def evaluate_witness(witness, suite=None):
    if suite is None:
        suite = load_suite()
    try:
        validate_shape(witness, suite)
    except InvalidWitness as error:
        return failure(str(error))
    results = [replay_case(case, witness["circuits"][case["id"]]) for case in suite["instances"]]
    families = sorted({result["family"] for result in results})
    family_scores = {
        family: sum(result["passed"] for result in results if result["family"] == family) / sum(result["family"] == family for result in results)
        for family in families
    }
    valid = all(result["valid"] for result in results)
    passed = all(result["passed"] for result in results)
    failed_ids = [result["id"] for result in results if not result["passed"]]
    return {
        "core_score": sum(result["passed"] for result in results) / len(results),
        "worst_family_score": min(family_scores.values()),
        "resource_score": sum(result["resource_score"] for result in results) / len(results),
        "valid": valid,
        "passed": passed,
        "reason": "ok" if passed else ("budget failures: " if valid else "semantic failures or budget failures: ") + ", ".join(failed_ids),
        "family_scores": family_scores,
        "cases": results,
    }


def evaluate(solution_dir):
    suite = load_suite()
    try:
        witness = read_witness(solution_dir)
        return evaluate_witness(witness, suite)
    except (OSError, ValueError, UnicodeError, RecursionError) as error:
        return failure("invalid submission: " + str(error))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?")
    parser.add_argument("--solution-dir", "--solution_dir", "--submission", dest="solution_dir")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    source = arguments.solution_dir or arguments.path
    if source is None:
        parser.error("provide a solution directory or witness JSON path")
    result = evaluate(source)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
