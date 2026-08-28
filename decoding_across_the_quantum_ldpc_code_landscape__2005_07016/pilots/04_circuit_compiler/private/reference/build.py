import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import time

from official import PUBLIC, compile_case, stim

sys.path.insert(0, str(PUBLIC.parent.parent / "private"))
from metrics import compare
from protocol import expand_operations, lower_operations, read_json, write_json
from weak import compile_case as forward_compile

ROOT = PUBLIC.parent.parent
CHALLENGE = ROOT / "private/challenge_pool"


def fault(qubits, paulis, probability):
    return {"op": "ERROR", "qubits": list(qubits), "paulis": list(paulis),
            "probability": probability}


def instrument(circuit):
    operations = []
    for instruction in circuit:
        if isinstance(instruction, stim.CircuitRepeatBlock):
            operations.append({"op": "REPEAT", "count": instruction.repeat_count,
                               "body": instrument(instruction.body_copy())})
            continue
        name = instruction.name
        targets = instruction.targets_copy()
        if name in ("QUBIT_COORDS", "SHIFT_COORDS"):
            continue
        if name == "TICK":
            operations.append({"op": name})
            continue
        if name in ("DETECTOR", "OBSERVABLE_INCLUDE"):
            operation = {"op": "DETECTOR" if name == "DETECTOR" else "OBSERVABLE",
                         "records": [target.value for target in targets]}
            if name == "OBSERVABLE_INCLUDE":
                operation["index"] = int(instruction.gate_args_copy()[0])
            operations.append(operation)
            continue
        qubits = [target.value for target in targets]
        if name in ("M", "MX", "MR", "MRX"):
            measurement = "MX" if name in ("MX", "MRX") else "M"
            pauli = "Z" if measurement == "MX" else "X"
            operations.extend(fault([qubit], [pauli], 0.0013) for qubit in qubits)
            operations.append({"op": measurement, "qubits": qubits})
            if name in ("MR", "MRX"):
                operations.append({"op": "RX" if name == "MRX" else "R", "qubits": qubits})
                operations.extend(fault([qubit], [pauli], 0.0008) for qubit in qubits)
        elif name in ("R", "RX"):
            operations.append({"op": name, "qubits": qubits})
            operations.extend(fault([qubit], ["X" if name == "R" else "Z"], 0.0008)
                              for qubit in qubits)
        elif name in ("H", "S", "S_DAG"):
            operations.append({"op": name, "qubits": qubits})
            for qubit in qubits:
                for pauli, probability in (("X", 0.0007), ("Y", 0.0004), ("Z", 0.0006)):
                    operations.append(fault([qubit], [pauli], probability * (1 + qubit % 7 / 20)))
        elif name in ("CX", "CZ", "SWAP"):
            operations.append({"op": name, "qubits": qubits})
            for pair_index in range(0, len(qubits), 2):
                control, target = qubits[pair_index:pair_index + 2]
                operations.extend([fault([control], ["Y"], 0.0011),
                                   fault([target], ["X"], 0.0005),
                                   fault([control, target], ["X", "Z"], 0.0008)])
        else:
            raise ValueError(f"Unhandled source gate {name}")
    return operations


def make_case(name, operations, provenance):
    expanded = list(expand_operations(operations))
    qubits = [qubit for operation in expanded for qubit in operation.get("qubits", [])]
    observables = [operation["index"] for operation in expanded if operation["op"] == "OBSERVABLE"]
    case = {"schema_version": 1, "case_id": name, "num_qubits": max(qubits, default=-1) + 1,
            "num_measurements": sum(len(operation["qubits"]) for operation in expanded
                                    if operation["op"] in ("M", "MX")),
            "num_detectors": sum(operation["op"] == "DETECTOR" for operation in expanded),
            "num_observables": max(observables, default=-1) + 1, "operations": operations}
    lower_operations(case)
    statistics = {"case_id": name, "qubits": case["num_qubits"],
                  "measurements": case["num_measurements"], "detectors": case["num_detectors"],
                  "observables": case["num_observables"], "expanded_operations": len(expanded),
                  "fault_events": sum(operation["op"] == "ERROR" for operation in expanded),
                  "provenance": provenance}
    return case, statistics


def mirror(seed, qubits=7, depth=20):
    generator = random.Random(seed)
    operations = [{"op": "R", "qubits": list(range(qubits))}]
    gates = []
    for gate_index in range(depth):
        name = generator.choice(["H", "S", "CX", "CZ", "SWAP"])
        targets = generator.sample(range(qubits), 2 if name in ("CX", "CZ", "SWAP") else 1)
        gate = {"op": name, "qubits": targets}
        gates.append(gate)
        operations.append(gate)
        operations.append(fault(targets, [generator.choice("XYZ") for target in targets],
                                generator.choice([1e-7, 0.003, 0.017, 0.21])))
    for gate in reversed(gates):
        operations.append({"op": "S_DAG" if gate["op"] == "S" else gate["op"],
                           "qubits": gate["qubits"]})
    operations.append({"op": "M", "qubits": list(range(qubits))})
    for qubit in range(qubits - 1):
        operations.append({"op": "DETECTOR", "records": [-qubits + qubit]})
    operations.append({"op": "OBSERVABLE", "index": 3, "records": [-1]})
    operations.extend([{"op": "RX", "qubits": [0]}, fault([0], ["Z"], 0.13),
                       {"op": "MX", "qubits": [0]}, {"op": "DETECTOR", "records": [-1]},
                       fault([0], ["Z"], 0.19), {"op": "RX", "qubits": [0]},
                       {"op": "MX", "qubits": [0]}, {"op": "DETECTOR", "records": [-1, -1]},
                       {"op": "OBSERVABLE", "index": 1, "records": [-1]}])
    return operations


