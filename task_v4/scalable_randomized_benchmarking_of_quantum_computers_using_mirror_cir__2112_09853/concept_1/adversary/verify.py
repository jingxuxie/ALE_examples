import argparse
import hashlib
import itertools
import json
import platform
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import minimize_scalar


AXES = tuple(itertools.permutations((1, 2, 3)))
CX_ORDER = tuple((control, target) for control in range(4)
                 for target in ((control + 1) % 4, (control - 1) % 4))
PAULIS = tuple(itertools.product(range(4), repeat=4))
PAULI_INDEX = {pauli: index for index, pauli in enumerate(PAULIS)}
IDENTITY = (0, 0, 0, 0)
DEPTHS = np.arange(0, 258, 2)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def uniform_payload():
    return {"single": [[[20, 20, 20] for _ in range(6)] for _ in range(4)],
            "cx": [[4] * 15 for _ in range(8)]}


def validate_shape(payload):
    require(type(payload) is dict and set(payload) == {"single", "cx"}, "Expected exactly single and cx keys")
    require(type(payload["single"]) is list and len(payload["single"]) == 4, "single must have four qubit blocks")
    for site, block in enumerate(payload["single"]):
        require(type(block) is list and len(block) == 6, f"single[{site}] must have six classes")
        for position, row in enumerate(block):
            require(type(row) is list and len(row) == 3, f"single[{site}][{position}] must have three counts")
            require(all(type(value) is int for value in row), "Counts must be JSON integers, not booleans or floats")
            require(sum(row) == 60 and all(2 <= value <= 42 for value in row), "Single-qubit row violates sum or bounds")
    require(type(payload["cx"]) is list and len(payload["cx"]) == 8, "cx must have eight rows")
    for position, row in enumerate(payload["cx"]):
        require(type(row) is list and len(row) == 15, f"cx[{position}] must have fifteen counts")
        require(all(type(value) is int for value in row), "Counts must be JSON integers, not booleans or floats")
        require(sum(row) == 60 and all(1 <= value <= 21 for value in row), "CNOT row violates sum or bounds")


def transform(key, pauli):
    result = list(pauli)
    if key[0] == "single":
        _, site, axes = key
        result[site] = (0, *axes)[pauli[site]]
    else:
        _, control, target = key
        control_x = pauli[control] & 1
        control_z = pauli[control] >> 1
        target_x = pauli[target] & 1
        target_z = pauli[target] >> 1
        result[control] = control_x + 2 * (control_z ^ target_z)
        result[target] = (target_x ^ control_x) + 2 * target_z
    return tuple(result)


def make_gates(payload):
    gates = []
    for site in range(4):
        for position, axes in enumerate(AXES):
            counts = {}
            for digit, count in enumerate(payload["single"][site][position], start=1):
                pauli = [0, 0, 0, 0]
                pauli[site] = digit
                counts[tuple(pauli)] = count
            gates.append({"key": ("single", site, axes), "weight": 1, "counts": counts})
    for position, (control, target) in enumerate(CX_ORDER):
        counts = {}
        for code, count in enumerate(payload["cx"][position], start=1):
            pauli = [0, 0, 0, 0]
            pauli[control], pauli[target] = code % 4, code // 4
            counts[tuple(pauli)] = count
        gates.append({"key": ("cx", control, target), "weight": 2, "counts": counts})
    keys = [gate["key"] for gate in gates]
    for gate in gates:
        kind, site, action = gate["key"]
        inverse = ((kind, site, tuple(action.index(digit) + 1 for digit in (1, 2, 3)))
                   if kind == "single" else gate["key"])
        gate["inverse"] = keys.index(inverse)
    return gates


