import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re
import stat


MAX_BYTES = 2_097_152
MAX_GATES_PER_TARGET = 20_000
MAX_JSON_DEPTH = 12
MAX_JSON_NODES = 400_000
MAX_INTEGER = (1 << 63) - 1
DEFAULT_INSTANCES = Path(__file__).resolve().parents[1] / "input" / "instances.json"


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def reject_number(token):
    raise ContractError("Only finite JSON integers are allowed; floats and nonfinite numbers are forbidden.")


def parse_integer(token):
    require(len(token.lstrip("-")) <= 19, "JSON integer is oversized.")
    value = int(token)
    require(abs(value) <= MAX_INTEGER, "JSON integer is outside the signed 63-bit magnitude limit.")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON object key.")
        result[key] = value
    return result


def validate_json_tree(document):
    pending = [(document, 1)]
    node_count = 0
    while pending:
        value, depth = pending.pop()
        node_count += 1
        require(node_count <= MAX_JSON_NODES, "Too many JSON nodes.")
        require(depth <= MAX_JSON_DEPTH, "JSON nesting is too deep.")
        if type(value) is dict:
            for key, child in value.items():
                require(type(key) is str and len(key) <= 128, "Invalid or oversized JSON key.")
                pending.append((child, depth + 1))
        elif type(value) is list:
            pending.extend((child, depth + 1) for child in value)
        elif type(value) is str:
            require(len(value) <= 128, "Oversized JSON string.")
        elif type(value) is int:
            require(abs(value) <= MAX_INTEGER, "Oversized JSON integer.")
        else:
            raise ContractError("Booleans, null, floats and non-JSON values are forbidden.")


def load_json_bytes(payload):
    require(len(payload) <= MAX_BYTES, "JSON file exceeds 2097152 bytes.")
    try:
        text = payload.decode("utf-8", errors="strict")
        nesting = 0
        quoted = False
        escaped = False
        for character in text:
            if quoted:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    quoted = False
            elif character == '"':
                quoted = True
            elif character in "[{":
                nesting += 1
                require(nesting <= MAX_JSON_DEPTH, "JSON nesting is too deep.")
            elif character in "]}":
                nesting -= 1
        document = json.loads(
            text,
            parse_int=parse_integer,
            parse_float=reject_number,
            parse_constant=reject_number,
            object_pairs_hook=unique_object,
        )
        validate_json_tree(document)
        return document
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ContractError("Malformed UTF-8 JSON.") from error


