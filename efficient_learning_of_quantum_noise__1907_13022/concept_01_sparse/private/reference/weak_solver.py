import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import sys

import numpy as np
from scipy.optimize import nnls


def main():
    with np.load(sys.argv[1], allow_pickle=False) as data:
        qubits = int(data["n_qubits"])
        hashes = data["hashes"]
        offsets = data["offsets"]
        values = data["eigenvalues"]
    paulis = np.zeros((3 * qubits, qubits), dtype=np.uint8)
    for qubit in range(qubits):
        paulis[3 * qubit : 3 * qubit + 3, qubit] = [1, 2, 3]
    labels = np.vstack([np.zeros((1, qubits), dtype=np.uint8), paulis])
    lookup = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.uint8)
    bits = lookup[labels].reshape(len(labels), 2 * qubits)
    generator = np.random.default_rng(73427)
    sample_count = min(3072, values.size)
    flat = generator.choice(values.size, sample_count, replace=False)
    groups, times, indexes = np.unravel_index(flat, values.shape)
    binary = ((indexes[:, None] >> np.arange(hashes.shape[1])) & 1).astype(np.uint8)
    masks = offsets[times] ^ ((binary[:, None, :] @ hashes[groups])[:, 0, :] & 1)
    design = 1.0 - 2.0 * ((masks @ bits.T) & 1)
    probabilities = nnls(design, values.ravel()[flat])[0]
    if probabilities.sum() > 1:
        probabilities /= probabilities.sum()
    np.savez(sys.argv[2], paulis=paulis, probabilities=probabilities[1:], p_identity=np.array(probabilities[0]))


if __name__ == "__main__":
    main()