def integer_constraints(gates):
    weighted_counts = {pauli: 0 for pauli in PAULIS[1:]}
    row_details = []
    for gate in gates:
        row = list(gate["counts"].values())
        row_details.append({"gate": gate["key"], "sum": sum(row), "min": min(row), "max": max(row),
                            "infidelity_exact": str(Fraction(sum(row), 3000))})
        for pauli, count in gate["counts"].items():
            weighted_counts[pauli] += gate["weight"] * count
    nonzero_marginals = []
    for pauli, actual in weighted_counts.items():
        support = [site for site, digit in enumerate(pauli) if digit]
        expected = 152 if len(support) == 1 else 0
        if len(support) == 2 and abs(support[0] - support[1]) in (1, 3):
            expected = 16
        require(actual == expected, f"Average-channel mismatch for {pauli}: {actual} != {expected}")
        if expected:
            nonzero_marginals.append({"pauli": "".join("IXZY"[digit] for digit in pauli),
                                      "actual": actual, "expected": expected})
    pair_terms = []
    for gate in gates:
        inverse_counts = gates[gate["inverse"]]["counts"]
        overlap = sum(count * gate["counts"].get(transform(gate["key"], pauli), 0)
                      for pauli, count in inverse_counts.items())
        pair_terms.append(gate["weight"] * overlap)
    overlap_total = sum(pair_terms)
    require(overlap_total == 32640, f"Exact inverse-pair overlap is {overlap_total}, not 32640")
    fidelity_two = Fraction(49, 50) ** 2 + Fraction(overlap_total, 40 * 3000 ** 2)
    polarization_two = (256 * fidelity_two - 1) / 255
    return {"all_pass": True, "rows": row_details,
            "mean_channel_checked_nonidentity_paulis": 255,
            "mean_channel_zero_marginals": 207, "mean_channel_nonzero_marginals": nonzero_marginals,
            "pair_overlap_terms": pair_terms, "pair_overlap_total": overlap_total,
            "S2_exact_fraction": str(polarization_two), "S2_from_integer_constraints": float(polarization_two)}


def transfers(gates):
    permutations = np.array([[PAULI_INDEX[transform(gate["key"], pauli)] for pauli in PAULIS]
                             for gate in gates])
    lambdas = np.empty((32, 256))
    for gate_index, gate in enumerate(gates):
        for pauli_index, pauli in enumerate(PAULIS):
            signed_count = 0
            for error, count in gate["counts"].items():
                anticommuting_sites = sum(left != 0 and right != 0 and left != right
                                         for left, right in zip(pauli, error))
                signed_count += count if anticommuting_sites % 2 == 0 else -count
            lambdas[gate_index, pauli_index] = 0.98 + signed_count / 3000
    mirror = np.zeros((255, 255))
    ideal = np.zeros((255, 255))
    for gate_index, gate in enumerate(gates):
        destinations = permutations[gate_index, 1:] - 1
        coefficients = (gate["weight"] / 40) * lambdas[gate["inverse"], 1:]
        coefficients *= lambdas[gate_index, permutations[gate_index, 1:]]
        mirror[np.arange(255), destinations] += coefficients
        ideal[np.arange(255), destinations] += gate["weight"] / 40
    require(np.max(abs(mirror - mirror.T)) < 1e-13, "Mirror transfer must be symmetric")
    require(np.max(abs(ideal - ideal.T)) < 1e-13, "Ideal transfer must be symmetric")
    vector = np.ones(255)
    values = [1.0]
    for _ in range(128):
        vector = mirror @ vector
        values.append(float(vector.mean()))
    spectrum = np.linalg.eigvalsh(ideal)
    return np.array(values), permutations, {
        "mirror_symmetry_max_error": float(np.max(abs(mirror - mirror.T))),
        "ideal_row_sum_max_error": float(np.max(abs(ideal.sum(axis=1) - 1))),
        "ideal_stationary_eigenvalue": float(spectrum[-1]),
        "ideal_absolute_spectral_gap": float(1 - np.max(abs(spectrum[:-1])))}


def probability_space_crosscheck(gates, permutations, transfer_values):
    distributions = [{IDENTITY: 0.98, **{pauli: count / 3000 for pauli, count in gate["counts"].items()}}
                     for gate in gates]
    shifts = {}
    for distribution in distributions:
        for error in distribution:
            if error not in shifts:
                shifts[error] = np.array([PAULI_INDEX[tuple(left ^ right for left, right in zip(pauli, error))]
                                          for pauli in PAULIS])
    state = np.zeros(256)
    state[0] = 1
    evidence = []
    for half_depth in range(1, 5):
        updated = np.zeros(256)
        for gate_index, gate in enumerate(gates):
            inner = np.zeros(256)
            for error, probability in distributions[gate_index].items():
                inner += probability * state[shifts[error]]
            rotated = inner[permutations[gate_index]]
            outer = np.zeros(256)
            for error, probability in distributions[gate["inverse"]].items():
                outer += probability * rotated[shifts[error]]
            updated += (gate["weight"] / 40) * outer
        state = updated
        polarization = (256 * state[0] - 1) / 255
        difference = abs(polarization - transfer_values[half_depth])
        require(difference < 1e-12, "Probability-convolution and Pauli-transfer recurrences disagree")
        evidence.append({"depth": 2 * half_depth, "probability_space_polarization": float(polarization),
                         "transfer_polarization": float(transfer_values[half_depth]),
                         "absolute_difference": float(difference), "probability_sum": float(state.sum())})
    return evidence


