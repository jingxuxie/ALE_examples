import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from solve import pack, unpack


def unitary(random, dimension):
    matrix = random.normal(size=(dimension, dimension)) + 1j * random.normal(size=(dimension, dimension))
    vectors, triangular = np.linalg.qr(matrix)
    phases = np.diag(triangular)
    return vectors * (phases / np.abs(phases)).conj()[None, :]


def resolvent(points, energies, residues):
    result = np.zeros((len(points),) + residues.shape[1:], dtype=complex)
    for start in range(0, len(energies), 4096):
        inverse = 1.0 / (points[:, None] - energies[None, start:start + 4096])
        result += np.einsum("ze,eab->zab", inverse, residues[start:start + 4096], optimize=True)
    return result


def finite_model(seed, dimension, bath_size, near_zero=False):
    random = np.random.default_rng(seed)
    diagonal = np.linspace(-1.0, 1.0, dimension) + random.normal(scale=0.14, size=dimension)
    orbital_rotation = unitary(random, dimension)
    local = orbital_rotation @ np.diag(diagonal) @ orbital_rotation.conj().T
    bath = np.linspace(-2.7, 2.7, bath_size) + random.normal(scale=0.08, size=bath_size)
    if near_zero:
        bath[bath_size // 2] = random.uniform(-0.035, 0.035)
    coupling = (random.normal(size=(dimension, bath_size)) + 1j * random.normal(size=(dimension, bath_size))) * 0.45 / np.sqrt(bath_size)
    hamiltonian = np.block([[local, coupling], [coupling.conj().T, np.diag(bath)]])
    energies, vectors = np.linalg.eigh(hamiltonian)
    projection = vectors[:dimension].T
    residues = np.einsum("ea,eb->eab", projection, projection.conj())
    return local, energies, residues, {"hamiltonian": pack(hamiltonian)}


def band_model(seed, dimension, grid_size):
    random = np.random.default_rng(seed)
    rotation = unitary(random, dimension)
    axes = np.arange(grid_size) * (2 * np.pi / grid_size)
    wave_x, wave_y = np.meshgrid(axes, axes, indexing="ij")
    wave_x = wave_x.ravel()
    wave_y = wave_y.ravel()
    hamiltonians = np.zeros((len(wave_x), dimension, dimension), dtype=complex)
    shifts = np.linspace(-0.7, 0.8, dimension) + random.uniform(-0.1, 0.1, dimension)
    hopping = random.uniform(0.45, 1.0, dimension)
    for orbital in range(dimension):
        hamiltonians[:, orbital, orbital] = shifts[orbital] - 2 * hopping[orbital] * (np.cos(wave_x) + 0.4 * np.cos(wave_y))
    for orbital in range(dimension - 1):
        coupling = 0.22 + 0.13 * np.cos(wave_y) + 0.17j * np.sin(wave_x)
        hamiltonians[:, orbital, orbital + 1] = coupling
        hamiltonians[:, orbital + 1, orbital] = coupling.conj()
    hamiltonians = np.einsum("ab,kbc,dc->kad", rotation, hamiltonians, rotation.conj(), optimize=True)
    energies, vectors = np.linalg.eigh(hamiltonians)
    projection = vectors.transpose(0, 2, 1).reshape(-1, dimension)
    residues = np.einsum("ea,eb->eab", projection, projection.conj()) / len(wave_x)
    return np.mean(hamiltonians, axis=0), energies.ravel(), residues, {"seed": seed, "dimension": dimension, "grid_size": grid_size}


def make_case(seed, family, dimension, variant=0, grid_size=160):
    if family == "discrete":
        local, energies, residues, model = finite_model(seed, dimension, 3 + variant % 3)
        eta = 0.15
    elif family == "dyson_zero":
        local, energies, residues, model = finite_model(seed, dimension, 6 + variant % 3, True)
        eta = 0.09
    else:
        local, energies, residues, model = band_model(seed, dimension, grid_size)
        eta = 0.28
    beta = 30.0 + 4 * (variant % 3)
    indices = np.unique(np.r_[np.arange(72), np.round(np.geomspace(73, 1100, 40)).astype(int)])
    matsubara = (2 * indices + 1) * np.pi / beta
    omega = np.linspace(-3.6, 3.6, 241)
    moments = [np.einsum("e,eab->ab", energies ** power, residues) for power in range(3)]
    green_iw = resolvent(1j * matsubara, energies, residues)
    green_real = resolvent(omega + 1j * eta, energies, residues)
    sigma = (omega + 1j * eta)[:, None, None] * np.eye(dimension) - local - np.linalg.inv(green_real)
    request = {"iw": matsubara.tolist(), "G_iw": pack(green_iw), "moments": [pack(moment) for moment in moments],
               "h0": pack(local), "omega": omega.tolist(), "eta": eta, "support": [float(energies.min() - 0.1), float(energies.max() + 0.1)],
               "absolute_data_error": 2e-13}
    reference = {"G_retarded": pack(green_real), "Sigma_retarded": pack(sigma)}
    spectral = -(green_real - green_real.conj().transpose(0, 2, 1)) / (2j * np.pi)
    validation = {"identity_moment_error": float(np.max(np.abs(moments[0] - np.eye(dimension)))),
                  "first_moment_error": float(np.max(np.abs(moments[1] - local))),
                  "minimum_spectral_eigenvalue": float(np.linalg.eigvalsh(spectral).min())}
    if family != "band":
        full_hamiltonian = unpack(model["hamiltonian"])
        direct = np.linalg.inv((omega + 1j * eta)[:, None, None] * np.eye(len(full_hamiltonian)) - full_hamiltonian)
        validation["direct_inverse_error"] = float(np.max(np.abs(direct[:, :dimension, :dimension] - green_real)))
    return request, reference, model, validation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="initial")
    arguments = parser.parse_args()
    groups = [("core", 21700, 2), ("challenge", 36710, 3)] if arguments.split == "initial" else [(arguments.split, 89000 if arguments.split == "ratchet" else 99220, 3)]
    for split, seed_base, count in groups:
        manifest = []
        for family_index, family in enumerate(["discrete", "dyson_zero", "band"]):
            for variant in range(count):
                seed = seed_base + family_index * 101 + variant * 7
                dimension = 2 + variant % 3
                request, reference, model, validation = make_case(seed, family, dimension, variant)
                identifier = hashlib.sha256(f"{split}:{seed}".encode()).hexdigest()[:14]
                target = ROOT / "private" / "challenge_pool" / split / identifier
                target.mkdir(parents=True, exist_ok=True)
                (target / "input.json").write_text(json.dumps(request))
                (target / "expected.json").write_text(json.dumps(reference))
                (target / "model.json").write_text(json.dumps(model))
                (target / "validation.json").write_text(json.dumps(validation, indent=2))
                manifest.append({"id": identifier, "family": family, "input": str(target.relative_to(ROOT / "private") / "input.json"),
                                 "expected": str(target.relative_to(ROOT / "private") / "expected.json"), "validation": validation})
                print(split, identifier, family, validation, flush=True)
        (ROOT / "private" / "challenge_pool" / f"{split}.json").write_text(json.dumps(manifest, indent=2))
    if arguments.split == "initial":
        sample, _, _, _ = make_case(713, "discrete", 2)
        (ROOT / "participant" / "input" / "example.json").write_text(json.dumps(sample))


if __name__ == "__main__":
    main()
