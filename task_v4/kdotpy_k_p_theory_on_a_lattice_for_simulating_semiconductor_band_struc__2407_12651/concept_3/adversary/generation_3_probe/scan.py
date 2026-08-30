import copy
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator"))
from remote_model import FAMILIES, assemble, band_metrics, coordinate_grid, evaluate_fourier, manufacture


def direct_matrix(witness, configuration, horizontal, vertical):
    sys.path.insert(0, str(ROOT / "participant/workspace"))
    from model import full_hamiltonian
    matrices = full_hamiltonian(witness, horizontal, vertical)
    cosine = np.cos(horizontal) + np.cos(vertical)
    for orbital in range(2):
        matrices[..., 2 + orbital, 2 + orbital] = configuration["energies"][orbital] + configuration["dispersion"][orbital] * cosine
        matrices[..., orbital, 2 + orbital] = configuration["onsite"][orbital] + configuration["even"][orbital] * cosine
    matrices[..., 0, 3] = configuration["odd"][0] * (np.sin(horizontal) - 1j * np.sin(vertical))
    matrices[..., 1, 2] = configuration["odd"][1] * (np.sin(horizontal) + 1j * np.sin(vertical))
    matrices[..., 2:, :2] = matrices[..., :2, 2:].conj().swapaxes(-1, -2)
    return matrices


def measure(witness, configuration, mesh, count=3):
    FAMILIES["private_scan"] = configuration
    horizontal, vertical = coordinate_grid(mesh)
    nominal = evaluate_fourier(assemble(witness, "private_scan", 1.0), horizontal, vertical)
    rows = []
    for mass in np.linspace(-0.05, 0.05, count):
        for anisotropy in np.linspace(-0.06, 0.06, count):
            matrices = manufacture(nominal, horizontal, vertical, mass, anisotropy)
            spectrum = np.linalg.eigvalsh(matrices)
            result = band_metrics(spectrum)
            result.update(mass_error=float(mass), anisotropy=float(anisotropy))
            for name, values, maximize in (("lower_max", spectrum[..., 0], True), ("lower_min", spectrum[..., 0], False), ("upper_min", spectrum[..., 1], False)):
                index = np.unravel_index(np.argmax(values) if maximize else np.argmin(values), values.shape)
                result[name] = {"k": [float(horizontal[index]), float(vertical[index])], "energy": float(values[index])}
            rows.append(result)
    return {"mesh": mesh, "scenario_count": len(rows), "sampled_bandwidth": max(row["bandwidth"] for row in rows), "sampled_direct_gap": min(row["direct_above"] for row in rows), "sampled_indirect_gap": min(row["indirect_above"] for row in rows), "sampled_gap12": min(row["gap_12"] for row in rows), "worst_width_scenario": max(rows, key=lambda row: row["bandwidth"]), "worst_gap_scenario": min(rows, key=lambda row: row["indirect_above"])}


def main():
    started = time.monotonic()
    witness = json.loads((ROOT / "champions/generation_2/submission/witness.json").read_text())
    base = copy.deepcopy(FAMILIES["parity_mixed"])
    variants = [("original", base)]
    for scale in (0.85, 0.90, 0.95, 1.05, 1.10, 1.15, 1.20):
        configuration = copy.deepcopy(base)
        for key in ("onsite", "even", "odd"):
            configuration[key] = [value * scale for value in base[key]]
        variants.append((f"hybrid_scale_{scale:.2f}", configuration))
    for shift in (-1.0, -0.5, -0.25, 0.25, 0.5, 1.0):
        configuration = copy.deepcopy(base)
        configuration["energies"] = [value + shift for value in base["energies"]]
        variants.append((f"remote_shift_{shift:+.2f}", configuration))
    for scale in (0.75, 0.9, 1.1, 1.25, 1.5):
        for key in ("onsite", "even", "odd"):
            configuration = copy.deepcopy(base)
            configuration[key] = [value * scale for value in base[key]]
            variants.append((f"{key}_scale_{scale:.2f}", configuration))
    for dispersion in (-0.3, -0.15, 0.15, 0.3):
        configuration = copy.deepcopy(base)
        configuration["dispersion"] = [dispersion, dispersion * 0.75]
        variants.append((f"remote_dispersion_{dispersion:+.2f}", configuration))
    results = []
    generator = np.random.default_rng(240712651)
    horizontal, vertical = generator.uniform(-np.pi, np.pi, (2, 23))
    rotation = np.diag([1.0, 1j, 1.0, 1j])
    validation = []
    for name, configuration in variants:
        FAMILIES["private_scan"] = configuration
        hoppings = assemble(witness, "private_scan", 1.0)
        matrix = evaluate_fourier(hoppings, horizontal, vertical)
        direct = direct_matrix(witness, configuration, horizontal, vertical)
        rotated = evaluate_fourier(hoppings, -vertical, horizontal)
        error = float(np.max(np.abs(rotated - rotation @ matrix @ rotation.conj().T)))
        derivative_error = 0.0
        for coordinate in range(2):
            plus = [horizontal.copy(), vertical.copy()]
            minus = [horizontal.copy(), vertical.copy()]
            plus[coordinate] += 1e-5
            minus[coordinate] -= 1e-5
            finite = (evaluate_fourier(hoppings, *plus) - evaluate_fourier(hoppings, *minus)) / 2e-5
            derivative_error = max(derivative_error, float(np.max(np.abs(finite - evaluate_fourier(hoppings, horizontal, vertical, coordinate)))))
        validation.append({"name": name, "c4_error": error, "direct_fourier_error": float(np.max(np.abs(matrix - direct))), "hermiticity_error": float(np.max(np.abs(matrix - matrix.conj().swapaxes(-1, -2)))), "derivative_error": derivative_error})
        assert max(validation[-1].values() - {name}) < 1e-7 if False else True
        row = {"name": name, "configuration": configuration} | measure(witness, configuration, 81)
        results.append(row)
        print(name, row["sampled_bandwidth"], row["sampled_indirect_gap"], row["sampled_gap12"], flush=True)
    assert all(max(value for key, value in row.items() if key != "name") < 1e-7 for row in validation)
    (DIRECTORY / "scan.json").write_text(json.dumps({"elapsed_seconds": time.monotonic() - started, "variants": results}, indent=2) + "\n")
    (DIRECTORY / "scan_validation.json").write_text(json.dumps(validation, indent=2) + "\n")


if __name__ == "__main__":
    main()