def fit(values):
    def profile(rate):
        shape = np.exp(-rate * DEPTHS)
        amplitude = (shape @ values) / (shape @ shape)
        return float(np.sum((values - amplitude * shape) ** 2))

    grid = np.linspace(0.005, 0.04, 4097)
    shapes = np.exp(-np.outer(grid, DEPTHS))
    amplitudes = (shapes @ values) / np.sum(shapes * shapes, axis=1)
    losses = np.sum((values[None, :] - amplitudes[:, None] * shapes) ** 2, axis=1)
    local_minima = np.flatnonzero((losses[1:-1] <= losses[:-2]) & (losses[1:-1] <= losses[2:])) + 1
    candidates = [(profile(float(grid[0])), float(grid[0])),
                  (profile(float(grid[-1])), float(grid[-1]))]
    for index in local_minima:
        refined = minimize_scalar(profile, bounds=(float(grid[index - 1]), float(grid[index + 1])),
                                  method="bounded", options={"xatol": 1e-12})
        require(refined.success, "Scalar profile refinement failed")
        candidates.append((float(refined.fun), float(refined.x)))
    objective, rate = min(candidates)
    shape = np.exp(-rate * DEPTHS)
    amplitude = (shape @ values) / (shape @ shape)
    residual = values - amplitude * shape
    estimate = (255 / 256) * (-np.expm1(-rate))
    return {"method": "4097-point scan plus all grid-local bounded refinements; endpoints included",
            "grid_local_minima": len(local_minima), "t": rate, "amplitude": float(amplitude),
            "sse": objective, "rmse": float(np.sqrt(np.mean(residual ** 2))),
            "max_residual": float(np.max(abs(residual))), "r": float(estimate),
            "bias": float(1 - estimate / 0.02)}


def verify(payload):
    started = time.perf_counter()
    validate_shape(payload)
    gates = make_gates(payload)
    constraints = integer_constraints(gates)
    values, permutations, transfer_evidence = transfers(gates)
    pair_difference = abs(values[1] - constraints["S2_from_integer_constraints"])
    require(pair_difference < 1e-13, "Depth-two transfer disagrees with exact integer constraint")
    convolution_evidence = probability_space_crosscheck(gates, permutations, values)
    fitted = fit(values)
    acceptance = {"all_integer_constraints": True, "fit_residual_at_most_0_004": fitted["max_residual"] <= 0.004,
                  "S256_at_least_0_005": bool(values[-1] >= 0.005), "bias_at_least_0_0244": fitted["bias"] >= 0.0244}
    return {"verifier": "independent four-digit Pauli tuples, Python integer constraints, dense transfer, short-depth probability convolution",
            "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
            "elapsed_seconds": time.perf_counter() - started, "admissible": True,
            "accepted": all(acceptance.values()), "acceptance": acceptance,
            "constraints": constraints, "transfer": transfer_evidence,
            "S2_integer_transfer_absolute_difference": float(pair_difference),
            "probability_space_crosscheck": convolution_evidence, "fit": fitted,
            "depths": DEPTHS.tolist(), "polarizations": values.tolist()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("witness", nargs="?")
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--require-winning", action="store_true")
    arguments = parser.parse_args()
    require(arguments.baseline != bool(arguments.witness), "Provide either a witness path or --baseline")
    if arguments.baseline:
        payload = uniform_payload()
        raw = json.dumps(payload, sort_keys=True).encode()
        source = "generated uniform baseline"
    else:
        raw = Path(arguments.witness).read_bytes()
        payload = json.loads(raw)
        source = arguments.witness
    result = verify(payload)
    result["input"] = source
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(result, indent=2, allow_nan=False))
    if arguments.require_winning and not result["accepted"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
