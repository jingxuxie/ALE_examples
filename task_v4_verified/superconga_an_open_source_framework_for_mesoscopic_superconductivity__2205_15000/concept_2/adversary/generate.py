import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np
from scipy.linalg import solve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
sys.path.insert(0, str(ROOT / "evaluator"))
from spectral import hamiltonian, response, validate_design
from checker import independent_hamiltonian, independent_response


def main():
    config = {
        "width": 12, "height": 12, "hopping": 1.0, "diagonal_hopping": 0.17,
        "gap_d": 0.42, "gap_xy": 0.23, "pin_potential": 1.65,
        "broadening": 0.032, "normal_site_count": 24,
        "candidates": [[column, row] for row in range(2, 10) for column in range(2, 10)],
        "probes": [[0, 3], [0, 8], [11, 2], [11, 9], [3, 0], [8, 11], [5, 5], [8, 4]],
        "energies": np.linspace(-0.9, 0.9, 31).tolist(),
        "conditions": [
            {"name": "nominal", "mu": -0.83, "pair_scale": 1.0, "flux": 0.18},
            {"name": "lower_gap", "mu": -0.79, "pair_scale": 0.94, "flux": 0.23},
            {"name": "higher_gap", "mu": -0.87, "pair_scale": 1.06, "flux": 0.13},
        ],
        "score_scale": 1.0,
    }
    seed = int.from_bytes(os.urandom(8), "little")
    random = np.random.default_rng(seed)
    library = []
    started = time.monotonic()
    for trial in range(24):
        while True:
            pattern = np.zeros(64, dtype=int)
            pattern[random.choice(64, 24, replace=False)] = 1
            try:
                validate_design(config, pattern)
                break
            except ValueError:
                continue
        spectra = response(config, pattern)
        selectivity = float(np.std(spectra[0, :, 15]) / np.mean(spectra[0, :, 15]))
        library.append({"pattern": pattern.tolist(), "selectivity": selectivity})
    design = max(library, key=lambda entry: entry["selectivity"])
    pattern = np.asarray(design["pattern"])
    target = response(config, pattern)
    input_dir = ROOT / "participant" / "input"
    (input_dir / "device.json").write_text(json.dumps(config, indent=2) + "\n")
    np.savez_compressed(input_dir / "target.npz", ldos=target)
    hidden = ROOT / "evaluator" / "hidden"
    witness = hidden / "feasible_design"
    witness.mkdir(exist_ok=True)
    (witness / "design.json").write_text(json.dumps({"pattern": pattern.tolist()}) + "\n")
    matrix = hamiltonian(config, pattern, config["conditions"][0])
    independent = independent_hamiltonian(config, pattern, config["conditions"][0])
    dimension = len(matrix)
    sites = dimension // 2
    eigenvalues = np.linalg.eigvalsh(matrix)
    gauge = random.uniform(-np.pi, np.pi, size=sites)
    unitary = np.exp(1j * np.concatenate([gauge, -gauge]))
    gauge_matrix = unitary[:, None] * matrix * unitary.conj()[None, :]
    transformed_values, transformed_vectors = np.linalg.eigh(gauge_matrix)
    transformed_ldos = []
    for column, row in config["probes"]:
        weights = np.abs(transformed_vectors[row * config["width"] + column]) ** 2
        transformed_ldos.append([float(np.sum(weights * config["broadening"] / np.pi / ((energy - transformed_values) ** 2 + config["broadening"] ** 2))) for energy in config["energies"]])
    inverse_ldos = []
    for energy in config["energies"][::5]:
        inverse = solve((energy + 1j * config["broadening"]) * np.eye(dimension) - matrix, np.eye(dimension))
        inverse_ldos.append([-float(inverse[row * config["width"] + column, row * config["width"] + column].imag) / np.pi for column, row in config["probes"]])
    independent_target = independent_response(config, pattern)
    normal_config = dict(config, gap_d=0.0, gap_xy=0.0, diagonal_hopping=0.0)
    normal_condition = dict(config["conditions"][0], flux=0.0)
    normal_matrix = hamiltonian(normal_config, np.zeros(64), normal_condition)
    horizontal_modes = np.arange(1, config["width"] + 1)
    vertical_modes = np.arange(1, config["height"] + 1)
    normal_exact = -2 * np.cos(np.pi * horizontal_modes[:, None] / (config["width"] + 1)) - 2 * np.cos(np.pi * vertical_modes[None, :] / (config["height"] + 1)) - normal_condition["mu"]
    report = {
        "hermiticity_error": float(np.max(np.abs(matrix - matrix.conj().T))),
        "particle_hole_spectrum_error": float(np.max(np.abs(eigenvalues + eigenvalues[::-1]))),
        "independent_matrix_error": float(np.max(np.abs(matrix - independent))),
        "independent_spectrum_error": float(np.max(np.abs(target - independent_target))),
        "gauge_ldos_error": float(np.max(np.abs(np.asarray(transformed_ldos) - target[0]))),
        "resolvent_ldos_error": float(np.max(np.abs(np.asarray(inverse_ldos).T - target[0, :, ::5]))),
        "normal_rectangle_spectrum_error": float(np.max(np.abs(np.linalg.eigvalsh(normal_matrix[:sites, :sites]) - np.sort(normal_exact.ravel())))),
        "library_size": len(library), "selected_zero_energy_selectivity": design["selectivity"],
        "generation_runtime_seconds": time.monotonic() - started,
    }
    for key, value in report.items():
        if key.endswith("error") and value > 1e-10:
            raise RuntimeError("independent validation failed: " + key)
    report["passed"] = True
    (hidden / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    (ROOT / "adversary" / "library.json").write_text(json.dumps({"private_seed": seed, "designs": library}, indent=2) + "\n")
    seal_paths = ["participant/input/device.json", "participant/input/target.npz",
                  "participant/TASK.md", "participant/input/INTERFACE.md",
                  "participant/workspace/spectral.py", "evaluator/checker.py", "evaluator/evaluate.py"]
    seal = {"core_target": 0.96, "worst_family_target": 0.94,
            "sha256": {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() for relative in seal_paths}}
    (hidden / "freeze.json").write_text(json.dumps(seal, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
