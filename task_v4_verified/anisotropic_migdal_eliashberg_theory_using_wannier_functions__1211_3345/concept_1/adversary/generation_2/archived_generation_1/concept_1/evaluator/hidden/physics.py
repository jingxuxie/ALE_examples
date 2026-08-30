"""Independent full-signed linear-convolution verifier, with direct-sum audit rows."""

import numpy as np
from scipy.signal import fftconvolve


INPUT_KEYS = ("temperature", "n_freq", "weights", "omega", "coupling", "coulomb", "initial_delta")


def fields(instance, delta):
    temperature = float(instance["temperature"])
    count = int(instance["n_freq"])
    frequencies = np.pi * temperature * (2 * np.arange(count) + 1)
    radius = np.hypot(frequencies, delta)
    normal_ratio = frequencies / radius
    gap_ratio = delta / radius
    signed_normal = np.concatenate((-normal_ratio[:, ::-1], normal_ratio), axis=1)
    signed_gap = np.concatenate((gap_ratio[:, ::-1], gap_ratio), axis=1)
    distances = 2 * np.pi * temperature * np.arange(-2 * count + 1, 2 * count)
    normal = np.zeros_like(delta)
    pairing = np.zeros_like(delta)
    for mode_index, energy in enumerate(instance["omega"]):
        kernel = energy ** 2 / (energy ** 2 + distances ** 2)
        matrix = instance["coupling"][mode_index] * instance["weights"]
        filtered_normal = fftconvolve(signed_normal, kernel[None, :], axes=1)[:, 3 * count - 1:4 * count - 1]
        filtered_gap = fftconvolve(signed_gap, kernel[None, :], axes=1)[:, 3 * count - 1:4 * count - 1]
        normal += matrix @ filtered_normal
        pairing += matrix @ filtered_gap
    pairing -= 2 * ((instance["coulomb"] * instance["weights"]) @ gap_ratio.sum(axis=1))[:, None]
    renormalization = 1 + np.pi * temperature * normal / frequencies
    return renormalization, np.pi * temperature * pairing


def metrics(instance, delta, renormalization, reference):
    expected_z, pairing = fields(instance, delta)
    floor = np.pi * float(instance["temperature"]) * 1e-10
    scales = np.maximum(np.max(np.abs(delta), axis=1), floor)
    orientation = 1 if np.dot(instance["weights"], delta[:, 0]) >= 0 else -1
    aligned = orientation * delta
    reference_scales = np.maximum(np.max(np.abs(reference), axis=1), floor)
    return {"gap_residual": float(np.max(np.abs(delta - pairing / expected_z) / scales[:, None])),
            "z_residual": float(np.max(np.abs(renormalization - expected_z) / np.maximum(1, expected_z))),
            "branch_error": float(np.max(np.abs(aligned - reference) / reference_scales[:, None])),
            "sign_correct": bool(np.all(aligned[:, 0] > 0))}


def direct_rows(instance, delta, renormalization, count_rows=32):
    count = int(instance["n_freq"])
    selected = np.unique(np.concatenate((np.arange(min(8, count)),
                                         np.geomspace(1, count, count_rows).astype(int) - 1,
                                         np.arange(max(0, count - 8), count))))
    temperature = float(instance["temperature"])
    positive = np.pi * temperature * (2 * np.arange(count) + 1)
    signed = np.concatenate((-positive[::-1], positive))
    full_delta = np.concatenate((delta[:, ::-1], delta), axis=1)
    radius = np.hypot(signed, full_delta)
    difference = positive[selected, None] - signed[None, :]
    normal = np.zeros((delta.shape[0], len(selected)))
    pairing = np.zeros_like(normal)
    for mode_index, energy in enumerate(instance["omega"]):
        kernel = energy ** 2 / (energy ** 2 + difference ** 2)
        matrix = instance["coupling"][mode_index] * instance["weights"]
        normal += matrix @ ((signed / radius) @ kernel.T)
        pairing += matrix @ ((full_delta / radius) @ kernel.T)
    pairing -= ((instance["coulomb"] * instance["weights"]) @ (full_delta / radius).sum(axis=1))[:, None]
    expected_z = 1 + np.pi * temperature * normal / positive[selected]
    scale = np.maximum(np.max(np.abs(delta), axis=1), np.pi * temperature * 1e-10)
    return {"rows": selected.tolist(),
            "gap_residual": float(np.max(np.abs(delta[:, selected] - np.pi * temperature * pairing / expected_z) / scale[:, None])),
            "z_residual": float(np.max(np.abs(renormalization[:, selected] - expected_z) / np.maximum(1, expected_z)))}
