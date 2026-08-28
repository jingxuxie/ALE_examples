import argparse
import json
from pathlib import Path

import numpy as np
import scipy.linalg


def fit_amplitude_length(coordinates, density):
    quarter = len(coordinates) // 4
    selection = slice(quarter, 2 * quarter)
    slope = np.polyfit(coordinates[selection], np.log(np.maximum(density[selection], 1e-300)), 1)[0]
    if slope >= 0:
        return float(coordinates[-1] - coordinates[0])
    return float(-2 / slope)


def analyze(case, arrays):
    if case["family"] == "bulk_tail":
        return {"xi_amplitude_nm": fit_amplitude_length(arrays["witness_x_nm"], arrays["witness_density"])}
    energies, vectors = scipy.linalg.eigh(arrays["energy_matrix"])
    positive = np.flatnonzero(energies > 0)
    selected = positive[np.argmin(energies[positive])]
    wavefunction = arrays["basis"] @ vectors[:, selected]
    coordinates = arrays["x_grid_nm"]
    density = np.bincount(np.searchsorted(coordinates, arrays["x_orbital_nm"]), weights=np.abs(wavefunction) ** 2)
    density /= density.sum()
    return {"rho_left": density.tolist(), "xi_window_nm": fit_amplitude_length(coordinates, density)}


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
