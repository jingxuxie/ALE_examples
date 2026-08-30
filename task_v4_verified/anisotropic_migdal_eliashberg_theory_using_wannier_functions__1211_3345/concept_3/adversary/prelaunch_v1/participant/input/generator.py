"""Disclosed finite-quadrature, causal Nambu spectral family (version 1)."""

import argparse
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss


FAMILIES = ("split_coherence", "overlapping_anisotropy", "satellite_rich", "three_sheet")
PARAMETER_COUNT = 32
EDGES = np.array([0, .75, 1.25, 1.75, 2.25, 2.75, 3.5, 4.5, 6, 8, 10, 13, 17, 23, np.inf])
RESOLUTION = .4
MASS_SCALES = np.array([.008] * 7 + [.010, .012, .012, .012, .010, .008, .006])
INDICES = np.unique(np.concatenate((np.arange(24), np.rint(np.geomspace(25, 511, 40)).astype(int))))
OMEGA = (2 * INDICES + 1) * np.pi * .04
PROBE = np.array([[1., 1., 1.], [.45, 1., 1.65]])
CORRELATION = .4
QUAD_NODES, QUAD_WEIGHTS = leggauss(32)
XI_FRACTION = (QUAD_NODES + 1) / 2
XI_WEIGHTS = QUAD_WEIGHTS / 2
THETA = 2 * np.pi * (np.arange(16) + .5) / 16


def parameter_names(family):
    bands = 3 if family == 3 else 2
    names = ["mixture_0", "mixture_1", "omega_1", "omega_2", "dispersion_1", "dispersion_2"]
    for band in range(bands):
        names.extend(f"band_{band}_{name}" for name in
                     ("gap", "anisotropy_2", "anisotropy_4", "lifetime", "lifetime_anisotropy", "bandwidth", "replica_1", "replica_2"))
    return names


def active_parameters(family):
    indices = list(range(6 + 8 * (3 if family == 3 else 2)))
    if family != 3:
        indices.remove(1)
    return np.asarray(indices)


def components(parameters, family):
    parameters = np.asarray(parameters)
    bands = 3 if family == 3 else 2
    if bands == 2:
        first = .25 + .5 * parameters[0]
        mixture = np.array([first, 1 - first])
    else:
        first = .18 + .3 * parameters[0]
        second = (1 - first) * (.3 + .4 * parameters[1])
        mixture = np.array([first, second, 1 - first - second])
    probe_weights = PROBE[:, :bands] * mixture[None, :]
    probe_weights = probe_weights / probe_weights.sum(axis=1, keepdims=True)
    shifts = np.array([0, 3.2 + 2.3 * parameters[2], 6.7 + 3.3 * parameters[3]])
    dispersions = np.array([0, .1 + .5 * parameters[4], .15 + .75 * parameters[5]])
    ranges = (
        ((.65, 1.25), (1.8, 3.1)),
        ((1., 1.8), (1.55, 2.6)),
        ((.8, 1.5), (1.8, 2.9)),
        ((.6, 1.2), (1.35, 2.1), (2.35, 3.2)),
    )[family]
    all_energy, all_width, all_coherence, all_weight = [], [], [], []
    for band in range(bands):
        latent = parameters[6 + 8 * band:14 + 8 * band]
        gap_center = ranges[band][0] + np.diff(ranges[band])[0] * latent[0]
        anisotropy = (.04 + .30 * latent[1]) if family == 1 else (.015 + .18 * latent[1])
        fourth = -.09 + .18 * latent[2]
        gap = gap_center * (1 + anisotropy * np.cos(2 * THETA) + fourth * np.cos(4 * THETA))
        lifetime = .025 + (.13 if family == 1 else .075) * latent[3]
        angular_width = lifetime * (1 + .55 * latent[4] * np.cos(2 * THETA + .7))
        bandwidth = 4.5 + 2.5 * latent[5]
        xi = bandwidth * XI_FRACTION
        energy = np.sqrt(gap[:, None] ** 2 + xi[None, :] ** 2)
        coherence = gap[:, None] / energy
        if family == 2:
            first_replica, second_replica = .15 + .18 * latent[6], .07 + .11 * latent[7]
        else:
            first_replica, second_replica = .025 + .13 * latent[6], .01 + .09 * latent[7]
        replicas = np.array([1 - first_replica - second_replica, first_replica, second_replica])
        for replica in range(3):
            shifted = energy + shifts[replica] + dispersions[replica] * np.cos(2 * THETA[:, None] + .3 * band)
            width = angular_width[:, None] + .025 * XI_FRACTION[None, :] ** 2 + .13 * replica
            measure = np.broadcast_to(XI_WEIGHTS[None, :] / len(THETA), energy.shape)
            weights = probe_weights[:, band, None] * replicas[replica] * measure.reshape(1, -1)
            all_energy.append(shifted.ravel())
            all_width.append(width.ravel())
            all_coherence.append(coherence.ravel())
            all_weight.append(weights)
    return (np.concatenate(all_energy), np.concatenate(all_width),
            np.concatenate(all_coherence), np.concatenate(all_weight, axis=1))


