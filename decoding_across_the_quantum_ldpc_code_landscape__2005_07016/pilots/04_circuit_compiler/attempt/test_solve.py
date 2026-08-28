import argparse
import gc
import io
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
import unittest

from solve import compile_case, compile_terms, prepare_operations, reverse_instructions, write_answer


PARTICIPANT = Path(__file__).resolve().parent.parent / "participant"
sys.dont_write_bytecode = True
sys.path.append(str(PARTICIPANT / "workspace"))
from weak import compile_case as forward_compile


def expand(operations):
    for operation in operations:
        if operation["op"] == "REPEAT":
            for repetition in range(operation["count"]):
                yield from expand(operation["body"])
        else:
            yield operation


def make_case(num_qubits, operations, num_observables=3):
    measurements = 0
    detectors = 0
    for operation in expand(operations):
        if operation["op"] in ("M", "MX"):
            measurements += len(operation["qubits"])
        elif operation["op"] == "DETECTOR":
            detectors += 1
    return {"schema_version": 1, "case_id": "authored_test",
            "num_qubits": num_qubits, "num_measurements": measurements,
            "num_detectors": detectors, "num_observables": num_observables,
            "operations": operations}


def canonical(answer):
    result = {}
    for term in answer["errors"]:
        detectors = term["detectors"]
        observables = term["observables"]
        assert detectors == sorted(set(detectors))
        assert observables == sorted(set(observables))
        assert detectors or observables
        assert all(0 <= detector < answer["num_detectors"] for detector in detectors)
        assert all(0 <= observable < answer["num_observables"] for observable in observables)
        assert 0 < term["probability"] <= 1
        key = (tuple(detectors), tuple(observables))
        assert key not in result
        result[key] = term["probability"]
    return result


def random_fault(generator, num_qubits):
    support = generator.sample(range(num_qubits), generator.randint(1, min(num_qubits, 4)))
    return {"op": "ERROR", "qubits": support,
            "paulis": [generator.choice("XYZI") for qubit in support],
            "probability": generator.choice([0, 1e-15, 1e-7, 0.003, 0.1, 0.2, 0.5, 0.9, 1.0])}


def random_gate(generator, num_qubits):
    name = generator.choice(["H", "S", "S_DAG", "CX", "CZ", "SWAP"])
    if name in ("H", "S", "S_DAG") or num_qubits == 1:
        if num_qubits == 1:
            name = generator.choice(["H", "S", "S_DAG"])
        qubits = [generator.randrange(num_qubits) for index in range(generator.randint(0, 5))]
    else:
        qubits = []
        for pair in range(generator.randint(1, 4)):
            qubits.extend(generator.sample(range(num_qubits), 2))
    return {"op": name, "qubits": qubits}


def random_case(seed):
    generator = random.Random(seed)
    num_qubits = generator.randint(1, 9)
    operations = []
    measurements = 0
    for step in range(generator.randint(15, 65)):
        choice = generator.randrange(8)
        if choice <= 1:
            operations.append(random_gate(generator, num_qubits))
        elif choice <= 3:
            operations.append(random_fault(generator, num_qubits))
        elif choice == 4:
            qubits = [generator.randrange(num_qubits) for index in range(generator.randint(0, 5))]
            operations.append({"op": generator.choice(["M", "MX"]), "qubits": qubits})
            measurements += len(qubits)
        elif choice == 5:
            operations.append({"op": generator.choice(["R", "RX"]),
                               "qubits": generator.sample(range(num_qubits), generator.randrange(num_qubits + 1))})
        elif choice == 6 and measurements:
            records = [-generator.randint(1, measurements) for index in range(generator.randint(0, 8))]
            if generator.randrange(2):
                operations.append({"op": "DETECTOR", "records": records})
            else:
                operations.append({"op": "OBSERVABLE", "index": generator.randrange(3), "records": records})
        else:
            operations.append({"op": "TICK"})
    return make_case(num_qubits, operations)


