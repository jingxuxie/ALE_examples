"""Check the anomalous joint-fit target against the stated optimization problem."""

import argparse
import json
from pathlib import Path
import sys
import time


parser = argparse.ArgumentParser()
parser.add_argument("--runtime", choices=("runtime", "runtime4"), required=True)
args = parser.parse_args()
AUTHOR = Path(__file__).resolve().parent
ROOT = AUTHOR.parent
sys.path.insert(0, str(AUTHOR / args.runtime))
sys.path.insert(0, str(ROOT / "concepts/fitting/private/reference"))

import numpy as np
import symfc
from symfc import Symfc
from symfc.utils.utils import SymfcAtoms
from physics import harmonic_forces, cubic_forces, invariant_errors


PRIVATE = ROOT / "concepts/fitting/private"
data = dict(np.load(PRIVATE / "challenge_pool/initial_si_8/input.npz", allow_pickle=False))
stored = dict(np.load(PRIVATE / "reference/initial_si_8.npz", allow_pickle=False))
candidate = dict(np.load(AUTHOR / "scores/fitting_pilot_artifacts/initial_si_8/result.npz", allow_pickle=False))
atoms = SymfcAtoms(cell=data["cell3"], scaled_positions=data["positions3"], numbers=data["numbers3"])
before_displacements = data["u3"].copy()
before_forces = data["f3"].copy()
started = time.monotonic()
solver = Symfc(atoms, displacements=data["u3"], forces=data["f3"],
               cutoff={3: float(data["cutoff3"])}, log_level=0)
solver.run(orders=[2, 3], is_compact_fc=True)
fresh = {f"fc{order}": solver.force_constants[order] for order in (2, 3)}
report = {"runtime": args.runtime, "symfc_version": symfc.__version__,
          "seconds": time.monotonic() - started,
          "input_displacements_mutated": not np.array_equal(before_displacements, data["u3"]),
          "input_forces_mutated": not np.array_equal(before_forces, data["f3"]),
          "solutions": {}}


def predict(solution, displacements):
    return harmonic_forces(solution["fc2"], displacements, data["s2p3"], data["compact_map3"]) + cubic_forces(solution["fc3"], displacements, data["s2p3"], data["compact_map3"])


independent = Symfc(atoms, cutoff={3: float(data["cutoff3"])}, log_level=0)
independent.compute_basis_set(orders=[2, 3])
coefficient_bases = {}
design_columns = []
counts = {}
for order in (2, 3):
    basis = independent.basis_set[order]
    matrix = np.asarray(basis.compact_compression_matrix @ basis.basis_set)
    counts[order] = matrix.shape[1]
    shape = (len(data["p2s3"]),) + (len(data["s2p3"]),) * (order - 1) + (3,) * order
    coefficient_bases[order] = matrix
    for column in range(matrix.shape[1]):
        tensor = matrix[:, column].reshape(shape)
        if order == 2:
            forces = harmonic_forces(tensor, before_displacements, data["s2p3"], data["compact_map3"])
        else:
            forces = cubic_forces(tensor, before_displacements, data["s2p3"], data["compact_map3"])
        design_columns.append(forces.ravel())
design = np.column_stack(design_columns)
coefficients, residuals, rank, singular_values = np.linalg.lstsq(design, before_forces.ravel(), rcond=None)
explicit = {
    "fc2": (coefficient_bases[2] @ coefficients[:counts[2]]).reshape(fresh["fc2"].shape),
    "fc3": (coefficient_bases[3] @ coefficients[counts[2]:]).reshape(fresh["fc3"].shape),
}
report["independent_design"] = {"shape": list(design.shape), "rank": int(rank),
                                "condition_number": float(singular_values[0] / singular_values[-1]),
                                "normal_residual": float(np.linalg.norm(design.T @ (design @ coefficients - before_forces.ravel())))}
for name, solution in (("stored_reference", stored), ("fresh_oracle", fresh), ("submitted", candidate), ("explicit_official_basis", explicit)):
    training_residual = predict(solution, before_displacements) - before_forces
    heldout_residual = predict(solution, stored["heldout_u3"]) - stored["heldout_f3"]
    report["solutions"][name] = {
        "train_rmse": float(np.sqrt(np.mean(training_residual**2))),
        "train_sse": float(np.sum(training_residual**2)),
        "heldout_rmse": float(np.sqrt(np.mean(heldout_residual**2))),
        "invariants": invariant_errors(solution, data),
        "tensor_norms": {key: float(np.linalg.norm(solution[key])) for key in ("fc2", "fc3")},
        "relative_to_fresh": {key: float(np.linalg.norm(solution[key] - fresh[key]) / max(np.linalg.norm(fresh[key]), 1e-20)) for key in ("fc2", "fc3")},
    }
residual = predict(stored, before_displacements) - before_forces
feasible_direction = predict(candidate, before_displacements) - predict(stored, before_displacements)
report["stored_reference_directional_objective_derivative"] = float(2 * np.sum(residual * feasible_direction))
report["direction_explanation"] = "A negative derivative toward another invariant-satisfying solution disproves optimality of the stored reference for the public least-squares objective."
destination = AUTHOR / "si_audit"
destination.mkdir(exist_ok=True)
np.savez_compressed(destination / f"fresh_{args.runtime}.npz", **fresh)
np.savez_compressed(destination / f"explicit_{args.runtime}.npz", **explicit)
(destination / f"{args.runtime}.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
