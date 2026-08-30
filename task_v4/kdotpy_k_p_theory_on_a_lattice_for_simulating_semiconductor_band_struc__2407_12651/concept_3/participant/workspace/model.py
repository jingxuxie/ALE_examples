import json
from pathlib import Path

import numpy as np


SPIN_MODES = [(horizontal, vertical) for horizontal in range(1, 4) for vertical in range(4) if (horizontal, vertical) != (1, 0)]
EVEN_MODES = [(horizontal, vertical) for horizontal in range(1, 4) for vertical in range(horizontal + 1)]


def baseline():
    return {
        "schema_version": 1,
        "mass": -1.0,
        "spin_orbit": [0.0] * len(SPIN_MODES),
        "orbital_mass": [1.0] + [0.0] * (len(EVEN_MODES) - 1),
        "scalar": [0.0] * len(EVEN_MODES),
    }


def pack(witness):
    return np.array([witness["mass"]] + witness["spin_orbit"] + witness["orbital_mass"] + witness["scalar"], dtype=float)


def unpack(parameters):
    return {
        "schema_version": 1,
        "mass": float(parameters[0]),
        "spin_orbit": parameters[1:12].tolist(),
        "orbital_mass": parameters[12:21].tolist(),
        "scalar": parameters[21:30].tolist(),
    }


def features(horizontal, vertical):
    horizontal, vertical = np.broadcast_arrays(horizontal, vertical)
    shape = horizontal.shape
    basis = np.zeros(shape + (4, 30))
    offset = np.zeros(shape + (4,))
    offset[..., 1] = np.sin(horizontal)
    offset[..., 2] = np.sin(vertical)
    basis[..., 3, 0] = 1.0
    for index, (order, cross) in enumerate(SPIN_MODES, 1):
        basis[..., 1, index] = np.sin(order * horizontal) * np.cos(cross * vertical)
        basis[..., 2, index] = np.cos(cross * horizontal) * np.sin(order * vertical)
    for index, (order, cross) in enumerate(EVEN_MODES):
        value = np.cos(order * horizontal) * np.cos(cross * vertical)
        if order != cross:
            value = value + np.cos(cross * horizontal) * np.cos(order * vertical)
        basis[..., 3, 12 + index] = value
        basis[..., 0, 21 + index] = value
    return offset, basis


def components(witness, horizontal, vertical, mass_error=0.0, anisotropy=0.0):
    offset, basis = features(horizontal, vertical)
    values = offset + np.einsum("...ij,j->...i", basis, pack(witness))
    values[..., 3] += mass_error
    values[..., 1] += anisotropy * np.sin(horizontal)
    values[..., 2] -= anisotropy * np.sin(vertical)
    return values


def energies(values):
    radius = np.linalg.norm(values[..., 1:], axis=-1)
    return values[..., 0] - radius, values[..., 0] + radius


def full_hamiltonian(witness, horizontal, vertical, mass_error=0.0, anisotropy=0.0):
    values = components(witness, horizontal, vertical, mass_error, anisotropy)
    matrices = np.zeros(values.shape[:-1] + (4, 4), dtype=complex)
    matrices[..., 0, 0] = values[..., 0] + values[..., 3]
    matrices[..., 1, 1] = values[..., 0] - values[..., 3]
    matrices[..., 0, 1] = values[..., 1] - 1j * values[..., 2]
    matrices[..., 1, 0] = values[..., 1] + 1j * values[..., 2]
    matrices[..., 2, 2] = 5.5
    matrices[..., 3, 3] = 8.0
    cosine = np.cos(horizontal) + np.cos(vertical)
    matrices[..., 0, 2] = 1.1 + 0.25 * cosine
    matrices[..., 1, 3] = 0.5 + 0.10 * cosine
    matrices[..., 0, 3] = 0.45 * (np.sin(horizontal) - 1j * np.sin(vertical))
    matrices[..., 1, 2] = 0.30 * (np.sin(horizontal) + 1j * np.sin(vertical))
    matrices[..., 2:, :2] = matrices[..., :2, 2:].conj().swapaxes(-1, -2)
    return matrices


def manufacturing_tail(witness, relative_error=0.004):
    spin = np.sqrt(2.0) * np.sum(np.abs(witness["spin_orbit"]))
    even = sum((1.0 if order == cross else 2.0) * (abs(mass) + abs(scalar)) for (order, cross), mass, scalar in zip(EVEN_MODES, witness["orbital_mass"], witness["scalar"]))
    return float(relative_error * (spin + even))


def sample(witness, mesh=81, uncertainty_points=3):
    axis = np.linspace(-np.pi, np.pi, mesh, endpoint=False)
    horizontal, vertical = np.meshgrid(axis, axis, indexing="ij")
    nominal = full_hamiltonian(witness, horizontal, vertical)
    worst_width = 0.0
    direct_gap = float("inf")
    indirect_gap = float("inf")
    for mass_error in np.linspace(-0.05, 0.05, uncertainty_points):
        for anisotropy in np.linspace(-0.06, 0.06, uncertainty_points):
            values = nominal.copy()
            values[..., 0, 0] += mass_error
            values[..., 1, 1] -= mass_error
            perturbation = anisotropy * (np.sin(horizontal) + 1j * np.sin(vertical))
            values[..., 0, 1] += perturbation
            values[..., 1, 0] += perturbation.conj()
            spectrum = np.linalg.eigvalsh(values)
            lower, upper = spectrum[..., 0], spectrum[..., 1]
            worst_width = max(worst_width, float(np.ptp(lower)))
            direct_gap = min(direct_gap, float(np.min(upper - lower)))
            indirect_gap = min(indirect_gap, float(np.min(upper) - np.max(lower)))
    tail = manufacturing_tail(witness)
    return {
        "sampled_bandwidth": worst_width,
        "sampled_direct_gap": direct_gap,
        "sampled_indirect_gap": indirect_gap,
        "coefficient_error_bound": tail,
        "bandwidth_plus_tail": worst_width + 2.0 * tail,
        "direct_gap_minus_tail": direct_gap - 2.0 * tail,
        "indirect_gap_minus_tail": indirect_gap - 2.0 * tail,
        "warning": "Mesh estimates only; no continuum or topology certificate.",
    }


def read_witness(path):
    return json.loads(Path(path).read_text())
