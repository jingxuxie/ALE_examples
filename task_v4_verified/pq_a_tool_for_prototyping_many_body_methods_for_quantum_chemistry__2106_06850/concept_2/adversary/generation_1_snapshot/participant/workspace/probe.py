"""Inspect a JSON artifact with the public oracle; not the official evaluator."""

import argparse
import json

import numpy as np

from api import CONSTRAINTS, check_continuation, endpoint_failures
from oracle import CCResult, DeterminantCC


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact")
    parser.add_argument("--continuation", action="store_true")
    arguments = parser.parse_args()
    with open(arguments.artifact) as stream:
        data = json.load(stream)
    oracle = DeterminantCC()
    interaction = np.asarray(data["pair_matrix"], dtype=float)
    amplitudes = np.asarray(data["amplitudes"], dtype=float)
    hamiltonian, _, _ = oracle.hamiltonian(CONSTRAINTS["orbital_energies"], interaction)
    residual, jacobian, hbar, positive, inverse = oracle.equations(hamiltonian, amplitudes)
    residual_norm = float(max(abs(residual)))
    result = CCResult(amplitudes, float(hbar[oracle.reference, oracle.reference]), residual_norm,
                      jacobian, hbar, positive[:, oracle.reference], inverse,
                      residual_norm <= CONSTRAINTS["cc_residual_max"])
    diagnostics = oracle.diagnostics(hamiltonian, result)
    diagnostics["endpoint_failures"] = endpoint_failures(diagnostics)
    diagnostics["target_reached"] = diagnostics["occupation_violation"] >= CONSTRAINTS["population_violation_min"]
    if arguments.continuation:
        diagnostics["continuation"] = check_continuation(interaction, amplitudes, oracle)
    print(json.dumps(diagnostics, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
