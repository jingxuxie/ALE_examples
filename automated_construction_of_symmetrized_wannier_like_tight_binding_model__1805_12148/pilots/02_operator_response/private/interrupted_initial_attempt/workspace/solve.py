import argparse
from pathlib import Path

import numpy as np

from atomic_h import energies, project_hamiltonian


def solve(case_path):
    with np.load(Path(case_path) / "model.npz", allow_pickle=False) as archive:
        payload = {name: archive[name] for name in archive.files}
    vectors, hopping = project_hamiltonian(payload)
    lookup = {tuple(vector): index for index, vector in enumerate(payload["rvec"])}
    connection = np.zeros(hopping.shape + (3,), dtype=complex)
    for index, vector in enumerate(vectors):
        source = lookup.get(tuple(vector))
        if source is not None:
            connection[index] = payload["connection"][source]
    query_count = len(payload["query_points"])
    return {
        "rvec": vectors, "ham": hopping, "connection": connection,
        "centers": payload["centers"], "energies": energies(payload),
        "berry_raw": np.zeros((query_count, 3)),
        "optical_raw": np.zeros((query_count, 3, 3), dtype=complex),
        "berry_repaired": np.zeros((query_count, 3)),
        "optical_repaired": np.zeros((query_count, 3, 3), dtype=complex),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(arguments.output, **solve(arguments.input))


if __name__ == "__main__":
    main()
