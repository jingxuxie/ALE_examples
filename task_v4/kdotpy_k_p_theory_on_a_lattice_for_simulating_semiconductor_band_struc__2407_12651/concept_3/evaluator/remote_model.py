import numpy as np
from reference import add_product, fourier_hoppings


FAMILIES = {
    "onsite_symmetric": {"energies": [5.5, 8.0], "dispersion": [0.0, 0.0], "onsite": [1.1, 0.5], "even": [0.0, 0.0], "odd": [0.0, 0.0]},
    "parity_mixed": {"energies": [5.5, 8.0], "dispersion": [0.0, 0.0], "onsite": [1.1, 0.5], "even": [0.25, 0.10], "odd": [0.45, 0.30]},
    "dispersive_remote": {"energies": [5.5, 8.0], "dispersion": [0.20, 0.15], "onsite": [1.1, 0.5], "even": [0.25, 0.10], "odd": [0.45, 0.30]},
}


def remote_terms(family):
    configuration = FAMILIES[family]
    remote = {(0, 0): np.diag(configuration["energies"]).astype(complex)}
    for orbital, dispersion in enumerate(configuration["dispersion"]):
        matrix = np.zeros((2, 2), complex)
        matrix[orbital, orbital] = 1.0
        add_product(remote, dispersion, matrix, 1, 0)
        add_product(remote, dispersion, matrix, 0, 1)
    hybrid = {(0, 0): np.diag(configuration["onsite"]).astype(complex)}
    for orbital, amplitude in enumerate(configuration["even"]):
        matrix = np.zeros((2, 2), complex)
        matrix[orbital, orbital] = 1.0
        add_product(hybrid, amplitude, matrix, 1, 0)
        add_product(hybrid, amplitude, matrix, 0, 1)
    for row, column, amplitude, handedness in ((0, 1, configuration["odd"][0], -1.0), (1, 0, configuration["odd"][1], 1.0)):
        matrix = np.zeros((2, 2), complex)
        matrix[row, column] = 1.0
        add_product(hybrid, amplitude, matrix, 1, 0, sine_x=True)
        add_product(hybrid, 1j * handedness * amplitude, matrix, 0, 1, sine_y=True)
    return remote, hybrid


def assemble(witness, family, strength):
    active = fourier_hoppings(witness)
    remote, hybrid = remote_terms(family)
    support = set(active) | set(remote) | set(hybrid) | {(-horizontal, -vertical) for horizontal, vertical in hybrid}
    hoppings = {}
    for displacement in support:
        matrix = np.zeros((4, 4), complex)
        matrix[:2, :2] = active.get(displacement, np.zeros((2, 2)))
        matrix[2:, 2:] = remote.get(displacement, np.zeros((2, 2)))
        matrix[:2, 2:] = strength * hybrid.get(displacement, np.zeros((2, 2)))
        reverse = (-displacement[0], -displacement[1])
        matrix[2:, :2] = strength * hybrid.get(reverse, np.zeros((2, 2))).conj().T
        if np.any(matrix):
            hoppings[displacement] = matrix
    return hoppings


def evaluate_fourier(hoppings, horizontal, vertical, derivative=None):
    horizontal, vertical = np.broadcast_arrays(horizontal, vertical)
    dimension = next(iter(hoppings.values())).shape[0]
    matrices = np.zeros(horizontal.shape + (dimension, dimension), complex)
    for displacement, matrix in hoppings.items():
        phase = np.exp(1j * (displacement[0] * horizontal + displacement[1] * vertical))
        if derivative is not None:
            phase *= 1j * displacement[derivative]
        matrices += phase[..., None, None] * matrix
    return matrices


def coordinate_grid(mesh, shift=(0.0, 0.0)):
    axis = 2.0 * np.pi * np.arange(mesh) / mesh - np.pi
    return np.meshgrid(axis + shift[0] * 2.0 * np.pi / mesh, axis + shift[1] * 2.0 * np.pi / mesh, indexing="ij")


def manufacture(nominal, horizontal, vertical, mass_error, anisotropy):
    matrices = nominal.copy()
    matrices[..., 0, 0] += mass_error
    matrices[..., 1, 1] -= mass_error
    offdiagonal = anisotropy * (np.sin(horizontal) + 1j * np.sin(vertical))
    matrices[..., 0, 1] += offdiagonal
    matrices[..., 1, 0] += offdiagonal.conj()
    return matrices


def band_metrics(spectrum):
    target = spectrum[..., 0]
    return {
        "bandwidth": float(np.ptp(target)),
        "gap_12": float(np.min(spectrum[..., 2] - spectrum[..., 1])),
        "direct_above": float(np.min(spectrum[..., 1] - target)),
        "indirect_above": float(np.min(spectrum[..., 1]) - np.max(target)),
        "all_band_direct_gap": float(np.min(np.diff(spectrum, axis=-1))),
    }
