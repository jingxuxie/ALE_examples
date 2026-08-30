"""Authoring-only validation calibration, never a participant solution."""

import json
import os
from pathlib import Path
import sys

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import nnls

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant/input"))
sys.path.insert(0, str(ROOT / "evaluator"))
from physics import kernel, observables
from runtime import execute_submission
from scoring import score_prediction


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def main():
    inputs = load(ROOT / "participant/input/validation_input.npz")
    prediction, runtime = execute_submission(
        ROOT / "participant/baseline",
        ROOT / "participant/input/validation_input.npz",
        ROOT / "participant/input",
    )
    labels = load(ROOT / "participant/input/validation_labels.npz")
    baseline_score = score_prediction(prediction, inputs, labels)
    np.savez_compressed(ROOT / "evaluator/hidden/baseline_validation_predictions.npz", **prediction)
    privileged = load(ROOT / "evaluator/hidden/validation_privileged.npz")
    mass = np.empty_like(labels["spectral_mass"])
    for row, beta in enumerate(inputs["beta"]):
        basis = privileged["basis"][row]
        basis = basis[:, basis.sum(axis=0) > 0.0]
        response = kernel(beta, inputs["tau"][row], inputs["omega_edges"])
        chol = np.linalg.cholesky(inputs["covariance"][row])
        design = solve_triangular(chol, response @ basis, lower=True)
        target = solve_triangular(chol, inputs["correlation"][row], lower=True)
        coefficients, _ = nnls(np.vstack((design, np.full((1, basis.shape[1]), 1e5))), np.append(target, 1e5))
        mass[row] = basis @ coefficients
        mass[row] /= mass[row].sum()
    low = observables(mass, inputs["omega_edges"])["low_mass"]
    privileged_prediction = {
        "sample_id": inputs["sample_id"],
        "spectral_mass": mass,
        "low_mass_quantiles": np.clip(low[:, None] + np.array([-0.01, 0.0, 0.01]), 0.0, 1.0),
    }
    privileged_score = score_prediction(privileged_prediction, inputs, labels)
    report = {
        "phase": "before target freeze and before fresh attempts",
        "baseline": {**baseline_score, **runtime},
        "privileged_known_component_shapes": privileged_score,
        "privilege_warning": "True latent component shapes supplied only to this diagnostic; not a feasible solver, not proof of attainability.",
    }
    (ROOT / "evaluator/hidden/calibration.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
