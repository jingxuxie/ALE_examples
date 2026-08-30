"""Synthetic attractive phonon sheets with repulsive intraband Coulomb terms."""

import numpy as np

from reference import calibrate, leading


def make(specification):
    random = np.random.default_rng(specification["seed"])
    bands = len(specification.get("sheet_targets", [specification.get("global_target", 1.001)]))
    per_band = specification.get("patches_per_band", 4)
    patches = bands * per_band
    count = specification["n_freq"]
    maximum_energy = np.exp(random.uniform(np.log(2), np.log(30)))
    temperature = maximum_energy / specification["max_phonon_over_temperature"]
    energies = maximum_energy * np.asarray(specification["mode_ratios"])
    weights = np.exp(random.uniform(-1.2, 0.8, patches))
    weights /= weights.sum()
    labels = np.repeat(np.arange(bands), per_band)
    frequencies = np.pi * temperature * (2 * np.arange(count) + 1)
    profile = 0.4 * maximum_energy / (1 + (frequencies / maximum_energy) ** 2)
    coupling = np.zeros((len(energies), patches, patches))
    coulomb = np.zeros((patches, patches))
    modes = np.zeros((bands, patches, count))
    calibrations = []
    coulomb_strengths = np.broadcast_to(specification["coulomb_strength"], (bands,))
    for band in range(bands):
        selected = np.flatnonzero(labels == band)
        mass = weights[selected].sum()
        angular = np.exp(random.uniform(-0.4, 0.4, per_band))
        perturbation = random.uniform(0.45, 1.55, (per_band, per_band))
        raw = angular[:, None] * angular[None, :] * (perturbation + perturbation.T) / (2 * mass)
        fractions = np.exp(random.uniform(-1.8, 1.2, (len(energies), per_band, per_band)))
        fractions = (fractions + fractions.transpose(0, 2, 1)) / 2
        fractions /= fractions.sum(axis=0)
        local_coupling = fractions * raw
        repulsion = random.uniform(0.7, 1.3, (per_band, per_band))
        repulsion = coulomb_strengths[band] * (repulsion + repulsion.T) / (2 * mass)
        local = {"temperature": np.array(temperature), "n_freq": np.array(count),
                 "weights": weights[selected] / mass, "omega": energies,
                 "coupling": local_coupling * mass, "coulomb": repulsion * mass,
                 "initial_delta": np.broadcast_to(profile, (per_band, count)).copy()}
        target = specification["sheet_targets"][band] if "sheet_targets" in specification else specification["global_target"]
        value, mode, multiplier, history = calibrate(local, target)
        coupling[:, selected[:, None], selected[None, :]] = local["coupling"] / mass
        coulomb[selected[:, None], selected[None, :]] = repulsion
        modes[band, selected] = mode
        calibrations.append({"sheet": band, "target": target, "eigenvalue": value,
                             "coupling_multiplier": multiplier, "history": history})
    link = specification.get("interband_factor", 0.0)
    for first in range(patches):
        for second in range(first):
            if labels[first] == labels[second]:
                continue
            strength = link * np.sqrt(coupling[:, first, first].sum() * coupling[:, second, second].sum())
            fractions = np.exp(random.uniform(-1.5, 1.5, len(energies)))
            fractions /= fractions.sum()
            coupling[:, first, second] = strength * fractions
            coupling[:, second, first] = strength * fractions
    permutation = random.permutation(patches)
    instance = {"temperature": np.array(temperature), "n_freq": np.array(count),
                "weights": weights[permutation], "omega": energies,
                "coupling": coupling[:, permutation][:, :, permutation],
                "coulomb": coulomb[permutation][:, permutation],
                "initial_delta": np.broadcast_to(profile, (patches, count)).copy()}
    value, unused = leading(instance)
    singular_ratios = [float(np.linalg.svd(matrix, compute_uv=False)[-1] / np.linalg.svd(matrix, compute_uv=False)[0])
                       for matrix in instance["coupling"]]
    metadata = dict(specification, patches=patches, bands=bands, band=labels[permutation].tolist(),
                    temperature=temperature, omega=energies.tolist(),
                    linear_eigenvalue=value, calibrations=calibrations,
                    smallest_to_largest_patch_singular_values=singular_ratios,
                    upper_frequency_over_max_phonon=float(frequencies[-1] / maximum_energy),
                    physical_scope="Finite-cutoff synthetic anisotropic phonon sheets; positive spectra, nonnegative intraband Coulomb repulsion, weak positive intersheet phonon links. Isolated-sheet instabilities are calibrated, not supplied to inference.")
    return instance, metadata, modes[:, permutation]
