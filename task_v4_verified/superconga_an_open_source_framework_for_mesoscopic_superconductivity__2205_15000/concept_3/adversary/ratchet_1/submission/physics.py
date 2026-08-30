import itertools

import numpy as np


SPEC = {
    'energies': [round(-2.4 + 0.12 * index, 8) for index in range(41)],
    'impurity_sites': [8 * row + column for row in range(1, 7) for column in range(1, 7)],
    'vortex_centers': [[column, row] for row in (1.5, 3.5, 5.5) for column in (1.5, 3.5, 5.5)],
}


def sectors():
    return [list(group) for count in (0, 1, 2) for group in itertools.combinations(range(9), count)]


def hamiltonian(potential, vortices):
    normal = np.diag(np.asarray(potential, dtype=float) + 0.7)
    for site in range(64):
        row, column = divmod(site, 8)
        for neighbor in ([site + 1] if column < 7 else []) + ([site + 8] if row < 7 else []):
            normal[site, neighbor] = normal[neighbor, site] = -1.0
    rows, columns = np.indices((8, 8))
    amplitude = np.full((8, 8), 0.55)
    angle = np.zeros((8, 8))
    for vortex in vortices:
        center_column, center_row = SPEC['vortex_centers'][vortex]
        displacement_column = columns - center_column
        displacement_row = rows - center_row
        amplitude *= np.tanh(np.hypot(displacement_column, displacement_row) / 1.15)
        angle += np.arctan2(displacement_row, displacement_column)
    pair = np.diag((amplitude * np.exp(1j * angle)).ravel())
    return np.block([[normal, pair], [pair.conj().T, -normal]])


def uniform_actions(count=56, seed=1701):
    generator = np.random.default_rng(seed)
    indices = generator.choice(64 * 41, count, replace=False)
    return [{'type': 'query', 'site': int(index // 41), 'energy_index': int(index % 41)} for index in indices]
