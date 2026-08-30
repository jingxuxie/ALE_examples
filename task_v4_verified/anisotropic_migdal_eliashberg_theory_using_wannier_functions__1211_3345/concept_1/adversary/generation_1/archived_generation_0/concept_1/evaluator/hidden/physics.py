"""Trusted independent, blocked direct-sum verification, never participant imports."""

import numpy as np


INPUT_KEYS = ("temperature", "n_freq", "weights", "omega", "coupling", "coulomb", "initial_delta")


def fields(instance, delta, block_size=64):
    temperature = float(instance["temperature"])
    frequencies = np.pi * temperature * (2 * np.arange(int(instance["n_freq"])) + 1)
    radius = np.hypot(frequencies[None, :], delta)
    normal_ratio = frequencies[None, :] / radius
    pair_ratio = delta / radius
    weighted = instance["coupling"] * instance["weights"][None, None, :]
    coulomb = instance["coulomb"] * instance["weights"][None, :]
    normal = np.zeros_like(delta)
    pairing = np.zeros_like(delta)
    for start in range(0, len(frequencies), block_size):
        stop = min(start + block_size, len(frequencies))
        difference = frequencies[start:stop, None] - frequencies[None, :]
        summation = frequencies[start:stop, None] + frequencies[None, :]
        for mode_index, energy in enumerate(instance["omega"]):
            lower = energy ** 2 / (energy ** 2 + difference ** 2)
            upper = energy ** 2 / (energy ** 2 + summation ** 2)
            normal[:, start:stop] += weighted[mode_index] @ (normal_ratio @ (lower - upper).T)
            pairing[:, start:stop] += weighted[mode_index] @ (pair_ratio @ (lower + upper).T)
    pairing -= 2 * (coulomb @ pair_ratio.sum(axis=1))[:, None]
    renormalization = 1 + np.pi * temperature * normal / frequencies[None, :]
    return renormalization, np.pi * temperature * pairing


def metrics(instance, delta, renormalization, reference):
    expected_z, pairing = fields(instance, delta)
    floor = np.pi * float(instance["temperature"]) * 1e-10
    scales = np.maximum(np.max(np.abs(delta), axis=1), floor)
    gap_residual = float(np.max(np.abs(delta - pairing / expected_z) / scales[:, None]))
    z_residual = float(np.max(np.abs(renormalization - expected_z) / np.maximum(expected_z, 1)))
    orientation = 1 if np.dot(instance["weights"], delta[:, 0]) >= 0 else -1
    aligned = orientation * delta
    reference_scales = np.maximum(np.max(np.abs(reference), axis=1), floor)
    branch_error = float(np.max(np.abs(aligned - reference) / reference_scales[:, None]))
    sign_correct = bool(np.all(aligned[:, 0] > 0))
    return {"gap_residual": gap_residual, "z_residual": z_residual,
            "branch_error": branch_error, "sign_correct": sign_correct}
