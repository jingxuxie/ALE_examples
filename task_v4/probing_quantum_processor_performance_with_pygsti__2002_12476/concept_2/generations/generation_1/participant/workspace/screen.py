import argparse
import json
import math
import stat
import time
from pathlib import Path

import numpy as np


INPUT = Path(__file__).resolve().parents[1] / "input"
SPEC = json.loads((INPUT / "specification.json").read_text())
FAMILIES = json.loads((INPUT / "calibration.json").read_text())
PAULIS = np.array([
    [[1, 0], [0, 1]], [[0, 1], [1, 0]],
    [[0, -1j], [1j, 0]], [[1, 0], [0, -1]],
], dtype=complex)
IDEALS = np.array([PAULIS[0], (PAULIS[0] - 1j * PAULIS[1]) / np.sqrt(2),
                   (PAULIS[0] - 1j * PAULIS[2]) / np.sqrt(2)])


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonstandard JSON constant")


def load_witness(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("symlink submission")
    if path.is_dir():
        path = path / "witness.json"
    if path.is_symlink():
        raise ValueError("symlink witness")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > SPEC["maximum_json_bytes"]:
        raise ValueError("submission must be a regular JSON file at most 32 KiB")
    with path.open("rb") as handle:
        payload = handle.read(SPEC["maximum_json_bytes"] + 1)
    if len(payload) > SPEC["maximum_json_bytes"]:
        raise ValueError("oversized JSON")
    witness = json.loads(payload.decode("utf-8"), object_pairs_hook=strict_pairs, parse_constant=reject_constant)
    validate_witness(witness)
    return witness


def validate_witness(witness):
    if type(witness) is not dict or set(witness) != {"version", "gate_parameters", "circuit"}:
        raise ValueError("expected exactly version, gate_parameters, circuit")
    if type(witness["version"]) is not int or witness["version"] != 1:
        raise ValueError("unsupported version")
    rows = witness["gate_parameters"]
    if type(rows) is not list or len(rows) != 3:
        raise ValueError("expected three gate rows")
    for row in rows:
        if type(row) is not list or len(row) != 5:
            raise ValueError("expected five numbers per gate")
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in row):
            raise ValueError("gate parameters must be finite numbers")
        if abs(row[0]) > SPEC["phase_absolute_max"]:
            raise ValueError("phase bound exceeded")
        if math.hypot(*row[1:]) > SPEC["coupling_norm_max"]:
            raise ValueError("coupling norm bound exceeded")
    word = witness["circuit"]
    if type(word) is not str or len(word) != SPEC["circuit_length"] or set(word) - set("IXY"):
        raise ValueError("expected a 64-gate IXY circuit")
    if any(word.count(symbol) < SPEC["minimum_each_gate_count"] for symbol in "IXY"):
        raise ValueError("circuit must contain at least four of every gate")
    if any(word in words for words in FAMILIES.values()):
        raise ValueError("held-out circuit is a calibration circuit")


def encode(words):
    encoded = np.full((len(words), max(map(len, words), default=0)), 3, dtype=int)
    for index, word in enumerate(words):
        encoded[index, :len(word)] = ["IXY".index(symbol) for symbol in word]
    return encoded


def operators(parameters):
    unitaries = [np.eye(3, dtype=complex) for index in range(4)]
    for index, row in enumerate(np.asarray(parameters).reshape(3, 5)):
        couplings = np.array([row[1] + 1j * row[2], row[3] + 1j * row[4]])
        hamiltonian = np.zeros((3, 3), dtype=complex)
        hamiltonian[:2, 2] = couplings
        hamiltonian[2, :2] = couplings.conj()
        radius = np.linalg.norm(couplings)
        mixing = np.eye(3) - 1j * np.sinc(radius / np.pi) * hamiltonian
        mixing -= .5 * np.sinc(radius / (2 * np.pi)) ** 2 * (hamiltonian @ hamiltonian)
        nominal = np.zeros((3, 3), dtype=complex)
        nominal[:2, :2] = IDEALS[index]
        nominal[2, 2] = np.exp(-1j * row[0])
        unitaries[index] = mixing @ nominal
    transfers = []
    for unitary in unitaries:
        first = unitary[:2, :2]
        second = np.zeros((2, 2), dtype=complex)
        second[1] = unitary[2, :2]
        images = first @ PAULIS @ first.conj().T + second @ PAULIS @ second.conj().T
        transfers.append((np.einsum("aij,bji->ab", PAULIS, images) / 2).real)
    return np.asarray(unitaries), np.asarray(transfers)


