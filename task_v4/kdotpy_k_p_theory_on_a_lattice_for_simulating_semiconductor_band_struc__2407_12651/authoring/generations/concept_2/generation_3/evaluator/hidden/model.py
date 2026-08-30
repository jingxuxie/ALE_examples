import numpy as np


LOWER = np.array([-1.65, .65, .65, .55, .55] + [-.5] * 4 + [-.15] * 4 + [.08] * 8 + [-np.pi] * 4)
UPPER = np.array([-.35, 1.35, 1.35, 1.25, 1.25] + [.5] * 4 + [.15] * 4 + [.70] * 8 + [np.pi] * 4)


def coefficients(parameters):
    values = np.asarray(parameters, dtype=float)
    onsite = np.zeros((6, 6), complex)
    cos_x = np.zeros_like(onsite)
    sin_x = np.zeros_like(onsite)
    cos_y = np.zeros_like(onsite)
    sin_y = np.zeros_like(onsite)
    mass, velocity_x, velocity_y, curvature_x, curvature_y = values[:5]
    onsite[0, 0], onsite[5, 5] = mass, -mass
    cos_x[0, 0], cos_x[5, 5] = curvature_x, -curvature_x
    cos_y[0, 0], cos_y[5, 5] = curvature_y, -curvature_y
    sin_x[0, 5] = velocity_x
    sin_y[0, 5] = -1j * velocity_y
    for orbital in range(1, 5):
        index = orbital - 1
        onsite[orbital, orbital] = values[5 + index]
        cos_x[orbital, orbital] = values[9 + index]
        cos_y[orbital, orbital] = (-1) ** index * values[9 + index]
        coupling_upper = values[13 + index]
        coupling_lower = values[17 + index]
        phase = np.exp(1j * values[21 + index])
        onsite[0, orbital] = coupling_upper
        cos_x[0, orbital] = .35 * coupling_upper
        sin_y[0, orbital] = .4j * coupling_lower
        onsite[orbital, 5] = phase * coupling_lower
        cos_y[orbital, 5] = -.35 * phase * coupling_lower
        sin_x[orbital, 5] = .4j * phase * coupling_upper
    for orbital in range(1, 4):
        onsite[orbital, orbital + 1] = .08 * np.exp(.7j * orbital)
    for matrix in (onsite, cos_x, sin_x, cos_y, sin_y):
        matrix += np.triu(matrix, 1).conj().T
    return onsite, cos_x, sin_x, cos_y, sin_y


def sample(parameters, size=33, shift=(.137, .271)):
    onsite, cos_x, sin_x, cos_y, sin_y = coefficients(parameters)
    axis = np.arange(size)
    momenta_x, momenta_y = np.meshgrid(2 * np.pi * (axis + shift[0]) / size,
                                      2 * np.pi * (axis + shift[1]) / size, indexing='ij')
    momenta_x = momenta_x[..., None, None]
    momenta_y = momenta_y[..., None, None]
    hamiltonian = (onsite + np.cos(momenta_x) * cos_x + np.sin(momenta_x) * sin_x
                   + np.cos(momenta_y) * cos_y + np.sin(momenta_y) * sin_y)
    derivative_x = -np.sin(momenta_x) * cos_x + np.cos(momenta_x) * sin_x
    derivative_y = -np.sin(momenta_y) * cos_y + np.cos(momenta_y) * sin_y
    return hamiltonian, derivative_x, derivative_y


def diagnose(parameters, size=33, shift=(.137, .271)):
    hamiltonian, derivative_x, derivative_y = sample(parameters, size, shift)
    energies, frames = np.linalg.eigh(hamiltonian)
    target = frames[..., :, 0]
    matrix_x = np.einsum('...a,...ab,...bm->...m', target.conj(), derivative_x, frames)
    matrix_y = np.einsum('...a,...ab,...bm->...m', target.conj(), derivative_y, frames)
    separations = energies[..., 1:] - energies[..., :1]
    contributions = -2 * np.imag(matrix_x[..., 1:] * matrix_y[..., 1:].conj()) / separations ** 2
    integrals = contributions.mean(axis=(0, 1)) * (2 * np.pi)
    optical = ((np.abs(matrix_x[..., 1:]) ** 2 + np.abs(matrix_y[..., 1:]) ** 2)
               / separations ** 2).mean(axis=(0, 1))
    links_x = np.einsum('...a,...a->...', target.conj(), np.roll(target, -1, axis=0))
    links_y = np.einsum('...a,...a->...', target.conj(), np.roll(target, -1, axis=1))
    flux = -np.angle(links_x * np.roll(links_y, -1, axis=0)
                     * np.roll(links_x.conj(), -1, axis=1) * links_y.conj())
    blocks = coefficients(parameters)
    lipschitz = sum(np.linalg.norm(block, 2) for block in blocks[1:])
    correction = 2 * np.pi * lipschitz / size
    windows = np.cumsum(integrals)[[1, 2, 3]]
    return {
        'size': int(size), 'windows': windows.tolist(), 'full': float(integrals.sum()),
        'contributions': integrals.tolist(), 'optical': optical.tolist(),
        'chern': float(flux.sum() / (2 * np.pi)),
        'sampled_gap': float(separations[..., 0].min()),
        'gap_lower_bound': float(separations[..., 0].min() - correction),
        'max_flux': float(np.abs(flux).max()),
        'min_overlap': float(min(np.abs(links_x).min(), np.abs(links_y).min())),
        'norm_upper_bound': float(np.abs(energies).max() + correction / 2),
        'plateau_spread': float(np.ptp(windows)),
        'plateau_mean': float(windows.mean()),
        'omitted_response': float(abs(integrals.sum() - windows.mean())),
        'retained_optical_min': float(optical[:4].min())
    }