def load_json_file(path):
    descriptor = None
    try:
        descriptor = os.open(os.fspath(path), os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        details = os.fstat(descriptor)
        require(stat.S_ISREG(details.st_mode), "Artifact must be a regular file, not a device, pipe, directory or symlink.")
        require(details.st_size <= MAX_BYTES, "JSON file exceeds 2097152 bytes.")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            payload = stream.read(MAX_BYTES + 1)
        return load_json_bytes(payload)
    except OSError as error:
        raise ContractError("Cannot read a regular JSON file (missing, inaccessible or symlink).") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def exact_keys(document, expected, label):
    require(type(document) is dict, label + " must be an object.")
    require(set(document) == set(expected), label + " has missing or unknown keys.")


def integer_between(value, minimum, maximum, label):
    require(type(value) is int and minimum <= value <= maximum, label + " must be an in-range integer, not a boolean or float.")


def matrix_rows(matrix):
    return [sum(bit << column for column, bit in enumerate(row)) for row in matrix]


def binary_rank(matrix):
    rows = matrix_rows(matrix)
    rank = 0
    for column in range(len(rows)):
        pivot = next((position for position in range(rank, len(rows)) if (rows[position] >> column) & 1), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for position in range(rank + 1, len(rows)):
            if (rows[position] >> column) & 1:
                rows[position] ^= rows[rank]
        rank += 1
    return rank


def validate_instances(suite):
    validate_json_tree(suite)
    exact_keys(suite, ("schema_version", "suite_id", "targets"), "Instance suite")
    integer_between(suite["schema_version"], 1, 1, "Instance schema_version")
    require(suite["suite_id"] == "native_cx_linear_v1", "Unknown instance suite.")
    require(type(suite["targets"]) is list and 1 <= len(suite["targets"]) <= 4, "Expected one to four targets.")
    names = set()
    for target in suite["targets"]:
        exact_keys(target, ("name", "family", "n_qubits", "native_cx", "matrix", "max_cx", "max_weighted_depth"), "Target")
        for label in ("name", "family"):
            require(type(target[label]) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,47}", target[label]) is not None, "Invalid target name or family.")
        require(target["name"] not in names, "Duplicate target name.")
        names.add(target["name"])
        qubit_count = target["n_qubits"]
        integer_between(qubit_count, 2, 36, "n_qubits")
        integer_between(target["max_cx"], 1, MAX_GATES_PER_TARGET, "max_cx")
        integer_between(target["max_weighted_depth"], 1, 2_000_000, "max_weighted_depth")
        matrix = target["matrix"]
        require(type(matrix) is list and len(matrix) == qubit_count, "Matrix has wrong row count.")
        for row in matrix:
            require(type(row) is list and len(row) == qubit_count, "Matrix has wrong column count.")
            for bit in row:
                integer_between(bit, 0, 1, "Matrix entry")
        require(binary_rank(matrix) == qubit_count, "Target matrix is singular over GF(2).")
        native_cx = target["native_cx"]
        require(type(native_cx) is list and len(native_cx) <= qubit_count * 3, "Invalid native-CX table.")
        directed_edges = set()
        neighbors = [set() for qubit in range(qubit_count)]
        for instruction in native_cx:
            require(type(instruction) is list and len(instruction) == 3, "Native-CX entries must be triples.")
            control, destination, duration = instruction
            integer_between(control, 0, qubit_count - 1, "Native control")
            integer_between(destination, 0, qubit_count - 1, "Native target")
            integer_between(duration, 1, 9, "Native duration")
            require(control != destination and (control, destination) not in directed_edges, "Duplicate or self-loop native gate.")
            directed_edges.add((control, destination))
            neighbors[control].add(destination)
            neighbors[destination].add(control)
        require(all((destination, control) in directed_edges for control, destination in directed_edges), "Both native directions must be specified.")
        require(all(len(adjacent) <= 3 for adjacent in neighbors), "Hardware degree exceeds three.")
        reached = {0}
        frontier = [0]
        while frontier:
            for neighbor in neighbors[frontier.pop()]:
                if neighbor not in reached:
                    reached.add(neighbor)
                    frontier.append(neighbor)
        require(len(reached) == qubit_count, "Hardware must be connected.")
    return suite


def invalid_target(target, reason):
    return {
        "name": target["name"], "family": target["family"], "valid": False,
        "correct": False, "cx_count": None, "weighted_depth": None,
        "max_cx": target["max_cx"], "max_weighted_depth": target["max_weighted_depth"],
        "count_ok": False, "depth_ok": False, "solved": False,
        "resource_score": 0.0, "reason": reason,
    }


def invalid_report(suite, reason):
    return {
        "valid": False, "passed": False, "reason": reason,
        "core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0,
        "solved_targets": 0, "total_targets": len(suite["targets"]),
        "family_scores": {target["family"]: 0.0 for target in suite["targets"]},
        "per_target": [invalid_target(target, reason) for target in suite["targets"]],
    }


def score_target(target, gates):
    require(type(gates) is list, "Circuit must be a list of CX pairs.")
    require(len(gates) <= MAX_GATES_PER_TARGET, "Circuit exceeds 20000 CX entries.")
    qubit_count = target["n_qubits"]
    durations = {(control, destination): duration for control, destination, duration in target["native_cx"]}
    rows = [1 << qubit for qubit in range(qubit_count)]
    ready = [0] * qubit_count
    for position, gate in enumerate(gates):
        require(type(gate) is list and len(gate) == 2, "Gate must be exactly [control, target].")
        control, destination = gate
        integer_between(control, 0, qubit_count - 1, "Control")
        integer_between(destination, 0, qubit_count - 1, "Target")
        require((control, destination) in durations, "Non-native or self-loop gate at index " + str(position) + ".")
        rows[destination] ^= rows[control]
        finish = max(ready[control], ready[destination]) + durations[(control, destination)]
        ready[control] = finish
        ready[destination] = finish
    mismatch_count = sum((actual ^ expected).bit_count() for actual, expected in zip(rows, matrix_rows(target["matrix"])))
    correct = mismatch_count == 0
    count = len(gates)
    depth = max(ready)
    count_ok = count <= target["max_cx"]
    depth_ok = depth <= target["max_weighted_depth"]
    failures = []
    if not correct:
        failures.append("matrix_mismatch")
    if not count_ok:
        failures.append("cx_cap_exceeded")
    if not depth_ok:
        failures.append("weighted_depth_cap_exceeded")
    resource_score = min(1.0, target["max_cx"] / max(1, count), target["max_weighted_depth"] / max(1, depth)) if correct else 0.0
    return {
        "name": target["name"], "family": target["family"], "valid": True,
        "correct": correct, "mismatch_entries": mismatch_count,
        "cx_count": count, "weighted_depth": depth,
        "max_cx": target["max_cx"], "max_weighted_depth": target["max_weighted_depth"],
        "count_ok": count_ok, "depth_ok": depth_ok,
        "solved": correct and count_ok and depth_ok,
        "resource_score": resource_score, "reason": ";".join(failures) if failures else "ok",
    }


def evaluate_document(solution, suite):
    try:
        validate_json_tree(solution)
        exact_keys(solution, ("schema_version", "circuits"), "Solution")
        integer_between(solution["schema_version"], 1, 1, "Solution schema_version")
        exact_keys(solution["circuits"], (target["name"] for target in suite["targets"]), "circuits")
    except ContractError as error:
        return invalid_report(suite, str(error))
    results = []
    for target in suite["targets"]:
        try:
            results.append(score_target(target, solution["circuits"][target["name"]]))
        except ContractError as error:
            results.append(invalid_target(target, str(error)))
    if not all(result["valid"] for result in results):
        report = invalid_report(suite, "Invalid circuit schema or non-native gate; submission rejected.")
        report["per_target"] = results
        return report
    families = defaultdict(list)
    for result in results:
        families[result["family"]].append(result["solved"])
    family_scores = {family: sum(solved) / len(solved) for family, solved in sorted(families.items())}
    solved_count = sum(result["solved"] for result in results)
    passed = solved_count == len(results)
    return {
        "valid": True, "passed": passed,
        "reason": "ok" if passed else "Every target must be correct and meet both caps; failing: " + ", ".join(result["name"] for result in results if not result["solved"]),
        "core_score": solved_count / len(results),
        "worst_family_score": min(family_scores.values()),
        "resource_score": min(result["resource_score"] for result in results),
        "solved_targets": solved_count, "total_targets": len(results),
        "family_scores": family_scores, "per_target": results,
    }


def evaluate_file(solution_path, suite):
    try:
        document = load_json_file(solution_path)
    except ContractError as error:
        return invalid_report(suite, str(error))
    return evaluate_document(document, suite)


def main():
    parser = argparse.ArgumentParser(description="Exact native-CX witness checker; no submitted code is executed.")
    parser.add_argument("solution", type=Path)
    parser.add_argument("--instances", type=Path, default=DEFAULT_INSTANCES)
    arguments = parser.parse_args()
    try:
        suite = validate_instances(load_json_file(arguments.instances))
    except ContractError as error:
        print(json.dumps({"valid": False, "passed": False, "reason": "Invalid instance bundle: " + str(error)}, allow_nan=False))
        return 2
    report = evaluate_file(arguments.solution, suite)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
