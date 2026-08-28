"""Independent real Fourier coordinates and spectral density transport."""

import math
import os
import sys

for thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[thread_variable] = "1"

import numpy as np


def geometry(spatial_shape):
    """Construct independent masks, stored partners, and momentum grids."""
    reduced_shape = spatial_shape[:-1] + (spatial_shape[-1] // 2 + 1,)
    coordinates = np.indices(reduced_shape, dtype=np.int64)
    conjugate_coordinates = tuple(
        (-coordinate) % length
        for coordinate, length in zip(coordinates, spatial_shape)
    )
    stored = conjugate_coordinates[-1] < reduced_shape[-1]
    partners = np.full(reduced_shape, -1, dtype=np.int64)
    partners[stored] = np.ravel_multi_index(
        tuple(coordinate[stored] for coordinate in conjugate_coordinates),
        reduced_shape,
    )
    indices = np.arange(math.prod(reduced_shape)).reshape(reduced_shape)
    real_mask = ~stored | (indices <= partners)
    imaginary_mask = real_mask & (indices != partners)
    signed_modes = np.stack(
        [
            np.where(2 * coordinate <= length, coordinate, coordinate - length)
            for coordinate, length in zip(coordinates, spatial_shape)
        ],
        axis=-1,
    )
    momenta = 2.0 * np.pi * signed_modes / np.asarray(spatial_shape)
    shell_squared = np.sum(signed_modes * signed_modes, axis=-1)
    return real_mask, imaginary_mask, partners, momenta, shell_squared


def solve(inputs):
    """Return all contract-v1 outputs without constructing spatial Jacobians."""
    spatial_shape = tuple(int(length) for length in inputs["spatial_shape"])
    channel_shape = tuple(int(length) for length in inputs["channel_shape"])
    batch_shape = tuple(int(length) for length in inputs["batch_shape"])
    dimensions = len(spatial_shape)
    volume = math.prod(spatial_shape)
    channels = math.prod(channel_shape)
    batches = math.prod(batch_shape)
    reduced_shape = spatial_shape[:-1] + (spatial_shape[-1] // 2 + 1,)
    reduced_volume = math.prod(reduced_shape)
    field_shape = batch_shape + spatial_shape + channel_shape
    canonical_shape = (batches,) + spatial_shape + (channels,)
    fourier_shape = (batches,) + reduced_shape + (channels,)
    spatial_axes = tuple(range(1, dimensions + 1))

    def forward_fft(field):
        return np.fft.rfftn(
            np.asarray(field, dtype=np.float64).reshape(canonical_shape),
            s=spatial_shape,
            axes=spatial_axes,
            norm="ortho",
        )

    def inverse_fft(coefficients):
        return np.fft.irfftn(
            coefficients, s=spatial_shape, axes=spatial_axes, norm="ortho"
        ).reshape(field_shape)

    real_mask, imaginary_mask, partners, momenta, shell_squared = geometry(
        spatial_shape
    )
    real_indices = np.flatnonzero(real_mask)
    imaginary_indices = np.flatnonzero(imaginary_mask)
    redundant_indices = np.flatnonzero(~real_mask)
    redundant_partners = partners.ravel()[redundant_indices]
    self_indices = np.flatnonzero(real_mask & ~imaginary_mask)

    field_fft = forward_fft(inputs["x"])
    flat_fft = field_fft.reshape(batches, reduced_volume, channels)
    packed = np.concatenate(
        (flat_fft[:, real_indices, :].real, flat_fft[:, imaginary_indices, :].imag),
        axis=1,
    ).reshape(batch_shape + (volume,) + channel_shape)

    coordinates = np.asarray(inputs["q"], dtype=np.float64).reshape(
        batches, volume, channels
    )
    decoded_fft = np.zeros((batches, reduced_volume, channels), dtype=np.complex128)
    decoded_fft[:, real_indices, :] = coordinates[:, : real_indices.size, :]
    decoded_fft[:, imaginary_indices, :] += (
        1j * coordinates[:, real_indices.size :, :]
    )
    decoded_fft[:, redundant_indices, :] = np.conj(
        decoded_fft[:, redundant_partners, :]
    )
    decoded_fft = decoded_fft.reshape(fourier_shape)

    base_input = np.asarray(inputs["base"], dtype=np.complex128)
    spectrum_channels = 1 if base_input.ndim == dimensions else channels
    spectrum_shape = reduced_shape + (spectrum_channels,)
    base = base_input.reshape(spectrum_shape)
    theta = np.asarray(inputs["theta"], dtype=np.float64)
    direction_theta = np.asarray(inputs["direction_theta"], dtype=np.float64)
    amplitude = np.asarray(inputs["amplitude"], dtype=np.float64).reshape(
        (theta.size,) + spectrum_shape
    )
    phase = np.asarray(inputs["phase"], dtype=np.float64).reshape(
        (theta.size,) + spectrum_shape
    )
    features = amplitude + 1j * phase
    log_change = np.einsum("p,p...->...", theta, features)
    spectrum = base * np.exp(log_change)
    transported_fft = spectrum * field_fft

    weights = real_mask.astype(np.float64) + imaginary_mask.astype(np.float64)
    channel_multiplier = channels if base_input.ndim == dimensions else 1
    log_determinant = channel_multiplier * np.sum(
        weights[..., None] * (np.log(np.abs(base)) + log_change.real)
    )
    determinant_gradient = channel_multiplier * np.sum(
        amplitude * weights[..., None], axis=tuple(range(1, amplitude.ndim))
    )
    log_density = np.asarray(inputs["log_density"], dtype=np.float64)

    directional_features = np.einsum("p,p...->...", direction_theta, features)
    jvp_fft = spectrum * forward_fft(inputs["direction_x"])
    jvp_fft += transported_fft * directional_features
    objective_scale = math.sqrt(batches * volume * channels)
    cotangent = np.asarray(inputs["cotangent"], dtype=np.float64)
    grad_x = inverse_fft(np.conj(spectrum) * forward_fft(cotangent))
    grad_x = grad_x / objective_scale
    grad_theta = np.empty_like(theta)
    for parameter_index, feature in enumerate(features):
        parameter_derivative = inverse_fft(transported_fft * feature)
        grad_theta[parameter_index] = (
            np.sum(cotangent * parameter_derivative) / objective_scale
            - determinant_gradient[parameter_index] / (volume * channels)
        )

    probes_input = np.asarray(inputs["probes"], dtype=np.complex128)
    probes = probes_input.reshape(
        probes_input.shape[0], reduced_volume, spectrum_channels
    )
    asymmetry = np.zeros(probes.shape[0], dtype=np.float64)
    if redundant_indices.size:
        pair_errors = np.abs(
            probes[:, redundant_indices, :]
            - np.conj(probes[:, redundant_partners, :])
        )
        asymmetry = np.maximum(asymmetry, np.max(pair_errors, axis=(1, 2)))
    if self_indices.size:
        self_errors = np.abs(probes[:, self_indices, :].imag)
        asymmetry = np.maximum(asymmetry, np.max(self_errors, axis=(1, 2)))

    return {
        "packed": packed,
        "unpacked_rfft": decoded_fft.reshape(batch_shape + reduced_shape + channel_shape),
        "unpacked": inverse_fft(decoded_fft),
        "mr": real_mask,
        "mi": imaginary_mask,
        "asymmetry": asymmetry,
        "y": inverse_fft(transported_fft),
        "reverse_y": inverse_fft(field_fft / spectrum),
        "log_density_y": log_density - log_determinant,
        "reverse_log_density": log_density + log_determinant,
        "jvp_y": inverse_fft(jvp_fft),
        "jvp_log_density": np.asarray(inputs["direction_log_density"], dtype=np.float64)
        - np.sum(direction_theta * determinant_gradient),
        "grad_x": grad_x,
        "grad_theta": grad_theta,
        "momenta": momenta,
        "lattice_momenta": 2.0 * np.sin(momenta / 2.0),
        "shell_squared": shell_squared,
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python solve.py INPUT.npz OUTPUT.npz")
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        outputs = solve(dict(archive))
    np.savez(sys.argv[2], **outputs)


if __name__ == "__main__":
    main()