def examples():
    yield "parity_probability", [{"op": "R", "qubits": [0, 1]}, fault([0], ["X"], 0.1),
                                  fault([0], ["X"], 0.2), {"op": "M", "qubits": [0]},
                                  {"op": "DETECTOR", "records": [-1]},
                                  {"op": "OBSERVABLE", "index": 0, "records": [-1]},
                                  fault([1], ["X"], 0.3), {"op": "M", "qubits": [1]},
                                  {"op": "OBSERVABLE", "index": 1, "records": [-1]}]
    yield "repeat_records", [{"op": "R", "qubits": [0]}, {"op": "M", "qubits": [0]},
                              {"op": "DETECTOR", "records": [-1]},
                              {"op": "REPEAT", "count": 4, "body": [fault([0], ["X"], 0.03),
                                  {"op": "M", "qubits": [0]},
                                  {"op": "DETECTOR", "records": [-1, -2]},
                                  {"op": "OBSERVABLE", "index": 2, "records": [-1, -2]}]},
                              {"op": "OBSERVABLE", "index": 0, "records": [-1]}]
    yield "clifford_reset", mirror(441, qubits=3, depth=7)


def hgp_circuit(rows_one, cols_one, rows_two, cols_two, rounds, seed):
    import numpy as np
    from scipy.sparse import csr_matrix
    from bposd.hgp import hgp
    from ldpc.ckt_noise.css_code_memory_circuit import make_css_code_memory_circuit

    generator = np.random.default_rng(seed)

    def seed_matrix(rows, columns):
        matrix = np.zeros((rows, columns), dtype=np.uint8)
        for column in range(columns):
            matrix[generator.choice(rows, 3, replace=False), column] = 1
        return matrix

    code = hgp(seed_matrix(rows_one, cols_one), seed_matrix(rows_two, cols_two))
    circuit = make_css_code_memory_circuit(
        x_stabilizers=csr_matrix(code.hx), z_stabilizers=csr_matrix(code.hz),
        x_logicals=csr_matrix(code.lx), z_logicals=csr_matrix(code.lz), num_rounds=rounds,
        basis="Z", include_opposite_basis_detectors=True)
    return circuit, {"family": "nongeometric_hgp", "data_qubits": code.hx.shape[1],
                     "rounds": rounds, "seed": seed, "classical_shapes": [[rows_one, cols_one], [rows_two, cols_two]],
                     "constructor": "ldpc.ckt_noise.css_code_memory_circuit.make_css_code_memory_circuit"}


def save_case(directory, name, case, statistics):
    directory.mkdir(parents=True, exist_ok=True)
    answer, metrics, circuit, model = compile_case(case)
    noiseless = circuit.without_noise().compile_detector_sampler(seed=824).sample(8, append_observables=True)
    if noiseless.any():
        raise AssertionError("Nonzero noiseless detector events")
    statistics.update(metrics)
    statistics["noiseless_sample_check"] = True
    write_json(directory / f"{name}.json", case)
    write_json(directory / f"{name}.answer.json", answer)
    if directory == CHALLENGE:
        (directory / f"{name}.stim").write_text(str(circuit))
        (directory / f"{name}.dem").write_text(str(model))
    statistics["input_sha256"] = hashlib.sha256((directory / f"{name}.json").read_bytes()).hexdigest()
    statistics["answer_sha256"] = hashlib.sha256((directory / f"{name}.answer.json").read_bytes()).hexdigest()
    return answer, statistics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()
    started = time.perf_counter()
    validations = []
    for name, operations in examples():
        case, statistics = make_case(name, operations, {"family": "tiny_example"})
        answer, statistics = save_case(PUBLIC / "examples", name, case, statistics)
        result = compare(forward_compile(case), answer)
        if not result["exact"]:
            raise AssertionError((name, result))
        validations.append({"case_id": name, **result})
    manifest = {"schema_version": 1, "cpu_budget_seconds": args.timeout, "performance": [], "audits": []}
    for seed in (7191, 41103):
        name = f"semantic_{seed}"
        case, statistics = make_case(name, mirror(seed), {"family": "clifford_semantic_audit"})
        answer, statistics = save_case(CHALLENGE, name, case, statistics)
        result = compare(forward_compile(case), answer)
        if not result["exact"]:
            raise AssertionError((name, result))
        validations.append({"case_id": name, **result})
        manifest["audits"].append(statistics)
    for distance, rounds in ((7, 8), (15, 30)):
        name = f"surface_d{distance}_r{rounds}"
        source = stim.Circuit.generated("surface_code:rotated_memory_z", distance=distance, rounds=rounds)
        case, statistics = make_case(name, instrument(source), {"family": "surface", "distance": distance,
                                                               "rounds": rounds, "constructor": "Stim generated rotated_memory_z"})
        answer, statistics = save_case(CHALLENGE, name, case, statistics)
        manifest["performance"].append(statistics)
        print(json.dumps(statistics), flush=True)
    for parameters in ((4, 7, 5, 8, 10, 613), (10, 16, 12, 20, 24, 9287)):
        source, provenance = hgp_circuit(*parameters)
        name = f"hgp_n{provenance['data_qubits']}_r{provenance['rounds']}"
        case, statistics = make_case(name, instrument(source), provenance)
        answer, statistics = save_case(CHALLENGE, name, case, statistics)
        manifest["performance"].append(statistics)
        print(json.dumps(statistics), flush=True)
    write_json(CHALLENGE / "manifest.json", manifest)
    write_json(ROOT / "private/reference/validation.json", {"comparisons": validations,
               "all_exact": all(result["exact"] for result in validations),
               "build_seconds": time.perf_counter() - started, "stim_version": stim.__version__})


if __name__ == "__main__":
    main()