def probabilities(parameters, encoded):
    unitaries, transfers = operators(parameters)
    states = np.zeros((len(encoded), 3), dtype=complex)
    states[:, 0] = 1
    bloch = np.tile([1., 0., 0., 1.], (len(encoded), 1))
    for column in encoded.T:
        states = (unitaries[column] @ states[..., None])[..., 0]
        bloch = (transfers[column] @ bloch[..., None])[..., 0]
    truth = .005 + .99 * np.abs(states[:, 0]) ** 2
    prediction = .005 + .99 * (bloch[:, 0] + bloch[:, 3]) / 2
    leakage = np.abs(states[:, 2]) ** 2
    return truth, prediction, leakage


def measure(witness):
    start = time.monotonic()
    validate_witness(witness)
    words = sum(FAMILIES.values(), []) + [witness["circuit"]]
    encoded = encode(words)
    scenarios = []
    calibration_accepted = True
    heldout_accepted = True
    tolerance = SPEC["numerical_tolerance"]
    for scenario in SPEC["scenarios"]:
        parameters = np.asarray(witness["gate_parameters"], dtype=float).copy()
        parameters[:, 0] += scenario["phase_shift"]
        parameters[:, 1:] *= scenario["coupling_scale"]
        truth, prediction, leakage = probabilities(parameters, encoded)
        errors = abs(truth - prediction)
        families = {}
        offset = 0
        for family, circuits in FAMILIES.items():
            family_errors = errors[offset:offset + len(circuits)]
            offset += len(circuits)
            maximum = float(max(family_errors))
            rms = float(np.sqrt(np.mean(family_errors ** 2)))
            families[family] = {"max_abs_error": maximum, "rms_error": rms}
            calibration_accepted &= maximum <= SPEC["calibration_max_abs_error"] + tolerance
            calibration_accepted &= rms <= SPEC["calibration_max_family_rms_error"] + tolerance
        heldout_accepted &= errors[-1] >= SPEC["heldout_min_abs_error"] - tolerance
        heldout_accepted &= leakage[-1] <= SPEC["heldout_max_final_leakage"] + tolerance
        scenarios.append({"name": scenario["name"], "calibration": families,
                          "heldout_truth": float(truth[-1]), "heldout_prediction": float(prediction[-1]),
                          "heldout_abs_error": float(errors[-1]), "final_leakage": float(leakage[-1])})
    passed = bool(calibration_accepted and heldout_accepted)
    reasons = []
    if not calibration_accepted:
        reasons.append("calibration screen rejected at least one scenario")
    if not heldout_accepted:
        reasons.append("held-out error or final-leakage bound failed")
    return {"core_score": scenarios[0]["heldout_abs_error"],
            "worst_family_score": min(scenario["heldout_abs_error"] for scenario in scenarios),
            "runtime_seconds": time.monotonic() - start, "passed": passed, "valid": True,
            "reason": "; ".join(reasons) if reasons else "valid robust counterexample",
            "calibration_accepted": bool(calibration_accepted), "scenarios": scenarios}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--witness", required=True, type=Path)
    args = parser.parse_args()
    start = time.monotonic()
    try:
        result = measure(load_witness(args.witness))
    except (ValueError, TypeError, OSError, OverflowError, RecursionError) as error:
        result = {"core_score": 0., "worst_family_score": 0., "runtime_seconds": time.monotonic() - start,
                  "passed": False, "valid": False, "reason": "invalid submission: " + str(error)}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
