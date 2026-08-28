import argparse
import json
from pathlib import Path

import numpy as np
import scipy.linalg


def analyze(case, arrays):
    if case["family"] == "bulk_tail":
        onsite, hopping = arrays["onsite"], arrays["hopping"]
        dimension = len(onsite)
        identity = np.eye(dimension)
        zeros = np.zeros_like(onsite)
        pencil_left = np.block([[-onsite, -hopping.conj().T], [identity, zeros]])
        pencil_right = np.block([[hopping, zeros], [zeros, identity]])
        roots = scipy.linalg.eigvals(pencil_left, pencil_right, homogeneous_eigvals=True)
        numerator, denominator = roots
        valid = np.abs(denominator) > 1e-13
        factors = np.abs(numerator[valid] / denominator[valid])
        stable = factors[(factors > 1e-12) & (factors < 1 - 1e-9)]
        length = -float(arrays["cell_length_nm"]) / np.log(stable.max())
        return {"xi_amplitude_nm": float(length)}
    energies, eigenvectors = scipy.linalg.eigh(arrays["energy_matrix"])
    pair = eigenvectors[:, np.argsort(np.abs(energies))[:2]]
    basis = arrays["basis"]
    position_in_basis = basis.conj().T @ (arrays["x_orbital_nm"][:, None] * basis)
    centers, end_coefficients = scipy.linalg.eigh(pair.conj().T @ position_in_basis @ pair)
    left_state = basis @ (pair @ end_coefficients[:, 0])
    coordinates = arrays["x_grid_nm"]
    profile = np.bincount(np.searchsorted(coordinates, arrays["x_orbital_nm"]), weights=np.abs(left_state) ** 2)
    profile /= profile.sum()
    quarter = len(coordinates) // 4
    fit_x = coordinates[quarter:2 * quarter]
    fit_y = np.log(profile[quarter:2 * quarter])
    fit_x = fit_x - fit_x.mean()
    slope = np.dot(fit_x, fit_y - fit_y.mean()) / np.dot(fit_x, fit_x)
    return {"rho_left": profile.tolist(), "xi_window_nm": float(-2 / slope)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.input / "manifest.json").read_text())
    predictions = {}
    for case in manifest["cases"]:
        with np.load(args.input / case["file"], allow_pickle=False) as arrays:
            predictions[case["id"]] = analyze(case, arrays)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"schema_version": 1, "predictions": predictions}, allow_nan=False))


if __name__ == "__main__":
    main()