def echo_case(seed):
    generator = random.Random(seed)
    num_qubits = generator.randint(2, 8)
    operations = []
    for basis in ("Z", "X"):
        operations.append({"op": "R" if basis == "Z" else "RX", "qubits": list(range(num_qubits))})
        gates = [random_gate(generator, num_qubits) for index in range(12)]
        for gate in gates:
            operations.extend([gate, random_fault(generator, num_qubits)])
        for gate in reversed(gates):
            inverse = dict(gate)
            if inverse["op"] == "S":
                inverse["op"] = "S_DAG"
            elif inverse["op"] == "S_DAG":
                inverse["op"] = "S"
            elif inverse["op"] in ("CX", "CZ", "SWAP"):
                qubits = inverse["qubits"]
                inverse["qubits"] = [qubit for position in range(len(qubits) - 2, -1, -2)
                                     for qubit in qubits[position:position + 2]]
            operations.extend([inverse, random_fault(generator, num_qubits)])
        operations.append({"op": "M" if basis == "Z" else "MX", "qubits": list(range(num_qubits))})
        for offset in range(-num_qubits, 0):
            operations.append({"op": "DETECTOR", "records": [offset]})
        operations.append({"op": "OBSERVABLE", "index": generator.randrange(3),
                           "records": list(range(-num_qubits, 0))})
    return make_case(num_qubits, operations)


def hgp_case(size, rounds):
    generator = random.Random(731)
    first_order = list(range(size))
    second_order = list(range(size))
    generator.shuffle(first_order)
    generator.shuffle(second_order)
    degree = min(size, 3)
    first_rows = [{first_order[(row + offset) % size] for offset in range(degree)}
                  for row in range(size)]
    second_rows = [{second_order[(row + offset) % size] for offset in range(degree)}
                   for row in range(size)]
    first_columns = [{row for row in range(size) if column in first_rows[row]}
                     for column in range(size)]
    second_columns = [{row for row in range(size) if column in second_rows[row]}
                      for column in range(size)]
    block = size * size
    num_data = 2 * block
    x_checks = []
    z_checks = []
    for first in range(size):
        for second in range(size):
            x_checks.append(sorted({column * size + second for column in first_rows[first]}
                                   | {block + first * size + row for row in second_columns[second]}))
            z_checks.append(sorted({first * size + column for column in second_rows[second]}
                                   | {block + row * size + second for row in first_columns[first]}))
    x_ancillas = list(range(num_data, num_data + block))
    z_ancillas = list(range(num_data + block, num_data + 2 * block))
    extraction = []
    for qubit in range(num_data):
        for pauli in "XYZ":
            extraction.append({"op": "ERROR", "qubits": [qubit], "paulis": [pauli], "probability": 0.001})
    for checks, ancillas, basis in ((x_checks, x_ancillas, "X"), (z_checks, z_ancillas, "Z")):
        extraction.append({"op": "RX" if basis == "X" else "R", "qubits": ancillas})
        for support, ancilla in zip(checks, ancillas):
            extraction.append({"op": "ERROR", "qubits": [ancilla],
                               "paulis": ["Z" if basis == "X" else "X"], "probability": 0.002})
            for qubit in support:
                pair = [ancilla, qubit] if basis == "X" else [qubit, ancilla]
                extraction.append({"op": "CX", "qubits": pair})
                for pauli in "XYZ":
                    extraction.append({"op": "ERROR", "qubits": pair,
                                       "paulis": [pauli, pauli], "probability": 0.001})
        extraction.append({"op": "MX" if basis == "X" else "M", "qubits": ancillas})
    first_detectors = [{"op": "DETECTOR", "records": [offset]} for offset in range(-block, 0)]
    repeated_detectors = [{"op": "DETECTOR", "records": [offset, offset - num_data]}
                          for offset in range(-num_data, 0)]
    operations = [{"op": "R", "qubits": list(range(num_data))}] + extraction + first_detectors
    operations.append({"op": "REPEAT", "count": rounds - 1,
                       "body": extraction + repeated_detectors + [{"op": "TICK"}]})
    operations.append({"op": "M", "qubits": list(range(num_data))})
    for check, support in enumerate(z_checks):
        operations.append({"op": "DETECTOR", "records": [qubit - num_data for qubit in support]
                           + [check - block - num_data]})
    operations.append({"op": "OBSERVABLE", "index": 0, "records": list(range(-num_data, 0))})
    return make_case(4 * block, operations, 1)


