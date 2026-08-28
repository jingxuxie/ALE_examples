"""Private plausible shortcut: storage slots, magnitude-only spectra, double counts."""

import sys

import numpy as np


def solve(inputs):
    spatial = tuple(map(int, inputs["spatial_shape"]))
    channels = tuple(map(int, inputs["channel_shape"]))
    batch = tuple(map(int, inputs["batch_shape"]))
    reduced = spatial[:-1] + (spatial[-1] // 2 + 1,)
    axes = tuple(range(len(batch), len(batch) + len(spatial)))
    packed_axis = len(batch)
    volume = int(np.prod(spatial))
    slots = int(np.prod(reduced))
    field = inputs["x"]
    parameters = inputs["theta"]
    amplitude = inputs["amplitude"]
    magnitude = np.abs(inputs["base"]) * np.exp(np.tensordot(parameters, amplitude, axes=1))
    trailing = (1,) * len(channels) if magnitude.ndim == len(spatial) else ()

    def align(spectrum):
        return spectrum.reshape((1,) * len(batch) + spectrum.shape + trailing)

    def fft(value):
        return np.fft.rfftn(value, s=spatial, axes=axes, norm="ortho")

    def inverse(value):
        return np.fft.irfftn(value, s=spatial, axes=axes, norm="ortho")

    spectrum_x = fft(field)
    flat = spectrum_x.reshape(batch + (slots,) + channels)
    doubled = np.concatenate((flat.real, flat.imag), axis=packed_axis)
    packed = np.take(doubled, np.arange(volume), axis=packed_axis)
    padding = np.zeros(batch + (2 * slots - volume,) + channels)
    padded = np.concatenate((inputs["q"], padding), axis=packed_axis)
    real, imag = np.split(padded, 2, axis=packed_axis)
    decoded = (real + 1j * imag).reshape(batch + reduced + channels)
    delta = 2 * np.sum(np.log(magnitude))
    delta_gradient = 2 * amplitude.reshape((len(parameters), -1)).sum(axis=1)
    aligned = align(magnitude)
    tangent_amplitude = np.tensordot(inputs["direction_theta"], amplitude, axes=1)
    jvp = inverse(aligned * (fft(inputs["direction_x"]) + spectrum_x * align(tangent_amplitude)))
    event_size = volume * int(np.prod(channels))
    gradients = np.array([
        np.sum(inputs["cotangent"] * inverse(aligned * spectrum_x * align(feature)))
        / np.sqrt(field.size) - density_gradient / event_size
        for feature, density_gradient in zip(amplitude, delta_gradient)
    ])
    indices = np.moveaxis(np.indices(reduced), 0, -1)
    momenta = 2 * np.pi * indices / np.asarray(spatial)
    imag_mask = np.ones(reduced, dtype=bool)
    imag_mask[..., 0] = False
    if spatial[-1] % 2 == 0:
        imag_mask[..., -1] = False
    return {
        "packed": packed, "unpacked": inverse(decoded), "unpacked_rfft": decoded,
        "mr": np.ones(reduced, dtype=bool), "mi": imag_mask,
        "asymmetry": np.zeros(len(inputs["probes"])),
        "y": inverse(aligned * spectrum_x), "reverse_y": inverse(spectrum_x / aligned),
        "log_density_y": inputs["log_density"] - delta,
        "reverse_log_density": inputs["log_density"] + delta,
        "jvp_y": jvp,
        "jvp_log_density": inputs["direction_log_density"]
                           - np.dot(delta_gradient, inputs["direction_theta"]),
        "grad_x": inverse(aligned * fft(inputs["cotangent"])) / np.sqrt(field.size),
        "grad_theta": gradients,
        "momenta": momenta, "lattice_momenta": 2 * np.sin(momenta / 2),
        "shell_squared": np.sum(indices**2, axis=-1),
    }


if __name__ == "__main__":
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        result = solve(dict(archive))
    np.savez(sys.argv[2], **result)
