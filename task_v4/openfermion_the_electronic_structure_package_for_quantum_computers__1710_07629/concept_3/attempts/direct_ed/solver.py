"""Ordinary relaxed-tolerance ED control, not a trained model."""

import json
import os
from pathlib import Path
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np
from scipy.sparse.linalg import LinearOperator, eigsh

from exact import sector_matrix, spin_kinetic


def direct_gap(hopping, interaction, potential, method="tensor", tolerance=1e-5, ncv=20):
    half = len(hopping) // 2
    sectors = ((half, half), (half, half - 1), (half + 1, half), (half + 1, half - 1))
    energies = []
    for up_count, down_count in sectors:
        if method == "csr":
            matrix = sector_matrix(hopping, interaction, potential, up_count, down_count)
        else:
            up_matrix, up_occupation = spin_kinetic(hopping, up_count)
            down_matrix, down_occupation = spin_kinetic(hopping, down_count)
            diagonal = ((up_occupation * interaction) @ down_occupation.T
                        + (up_occupation @ potential)[:, None]
                        + (down_occupation @ potential)[None, :])

            def matvec(vector):
                amplitudes = vector.reshape(diagonal.shape)
                return (up_matrix @ amplitudes + (down_matrix @ amplitudes.T).T
                        + diagonal * amplitudes).ravel()

            matrix = LinearOperator((diagonal.size, diagonal.size), matvec=matvec, dtype=np.float64)
        initial = np.random.default_rng(8931).standard_normal(matrix.shape[0])
        energy = eigsh(matrix, k=1, which="SA", ncv=ncv, tol=tolerance, v0=initial,
                       maxiter=12000, return_eigenvectors=False)[0]
        energies.append(energy)
    return [float(energies[1] + energies[2] - 2.0 * energies[0]),
            float(energies[3] - energies[0])]


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    configuration_path = Path(__file__).with_name("control.json")
    configuration = json.loads(configuration_path.read_text()) if configuration_path.exists() else {}
    with np.load(request["inputs"], allow_pickle=False) as archive:
        inputs = dict(archive)
    predictions = []
    started = time.perf_counter()
    for index, n_sites in enumerate(inputs["n_sites"]):
        predictions.append(direct_gap(inputs["hopping"][index, :n_sites, :n_sites],
                                      inputs["interaction"][index, :n_sites],
                                      inputs["potential"][index, :n_sites], request.get("method", "tensor"),
                                      request.get("tolerance", configuration.get("tolerance", 1e-5)),
                                      request.get("ncv", configuration.get("ncv", 20))))
        if (index + 1) % 8 == 0:
            print(json.dumps({"completed": index + 1, "seconds": time.perf_counter() - started}), flush=True)
    Path(sys.argv[2]).write_text(json.dumps({"schema_version": 1, "predictions": predictions}) + "\n")


if __name__ == "__main__":
    main()
