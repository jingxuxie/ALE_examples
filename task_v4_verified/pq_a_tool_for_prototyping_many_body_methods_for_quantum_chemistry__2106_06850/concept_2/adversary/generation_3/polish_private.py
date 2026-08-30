"""Private exact-right-state centering of a low-sensitivity warm-start witness."""

import json
import os
import sys
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.optimize import root_scalar

BASE = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "participant" / "workspace"))
from api import artifact, robust_screen
from oracle import DeterminantCC


def main():
    source = BASE / "adversary/generation_2/worker_feasibility_champion_high/closest_candidate.json"
    data = json.loads(source.read_text())
    oracle = DeterminantCC()
    interaction = np.array(data["pair_matrix"])
    initial = np.array(data["amplitudes"])
    energies = data["orbital_energies"]
    indices = np.triu_indices(15)
    basis = []
    zero = oracle.hamiltonian(energies, np.zeros((15, 15)))[0]
    for row, column in zip(*indices):
        direction = np.zeros((15, 15))
        direction[row, column] = 1
        direction[column, row] = 1
        basis.append(oracle.hamiltonian(energies, direction)[0] - zero)
    basis = np.array(basis)
    hamiltonian = oracle.hamiltonian(energies, interaction)[0]
    result = oracle.solve(hamiltonian, initial, tolerance=2e-12)
    positive, inverse = oracle.exponentials(result.amplitudes)
    fixed = inverse @ basis @ positive
    amplitude_derivative = np.linalg.solve(result.jacobian, -fixed[:, oracle.targets, oracle.reference].T).T
    cluster_derivative = (amplitude_derivative @ oracle.generator_flat).reshape(120, 20, 20)
    transformed_derivative = fixed + result.hbar @ cluster_derivative - cluster_derivative @ result.hbar
    direction = transformed_derivative[:, -1, oracle.reference]
    direction /= np.linalg.norm(direction)
    matrix_direction = np.zeros((15, 15))
    matrix_direction[indices] = direction
    matrix_direction[(indices[1], indices[0])] = direction

    def triple(displacement):
        matrix = oracle.hamiltonian(energies, interaction + displacement * matrix_direction)[0]
        solved = oracle.solve(matrix, initial, tolerance=2e-12, max_evaluations=250)
        if not solved.converged:
            raise ValueError("private polishing root failed")
        return solved.hbar[-1, oracle.reference]

    answer = root_scalar(triple, x0=0.0, x1=0.001, method="secant", xtol=1e-13)
    if not answer.converged:
        raise ValueError("private triple residual centering failed")
    changed = interaction + answer.root * matrix_direction
    solved = oracle.solve(oracle.hamiltonian(energies, changed)[0], initial, tolerance=2e-12)
    destination = OUTPUT / "private_centered_candidate.json"
    destination.write_text(json.dumps(artifact(changed, solved.amplitudes), indent=2, allow_nan=False))
    report = robust_screen(changed, solved.amplitudes, oracle, check_paths=False)
    report["centering_displacement"] = answer.root
    (OUTPUT / "private_centered_endpoint_report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({key: value for key, value in report.items() if key != "points"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
