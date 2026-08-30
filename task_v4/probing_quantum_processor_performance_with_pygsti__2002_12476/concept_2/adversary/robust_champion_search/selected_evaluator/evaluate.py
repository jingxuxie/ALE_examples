import argparse
import hashlib
import json
import math
import stat
import time
from pathlib import Path

import numpy as np
from scipy.linalg import expm


HIDDEN = Path(__file__).resolve().parent / "hidden"
SPEC = json.loads((HIDDEN / "specification.json").read_text())
FAMILIES = json.loads((HIDDEN / "calibration.json").read_text())
MANIFEST = json.loads((HIDDEN / "manifest.json").read_text())


def integrity_check():
    for name, expected in MANIFEST.items():
        if hashlib.sha256((HIDDEN / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError("trusted evaluator asset checksum mismatch")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonstandard JSON constant")


def read_submission(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("submission path is a symlink")
    if path.is_dir():
        path = path / "witness.json"
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("witness is not a regular file")
    limit = SPEC["maximum_json_bytes"]
    if info.st_size > limit:
        raise ValueError("witness exceeds 32 KiB")
    with path.open("rb") as handle:
        payload = handle.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("witness exceeds 32 KiB")
    witness = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant)
    check_input(witness)
    return witness


def check_input(witness):
    if type(witness) is not dict or set(witness) != {"version", "gate_parameters", "circuit"}:
        raise ValueError("incorrect witness fields")
    if type(witness["version"]) is not int or witness["version"] != 1:
        raise ValueError("unsupported witness version")
    parameters = witness["gate_parameters"]
    if type(parameters) is not list or len(parameters) != 3:
        raise ValueError("gate_parameters must have three rows")
    for row in parameters:
        if type(row) is not list or len(row) != 5:
            raise ValueError("gate row must have five coordinates")
        for value in row:
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("coordinates must be finite real JSON numbers")
        if abs(row[0]) > SPEC["phase_absolute_max"]:
            raise ValueError("phase out of bounds")
        if math.hypot(*row[1:]) > SPEC["coupling_norm_max"]:
            raise ValueError("coupling norm out of bounds")
    word = witness["circuit"]
    if type(word) is not str or len(word) != SPEC["circuit_length"] or any(symbol not in "IXY" for symbol in word):
        raise ValueError("circuit must be a 64-character IXY string")
    if any(word.count(symbol) < SPEC["minimum_each_gate_count"] for symbol in "IXY"):
        raise ValueError("fewer than four instances of a gate")
    if any(word in words for words in FAMILIES.values()):
        raise ValueError("circuit is not held out")


def physical_maps(parameters):
    identities = np.eye(2, dtype=complex)
    pauli_x = np.array([[0, 1], [1, 0]], dtype=complex)
    pauli_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    rotations = [identities, expm(-1j * np.pi * pauli_x / 4), expm(-1j * np.pi * pauli_y / 4)]
    unitaries = []
    kraus_first = []
    kraus_second = []
    for index, row in enumerate(parameters):
        coupling_0 = complex(row[1], row[2])
        coupling_1 = complex(row[3], row[4])
        hamiltonian = np.array([[0, 0, coupling_0], [0, 0, coupling_1],
                                [coupling_0.conjugate(), coupling_1.conjugate(), 0]], dtype=complex)
        nominal = np.zeros((3, 3), dtype=complex)
        nominal[:2, :2] = rotations[index]
        nominal[2, 2] = np.exp(-1j * row[0])
        unitary = expm(-1j * hamiltonian) @ nominal
        first = unitary[:2, :2].copy()
        second = np.zeros((2, 2), dtype=complex)
        second[1, :] = unitary[2, :2]
        if np.max(abs(unitary.conj().T @ unitary - np.eye(3))) > 1e-11:
            raise ArithmeticError("unitary check failed")
        if np.max(abs(first.conj().T @ first + second.conj().T @ second - identities)) > 1e-11:
            raise ArithmeticError("trace preservation check failed")
        unitaries.append(unitary)
        kraus_first.append(first)
        kraus_second.append(second)
    unitaries.append(np.eye(3, dtype=complex))
    kraus_first.append(np.eye(2, dtype=complex))
    kraus_second.append(np.zeros((2, 2), dtype=complex))
    return np.array(unitaries), np.array(kraus_first), np.array(kraus_second)


def simulate(parameters, words):
    unitaries, first, second = physical_maps(parameters)
    count = len(words)
    labels = np.full((count, max(map(len, words), default=0)), 3, dtype=int)
    for index, word in enumerate(words):
        labels[index, :len(word)] = ["IXY".index(symbol) for symbol in word]
    density = np.zeros((count, 3, 3), dtype=complex)
    density[:, 0, 0] = 1
    reduced = np.zeros((count, 2, 2), dtype=complex)
    reduced[:, 0, 0] = 1
    for column in labels.T:
        unitary = unitaries[column]
        density = unitary @ density @ unitary.conj().swapaxes(1, 2)
        first_gate = first[column]
        second_gate = second[column]
        reduced = first_gate @ reduced @ first_gate.conj().swapaxes(1, 2) + second_gate @ reduced @ second_gate.conj().swapaxes(1, 2)
    if max(np.max(abs(np.trace(density, axis1=1, axis2=2) - 1)),
           np.max(abs(np.trace(reduced, axis1=1, axis2=2) - 1))) > 1e-10:
        raise ArithmeticError("simulation trace drift")
    truth = .005 + .99 * density[:, 0, 0].real
    prediction = .005 + .99 * reduced[:, 0, 0].real
    leakage = density[:, 2, 2].real
    for array in [truth, prediction, leakage]:
        if not np.isfinite(array).all() or array.min() < -1e-10 or array.max() > 1 + 1e-10:
            raise ArithmeticError("nonphysical simulated probability")
    return truth, prediction, leakage


def score_witness(witness):
    check_input(witness)
    words = []
    family_indices = {}
    for family, circuits in FAMILIES.items():
        family_indices[family] = slice(len(words), len(words) + len(circuits))
        words.extend(circuits)
    words.append(witness["circuit"])
    records = []
    failures = []
    tolerance = SPEC["numerical_tolerance"]
    for scenario in SPEC["scenarios"]:
        parameters = np.asarray(witness["gate_parameters"], dtype=float).copy()
        parameters[:, 0] += scenario["phase_shift"]
        parameters[:, 1:] *= scenario["coupling_scale"]
        truth, prediction, leakage = simulate(parameters, words)
        errors = abs(truth - prediction)
        family_scores = {}
        for family, indices in family_indices.items():
            maximum = float(np.max(errors[indices]))
            rms = float(np.sqrt(np.mean(np.square(errors[indices]))))
            family_scores[family] = {"max_abs_error": maximum, "rms_error": rms}
            if maximum > SPEC["calibration_max_abs_error"] + tolerance:
                failures.append(scenario["name"] + ": " + family + " calibration maximum")
            if rms > SPEC["calibration_max_family_rms_error"] + tolerance:
                failures.append(scenario["name"] + ": " + family + " calibration RMS")
        if errors[-1] < SPEC["heldout_min_abs_error"] - tolerance:
            failures.append(scenario["name"] + ": held-out prediction gap")
        if leakage[-1] > SPEC["heldout_max_final_leakage"] + tolerance:
            failures.append(scenario["name"] + ": final leakage")
        records.append({"name": scenario["name"], "calibration": family_scores,
                        "heldout_truth": float(truth[-1]), "heldout_prediction": float(prediction[-1]),
                        "heldout_abs_error": float(errors[-1]), "final_leakage": float(leakage[-1])})
    return {"core_score": records[0]["heldout_abs_error"],
            "worst_family_score": min(record["heldout_abs_error"] for record in records),
            "passed": not failures, "valid": True,
            "reason": "valid robust counterexample" if not failures else "; ".join(failures),
            "calibration_accepted": not any("calibration" in failure for failure in failures),
            "violations": failures, "scenarios": records}


def evaluate(path):
    start = time.monotonic()
    integrity_check()
    try:
        witness = read_submission(path)
        result = score_witness(witness)
    except (ValueError, TypeError, OSError, OverflowError, RecursionError) as error:
        result = {"core_score": 0., "worst_family_score": 0., "passed": False, "valid": False,
                  "reason": "invalid submission: " + type(error).__name__}
    result["runtime_seconds"] = time.monotonic() - start
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = evaluate(args.submission)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(result, indent=2, allow_nan=False) + "\n"
    args.output.write_text(serialized)
    print(serialized, end="")


if __name__ == "__main__":
    main()
