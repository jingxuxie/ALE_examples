import json
from pathlib import Path

import numpy as np


def finite_response(payload, point, occupied, step):
    displacement = payload["rvec"][:, None, None, :] @ payload["lattice"]
    displacement = displacement + payload["centers"][None, None, :, :] - payload["centers"][None, :, None, :]
    reduced_displacement = displacement @ np.linalg.inv(payload["lattice"])
    base_phase = np.exp(2j * np.pi * np.einsum("rmna,a->rmn", reduced_displacement, point))

    def sample(offset):
        phase = base_phase * np.exp(1j * np.einsum("rmna,a->rmn", displacement, offset))
        hamiltonian = np.einsum("rmn,rmn->mn", phase, payload["ham"])
        _, vectors = np.linalg.eigh((hamiltonian + hamiltonian.conj().T) / 2)
        projector = vectors[:, :occupied] @ vectors[:, :occupied].conj().T
        connection = np.einsum("rmn,rmna->amn", phase, payload["connection"])
        connection = (connection + connection.swapaxes(1, 2).conj()) / 2
        trace_connection = np.einsum("nm,amn->a", projector, connection).real
        return projector, connection, trace_connection

    projector, connection, _ = sample(np.zeros(3))
    gradients, connection_gradients = [], []
    for direction in np.eye(3):
        plus = sample(step * direction)
        minus = sample(-step * direction)
        gradients.append((plus[0] - minus[0]) / (2 * step))
        connection_gradients.append((plus[2] - minus[2]) / (2 * step))
    berry = []
    for alpha, beta in [(1, 2), (2, 0), (0, 1)]:
        commutator = gradients[alpha] @ gradients[beta] - gradients[beta] @ gradients[alpha]
        internal = (1j * np.trace(projector @ commutator)).real
        berry.append(internal + connection_gradients[alpha][beta] - connection_gradients[beta][alpha])
    complement = np.eye(len(projector)) - projector
    amplitudes = [projector @ (connection[axis] - 1j * gradients[axis]) @ complement for axis in range(3)]
    optical = np.array([[1j * np.trace(left @ right.conj().T) for right in amplitudes] for left in amplitudes])
    return np.asarray(berry), optical


def check_case(case_path, expected):
    case_path = Path(case_path)
    metadata = json.loads((case_path / "case.json").read_text())
    with np.load(case_path / "model.npz", allow_pickle=False) as archive:
        payload = {name: archive[name] for name in archive.files}
    results = {}
    for step in [1e-4, 5e-5]:
        berry, optical = finite_response(payload, payload["query_points"][0], metadata["occupied"], step)
        errors = {
            "berry_relative_error": float(np.linalg.norm(berry - expected["berry_raw"][0]) / max(np.linalg.norm(expected["berry_raw"][0]), 1e-12)),
            "optical_relative_error": float(np.linalg.norm(optical - expected["optical_raw"][0]) / max(np.linalg.norm(expected["optical_raw"][0]), 1e-12)),
        }
        results[str(step)] = errors
    assert results["5e-05"]["berry_relative_error"] < 5e-3, results
    assert results["5e-05"]["optical_relative_error"] < 5e-3, results
    return results
