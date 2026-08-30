"""Replay the independent generation-time evaluator audit, not a participant attempt.

Run from the task directory with:
    python3 -B authoring/audits/concept_3_audit.py

Only the adjacent JSON report and disposable /tmp fixtures are written. The
generator's main function and participant attempts are never executed.
"""

import ast
import copy
import hashlib
import importlib.util
import json
import random
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[2] / "concept_3"
REPORT = SCRIPT.with_suffix(".json")


class AuditFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_checker():
    specification = importlib.util.spec_from_file_location(
        "independent_audit_hidden_checker", ROOT / "evaluator/hidden/checker.py"
    )
    checker = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(checker)
    return checker


def replay_entrypoint(submission):
    completed = subprocess.run(
        [sys.executable, "-B", str(ROOT / "evaluator/evaluate.py"),
         "--submission", str(ROOT / submission)],
        cwd="/tmp", capture_output=True, text=True, check=True, timeout=65,
    )
    return json.loads(completed.stdout)


def generator_functions():
    parsed = ast.parse((ROOT / "adversary/build.py").read_text(encoding="utf-8"))
    names = {"xor_forms", "make_circuit"}
    functions = [node for node in parsed.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    require({node.name for node in functions} == names, "Generator functions missing")
    selected = ast.Module(body=functions, type_ignores=[])
    namespace = {"random": random}
    exec(compile(selected, "<audit-generator-functions>", "exec"), namespace)
    return namespace


def parity(expression, values):
    result = 0
    for reference in expression:
        result ^= values[reference]
    return result


def independent_rows(instance, circuit):
    table = []
    for address in range(1 << instance["n"]):
        values = [1] + [(address >> bit) & 1 for bit in range(instance["n"])]
        for gate in circuit["gates"]:
            values.append(parity(gate["left"], values) * parity(gate["right"], values))
        output = 0
        for bit, expression in enumerate(circuit["outputs"]):
            output |= parity(expression, values) << bit
        table.append(output)
    return table


def independent_usage(instance, circuit):
    depths = [0] * (instance["n"] + 1)
    affine_size = 0
    for gate in circuit["gates"]:
        dependencies = gate["left"] + gate["right"]
        depths.append(1 + max((depths[reference] for reference in dependencies), default=0))
        affine_size += len(dependencies)
    output_depths = [max((depths[reference] for reference in expression), default=0)
                     for expression in circuit["outputs"]]
    affine_size += sum(map(len, circuit["outputs"]))
    products = len(circuit["gates"])
    return {"and": products, "depth": max(depths + output_depths),
            "affine": affine_size, "ancilla": products + 2 if products else 0}


def independent_structure(instance):
    coefficients = instance["table"].copy()
    for bit in range(instance["n"]):
        stride = 1 << bit
        for start in range(0, len(coefficients), 2 * stride):
            for offset in range(stride):
                coefficients[start + stride + offset] ^= coefficients[start + offset]
    degrees = [max((mask.bit_count() for mask, value in enumerate(coefficients)
                    if (value & combination).bit_count() & 1), default=0)
               for combination in range(1, 1 << instance["m"])]
    active = sum(any(value != instance["table"][address ^ (1 << bit)]
                     for address, value in enumerate(instance["table"]))
                 for bit in range(instance["n"]))
    return min(degrees), active


def compile_clean_lift(instance, circuit):
    width, output_width = instance["n"], instance["m"]
    products = len(circuit["gates"])
    scratch_left = width + output_width + products
    scratch_right = scratch_left + 1

    def affine_operations(expression, target):
        operations = []
        for reference in expression:
            if reference == 0:
                operations.append(("X", target))
            else:
                control = (reference - 1 if reference <= width
                           else width + output_width + reference - width - 1)
                operations.append(("CX", control, target))
        return operations

    forward = []
    for index, gate in enumerate(circuit["gates"]):
        preparation = (affine_operations(gate["left"], scratch_left)
                       + affine_operations(gate["right"], scratch_right))
        product = ("CCX", scratch_left, scratch_right, width + output_width + index)
        forward.extend(preparation + [product] + list(reversed(preparation)))
    output_operations = []
    for bit, expression in enumerate(circuit["outputs"]):
        output_operations.extend(affine_operations(expression, width + bit))
    operations = forward + output_operations + list(reversed(forward))
    target_register = set(range(width, width + output_width))
    require(all(not any(control in target_register for control in operation[1:-1])
                for operation in operations), "Lift uses target register as a control")
    require(all(operation[-1] >= width for operation in operations),
            "Lift modifies an address wire")
    require(sum(operation[0] == "CCX" for operation in operations) == 2 * products,
            "Lift Toffoli convention mismatch")
    workspace = products + 2 if products else 0
    return operations, width + output_width + workspace


def check_clean_lift(instance, circuit):
    operations, qubit_count = compile_clean_lift(instance, circuit)
    width, output_width = instance["n"], instance["m"]
    row_count = 1 << width
    ones = (1 << row_count) - 1
    addresses = [sum(((address >> bit) & 1) << address for address in range(row_count))
                 for bit in range(width)]
    expected = [sum(((value >> bit) & 1) << address
                    for address, value in enumerate(instance["table"]))
                for bit in range(output_width)]
    for pattern in range(3):
        initial_target = [0 if pattern == 0 else ones if pattern == 1
                          else addresses[bit % width] ^ (ones if bit % 2 else 0)
                          for bit in range(output_width)]
        qubits = addresses + initial_target + [0] * (qubit_count - width - output_width)
        for operation in operations:
            if operation[0] == "X":
                qubits[operation[1]] ^= ones
            elif operation[0] == "CX":
                qubits[operation[2]] ^= qubits[operation[1]]
            else:
                qubits[operation[3]] ^= qubits[operation[1]] & qubits[operation[2]]
        require(qubits[:width] == addresses, "Address changed during clean lift")
        require(qubits[width:width + output_width]
                == [before ^ value for before, value in zip(initial_target, expected)],
                "Clean lift target XOR mismatch")
        require(not any(qubits[width + output_width:]), "Clean lift leaves dirty workspace")
    return len(operations)


def check_positive_designs(suite, witness, provenance, positive, baseline):
    private_by_id = {circuit["id"]: circuit for circuit in witness["circuits"]}
    provenance_by_id = {record["id"]: record for record in provenance}
    positive_by_id = {record["id"]: record for record in positive["instances"]}
    baseline_by_id = {record["id"]: record for record in baseline["instances"]}
    generator = generator_functions()
    records = []
    for instance in suite["instances"]:
        identifier = instance["id"]
        circuit = private_by_id[identifier]
        recorded = provenance_by_id[identifier]
        require(len(instance["table"]) == 1 << instance["n"], "Invalid table row count")
        require(all(type(value) is int and 0 <= value < 1 << instance["m"]
                    for value in instance["table"]), "Invalid table value")
        regenerated = generator["make_circuit"](
            recorded["seed"], instance["n"], instance["m"], instance["family"]
        )
        require(regenerated == circuit, identifier + ": seed reproduction mismatch")
        require(independent_rows(instance, circuit) == instance["table"],
                identifier + ": independent scalar truth-table mismatch")
        usage = independent_usage(instance, circuit)
        require(usage == recorded["private_usage"] == positive_by_id[identifier]["usage"],
                identifier + ": resource usage mismatch")
        require(instance["caps"] == recorded["caps"], identifier + ": cap provenance mismatch")
        require(all(usage[key] <= instance["caps"][key] for key in usage),
                identifier + ": private witness exceeds caps")
        require(recorded["baseline_and"] == baseline_by_id[identifier]["usage"]["and"],
                identifier + ": baseline provenance mismatch")
        minimum_degree, active = independent_structure(instance)
        require(minimum_degree == recorded["minimum_output_combination_degree"]
                and minimum_degree >= 3, identifier + ": degree provenance mismatch")
        require(active == recorded["active_input_bits"] == instance["n"],
                identifier + ": active-input provenance mismatch")
        operation_count = check_clean_lift(instance, circuit)
        records.append({"id": identifier, "rows": len(instance["table"]),
                        "usage": usage, "caps": instance["caps"],
                        "minimum_output_combination_degree": minimum_degree,
                        "active_input_bits": active, "clean_lift_operations": operation_count,
                        "clean_lift_toffolis": 2 * len(circuit["gates"])})
    return records


def check_resources_and_rows(checker, suite, witness):
    circuits = {circuit["id"]: circuit for circuit in witness["circuits"]}
    resource_checks = 0
    row_checks = 0
    for instance in suite["instances"]:
        circuit = circuits[instance["id"]]
        boundary = copy.deepcopy(instance)
        boundary["caps"] = independent_usage(instance, circuit)
        require(checker.check(boundary, circuit)["passed"], "Exact cap boundary rejected")
        for resource in boundary["caps"]:
            bounded = copy.deepcopy(boundary)
            bounded["caps"][resource] -= 1
            result = checker.check(bounded, circuit)
            require(result["exact"] and not result["within_caps"] and not result["passed"],
                    instance["id"] + ": violated " + resource + " cap accepted")
            resource_checks += 1
        for address in [0, len(instance["table"]) // 2, len(instance["table"]) - 1]:
            for bit in [0, instance["m"] - 1]:
                altered = copy.deepcopy(instance)
                altered["table"][address] ^= 1 << bit
                result = checker.check(altered, circuit)
                require(not result["exact"] and not result["passed"], "Wrong row accepted")
                require(result["row_accuracy"] == 1 - 1 / len(instance["table"]),
                        "Wrong single-row accuracy")
                row_checks += 1
    return {"cap_equalities_accepted": len(suite["instances"]),
            "individual_cap_violations_rejected": resource_checks,
            "single_row_bit_corruptions_rejected": row_checks}


def check_edge_semantics(checker):
    instance = {"id": "tiny", "family": "audit", "n": 2, "m": 2,
                "table": [2, 0, 2, 0],
                "caps": {"and": 0, "depth": 0, "affine": 2, "ancilla": 0}}
    circuit = {"id": "tiny", "gates": [], "outputs": [[], [0, 1]]}
    require(checker.check(instance, circuit)["passed"], "Affine-only circuit rejected")
    circuit["gates"] = [{"left": [], "right": []}, {"left": [3], "right": []}]
    instance["caps"] = {"and": 2, "depth": 2, "affine": 3, "ancilla": 4}
    result = checker.check(instance, circuit)
    require(result["usage"] == instance["caps"] and result["passed"],
            "Unused product resource charges mismatch")
    instance["caps"]["depth"] = 1
    require(not checker.check(instance, circuit)["passed"], "Unused gate depth not charged")


def replace_at(payload, path, value):
    destination = payload
    for component in path[:-1]:
        destination = destination[component]
    destination[path[-1]] = value


def check_artifacts(checker, suite, witness):
    rejected = []
    with tempfile.TemporaryDirectory(prefix="qualtran-concept3-audit-", dir="/tmp") as temporary:
        directory = Path(temporary)
        ordinary = directory / "ordinary"
        ordinary.mkdir()
        artifact = ordinary / "circuits.json"

        def reject(name, payload=None, raw=None):
            artifact.write_text(raw if raw is not None else json.dumps(payload), encoding="utf-8")
            result = checker.evaluate(suite, ordinary)
            require(not result["passed"] and result["core_score"] == 0
                    and "instances" not in result, name + ": malformed artifact not rejected")
            rejected.append(name)

        expressions = [
            ("boolean reference", [True]), ("float reference", [1.0]),
            ("negative reference", [-1]), ("duplicate references", [0, 0]),
            ("unsorted references", [1, 0]), ("unavailable reference", [999999]),
            ("string reference", ["1"]), ("null reference", [None]),
            ("non-list expression", {}), ("NaN", [float("nan")]),
            ("Infinity", [float("inf")]), ("negative Infinity", [-float("inf")]),
        ]
        for name, expression in expressions:
            altered = copy.deepcopy(witness)
            altered["circuits"][0]["outputs"][0] = expression
            reject(name, altered)

        first = witness["circuits"][0]
        width = next(instance["n"] for instance in suite["instances"]
                     if instance["id"] == first["id"])
        extra = copy.deepcopy(first)
        extra["id"] = "extra"
        mutations = [
            ("self reference", ("circuits", 0, "gates", 0, "left"), [width + 1]),
            ("forward reference", ("circuits", 0, "gates", 0, "right"), [width + 2]),
            ("extra top-level field", ("metadata",), {}),
            ("extra circuit field", ("circuits", 0, "declared_and"), 0),
            ("extra gate field", ("circuits", 0, "gates", 0, "hint"), 0),
            ("missing gate field", ("circuits", 0, "gates", 0),
             {"left": first["gates"][0]["left"]}),
            ("wrong output width", ("circuits", 0, "outputs"), first["outputs"][:-1]),
            ("diagnostic gate limit", ("circuits", 0, "gates"),
             [{"left": [], "right": []}] * 50001),
            ("non-list gates", ("circuits", 0, "gates"), {}),
            ("non-list outputs", ("circuits", 0, "outputs"), {}),
            ("non-string ID", ("circuits", 0, "id"), True),
            ("duplicate circuit ID", ("circuits",), witness["circuits"] + [first]),
            ("missing circuit ID", ("circuits",), witness["circuits"][:-1]),
            ("extra circuit ID", ("circuits",), witness["circuits"] + [extra]),
        ]
        for name, path, value in mutations:
            altered = copy.deepcopy(witness)
            replace_at(altered, path, value)
            reject(name, altered)

        encoded = json.dumps(witness)
        reject("duplicate JSON root key", raw='{"circuits": [], "circuits": '
               + json.dumps(witness["circuits"]) + "}")
        reject("duplicate JSON nested key",
               raw=encoded.replace('"left":', '"left": [], "left":', 1))
        reject("overflowed float", raw=encoded.replace('"left": [', '"left": [1e309, ', 1))
        reject("oversized file", raw=encoded.ljust(8 * 1024**2 + 1))
        reject("invalid JSON", raw="{")
        reject("non-object artifact", [])
        reject("non-list circuit collection", {"circuits": {}})
        reject("non-object circuit", {"circuits": [None]})

        artifact.write_text(encoded, encoding="utf-8")
        linked_leaf = directory / "linked-leaf"
        linked_leaf.mkdir()
        (linked_leaf / "circuits.json").symlink_to(artifact)
        require(not checker.evaluate(suite, linked_leaf)["passed"], "Leaf symlink accepted")
        rejected.append("leaf symlink")
        require(not checker.evaluate(suite, directory / "missing")["passed"],
                "Missing artifact accepted")
        rejected.append("missing artifact")
        directory_artifact = directory / "directory-artifact"
        directory_artifact.mkdir()
        (directory_artifact / "circuits.json").mkdir()
        require(not checker.evaluate(suite, directory_artifact)["passed"],
                "Directory artifact accepted")
        rejected.append("non-file artifact")

        linked_parent = directory / "linked-parent"
        linked_parent.symlink_to(ordinary, target_is_directory=True)
        ancestor_symlink_accepted = checker.evaluate(suite, linked_parent)["passed"]

        altered = copy.deepcopy(witness)
        output = altered["circuits"][0]["outputs"][0]
        altered["circuits"][0]["outputs"][0] = sorted(set(output) ^ {0})
        artifact.write_text(json.dumps(altered), encoding="utf-8")
        partial = checker.evaluate(suite, ordinary)
        require(not partial["passed"] and partial["core_score"] == 5 / 6
                and partial["worst_family_score"] == 2 / 3
                and partial["resource_score"] == 1, "Partial-success scoring mismatch")

    require(len(rejected) == 37, "Unexpected parser/artifact test coverage")
    return {"schema_artifact_rejections": len(rejected), "rejected_cases": rejected,
            "ancestor_symlink_accepted": ancestor_symlink_accepted,
            "partial_success": {key: partial[key] for key in
                                ("core_score", "worst_family_score", "resource_score", "passed")},
            "temporary_fixtures_removed": not directory.exists()}


def run_audit():
    freeze = read_json(ROOT / "adversary/generation_1_freeze.json")
    before = {filename: digest(ROOT / filename) for filename in freeze["sha256"]}
    require(before == freeze["sha256"], "Frozen-file hashes do not match the manifest")
    for public, hidden in [("participant/workspace/verify.py", "evaluator/hidden/checker.py"),
                           ("participant/input/suite.json", "evaluator/hidden/suite.json")]:
        require((ROOT / public).read_bytes() == (ROOT / hidden).read_bytes(),
                "Public/hidden copies differ: " + public)
    audit_inputs = ["adversary/build.py", "adversary/provenance.json",
                    "adversary/selftest.json", "adversary/private_witness/circuits.json"]
    input_hashes = {filename: digest(ROOT / filename) for filename in audit_inputs}
    checker = load_checker()
    suite = read_json(ROOT / "evaluator/hidden/suite.json")
    witness = read_json(ROOT / "adversary/private_witness/circuits.json")
    provenance = read_json(ROOT / "adversary/provenance.json")
    selftest = read_json(ROOT / "adversary/selftest.json")
    require(len(suite["instances"]) == 6, "Expected the frozen six-instance suite")

    positive = replay_entrypoint("adversary/private_witness")
    baseline = replay_entrypoint("participant/baseline")
    require(positive["passed"] and positive["core_score"] == 1
            and all(record["exact"] and record["within_caps"] for record in positive["instances"]),
            "Private designs failed the actual hidden entry point")
    require(not baseline["passed"] and baseline["core_score"] == 0
            and all(record["exact"] and not record["within_caps"] for record in baseline["instances"]),
            "Baseline no longer exact and over budget on all six instances")
    print("Hidden entry point: private designs 6/6; baseline exact 6/6, within caps 0/6.", flush=True)
    instances = check_positive_designs(suite, witness, provenance, positive, baseline)
    rows = sum(record["rows"] for record in instances)
    require(selftest["passed"] and selftest["positive_full_row_checks"] == rows
            and selftest["negative_checks"] == 30, "Stored selftest metadata mismatch")
    print("Independent rows, provenance, resources, and clean reversible lifts passed.", flush=True)
    boundaries = check_resources_and_rows(checker, suite, witness)
    check_edge_semantics(checker)
    artifacts = check_artifacts(checker, suite, witness)
    require({filename: digest(ROOT / filename) for filename in before} == before,
            "Frozen files changed during audit; results are not a stable snapshot")
    require({filename: digest(ROOT / filename) for filename in audit_inputs} == input_hashes,
            "Private audit inputs changed during audit")

    limitations = [
        "Clean ancilla is validated under the mandated retain-products/two-scratch lift, not alternative uncomputation schedules.",
        "Ancilla caps are redundant with AND caps in this suite; multiplicative depth and affine size are representation costs, not hardware costs.",
        "The phase-free X/CNOT/Toffoli lift and target-control independence justify arbitrary-target/coherent behavior; no full statevector simulation was performed.",
        "Stored selftests cover 30 wrong-output/invalid-reference negatives; this audit adds parser, path, and individual-resource corruption coverage.",
        "Feasible designs do not establish one-hour synthesis discoverability, optimality, or hardware performance.",
        "No fresh participant attempt or expensive generation was run; infrastructure failures are not evidence of task hardness.",
    ]
    if artifacts["ancestor_symlink_accepted"]:
        limitations.insert(0, "Harmless ancestor-symlink limitation: a symlinked submission directory is accepted, but the correct artifact still undergoes full truth/resource validation; leaf symlinks are rejected.")
    return {
        "integrity": {"frozen_hashes_verified": len(before), "frozen_files_unchanged": True,
                      "public_hidden_copies_identical": True, "private_inputs_unchanged": True,
                      "freeze_manifest_sha256": digest(ROOT / "adversary/generation_1_freeze.json")},
        "positive_designs": {"passed": True, "instances": len(instances), "core_score": 1.0,
                             "independent_rows_checked": rows, "seed_and_provenance_checks": True,
                             "entrypoint_runtime_seconds": positive["runtime_seconds"]},
        "clean_reversible_lift": {"passed": True, "rows_checked": rows,
                                  "target_patterns_per_instance": 3,
                                  "address_preserved": True, "workspace_cleared": True,
                                  "target_register_never_controls": True,
                                  "two_toffolis_per_product": True},
        "baseline": {"exact_instances": 6, "within_caps_instances": 0, "core_score": 0.0,
                     "entrypoint_runtime_seconds": baseline["runtime_seconds"]},
        "corruption_checks": {**boundaries, **artifacts, "edge_semantics_passed": True},
        "recorded_selftest": {"negative_checks": selftest["negative_checks"],
                              "positive_full_row_checks": selftest["positive_full_row_checks"]},
        "instances": instances,
        "limitations": limitations,
        "references": ["participant/TASK.md:14", "participant/workspace/interface.md:16",
                       "evaluator/hidden/checker.py:20", "evaluator/hidden/checker.py:39",
                       "evaluator/hidden/checker.py:62", "evaluator/hidden/checker.py:74",
                       "evaluator/evaluate.py:7", "adversary/build.py:109",
                       "adversary/build.py:137", "adversary/provenance.json:3",
                       "adversary/generation_1_freeze.json:5"],
    }


def main():
    started = time.monotonic()
    report = {"format_version": 1, "audit_kind": "independent_generation_time_evaluator_audit",
              "scope": "concept_3", "fresh_participant_attempt": False,
              "frozen_or_attempt_files_written": False,
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "script_sha256": digest(SCRIPT)}
    try:
        report.update(run_audit())
        report.update(status="passed", serious_issues_found=False)
    except Exception as error:
        report.update(status="failed" if isinstance(error, AuditFailure) else "error",
                      serious_issues_found=None, error_type=type(error).__name__,
                      error=str(error), task_hardness_inference=False)
        traceback.print_exc()
    report["runtime_seconds"] = round(time.monotonic() - started, 6)
    REPORT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(REPORT),
                      "runtime_seconds": report["runtime_seconds"]}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