class CompilerTests(unittest.TestCase):
    def assert_answers_equal(self, actual, expected):
        self.assertEqual(actual["schema_version"], expected["schema_version"])
        self.assertEqual(actual["num_detectors"], expected["num_detectors"])
        self.assertEqual(actual["num_observables"], expected["num_observables"])
        actual_terms = canonical(actual)
        expected_terms = canonical(expected)
        self.assertEqual(actual_terms.keys(), expected_terms.keys())
        for signature, probability in actual_terms.items():
            self.assertTrue(math.isclose(probability, expected_terms[signature], rel_tol=1e-9, abs_tol=1e-12),
                            (signature, probability, expected_terms[signature]))

    def test_worked_examples(self):
        for source in sorted((PARTICIPANT / "workspace" / "examples").glob("*.json")):
            if not source.name.endswith(".answer.json"):
                with self.subTest(case=source.stem):
                    expected = json.loads(source.with_suffix(".answer.json").read_text())
                    self.assert_answers_equal(compile_case(json.loads(source.read_text())), expected)

    def test_random_differential(self):
        for seed in range(600):
            with self.subTest(seed=seed):
                case = random_case(seed)
                self.assert_answers_equal(compile_case(case), forward_compile(case))

    def test_deterministic_clifford_echoes(self):
        for seed in range(100):
            with self.subTest(seed=seed):
                case = echo_case(seed)
                self.assert_answers_equal(compile_case(case), forward_compile(case))

    def test_nested_repeats(self):
        for depth in range(5):
            body = [{"op": "ERROR", "qubits": [0, 1], "paulis": ["X", "Y"], "probability": 0.07},
                    {"op": "M", "qubits": [0]}, {"op": "MX", "qubits": [1]},
                    {"op": "DETECTOR", "records": [-1, -3, -2, -4]},
                    {"op": "OBSERVABLE", "index": 1, "records": [-1, -3]},
                    {"op": "REPEAT", "count": 10, "body": []},
                    {"op": "REPEAT", "count": 0, "body": [{"op": "M", "qubits": [0]}]}]
            for level in range(depth):
                body = [{"op": "REPEAT", "count": 2, "body": body}]
            operations = [{"op": "R", "qubits": [0]}, {"op": "RX", "qubits": [1]},
                          {"op": "M", "qubits": [0]}, {"op": "MX", "qubits": [1]}] + body
            case = make_case(2, operations)
            self.assertEqual(list(reverse_instructions(prepare_operations(operations))),
                             list(reversed(prepare_operations(list(expand(operations))))))
            self.assert_answers_equal(compile_case(case), forward_compile(case))

    def test_deep_repeat_traversal(self):
        measurement = {"op": "M", "qubits": [0]}
        operations = [measurement]
        for depth in range(2000):
            operations = [{"op": "REPEAT", "count": 1, "body": operations}]
        self.assertEqual(list(reverse_instructions(prepare_operations(operations))),
                         prepare_operations([measurement]))

    def test_long_repeat_analytic(self):
        rounds = 10000
        operations = [{"op": "R", "qubits": [0]}, {"op": "M", "qubits": [0]},
                      {"op": "DETECTOR", "records": [-1]},
                      {"op": "REPEAT", "count": rounds, "body": [
                          {"op": "ERROR", "qubits": [0], "paulis": ["X"], "probability": 0.125},
                          {"op": "M", "qubits": [0]},
                          {"op": "DETECTOR", "records": [-1, -2]}]},
                      {"op": "OBSERVABLE", "index": 0, "records": [-1]}]
        case = make_case(1, operations, 1)
        answer = compile_case(case)
        actual = canonical(answer)
        self.assertEqual(actual, {((detector,), (0,)): 0.125 for detector in range(1, rounds + 1)})
        destination = io.StringIO()
        write_answer(destination, case, compile_terms(case, prepare_operations(operations)))
        self.assert_answers_equal(json.loads(destination.getvalue()), answer)

    def test_streamed_output(self):
        for case in [make_case(0, [], 0)] + [random_case(seed) for seed in range(40)]:
            destination = io.StringIO()
            write_answer(destination, case, compile_terms(case, prepare_operations(case["operations"])))
            self.assert_answers_equal(json.loads(destination.getvalue()), forward_compile(case))

    def test_distinct_probabilities_without_observables(self):
        operations = []
        expected = {}
        for detector in range(1200):
            probability = (detector + 1) / 2001
            operations.extend([{"op": "R", "qubits": [0]},
                               {"op": "ERROR", "qubits": [0], "paulis": ["X"], "probability": probability},
                               {"op": "M", "qubits": [0]},
                               {"op": "DETECTOR", "records": [-1]}])
            expected[((detector,), ())] = probability
        case = make_case(1, operations, 0)
        destination = io.StringIO()
        write_answer(destination, case, compile_terms(case, prepare_operations(operations)))
        self.assertEqual(canonical(json.loads(destination.getvalue())), expected)

    def test_hgp_extraction(self):
        for size, rounds in [(1, 1), (2, 2), (3, 3), (4, 2)]:
            with self.subTest(size=size, rounds=rounds):
                case = hgp_case(size, rounds)
                self.assert_answers_equal(compile_case(case), forward_compile(case))

    def test_probability_and_full_signature(self):
        operations = [{"op": "ERROR", "qubits": [0], "paulis": ["X"], "probability": 1},
                      {"op": "ERROR", "qubits": [0], "paulis": ["X"], "probability": 1},
                      {"op": "M", "qubits": [0]}, {"op": "DETECTOR", "records": [-1]}]
        self.assertEqual(compile_case(make_case(1, operations))["errors"], [])
        operations = [{"op": "ERROR", "qubits": [0], "paulis": ["X"], "probability": 0.1},
                      {"op": "ERROR", "qubits": [0, 1], "paulis": ["X", "X"], "probability": 0.2},
                      {"op": "ERROR", "qubits": [1], "paulis": ["X"], "probability": 0.3},
                      {"op": "M", "qubits": [0, 1]},
                      {"op": "DETECTOR", "records": [-2, -1, -1]},
                      {"op": "OBSERVABLE", "index": 2, "records": [-1]},
                      {"op": "ERROR", "qubits": [0], "paulis": ["X"], "probability": 0.8}]
        expected = {((0,), ()): 0.1, ((0,), (2,)): 0.2, ((), (2,)): 0.3}
        self.assertEqual(canonical(compile_case(make_case(2, operations))), expected)

    def test_empty(self):
        self.assertEqual(compile_case(make_case(0, [], 0)),
                         {"schema_version": 1, "num_detectors": 0, "num_observables": 0, "errors": []})

    def test_cli(self):
        directory = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            source = Path(temporary) / "case.json"
            destination = Path(temporary) / "answer.json"
            case = echo_case(92)
            source.write_text(json.dumps(case))
            subprocess.run([sys.executable, str(directory / "solve.py"), "--input", str(source),
                            "--output", str(destination)], check=True)
            self.assert_answers_equal(json.loads(destination.read_text()), forward_compile(case))


