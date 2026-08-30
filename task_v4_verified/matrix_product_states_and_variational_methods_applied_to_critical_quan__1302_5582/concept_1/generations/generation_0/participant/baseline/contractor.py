"""Public finite-Hamiltonian specification and stable MPS contractions."""

import argparse
import json
from pathlib import Path
import zipfile

import numpy as np


def local_operators(dimension, omega):
    padded = dimension + 4
    annihilation = np.diag(np.sqrt(np.arange(1, padded)), 1)
    position = (annihilation + annihilation.T) / np.sqrt(2 * omega)
    momentum = -1j * np.sqrt(omega / 2) * (annihilation - annihilation.T)
    square = position @ position
    return {
        "q": position[:dimension, :dimension].copy(),
        "q2": square[:dimension, :dimension].copy(),
        "q4": (square @ square)[:dimension, :dimension].copy(),
        "p2": (momentum @ momentum).real[:dimension, :dimension].copy(),
        "parity": np.diag((-1.0) ** np.arange(dimension)),
        "identity": np.eye(dimension),
    }


def hamiltonian_terms(request):
    operators = [local_operators(request["local_dim"], frequency)
                 for frequency in request["omega"]]
    onsite = []
    for site, local in enumerate(operators):
        spring = 0.0
        if site:
            spring += request["coupling"][site - 1]
        if site + 1 < request["n_sites"]:
            spring += request["coupling"][site]
        onsite.append(0.5 * local["p2"]
                      + 0.5 * (request["mass2"][site] + spring) * local["q2"]
                      + request["lambda4"][site] * local["q4"] / 24
                      - request["field"][site] * local["q"])
    return onsite, [local["q"] for local in operators]


def validate_mps(tensors, request):
    if len(tensors) != request["n_sites"]:
        raise ValueError("wrong number of tensors")
    previous = 1
    for tensor in tensors:
        if tensor.dtype not in (np.dtype("float64"), np.dtype("complex128")):
            raise ValueError("tensor dtype must be float64 or complex128")
        if tensor.ndim != 3 or tensor.shape[0] != previous:
            raise ValueError("rank or adjacent bond mismatch")
        if tensor.shape[1] != request["local_dim"]:
            raise ValueError("physical dimension mismatch")
        if not 1 <= tensor.shape[2] <= request["bond_cap"]:
            raise ValueError("bond cap exceeded or empty bond")
        if not np.isfinite(tensor).all() or np.max(np.abs(tensor)) > 1e100:
            raise ValueError("nonfinite or excessive tensor entries")
        if not np.any(tensor):
            raise ValueError("zero tensor")
        previous = tensor.shape[2]
    if previous != 1:
        raise ValueError("right boundary must have dimension one")


def load_mps(path, request):
    path = Path(path)
    limit = 8 * 1024 * 1024
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("state must be a bounded regular file")
    expected = {"A%d.npy" % site for site in range(request["n_sites"])}
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) != len(expected) or {entry.filename for entry in entries} != expected:
            raise ValueError("unexpected or duplicate archive members")
        if sum(entry.file_size for entry in entries) > limit:
            raise ValueError("uncompressed state exceeds size limit")
        for entry in entries:
            with archive.open(entry) as stream:
                version = np.lib.format.read_magic(stream)
                if version == (1, 0):
                    shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
                elif version == (2, 0):
                    shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
                else:
                    raise ValueError("unsupported NPY version")
                if len(shape) != 3 or any(size < 1 for size in shape):
                    raise ValueError("invalid tensor header")
                if (shape[0] > request["bond_cap"] or shape[2] > request["bond_cap"]
                        or shape[1] != request["local_dim"]):
                    raise ValueError("tensor header dimensions exceed contract")
                if dtype not in (np.dtype("float64"), np.dtype("complex128")):
                    raise ValueError("invalid tensor header dtype")
                if int(np.prod(shape)) * dtype.itemsize > entry.file_size:
                    raise ValueError("truncated tensor payload")
    with np.load(path, allow_pickle=False) as archive:
        tensors = [archive["A%d" % site].copy() for site in range(request["n_sites"])]
    validate_mps(tensors, request)
    return tensors


def canonicalize(tensors):
    result = [np.array(tensor, copy=True) / np.max(np.abs(tensor)) for tensor in tensors]
    for site in range(len(result) - 1):
        left, physical, right = result[site].shape
        orthogonal, triangular = np.linalg.qr(result[site].reshape(left * physical, right))
        result[site] = orthogonal.reshape(left, physical, orthogonal.shape[1])
        following = np.tensordot(triangular, result[site + 1], axes=(1, 0))
        scale = np.max(np.abs(following))
        if not np.isfinite(scale) or scale == 0:
            raise ValueError("zero state or unstable gauge")
        result[site + 1] = following / scale
    norm = np.linalg.norm(result[-1])
    if not np.isfinite(norm) or norm == 0:
        raise ValueError("zero state")
    result[-1] /= norm
    return result


def transfer(environment, tensor, operator=None):
    if operator is None:
        return np.einsum("ab,apr,bps->rs", environment, tensor.conj(), tensor, optimize=True)
    return np.einsum("ab,apr,pq,bqs->rs", environment, tensor.conj(), operator, tensor,
                     optimize=True)


def measure(tensors, request):
    validate_mps(tensors, request)
    tensors = canonicalize(tensors)
    onsite, positions = hamiltonian_terms(request)
    norm_environment = np.ones((1, 1), dtype=complex)
    energy_environment = np.zeros((1, 1), dtype=complex)
    previous_position = None
    parity_environment = norm_environment.copy()
    parity = np.diag((-1.0) ** np.arange(request["local_dim"]))
    for site, tensor in enumerate(tensors):
        new_energy = transfer(energy_environment, tensor)
        new_energy += transfer(norm_environment, tensor, onsite[site])
        if previous_position is not None:
            new_energy -= request["coupling"][site - 1] * transfer(
                previous_position, tensor, positions[site])
        previous_position = transfer(norm_environment, tensor, positions[site])
        norm_environment = transfer(norm_environment, tensor)
        parity_environment = transfer(parity_environment, tensor, parity)
        energy_environment = new_energy
    norm = norm_environment.item()
    energy = energy_environment.item() / norm
    parity_value = parity_environment.item() / norm
    if (not np.isfinite([norm, energy, parity_value]).all() or abs(norm.imag) > 1e-8
            or norm.real <= 0 or abs(energy.imag) > 1e-8 * max(1, abs(energy.real))):
        raise ValueError("invalid contraction")
    sector = request["sector"]
    if sector != "any":
        expected = 1.0 if sector == "even" else -1.0
        if abs(parity_value - expected) > 1e-6:
            raise ValueError("requested parity sector violated")
    return {"energy": float(energy.real), "parity": float(parity_value.real),
            "norm_after_canonicalization": float(norm.real),
            "max_bond": max(tensor.shape[2] for tensor in tensors)}


def save_mps(path, tensors):
    path = Path(path)
    with path.open("wb") as stream:
        np.savez(stream, **{"A%d" % site: tensor for site, tensor in enumerate(tensors)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--state", required=True)
    args = parser.parse_args()
    request = json.loads(Path(args.request).read_text())
    print(json.dumps(measure(load_mps(args.state, request), request), allow_nan=False))


if __name__ == "__main__":
    main()
