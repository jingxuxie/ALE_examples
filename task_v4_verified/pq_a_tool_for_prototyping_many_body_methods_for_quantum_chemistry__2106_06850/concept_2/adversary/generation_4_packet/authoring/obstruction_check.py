"""Check the scope of a proposed purely kinematic gradient obstruction."""

import json
import sys
from pathlib import Path

import numpy as np

PACKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKET / "participant" / "workspace"))
from oracle import DeterminantCC


def main():
    oracle = DeterminantCC()
    reference_density = np.outer(oracle.ref, oracle.ref)
    tangent = oracle.generators[0] @ oracle.ref
    coefficient = np.sqrt(0.02 * 1.02)
    deviation = coefficient * (np.outer(tangent, oracle.ref) + np.outer(oracle.ref, tangent))
    relaxed_density = reference_density + deviation
    density = np.einsum("ij,pqji->pq", relaxed_density, oracle.one)
    derivatives = []
    for row in range(15):
        for column in range(row, 15):
            direction = np.zeros((15, 15))
            direction[row, column] = direction[column, row] = 1.0 if row == column else 1 / np.sqrt(2)
            derivatives.append(oracle.hamiltonian(np.zeros(6), direction)[0])
    gradient = np.einsum("ij,kji->k", deviation, derivatives)
    occupations = np.linalg.eigvalsh(density)
    report = {"scope": "linear fixed-particle response relaxation, NOT a stationary CCSD witness",
              "occupation_violation": float(max(-occupations[0], occupations[-1] - 1)),
              "density_dad": float(np.linalg.norm(density - density.T) / np.sqrt(3)),
              "particle_number": float(np.trace(density)), "gradient_norm": float(np.linalg.norm(gradient)),
              "reason": "The Fock-restoring counterterm makes every integral derivative Brillouin-silent between reference and singles. A symmetric reference-single response is invisible to all 120 gradient coordinates but changes the one-body spectrum.",
              "conclusion": "No universal bound follows from density Hermiticity, particle number, and this gradient alone. Additional stationary-CCSD and ground-connection constraints are not relaxed in the task and could impose stronger restrictions; this calculation neither proves task feasibility nor rules out such an obstruction.",
              "ccsd_feasibility": "unknown", "analytic_infeasibility_proof_found": False}
    (PACKET / "authoring" / "obstruction_audit.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
