import hashlib
import json
from pathlib import Path

import numpy as np

import generate


ORIGINAL_BAND = generate.band_model


def chiral_band(seed, dimension, grid_size):
    _, energies, residues, _ = ORIGINAL_BAND(seed, dimension, grid_size)
    count = grid_size ** 2
    hamiltonians = (energies[:, None, None] * residues).reshape(count, dimension, dimension, dimension).sum(axis=1) * count
    axes = np.arange(grid_size) * (2 * np.pi / grid_size)
    wave_x, wave_y = np.meshgrid(axes, axes, indexing="ij")
    phase = 0.43 + (seed % 17) * 0.041
    loop = (0.37 + 0.19 * np.cos(wave_x.ravel())) * np.exp(1j * phase) + 0.23j * np.sin(wave_y.ravel())
    hamiltonians[:, 0, dimension - 1] += loop
    hamiltonians[:, dimension - 1, 0] += loop.conj()
    eigenvalues, eigenvectors = np.linalg.eigh(hamiltonians)
    projection = eigenvectors.transpose(0, 2, 1).reshape(-1, dimension)
    spectral_weights = np.einsum("ea,eb->eab", projection, projection.conj()) / count
    witness = float(np.trace(hamiltonians[0] @ hamiltonians[grid_size // 3] @ hamiltonians[(grid_size // 3) * grid_size + grid_size // 5]).imag)
    return hamiltonians.mean(axis=0), eigenvalues.ravel(), spectral_weights, {"seed": seed, "dimension": dimension, "grid_size": grid_size,
                                                                          "complex_trace_witness": witness, "phase": phase}


def main():
    generate.band_model = chiral_band
    root = Path(__file__).resolve().parents[2]
    manifest = []
    for index, seed in enumerate([49391, 49439, 49523, 49603]):
        dimension = 3 + index % 2
        request, reference, model, validation = generate.make_case(seed, "band", dimension, index, 160)
        finer = generate.make_case(seed, "band", dimension, index, 256)
        for key in ["G_retarded", "Sigma_retarded"]:
            difference = np.linalg.norm(generate.unpack(reference[key]) - generate.unpack(finer[1][key])) / np.linalg.norm(generate.unpack(finer[1][key]))
            validation[key + "_grid_relative_difference"] = float(difference)
        validation["complex_trace_witness"] = model["complex_trace_witness"]
        identifier = hashlib.sha256(f"stress:{seed}".encode()).hexdigest()[:14]
        destination = root / "private" / "challenge_pool" / "stress" / identifier
        destination.mkdir(parents=True, exist_ok=True)
        for filename, value in [("input.json", request), ("expected.json", reference), ("model.json", model), ("validation.json", validation)]:
            (destination / filename).write_text(json.dumps(value))
        manifest.append({"id": identifier, "family": "chiral_band_" + str(dimension), "input": str(destination.relative_to(root / "private") / "input.json"),
                         "expected": str(destination.relative_to(root / "private") / "expected.json"), "validation": validation})
        print(identifier, validation, flush=True)
    (root / "private" / "challenge_pool" / "stress.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
