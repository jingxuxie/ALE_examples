import argparse
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

import networkx as nx
import numpy as np


CONCEPT_ROOT = Path(__file__).resolve().parents[1]


def import_file(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


evaluator = import_file("private_evaluator", CONCEPT_ROOT / "evaluator" / "evaluate.py")
checker, SUITE, MANIFEST = evaluator.load_trusted()
baseline = import_file("baseline_solver", CONCEPT_ROOT / "participant" / "baseline" / "solve.py")
WITNESS = checker.load_json_file(CONCEPT_ROOT / "evaluator" / "hidden" / "planted_solution.json")
BASELINE = checker.load_json_file(CONCEPT_ROOT / "adversary" / "weak_baseline" / "solution.json")


def dense_matrix(qubit_count, gates):
    result = np.eye(qubit_count, dtype=np.uint8)
    for control, target in gates:
        elementary = np.eye(qubit_count, dtype=np.uint8)
        elementary[target, control] = 1
        result = (elementary @ result) % 2
    return result.tolist()


def dag_depth(native_cx, gates):
    if not gates:
        return 0
    durations = {(control, target): duration for control, target, duration in native_cx}
    graph = nx.DiGraph()
    graph.add_node(-1)
    for position, gate in enumerate(gates):
        duration = durations[tuple(gate)]
        graph.add_edge(-1, position, weight=duration)
        for previous in range(position):
            if set(gate).intersection(gates[previous]):
                graph.add_edge(previous, position, weight=duration)
    return nx.dag_longest_path_length(graph)


def toy_target(gates, qubit_count=4):
    native_cx = [[0, 1, 2], [1, 0, 5], [1, 2, 3], [2, 1, 1], [2, 3, 4], [3, 2, 2]]
    if qubit_count != 4:
        native_cx = []
        for qubit in range(qubit_count - 1):
            native_cx.extend(([qubit, qubit + 1, qubit % 5 + 1], [qubit + 1, qubit, (qubit + 2) % 5 + 1]))
    return {
        "name": "toy", "family": "toy", "n_qubits": qubit_count,
        "matrix": dense_matrix(qubit_count, gates), "native_cx": native_cx,
        "max_cx": 20_000, "max_weighted_depth": 2_000_000,
    }


def toy_suite(target):
    return {"schema_version": 1, "suite_id": "native_cx_linear_v1", "targets": [target]}


class EvaluatorTests(unittest.TestCase):
    def scratch(self):
        temporary = tempfile.TemporaryDirectory(prefix="selftest_", dir=CONCEPT_ROOT / "adversary")
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def assert_rejected(self, document):
        report = checker.evaluate_document(document, SUITE)
        self.assertFalse(report["valid"])
        self.assertFalse(report["passed"])
        for field in ("core_score", "worst_family_score", "resource_score"):
            self.assertEqual(report[field], 0.0)
        return report

    def clone_evaluator(self, root):
        destination = root / "evaluator"
        (destination / "hidden").mkdir(parents=True)
        for relative in ("evaluate.py", "_checker.py", "frozen.json", "hidden/instances.json"):
            shutil.copyfile(CONCEPT_ROOT / "evaluator" / relative, destination / relative)
        return destination

    def test_public_and_trusted_sources_are_identical(self):
        self.assertEqual((CONCEPT_ROOT / "participant" / "workspace" / "checker.py").read_bytes(), (CONCEPT_ROOT / "evaluator" / "_checker.py").read_bytes())
        self.assertEqual((CONCEPT_ROOT / "participant" / "input" / "instances.json").read_bytes(), (CONCEPT_ROOT / "evaluator" / "hidden" / "instances.json").read_bytes())

    def test_all_private_witnesses_pass(self):
        report = evaluator.evaluate(CONCEPT_ROOT / "evaluator" / "hidden" / "planted_solution.json")
        self.assertTrue(report["valid"])
        self.assertTrue(report["passed"])
        self.assertEqual(report["solved_targets"], 4)
        for field in ("core_score", "worst_family_score", "resource_score"):
            self.assertEqual(report[field], 1.0)
        metadata = checker.load_json_file(CONCEPT_ROOT / "evaluator" / "hidden" / "generation_metadata.json")
        for result, private_case in zip(report["per_target"], metadata["private_cases"]):
            self.assertEqual(result["cx_count"], private_case["cx_count"])
            self.assertEqual(result["weighted_depth"], private_case["weighted_depth"])
            self.assertEqual(result["max_cx"], (result["cx_count"] * 106 + 99) // 100)
            self.assertEqual(result["max_weighted_depth"], (result["weighted_depth"] * 108 + 99) // 100)

    def test_dense_numpy_matrix_oracle(self):
        for target in SUITE["targets"]:
            with self.subTest(target=target["name"]):
                gates = WITNESS["circuits"][target["name"]]
                self.assertEqual(dense_matrix(target["n_qubits"], gates), target["matrix"])

    def test_independent_networkx_schedule_oracle(self):
        for target in SUITE["targets"]:
            gates = WITNESS["circuits"][target["name"]]
            with self.subTest(target=target["name"]):
                self.assertEqual(checker.score_target(target, gates)["weighted_depth"], dag_depth(target["native_cx"], gates))

    def test_all_basis_vectors_exact(self):
        for target in SUITE["targets"]:
            for column in range(target["n_qubits"]):
                state = [0] * target["n_qubits"]
                state[column] = 1
                for control, destination in WITNESS["circuits"][target["name"]]:
                    state[destination] ^= state[control]
                self.assertEqual(state, [row[column] for row in target["matrix"]])

    def test_random_small_circuits_against_independent_oracles(self):
        random_source = random.Random(918_274)
        for qubit_count in range(2, 9):
            for repetition in range(16):
                target = toy_target([], qubit_count)
                gates = [list(random_source.choice(target["native_cx"])[:2]) for position in range(random_source.randrange(41))]
                target["matrix"] = dense_matrix(qubit_count, gates)
                checker.validate_instances(toy_suite(target))
                result = checker.score_target(target, gates)
                self.assertTrue(result["correct"])
                self.assertEqual(result["weighted_depth"], dag_depth(target["native_cx"], gates))
                recovered = baseline.synthesize(target)
                self.assertEqual(dense_matrix(qubit_count, recovered), target["matrix"])

    def test_baseline_exact_and_fails_every_cap(self):
        report = evaluator.evaluate(CONCEPT_ROOT / "adversary" / "weak_baseline" / "solution.json")
        self.assertTrue(report["valid"])
        self.assertFalse(report["passed"])
        self.assertEqual(report["core_score"], 0.0)
        self.assertEqual(report["worst_family_score"], 0.0)
        self.assertGreater(report["resource_score"], 0.0)
        for result in report["per_target"]:
            self.assertTrue(result["correct"])
            self.assertFalse(result["count_ok"])
            self.assertFalse(result["depth_ok"])

    def test_routed_cx_restores_intermediate_wires(self):
        for qubit_count in range(2, 9):
            neighbors = [[neighbor for neighbor in (qubit - 1, qubit + 1) if 0 <= neighbor < qubit_count] for qubit in range(qubit_count)]
            for control in range(qubit_count):
                for target in range(qubit_count):
                    if control != target:
                        routed = baseline.routed_cx(neighbors, control, target)
                        self.assertEqual(dense_matrix(qubit_count, routed), dense_matrix(qubit_count, [[control, target]]))
                        self.assertTrue(all(destination in neighbors[source] for source, destination in routed))

    def test_participant_only_relocation_runs(self):
        root = self.scratch()
        public = root / "participant"
        shutil.copytree(CONCEPT_ROOT / "participant", public, ignore=shutil.ignore_patterns("__pycache__"))
        artifact = root / "output" / "solution.json"
        completed = subprocess.run([sys.executable, "-I", "-B", str(public / "baseline" / "solve.py"), "--output", str(artifact)], capture_output=True, text=True, timeout=30, cwd=root)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(checker.load_json_file(artifact), BASELINE)
        checked = subprocess.run([sys.executable, "-I", "-B", str(public / "workspace" / "checker.py"), str(artifact)], capture_output=True, text=True, timeout=30, cwd=root)
        self.assertEqual(checked.returncode, 1, checked.stderr)
        self.assertTrue(json.loads(checked.stdout)["valid"])

    def test_row_orientation_and_temporal_order(self):
        target = toy_target([[0, 1], [1, 2]], 3)
        self.assertEqual(target["matrix"], [[1, 0, 0], [1, 1, 0], [1, 1, 1]])
        self.assertTrue(checker.score_target(target, [[0, 1], [1, 2]])["correct"])
        self.assertFalse(checker.score_target(target, [[1, 2], [0, 1]])["correct"])
        self.assertFalse(checker.score_target(target, [[1, 0], [2, 1]])["correct"])

    def test_weighted_disjoint_parallelism(self):
        gates = [[0, 1], [2, 3], [1, 2]]
        self.assertEqual(checker.score_target(toy_target(gates), gates)["weighted_depth"], 7)
        self.assertEqual(checker.score_target(toy_target(gates[:2]), gates[:2])["weighted_depth"], 4)

    def test_shared_control_serialization(self):
        gates = [[1, 0], [1, 2]]
        self.assertEqual(checker.score_target(toy_target(gates), gates)["weighted_depth"], 8)

    def test_direction_specific_durations(self):
        self.assertEqual(checker.score_target(toy_target([[0, 1]]), [[0, 1]])["weighted_depth"], 2)
        self.assertEqual(checker.score_target(toy_target([[1, 0]]), [[1, 0]])["weighted_depth"], 5)

    def test_cancellation_not_free(self):
        target = toy_target([])
        result = checker.score_target(target, [[0, 1], [0, 1]])
        self.assertTrue(result["correct"])
        self.assertEqual(result["cx_count"], 2)
        self.assertEqual(result["weighted_depth"], 4)

    def test_empty_identity_and_empty_nonidentity(self):
        result = checker.score_target(toy_target([]), [])
        self.assertTrue(result["solved"])
        self.assertEqual((result["cx_count"], result["weighted_depth"]), (0, 0))
        self.assertFalse(checker.score_target(SUITE["targets"][0], [])["correct"])

    def test_count_and_depth_equality(self):
        gates = [[0, 1], [2, 3], [1, 2]]
        target = toy_target(gates)
        target["max_cx"] = 3
        target["max_weighted_depth"] = 7
        self.assertTrue(checker.score_target(target, gates)["solved"])

    def test_count_one_over_independently_fails(self):
        gates = [[0, 1], [2, 3], [1, 2]]
        target = toy_target(gates)
        target["max_cx"] = 2
        result = checker.score_target(target, gates)
        self.assertTrue(result["correct"] and result["depth_ok"])
        self.assertFalse(result["count_ok"] or result["solved"])

    def test_weighted_depth_one_over_independently_fails(self):
        gates = [[0, 1], [2, 3], [1, 2]]
        target = toy_target(gates)
        target["max_weighted_depth"] = 6
        result = checker.score_target(target, gates)
        self.assertTrue(result["correct"] and result["count_ok"])
        self.assertFalse(result["depth_ok"] or result["solved"])

    def test_altered_witness_partial_success_never_passes(self):
        changed = copy.deepcopy(WITNESS)
        changed["circuits"]["mesh_22"].pop()
        report = checker.evaluate_document(changed, SUITE)
        self.assertTrue(report["valid"])
        self.assertFalse(report["passed"])
        self.assertEqual(report["core_score"], 0.75)
        self.assertEqual(report["worst_family_score"], 0.5)
        self.assertEqual(report["resource_score"], 0.0)
        self.assertFalse(report["per_target"][0]["correct"])

    def test_altered_matrix_rejects_previous_witness(self):
        changed = copy.deepcopy(SUITE)
        matrix = changed["targets"][0]["matrix"]
        matrix[0] = [first ^ second for first, second in zip(matrix[0], matrix[1])]
        checker.validate_instances(changed)
        report = checker.evaluate_document(WITNESS, changed)
        self.assertTrue(report["valid"])
        self.assertFalse(report["passed"])
        self.assertEqual(report["core_score"], 0.75)

    def test_transposed_matrix_not_equivalent(self):
        changed = copy.deepcopy(SUITE)
        changed["targets"][0]["matrix"] = [list(column) for column in zip(*changed["targets"][0]["matrix"])]
        checker.validate_instances(changed)
        self.assertFalse(checker.evaluate_document(WITNESS, changed)["per_target"][0]["correct"])

    def test_reversed_witness_not_equivalent(self):
        changed = copy.deepcopy(WITNESS)
        changed["circuits"]["mesh_22"].reverse()
        self.assertFalse(checker.evaluate_document(changed, SUITE)["per_target"][0]["correct"])

    def test_resource_score_is_worst_target_not_mean(self):
        report = checker.evaluate_document(BASELINE, SUITE)
        expected = min(min(1.0, result["max_cx"] / result["cx_count"], result["max_weighted_depth"] / result["weighted_depth"]) for result in report["per_target"])
        self.assertEqual(report["resource_score"], expected)
        self.assertTrue(math.isfinite(expected))

    def test_missing_or_unknown_target_rejects_whole_artifact(self):
        changed = copy.deepcopy(WITNESS)
        del changed["circuits"]["mesh_22"]
        self.assert_rejected(changed)
        changed = copy.deepcopy(WITNESS)
        changed["circuits"]["extra"] = []
        self.assert_rejected(changed)

    def test_unknown_keys_and_claimed_metrics_rejected(self):
        for key, value in (("passed", 1), ("layout", []), ("matrix", []), ("cost", 0)):
            with self.subTest(key=key):
                changed = copy.deepcopy(WITNESS)
                changed[key] = value
                self.assert_rejected(changed)

    def test_wrong_root_and_schema_version(self):
        for document in ([], 1, "string", {}, {"schema_version": 2, "circuits": WITNESS["circuits"]}):
            with self.subTest(document_type=type(document).__name__):
                self.assert_rejected(document)

    def test_boolean_null_float_and_nonfinite_values(self):
        for value in (True, False, None, 0.0, 1.0, float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=repr(value)):
                changed = copy.deepcopy(WITNESS)
                changed["circuits"]["mesh_22"][0][0] = value
                self.assert_rejected(changed)
        changed = copy.deepcopy(WITNESS)
        changed["schema_version"] = True
        self.assert_rejected(changed)

    def test_noninteger_number_syntax_rejected(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e309", "-1e309", "1.0", "1e0", "-0.0", "true", "false", "null"):
            with self.subTest(token=token), self.assertRaises(checker.ContractError):
                checker.load_json_bytes(('{"schema_version":' + token + ',"circuits":{}}').encode())

    def test_duplicate_plain_and_escaped_keys(self):
        payloads = (
            b'{"schema_version":1,"schema_version":1,"circuits":{}}',
            b'{"schema_version":1,"circuits":{"mesh_22":[],"mesh_22":[]}}',
            b'{"schema_version":1,"circuits":{"mesh_22":[],"\\u006desh_22":[]}}',
        )
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(checker.ContractError):
                checker.load_json_bytes(payload)

    def test_malformed_json_and_utf8(self):
        for payload in (b"", b"{", b"{} []", b"{} garbage", b"\xff", b"\xef\xbb\xbf{}", b'{"schema_version":01}', b'{"schema_version":+1}', b'{"schema_version":1,}'):
            with self.subTest(payload=repr(payload)), self.assertRaises(checker.ContractError):
                checker.load_json_bytes(payload)

    def test_trailing_whitespace_and_key_order_allowed(self):
        reordered = {"circuits": dict(reversed(list(WITNESS["circuits"].items()))), "schema_version": 1}
        document = checker.load_json_bytes(json.dumps(reordered).encode() + b"\n\t ")
        self.assertTrue(checker.evaluate_document(document, SUITE)["passed"])

    def test_wrong_gate_shapes(self):
        for gate in (0, "CX", [], [0], [0, 1, 2], {"control": 0, "target": 1}):
            with self.subTest(gate=gate):
                changed = copy.deepcopy(WITNESS)
                changed["circuits"]["mesh_22"][0] = gate
                self.assert_rejected(changed)
        changed = copy.deepcopy(WITNESS)
        changed["circuits"]["mesh_22"] = {"gates": []}
        self.assert_rejected(changed)

    def test_out_of_range_self_loop_and_non_native(self):
        target = SUITE["targets"][0]
        native = {tuple(instruction[:2]) for instruction in target["native_cx"]}
        non_native = next([control, destination] for control in range(target["n_qubits"]) for destination in range(target["n_qubits"]) if control != destination and (control, destination) not in native)
        for gate in ([-1, 0], [0, target["n_qubits"]], [0, 0], non_native, ["0", 1]):
            with self.subTest(gate=gate):
                changed = copy.deepcopy(WITNESS)
                changed["circuits"]["mesh_22"][0] = gate
                self.assert_rejected(changed)

    def test_oversized_gate_list(self):
        changed = copy.deepcopy(WITNESS)
        changed["circuits"]["mesh_22"] = [changed["circuits"]["mesh_22"][0]] * (checker.MAX_GATES_PER_TARGET + 1)
        self.assert_rejected(changed)

    def test_maximum_gate_list_is_syntactically_allowed(self):
        target = toy_target([])
        target["max_cx"] = 1
        result = checker.score_target(target, [[0, 1]] * checker.MAX_GATES_PER_TARGET)
        self.assertTrue(result["valid"] and result["correct"])
        self.assertFalse(result["count_ok"])

    def test_oversized_file_and_bounded_read(self):
        path = self.scratch() / "solution.json"
        with path.open("wb") as stream:
            stream.truncate(checker.MAX_BYTES + 1)
        self.assertFalse(evaluator.evaluate(path)["valid"])
        with self.assertRaises(checker.ContractError):
            checker.load_json_bytes(b" " * (checker.MAX_BYTES + 1))

    def test_oversized_integer_and_strings(self):
        for payload in (b"9223372036854775808", b"-9223372036854775808", b"9" * 10_000, json.dumps("x" * 129).encode(), ("{\"" + "x" * 129 + "\":0}").encode()):
            with self.subTest(length=len(payload)), self.assertRaises(checker.ContractError):
                checker.load_json_bytes(payload)
        self.assertEqual(checker.load_json_bytes(b"9223372036854775807"), checker.MAX_INTEGER)

    def test_depth_and_node_limits(self):
        for payload in (b"[" * 2000 + b"0" + b"]" * 2000, b"[" + b"0," * checker.MAX_JSON_NODES + b"0]"):
            with self.assertRaises(checker.ContractError):
                checker.load_json_bytes(payload)

    def test_missing_file_directory_symlink_fifo(self):
        root = self.scratch()
        self.assertFalse(evaluator.evaluate(root / "missing.json")["valid"])
        self.assertFalse(evaluator.evaluate(root)["valid"])
        directory = root / "directory"
        directory.mkdir()
        with self.assertRaises(checker.ContractError):
            checker.load_json_file(directory)
        symlink = root / "link.json"
        symlink.symlink_to(CONCEPT_ROOT / "evaluator" / "hidden" / "planted_solution.json")
        self.assertFalse(evaluator.evaluate(symlink)["valid"])
        fifo = root / "pipe.json"
        os.mkfifo(fifo)
        self.assertFalse(evaluator.evaluate(fifo)["valid"])

    def test_invalid_artifact_cli_emits_json(self):
        path = self.scratch() / "solution.json"
        path.write_bytes(b'{"schema_version": true}')
        completed = subprocess.run([sys.executable, "-I", "-B", str(CONCEPT_ROOT / "evaluator" / "evaluate.py"), str(path)], capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 1)
        self.assertFalse(json.loads(completed.stdout)["valid"])

    def test_file_directory_and_option_cli_interfaces(self):
        root = self.scratch()
        artifact = root / "solution.json"
        artifact.write_text(json.dumps(WITNESS), encoding="utf-8")
        for options in ([str(artifact)], ["--solution", str(artifact)], ["--submission", str(root)]):
            report_path = root / "score.json"
            completed = subprocess.run([sys.executable, "-I", "-B", str(CONCEPT_ROOT / "evaluator" / "evaluate.py"), *options, "--output", str(report_path)], capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report, json.loads(report_path.read_text(encoding="utf-8")))
            self.assertTrue(report["passed"])

    def test_report_cannot_overwrite_artifact(self):
        path = self.scratch() / "solution.json"
        original = json.dumps(WITNESS).encode()
        path.write_bytes(original)
        completed = subprocess.run([sys.executable, "-I", "-B", str(CONCEPT_ROOT / "evaluator" / "evaluate.py"), str(path), "--output", str(path)], capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(path.read_bytes(), original)

    def test_frozen_checker_hash_tamper_fails_closed(self):
        root = self.scratch()
        copied = self.clone_evaluator(root)
        with (copied / "_checker.py").open("ab") as stream:
            stream.write(b"\n")
        with self.assertRaises(evaluator.IntegrityError):
            evaluator.load_trusted(copied)
        completed = subprocess.run([sys.executable, "-I", "-B", str(copied / "evaluate.py"), str(CONCEPT_ROOT / "evaluator" / "hidden" / "planted_solution.json")], capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 2)
        self.assertTrue(json.loads(completed.stdout)["evaluator_error"])

    def test_frozen_matrix_and_caps_tamper_fails_closed(self):
        for mutation in ("matrix", "cap"):
            with self.subTest(mutation=mutation):
                root = self.scratch()
                copied = self.clone_evaluator(root)
                changed = copy.deepcopy(SUITE)
                if mutation == "matrix":
                    changed["targets"][0]["matrix"][0][0] ^= 1
                else:
                    changed["targets"][0]["max_cx"] += 1
                (copied / "hidden" / "instances.json").write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(evaluator.IntegrityError):
                    evaluator.load_trusted(copied)

    def test_evaluator_ignores_mutated_public_files_and_needs_no_seed(self):
        root = self.scratch()
        copied = self.clone_evaluator(root)
        public = root / "participant"
        (public / "workspace").mkdir(parents=True)
        (public / "input").mkdir()
        (public / "workspace" / "checker.py").write_bytes(b"This is deliberately not Python code.")
        changed = copy.deepcopy(SUITE)
        changed["targets"][0]["matrix"][0][0] ^= 1
        changed["targets"][0]["max_cx"] = 1
        (public / "input" / "instances.json").write_text(json.dumps(changed), encoding="utf-8")
        self.assertFalse((copied / "hidden" / "seed.json").exists())
        self.assertFalse((copied / "hidden" / "planted_solution.json").exists())
        report = evaluator.evaluate(CONCEPT_ROOT / "evaluator" / "hidden" / "planted_solution.json", copied)
        self.assertTrue(report["passed"])

    def test_submitted_code_is_never_executed(self):
        root = self.scratch()
        marker = root / "executed"
        artifact = root / "solution.json"
        artifact.write_text("__import__('pathlib').Path(" + repr(str(marker)) + ").touch()", encoding="utf-8")
        self.assertFalse(evaluator.evaluate(artifact)["valid"])
        self.assertFalse(marker.exists())

    def test_invalid_instance_shapes_bits_and_rank(self):
        mutations = []
        changed = copy.deepcopy(SUITE)
        changed["targets"][0]["matrix"][0][0] = True
        mutations.append(changed)
        changed = copy.deepcopy(SUITE)
        changed["targets"][0]["matrix"][0].pop()
        mutations.append(changed)
        changed = copy.deepcopy(SUITE)
        changed["targets"][0]["matrix"][0] = changed["targets"][0]["matrix"][1][:]
        mutations.append(changed)
        changed = copy.deepcopy(SUITE)
        changed["targets"][0]["n_qubits"] = 22.0
        mutations.append(changed)
        for changed in mutations:
            with self.assertRaises(checker.ContractError):
                checker.validate_instances(changed)

    def test_invalid_hardware_and_cap_contracts(self):
        for mutation in ("zero_duration", "duplicate", "one_direction", "disconnected", "self_loop", "bad_cap"):
            changed = copy.deepcopy(SUITE)
            target = changed["targets"][0]
            if mutation == "zero_duration":
                target["native_cx"][0][2] = 0
            elif mutation == "duplicate":
                target["native_cx"].append(target["native_cx"][0])
            elif mutation == "one_direction":
                target["native_cx"].pop()
            elif mutation == "disconnected":
                target["native_cx"] = [gate for gate in target["native_cx"] if 0 not in gate[:2]]
            elif mutation == "self_loop":
                target["native_cx"][0][1] = target["native_cx"][0][0]
            else:
                target["max_weighted_depth"] = False
            with self.subTest(mutation=mutation), self.assertRaises(checker.ContractError):
                checker.validate_instances(changed)

    def test_hardware_shape_and_private_program_properties(self):
        generator = import_file("private_generator", CONCEPT_ROOT / "evaluator" / "hidden" / "generate_instances.py")
        for target in SUITE["targets"]:
            graph = nx.Graph()
            graph.add_nodes_from(range(target["n_qubits"]))
            graph.add_edges_from(instruction[:2] for instruction in target["native_cx"])
            self.assertTrue(nx.is_connected(graph))
            self.assertEqual({degree for node, degree in graph.degree()}, {2, 3})
            gates = WITNESS["circuits"][target["name"]]
            self.assertTrue(generator.sufficiently_mixed(target["matrix"], target["native_cx"], gates))
            for position, (control, destination) in enumerate(gates):
                self.assertFalse(generator.would_cancel(gates[:position], control, destination))

    def test_private_seed_reproduces_frozen_release(self):
        completed = subprocess.run([sys.executable, "-I", "-B", str(CONCEPT_ROOT / "evaluator" / "hidden" / "generate_instances.py"), "--verify"], capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["verified"])

    def test_private_generator_refuses_overwrite(self):
        completed = subprocess.run([sys.executable, "-I", "-B", str(CONCEPT_ROOT / "evaluator" / "hidden" / "generate_instances.py")], capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("Refusing to replace", completed.stderr)


class RecordingResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.successes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test.id())


def main():
    parser = argparse.ArgumentParser(description="Privileged evaluator selftests; does not launch a fresh solver.")
    parser.add_argument("--report", type=Path, default=CONCEPT_ROOT / "adversary" / "selftests.json")
    arguments = parser.parse_args()
    started = time.monotonic()
    tests = unittest.defaultTestLoader.loadTestsFromTestCase(EvaluatorTests)
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordingResult).run(tests)
    report = {
        "passed": result.wasSuccessful(), "tests_run": result.testsRun,
        "duration_seconds": time.monotonic() - started,
        "successes": result.successes,
        "failures": [{"test": test.id(), "traceback": traceback} for test, traceback in result.failures],
        "errors": [{"test": test.id(), "traceback": traceback} for test, traceback in result.errors],
        "skipped": [{"test": test.id(), "reason": reason} for test, reason in result.skipped],
        "numpy_version": np.__version__, "networkx_version": nx.__version__,
        "fresh_agents_run": 0,
    }
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "tests_run": report["tests_run"], "report": str(arguments.report)}, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