def benchmark(size, rounds):
    case = hgp_case(size, rounds)
    encoded_input = json.dumps(case, separators=(",", ":"))
    gc.collect()
    gc.disable()
    start = time.process_time()
    parsed = json.loads(encoded_input)
    parsed_time = time.process_time()
    terms = compile_terms(parsed, prepare_operations(parsed["operations"]))
    compiled_time = time.process_time()
    destination = io.StringIO()
    write_answer(destination, parsed, terms)
    encoded_output = destination.getvalue()
    serialized_time = time.process_time()
    print(json.dumps({"qubits": case["num_qubits"], "rounds": rounds,
                      "detectors": case["num_detectors"],
                      "expanded_operations": sum(1 for operation in expand(case["operations"])),
                      "terms": len(terms), "input_bytes": len(encoded_input),
                      "output_bytes": len(encoded_output), "parse_cpu": parsed_time - start,
                      "compile_cpu": compiled_time - parsed_time,
                      "serialize_cpu": serialized_time - compiled_time,
                      "total_cpu": serialized_time - start}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--size", type=int, default=12)
    parser.add_argument("--rounds", type=int, default=32)
    arguments, remaining = parser.parse_known_args()
    if arguments.benchmark:
        benchmark(arguments.size, arguments.rounds)
    else:
        unittest.main(argv=[sys.argv[0]] + remaining)
