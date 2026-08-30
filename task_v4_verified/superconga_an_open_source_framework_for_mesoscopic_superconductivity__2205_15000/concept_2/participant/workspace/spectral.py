import json
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.ndimage import label


def load_problem(directory):
    directory = Path(directory)
    config = json.loads((directory / "device.json").read_text())
    with np.load(directory / "target.npz", allow_pickle=False) as arrays:
        target = arrays["ldos"].copy()
    return config, target


def validate_design(config, design):
    pattern = np.asarray(design, dtype=float)
    count = len(config["candidates"])
    if pattern.shape != (count,) or not np.isfinite(pattern).all():
        raise ValueError("pattern must be a finite vector with one entry per candidate")
    if not np.logical_or(pattern == 0, pattern == 1).all():
        raise ValueError("fabrication pattern must be binary")
    if int(pattern.sum()) != config["normal_site_count"]:
        raise ValueError("wrong normal-material budget")
    superconducting = np.ones((config["height"], config["width"]), dtype=int)
    for occupied, (column, row) in zip(pattern, config["candidates"]):
        if occupied:
            superconducting[row, column] = 0
    if label(superconducting)[1] != 1:
        raise ValueError("superconducting material must remain four-neighbor connected")
    return pattern


def hamiltonian(config, pattern, condition):
    width = config["width"]
    height = config["height"]
    sites = width * height
    normal = np.zeros(sites)
    for occupied, (column, row) in zip(pattern, config["candidates"]):
        normal[row * width + column] = occupied
    amplitude = 1.0 - normal
    hopping = np.diag(-condition["mu"] + config["pin_potential"] * normal).astype(complex)
    pairing = np.zeros((sites, sites), dtype=complex)
    pair_scale = condition["pair_scale"]
    field = condition["flux"] * 2.0 * np.pi / ((width - 1) * (height - 1))
    for row in range(height):
        for column in range(width):
            source = row * width + column
            for delta_column, delta_row, hop, gap in (
                (1, 0, config["hopping"], config["gap_d"]),
                (0, 1, config["hopping"], -config["gap_d"]),
                (1, 1, config["diagonal_hopping"], 1j * config["gap_xy"]),
                (-1, 1, config["diagonal_hopping"], -1j * config["gap_xy"]),
            ):
                other_column = column + delta_column
                other_row = row + delta_row
                if not (0 <= other_column < width and 0 <= other_row < height):
                    continue
                destination = other_row * width + other_column
                midpoint_column = (column + other_column - width + 1) / 2.0
                midpoint_row = (row + other_row - height + 1) / 2.0
                peierls = 0.5 * field * (midpoint_column * delta_row - midpoint_row * delta_column)
                hopping[source, destination] = -hop * np.exp(1j * peierls)
                hopping[destination, source] = hopping[source, destination].conjugate()
                pair_value = gap * pair_scale * amplitude[source] * amplitude[destination]
                pairing[source, destination] = pair_value
                pairing[destination, source] = pair_value
    return np.block([[hopping, pairing], [pairing.conj().T, -hopping.conj()]])


def response(config, pattern):
    sites = config["width"] * config["height"]
    probes = [row * config["width"] + column for column, row in config["probes"]]
    energies = np.asarray(config["energies"])
    broadening = config["broadening"]
    output = []
    for condition in config["conditions"]:
        eigenvalues, eigenvectors = eigh(hamiltonian(config, pattern, condition),
                                       check_finite=False, driver="evr")
        spectral_weights = np.abs(eigenvectors[:sites][probes]) ** 2
        lorentzian = broadening / np.pi / ((energies[:, None] - eigenvalues[None, :]) ** 2 + broadening ** 2)
        output.append(spectral_weights @ lorentzian.T)
    return np.asarray(output)


def discrepancies(config, observed, target):
    scales = np.sqrt(np.mean(target ** 2, axis=2, keepdims=True))
    scaled = (np.asarray(observed) - target) / np.maximum(scales, 0.02)
    family_errors = np.sqrt(np.mean(scaled ** 2, axis=(1, 2)))
    core_error = float(np.sqrt(np.mean(scaled ** 2)))
    family_scores = np.maximum(0.0, 1.0 - family_errors / config["score_scale"])
    return {"relative_rmse": core_error, "family_errors": family_errors.tolist(),
            "core_score": max(0.0, 1.0 - core_error / config["score_scale"]),
            "worst_family_score": float(family_scores.min())}
