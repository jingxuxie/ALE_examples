import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "snapshots/trusted"))
from trusted_contractor import canonicalize, hamiltonian_terms, local_operators, measure


def main():
    discrepancies = []
    rejected_naive_powers = []
    for dimension in (4, 12, 14):
        for omega in (0.55, 0.75, 1.5):
            padded = dimension + 8
            lowering = np.diag(np.sqrt(np.arange(1, padded)), 1)
            position = (lowering + lowering.T) / np.sqrt(2 * omega)
            momentum = -1j * np.sqrt(omega / 2) * (lowering - lowering.T)
            independent = {"q": position, "q2": np.linalg.matrix_power(position, 2),
                           "q4": np.linalg.matrix_power(position, 4), "p2": momentum @ momentum}
            trusted = local_operators(dimension, omega)
            for name, matrix in independent.items():
                error = float(np.max(np.abs(trusted[name] - matrix[:dimension, :dimension])))
                assert error < 1e-10
                discrepancies.append(error)
            incorrect = np.linalg.matrix_power(trusted["q"], 4)
            difference = float(np.linalg.norm(incorrect - trusted["q4"]))
            assert difference > 1
            rejected_naive_powers.append(difference)
    generator = np.random.default_rng(1208)
    request = {"n_sites": 3, "local_dim": 4, "bond_cap": 4, "sector": "any",
               "omega": [0.55, 0.71, 0.65], "mass2": [-0.02, 0.01, -0.034],
               "lambda4": [0.05, 0.13, 0.08], "field": [0.001, -0.002, 0.0],
               "coupling": [1.2, 0.05]}
    tensors = canonicalize([generator.normal(size=shape) + 1j * generator.normal(size=shape)
                            for shape in ((1, 4, 4), (4, 4, 4), (4, 4, 1))])
    dense = np.einsum("apb,bqc,crd->pqr", *tensors).ravel()
    onsite, positions = hamiltonian_terms(request)
    identity = np.eye(4)
    hamiltonian = (np.kron(np.kron(onsite[0], identity), identity)
                   + np.kron(np.kron(identity, onsite[1]), identity)
                   + np.kron(np.kron(identity, identity), onsite[2])
                   - request["coupling"][0] * np.kron(np.kron(positions[0], positions[1]), identity)
                   - request["coupling"][1] * np.kron(np.kron(identity, positions[1]), positions[2]))
    dense_energy = float(np.vdot(dense, hamiltonian @ dense).real / np.vdot(dense, dense).real)
    checked = measure(tensors, request)
    assert abs(dense_energy - checked["energy"]) < 1e-11
    result = {"padded_d_plus_8_operator_max_error": max(discrepancies),
              "minimum_naive_q4_disagreement": min(rejected_naive_powers),
              "dense_vs_contractor_energy_error": abs(dense_energy - checked["energy"]),
              "passed": True}
    (ROOT / "validation/projected_convention.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
