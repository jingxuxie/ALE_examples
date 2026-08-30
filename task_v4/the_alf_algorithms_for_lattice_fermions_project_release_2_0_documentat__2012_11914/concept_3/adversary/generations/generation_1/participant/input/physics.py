"""Numerical definitions of the public forward model and spectral observables."""

import numpy as np


FAMILY_NAMES = (
    "coherent_quasiparticle",
    "hubbard_metal",
    "mott_insulator",
    "pseudogap",
    "asymmetric_continuum",
    "multiband_continuum",
)
BAND_EDGES = np.array([-8.0, -2.0, -0.5, 0.5, 2.0, 8.0])
QUANTILE_LEVELS = np.array([0.1, 0.5, 0.9])


def kernel(beta, tau, omega_edges):
    nodes, weights = np.polynomial.legendre.leggauss(6)
    centers = (omega_edges[:-1] + omega_edges[1:]) / 2.0
    half_widths = np.diff(omega_edges) / 2.0
    omega = centers[:, None] + half_widths[:, None] * nodes
    exponent = -np.asarray(tau)[:, None, None] * omega[None, :, :]
    exponent -= np.logaddexp(0.0, -float(beta) * omega)[None, :, :]
    return np.exp(exponent) @ (weights / 2.0)


def window_weights(omega_edges, lower, upper):
    overlap = np.maximum(
        0.0,
        np.minimum(omega_edges[1:], upper) - np.maximum(omega_edges[:-1], lower),
    )
    return overlap / np.diff(omega_edges)


def observables(spectral_mass, omega_edges):
    spectral_mass = np.atleast_2d(spectral_mass)
    low_mass = spectral_mass @ window_weights(omega_edges, -0.5, 0.5)
    band_weights = np.stack(
        [
            spectral_mass @ window_weights(omega_edges, lower, upper)
            for lower, upper in zip(BAND_EDGES[:-1], BAND_EDGES[1:])
        ],
        axis=1,
    )
    radius_edges = np.unique(np.abs(omega_edges))
    shell_weights = np.stack(
        [window_weights(omega_edges, -radius, radius) for radius in radius_edges],
        axis=1,
    )
    radial_cdf = spectral_mass @ shell_weights
    upper_index = np.argmax(radial_cdf >= 0.1, axis=1)
    upper_index = np.maximum(upper_index, 1)
    row_index = np.arange(len(spectral_mass))
    lower_cdf = radial_cdf[row_index, upper_index - 1]
    upper_cdf = radial_cdf[row_index, upper_index]
    fraction = (0.1 - lower_cdf) / np.maximum(upper_cdf - lower_cdf, 1e-30)
    gap10 = radius_edges[upper_index - 1] + fraction * (
        radius_edges[upper_index] - radius_edges[upper_index - 1]
    )
    return {"low_mass": low_mass, "band_weights": band_weights, "gap10": gap10}


def wasserstein(spectral_mass, truth, omega_edges):
    difference = spectral_mass - truth
    cdf_right = np.cumsum(difference, axis=1)
    cdf_left = cdf_right - difference
    magnitude_left = np.abs(cdf_left)
    magnitude_right = np.abs(cdf_right)
    same_sign = cdf_left * cdf_right >= 0.0
    crossing_integral = (magnitude_left**2 + magnitude_right**2) / np.maximum(
        2.0 * (magnitude_left + magnitude_right), 1e-300
    )
    integral = np.where(
        same_sign, (magnitude_left + magnitude_right) / 2.0, crossing_integral
    )
    return integral @ np.diff(omega_edges)
