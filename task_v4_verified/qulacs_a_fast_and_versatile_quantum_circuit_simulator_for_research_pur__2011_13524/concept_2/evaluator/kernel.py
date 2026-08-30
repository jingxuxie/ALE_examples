import json
import math
import os
import stat

import numpy as np


MAX_JSON_BYTES = 1024 * 1024
MAX_INPUT_JSON_BYTES = 8 * 1024 * 1024


class WitnessError(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise WitnessError("duplicate JSON key")
        result[name] = value
    return result


def reject_constant(value):
    raise WitnessError("nonfinite JSON constant")


def parse_json(contents):
    try:
        return json.loads(
            contents, object_pairs_hook=unique_object, parse_constant=reject_constant
        )
    except (ValueError, UnicodeError, RecursionError) as error:
        raise WitnessError("invalid JSON: " + str(error)[:200]) from error


def read_json(path, max_bytes=MAX_JSON_BYTES):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        information = os.fstat(descriptor)
        if not stat.S_ISREG(information.st_mode):
            raise WitnessError("answer must be a regular file")
        if information.st_size > max_bytes:
            raise WitnessError("JSON exceeds the " + str(max_bytes) + "-byte limit")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            contents = handle.read(max_bytes + 1)
        if len(contents) > max_bytes:
            raise WitnessError("JSON exceeds the " + str(max_bytes) + "-byte limit")
        return parse_json(contents)
    finally:
        os.close(descriptor)


def finite_number(value):
    if type(value) not in (int, float):
        raise WitnessError("angles must be finite real JSON numbers")
    try:
        converted = float(value)
    except (OverflowError, ValueError) as error:
        raise WitnessError("angle cannot be represented as a finite scalar") from error
    if not math.isfinite(converted):
        raise WitnessError("angles must be finite real JSON numbers")
    return converted


def qubit_index(value, qubit_count):
    if type(value) is not int or not 0 <= value < qubit_count:
        raise WitnessError("qubit index must be an in-range JSON integer")
    return value


def validate_gates(gates, target):
    if not isinstance(gates, list):
        raise WitnessError("a circuit must be a gate list")
    if len(gates) > target["max_cnot"] + target["max_u3"]:
        raise WitnessError("total gate budget exceeded")
    qubit_count = target["n_qubits"]
    edges = {tuple(sorted(edge)) for edge in target["connectivity"]}
    counts = {"U3": 0, "CNOT": 0}
    for gate in gates:
        if not isinstance(gate, dict):
            raise WitnessError("each gate must be an object")
        kind = gate.get("gate")
        if kind == "U3":
            if set(gate) != {"gate", "qubit", "theta", "phi", "lambda"}:
                raise WitnessError("incorrect U3 fields")
            qubit_index(gate["qubit"], qubit_count)
            for parameter in ("theta", "phi", "lambda"):
                finite_number(gate[parameter])
        elif kind == "CNOT":
            if set(gate) != {"gate", "control", "target"}:
                raise WitnessError("incorrect CNOT fields")
            control = qubit_index(gate["control"], qubit_count)
            destination = qubit_index(gate["target"], qubit_count)
            if control == destination or tuple(sorted((control, destination))) not in edges:
                raise WitnessError("CNOT must use an allowed edge with distinct endpoints")
        else:
            raise WitnessError("only U3 and CNOT gates are allowed")
        counts[kind] += 1
    if counts["U3"] > target["max_u3"] or counts["CNOT"] > target["max_cnot"]:
        raise WitnessError("individual gate budget exceeded")
    return counts


def u3_matrix(theta, phi, lam):
    cosine = math.cos(float(theta) * 0.5)
    sine = math.sin(float(theta) * 0.5)
    phase_phi = complex(math.cos(float(phi)), math.sin(float(phi)))
    phase_lam = complex(math.cos(float(lam)), math.sin(float(lam)))
    return np.array(
        [[cosine, -phase_lam * sine], [phase_phi * sine, phase_phi * phase_lam * cosine]],
        dtype=np.complex128,
    )


def circuit_unitary(qubit_count, gates):
    dimension = 1 << qubit_count
    result = np.eye(dimension, dtype=np.complex128)
    indices = np.arange(dimension)
    for gate in gates:
        if gate["gate"] == "U3":
            bit = 1 << gate["qubit"]
            zero_rows = indices[(indices & bit) == 0]
            one_rows = zero_rows | bit
            zero_values = result[zero_rows].copy()
            one_values = result[one_rows].copy()
            local = u3_matrix(gate["theta"], gate["phi"], gate["lambda"])
            result[zero_rows] = local[0, 0] * zero_values + local[0, 1] * one_values
            result[one_rows] = local[1, 0] * zero_values + local[1, 1] * one_values
        else:
            control_bit = 1 << gate["control"]
            target_bit = 1 << gate["target"]
            zero_rows = indices[((indices & control_bit) != 0) & ((indices & target_bit) == 0)]
            one_rows = zero_rows | target_bit
            temporary = result[zero_rows].copy()
            result[zero_rows] = result[one_rows]
            result[one_rows] = temporary
    return result


def target_matrix(target):
    dimension = 1 << target["n_qubits"]
    matrix = np.asarray(target["unitary_real"], dtype=float) + 1j * np.asarray(
        target["unitary_imag"], dtype=float
    )
    if matrix.shape != (dimension, dimension) or not np.all(np.isfinite(matrix)):
        raise WitnessError("invalid target matrix")
    defect = np.linalg.norm(matrix.conj().T @ matrix - np.eye(dimension), ord="fro")
    if defect > 1e-10:
        raise WitnessError("target matrix is not unitary")
    return matrix


def unitary_metrics(target, candidate):
    dimension = target.shape[0]
    overlap = np.vdot(target, candidate) / dimension
    amplitude = float(abs(overlap))
    phase = np.conj(overlap) / amplitude if amplitude > 0 else 1.0
    infidelity = max(0.0, 1.0 - min(1.0, amplitude) ** 2)
    discrepancy = float(np.linalg.norm(phase * candidate - target, ord="fro") / math.sqrt(dimension))
    return {"infidelity": infidelity, "normalized_frobenius": discrepancy}


def score_payload(specification, payload):
    targets = specification["targets"]
    expected = {target["id"] for target in targets}
    if not isinstance(payload, dict) or set(payload) != expected:
        raise WitnessError("output must map exactly the input target IDs to gate lists")
    cases = []
    for target in targets:
        case = {"id": target["id"], "valid": False, "passed": False, "score": 0.0}
        try:
            gates = payload[target["id"]]
            case["gate_counts"] = validate_gates(gates, target)
            candidate = circuit_unitary(target["n_qubits"], gates)
            metrics = unitary_metrics(target_matrix(target), candidate)
            if not all(math.isfinite(value) for value in metrics.values()):
                raise WitnessError("nonfinite matrix comparison")
            case.update(metrics)
            case["valid"] = True
            case["passed"] = all(
                metrics[name] <= specification["tolerances"][name] for name in metrics
            )
            case["score"] = float(case["passed"])
        except (WitnessError, ValueError, TypeError, OverflowError) as error:
            case["error"] = str(error)[:240]
        cases.append(case)
    achieved = all(case["passed"] for case in cases)
    return {
        "mode": "C",
        "core_score": sum(case["score"] for case in cases) / len(cases),
        "valid": all(case["valid"] for case in cases),
        "target_met": achieved,
        "success": achieved,
        "cases": cases,
    }