def clean_observations(parameters, family, omega=OMEGA):
    energy, width, coherence, weight = components(parameters, family)
    shifted_frequency = omega[:, None] + width[None, :]
    denominator = shifted_frequency ** 2 + energy[None, :] ** 2
    diagonal = (omega[:, None] * shifted_frequency / denominator) @ weight.T
    anomalous = (omega[:, None] * (coherence * energy)[None, :] / denominator) @ weight.T
    return np.stack((diagonal.T, anomalous.T), axis=1)


def target_mass(parameters, family):
    energy, width, coherence, weight = components(parameters, family)
    total_width = width + RESOLUTION
    finite_edges = EDGES[:-1, None]
    cumulative = (np.arctan((finite_edges - energy) / total_width)
                  + np.arctan((finite_edges + energy) / total_width)) / np.pi
    cumulative = np.concatenate((cumulative, np.ones((1, len(energy)))), axis=0)
    return weight @ np.diff(cumulative, axis=0).T


def resolved_density(parameters, family, energy_grid, resolution=RESOLUTION):
    centers, widths, coherence, weight = components(parameters, family)
    widths = widths + resolution
    grid = np.asarray(energy_grid)[:, None]
    kernel = widths / np.pi * (1 / ((grid - centers) ** 2 + widths ** 2)
                               + 1 / ((grid + centers) ** 2 + widths ** 2))
    return weight @ kernel.T


def whiten(values, sigma, correlation=CORRELATION):
    standardized = values / sigma
    result = np.empty_like(standardized)
    result[..., 0] = standardized[..., 0]
    result[..., 1:] = (standardized[..., 1:] - correlation * standardized[..., :-1]) / np.sqrt(1 - correlation ** 2)
    return result


def draw_dataset(seed, per_family):
    random = np.random.default_rng(seed)
    families = np.repeat(np.arange(4), per_family)
    random.shuffle(families)
    count = len(families)
    parameters = random.uniform(0, 1, (count, PARAMETER_COUNT))
    observed = np.empty((count, 2, 2, len(OMEGA)))
    sigma = np.empty_like(observed)
    targets = np.empty((count, 2, len(EDGES) - 1))
    clean = np.empty_like(observed)
    for index, family in enumerate(families):
        clean[index] = clean_observations(parameters[index], int(family))
        targets[index] = target_mass(parameters[index], int(family))
        amplitude = np.exp(random.uniform(np.log(1.e-6), np.log(4.e-6)))
        sigma[index] = amplitude * (1 + .35 * np.arange(2))[None, :, None] * (.6 + .4 / (1 + OMEGA / 6))
        noise = random.normal(size=clean[index].shape)
        for frequency in range(1, len(OMEGA)):
            noise[..., frequency] = CORRELATION * noise[..., frequency - 1] + np.sqrt(1 - CORRELATION ** 2) * noise[..., frequency]
        observed[index] = clean[index] + sigma[index] * noise
    features = dict(observed=observed, sigma=sigma, omega=OMEGA.copy(), matsubara_indices=INDICES.copy(),
                    temperature=np.array(.04), noise_correlation=np.array(CORRELATION), probe=PROBE.copy(),
                    bin_edges=EDGES.copy(), resolution=np.array(RESOLUTION), format_version=np.array(1))
    labels = dict(spectral_mass=targets, family=families)
    private = dict(parameters=parameters, family=families, clean=clean)
    return features, labels, private


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--per-family", type=int, default=16)
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    features, labels, private = draw_dataset(arguments.seed, arguments.per_family)
    np.savez_compressed(arguments.output_dir / "features.npz", **features)
    np.savez_compressed(arguments.output_dir / "labels.npz", **labels)


if __name__ == "__main__":
    main()
