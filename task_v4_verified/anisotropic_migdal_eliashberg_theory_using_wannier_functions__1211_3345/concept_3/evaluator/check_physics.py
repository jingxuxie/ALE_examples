"""Independent normalization, causality, forward-map and noise checks."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.integrate import quad


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))
import generator


def main():
    random = np.random.default_rng(98732)
    maximum_forward_error, maximum_integral_error, minimum_eigenvalue = 0., 0., np.inf
    for family in range(4):
        parameters = random.uniform(0, 1, generator.PARAMETER_COUNT)
        energy, width, coherence, weight = generator.components(parameters, family)
        assert np.all(width > 0) and np.all(energy > 0) and np.all(weight >= 0)
        assert np.all((coherence > 0) & (coherence <= 1))
        assert np.allclose(weight.sum(axis=1), 1, rtol=0, atol=1.e-13)
        frequency = generator.OMEGA
        positive = 1 / (1j * frequency[:, None] - energy + 1j * width)
        negative = 1 / (1j * frequency[:, None] + energy + 1j * width)
        diagonal = ((positive + negative) / 2) @ weight.T
        anomalous = ((positive - negative) * coherence / 2) @ weight.T
        direct = np.stack((-frequency * diagonal.T.imag, -frequency * anomalous.T.real), axis=1)
        maximum_forward_error = max(maximum_forward_error, float(np.max(np.abs(direct - generator.clean_observations(parameters, family)))))
        for real_energy in np.linspace(-20, 20, 81):
            positive = 1 / (real_energy - energy + 1j * width)
            negative = 1 / (real_energy + energy + 1j * width)
            diagonal = -np.imag(weight @ ((positive + negative) / 2)) / np.pi
            anomalous = -np.imag(weight @ ((positive - negative) * coherence / 2)) / np.pi
            minimum_eigenvalue = min(minimum_eigenvalue, float(np.min(diagonal - np.abs(anomalous))))
        targets = generator.target_mass(parameters, family)
        bands = 3 if family == 3 else 2
        assert np.allclose(targets[:bands].sum(axis=1), 1, rtol=0, atol=1.e-13)
        assert np.all(targets[bands:] == 0)
        per_band = len(energy) // bands
        for band in range(bands):
            section = slice(band * per_band, (band + 1) * per_band)
            centers, widths = energy[section], width[section] + generator.RESOLUTION
            measure = weight[0, section] / weight[0, section].sum()
            def density(real_energy):
                return float(measure @ (widths / np.pi * (1 / ((real_energy - centers) ** 2 + widths ** 2)
                                                          + 1 / ((real_energy + centers) ** 2 + widths ** 2))))
            for window in (1, 5, 10, 13):
                integral, error = quad(density, generator.EDGES[window], generator.EDGES[window + 1], epsabs=1.e-10, limit=200)
                maximum_integral_error = max(maximum_integral_error, abs(integral - targets[band, window]))
    hidden = ROOT / "evaluator" / "hidden"
    with np.load(hidden / "test_features.npz", allow_pickle=False) as features, np.load(hidden / "test_latent.npz", allow_pickle=False) as latent:
        assert not {"family", "parameters", "clean", "spectral_mass"}.intersection(features.files)
        residual = generator.whiten(features["observed"] - latent["clean"], features["sigma"])
        noise_mean, noise_std = float(residual.mean()), float(residual.std())
    manifest = json.loads((hidden / "data_manifest.json").read_text())
    hashes_match = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in manifest["files"].items())
    passed = maximum_forward_error < 1.e-12 and maximum_integral_error < 1.e-8 and minimum_eigenvalue >= -1.e-12 and hashes_match
    report = dict(passed=passed, maximum_forward_error=maximum_forward_error, maximum_independent_integral_error=maximum_integral_error,
                  minimum_nambu_spectral_eigenvalue=minimum_eigenvalue, whitened_noise_mean=noise_mean,
                  whitened_noise_std=noise_std, frozen_data_hashes_match=hashes_match,
                  target_sha256=manifest["target_sha256"], role="physics and data sanity only, not predictive attainability")
    (hidden / "physics_checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    assert passed


if __name__ == "__main__":
    main()
