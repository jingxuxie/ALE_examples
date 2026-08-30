import numpy as np
from scipy.linalg import eigh
from scipy.sparse import coo_matrix


def independent_hamiltonian(config, pattern, condition):
    width, height = config["width"], config["height"]
    sites = width * height
    locations = np.array([(column, row) for row in range(height) for column in range(width)])
    normal = np.zeros(sites)
    for selected, coordinate in zip(pattern, config["candidates"]):
        normal[int(coordinate[1]) * width + int(coordinate[0])] = selected
    difference = locations[None, :, :] - locations[:, None, :]
    delta_column, delta_row = difference[:, :, 0], difference[:, :, 1]
    horizontal = (np.abs(delta_column) == 1) & (delta_row == 0)
    vertical = (delta_column == 0) & (np.abs(delta_row) == 1)
    diagonal = (np.abs(delta_column) == 1) & (np.abs(delta_row) == 1)
    amplitudes = config["hopping"] * (horizontal | vertical) + config["diagonal_hopping"] * diagonal
    center = np.array([(width - 1) / 2, (height - 1) / 2])
    centered = locations - center
    oriented_area = centered[:, 0, None] * centered[None, :, 1] - centered[:, 1, None] * centered[None, :, 0]
    phases = np.pi * condition["flux"] / ((width - 1) * (height - 1)) * oriented_area
    electron = -amplitudes * np.exp(1j * phases)
    electron[np.diag_indices(sites)] = -condition["mu"] + config["pin_potential"] * normal
    gap = config["gap_d"] * (horizontal.astype(float) - vertical.astype(float))
    gap = gap + 1j * config["gap_xy"] * diagonal * np.sign(delta_column * delta_row)
    gap *= condition["pair_scale"] * np.outer(1 - normal, 1 - normal)
    output = np.zeros((2 * sites, 2 * sites), dtype=complex)
    output[:sites, :sites] = electron
    output[sites:, sites:] = -electron.T
    output[:sites, sites:] = gap
    output[sites:, :sites] = gap.conj().T
    return output


def independent_response(config, pattern):
    positions = np.array([row * config["width"] + column for column, row in config["probes"]])
    broadening = config["broadening"]
    output = []
    for condition in config["conditions"]:
        energies, vectors = eigh(independent_hamiltonian(config, pattern, condition), driver="evd")
        values = []
        for energy in config["energies"]:
            denominator = (energy - energies) ** 2 + broadening ** 2
            values.append(np.sum(np.abs(vectors[positions]) ** 2 / denominator[None, :], axis=1) * broadening / np.pi)
        output.append(np.array(values).T)
    return np.array(output)
