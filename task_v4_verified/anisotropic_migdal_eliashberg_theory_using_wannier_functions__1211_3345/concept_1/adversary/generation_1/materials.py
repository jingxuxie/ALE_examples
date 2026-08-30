"""Finer genuinely anisotropic patch quadrature and low-temperature material draws."""

from pathlib import Path
import sys

import numpy as np
from scipy.optimize import brentq


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from build_suite import leading


def make(specification):
    random = np.random.default_rng(specification["seed"])
    bands = specification["bands"]
    per_band = specification["patches_per_band"]
    patches = bands * per_band
    labels = np.repeat(np.arange(bands), per_band)
    weights = np.exp(random.uniform(-1.7, 1.0, patches))
    weights /= weights.sum()
    masses = np.bincount(labels, weights=weights)
    maximum_energy = np.exp(random.uniform(np.log(3), np.log(70)))
    energies = maximum_energy * np.asarray(specification["mode_ratios"])
    temperature = maximum_energy / specification["max_phonon_over_temperature"]
    weak = specification["family"] in ("weak_interband", "combined")
    intraband = np.linspace(0.45, 1.3, bands) * random.uniform(0.85, 1.15, bands) if weak else random.uniform(0.75, 1.8, bands)
    interband = 10 ** random.uniform(-7.5, -5.0) if weak else random.uniform(0.035, 0.14)
    block = np.sqrt(intraband[:, None] * intraband[None, :]) * interband
    np.fill_diagonal(block, intraband)
    block /= np.sqrt(masses[:, None] * masses[None, :])
    angular = np.exp(random.uniform(-0.32, 0.32, patches))
    raw = block[labels[:, None], labels[None, :]] * angular[:, None] * angular[None, :]
    perturbation = random.uniform(0.8, 1.2, (patches, patches))
    raw *= (perturbation + perturbation.T) / 2
    fractions = random.uniform(0.15, 1.0, (len(energies), patches, patches))
    fractions = (fractions + fractions.transpose(0, 2, 1)) / 2
    fractions[0] *= 3.5
    fractions /= fractions.sum(axis=0)
    coupling = fractions * raw
    coulomb = np.zeros_like(raw) if weak else random.uniform(0.02, 0.07) * raw / np.max(raw @ weights)
    frequencies = np.pi * temperature * (2 * np.arange(specification["n_freq"]) + 1)
    initial = 0.4 * maximum_energy / (1 + (frequencies / maximum_energy) ** 2)
    permutation = random.permutation(patches)
    instance = {"temperature": np.array(temperature), "n_freq": np.array(specification["n_freq"]),
                "weights": weights[permutation], "omega": energies,
                "coupling": coupling[:, permutation][:, :, permutation],
                "coulomb": coulomb[permutation][:, permutation],
                "initial_delta": np.broadcast_to(initial, (patches, len(frequencies))).copy()}
    calibration = []
    multiplier = 1.0
    if "target_linear_eigenvalue" in specification:
        original = instance["coupling"].copy()

        def difference(scale):
            instance["coupling"] = original * scale
            value, unused = leading(instance)
            calibration.append({"coupling_multiplier": float(scale), "linear_eigenvalue": value})
            return value - specification["target_linear_eigenvalue"]

        multiplier = brentq(difference, 0.015, 4.0, xtol=2e-10, rtol=2e-10)
        instance["coupling"] = original * multiplier
    value, unused = leading(instance)
    metadata = dict(specification, patches=patches, band=labels[permutation].tolist(),
                    interband_factor=interband, temperature=temperature,
                    phonon_ratio=float(energies.max() / energies.min()),
                    min_phonon_over_temperature=float(energies.min() / temperature),
                    max_frequency_over_max_phonon=float(frequencies[-1] / maximum_energy),
                    linear_eigenvalue=value, coupling_multiplier=float(multiplier), calibration=calibration,
                    quadrature_scope="Independently drawn anisotropic couplings on each patch; no duplicated patches or padding")
    return instance, metadata
