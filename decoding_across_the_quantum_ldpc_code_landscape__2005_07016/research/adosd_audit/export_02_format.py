import sys

sys.dont_write_bytecode = True

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASK = ROOT.parent.parent
sys.path.insert(0, str(TASK / "research/vendor"))
import numpy as np


def export_alist(matrix, destination):
    rows, columns = matrix.shape
    column_weights = np.count_nonzero(matrix, axis=0)
    row_weights = np.count_nonzero(matrix, axis=1)
    max_column = int(column_weights.max())
    max_row = int(row_weights.max())
    with destination.open("w") as output:
        output.write(f"{columns} {rows}\n{max_column} {max_row}\n")
        output.write(" ".join(map(str, column_weights)) + "\n")
        output.write(" ".join(map(str, row_weights)) + "\n")
        for column in range(columns):
            indices = np.flatnonzero(matrix[:, column])
            values = [value for row in indices for value in (int(row) + 1, int(matrix[row, column]))]
            values.extend([0, 0] * (max_column - len(indices)))
            output.write(" ".join(map(str, values)) + "\n")
        for row in range(rows):
            indices = np.flatnonzero(matrix[row])
            values = [value for column in indices for value in (int(column) + 1, int(matrix[row, column]))]
            values.extend([0, 0] * (max_row - len(indices)))
            output.write(" ".join(map(str, values)) + "\n")


path = TASK / "pilots/02_biased_pauli/private/challenge_pool/calibration/case_02.npz"
with np.load(path, allow_pickle=False) as archive:
    matrix = archive["gx"] + 2 * archive["gz"]
    probabilities = archive["pauli_probs"][:, [0, 1, 3, 2]]
    syndrome = archive["syndrome"]
    export_alist(matrix, ROOT / "case02.physical_A4.txt")
    np.savetxt(ROOT / "case02.priors_IXZY.txt", probabilities, fmt="%.17g")
    np.savetxt(ROOT / "case02.syndromes.txt", syndrome, fmt="%d")
    generator = np.random.default_rng(5481)
    labels = generator.integers(0, 4, size=(12, matrix.shape[1]), dtype=np.uint8)
    native_pairing = np.zeros((len(labels), len(matrix)), dtype=np.uint8)
    for shot, error in enumerate(labels):
        native_pairing[shot] = np.sum((matrix != 0) & (error[None, :] != 0)
                                      & (matrix != error[None, :]), axis=1) % 2
    task_pairing = ((labels & 1) @ archive["gz"].T + (labels >> 1) @ archive["gx"].T) % 2
    assert np.array_equal(native_pairing, task_pairing)
    report = {"fixture": str(path), "fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "qubits": int(matrix.shape[1]), "check_rows": int(matrix.shape[0]),
              "shots": int(len(syndrome)), "physical_pauli_encoding": "gx + 2*gz: I,X,Z,Y",
              "prior_column_permutation_from_pilot": [0, 1, 3, 2],
              "pairing_checks": len(labels), "pairing_exact": True,
              "native_decoder_on_fixture_tested": False}
(ROOT / "format_mapping.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
