"""Private synthetic spectral benchmark authoring; no upstream code copied."""

import hashlib
import json
import os
from pathlib import Path
import sys

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant" / "input"))
from physics import FAMILY_NAMES, kernel, observables


EDGES = np.linspace(-8.0, 8.0, 257)
OMEGA = (EDGES[:-1] + EDGES[1:]) / 2.0


def normalized(values):
    return values / values.sum()


def gaussian(center, width):
    return normalized(np.exp(-0.5 * ((OMEGA - center) / width) ** 2))


def continuum(center, width, skew, shape):
    coordinate = (OMEGA - center) / width
    values = np.maximum(1.0 - coordinate**2, 0.0) ** shape
    values *= np.exp(np.clip(skew * coordinate, -6.0, 6.0))
    return normalized(values)


def spectrum(random, family):
    components = []
    if family == 0:
        center = random.uniform(-0.4, 0.4)
        width = random.uniform(0.09, 0.24)
        peak = gaussian(center, width)
        background = continuum(random.uniform(-0.8, 0.8), random.uniform(2.0, 4.0), random.uniform(-1.2, 1.2), random.uniform(0.3, 1.8))
        components = [peak, background]
        peak_weight = random.uniform(0.4, 0.85)
        weights = np.array([peak_weight, 1.0 - peak_weight])
    elif family in (1, 2):
        separation = random.uniform(1.6, 4.6)
        shift = random.uniform(-0.65, 0.65)
        left_width, right_width = random.uniform(0.4, 1.0, 2)
        left = gaussian(shift - separation / 2.0, left_width)
        right = gaussian(shift + separation / 2.0, right_width)
        if family == 2:
            gap = random.uniform(0.25, min(1.3, separation / 2.0 - 0.1))
            taper = np.clip((np.abs(OMEGA) - gap) / random.uniform(0.10, 0.35), 0.0, 1.0)
            left = normalized(left * taper)
            right = normalized(right * taper)
        components = [left, right]
        left_weight = random.uniform(0.25, 0.75)
        weights = np.array([left_weight, 1.0 - left_weight])
        if family == 1:
            peak_weight = random.uniform(0.10, 0.45)
            components.append(gaussian(random.uniform(-0.25, 0.25), random.uniform(0.09, 0.26)))
            weights = np.append((1.0 - peak_weight) * weights, peak_weight)
    elif family == 3:
        broad = continuum(random.uniform(-0.6, 0.6), random.uniform(2.0, 4.5), random.uniform(-1.4, 1.4), random.uniform(0.2, 1.6))
        notch_width = random.uniform(0.25, 1.0)
        depth = random.uniform(0.60, 0.98)
        notch_center = random.uniform(-0.12, 0.12)
        notch = 1.0 - depth * np.exp(-0.5 * ((OMEGA - notch_center) / notch_width) ** 2)
        components = [normalized(broad * notch)]
        shoulder = gaussian(random.choice([-1.0, 1.0]) * random.uniform(0.6, 1.5), random.uniform(0.2, 0.5))
        components.append(normalized(shoulder * notch))
        shoulder_weight = random.uniform(0.0, 0.25)
        weights = np.array([1.0 - shoulder_weight, shoulder_weight])
    elif family == 4:
        broad = continuum(random.uniform(-1.2, 1.2), random.uniform(2.2, 4.8), random.uniform(-2.0, 2.0), random.uniform(0.2, 1.8))
        satellite = gaussian(random.choice([-1.0, 1.0]) * random.uniform(1.5, 4.8), random.uniform(0.25, 0.9))
        components = [broad, satellite]
        satellite_weight = random.uniform(0.08, 0.4)
        weights = np.array([1.0 - satellite_weight, satellite_weight])
    else:
        count = int(random.integers(3, 6))
        centers = np.sort(random.uniform(-4.8, 4.8, count))
        for center in centers:
            components.append(continuum(center, random.uniform(0.45, 1.5), random.uniform(-1.5, 1.5), random.uniform(0.2, 1.6)))
        weights = random.dirichlet(np.full(count, 2.0))
    basis = np.stack(components, axis=1)
    mass = normalized(basis @ weights)
    return mass, basis


def make_split(name, per_family, seed):
    sequence = np.random.SeedSequence(seed)
    shape_seed, observation_seed, shuffle_seed, identifier_seed = sequence.spawn(4)
    shapes = np.random.default_rng(shape_seed)
    observations = np.random.default_rng(observation_seed)
    shuffling = np.random.default_rng(shuffle_seed)
    identifiers = np.random.default_rng(identifier_seed)
    count = per_family * len(FAMILY_NAMES)
    family = np.repeat(np.arange(len(FAMILY_NAMES)), per_family)
    spectral_mass = []
    private_basis = []
    for family_index in family:
        mass, basis = spectrum(shapes, family_index)
        spectral_mass.append(mass)
        padded = np.zeros((256, 5))
        padded[:, :basis.shape[1]] = basis
        private_basis.append(padded)
    spectral_mass = np.stack(spectral_mass)
    beta = observations.uniform(6.0, 28.0, count)
    noise = np.exp(observations.uniform(np.log(3e-5), np.log(1.2e-3), count))
    tau = []
    correlation = []
    covariance = []
    noiseless = []
    for row in range(count):
        coordinate = (1.0 - np.cos(np.linspace(0.0, np.pi, 56))) / 2.0
        coordinate[1:-1] += observations.uniform(-0.15, 0.15, 54) * np.minimum(np.diff(coordinate)[:-1], np.diff(coordinate)[1:])
        local_tau = beta[row] * coordinate
        correlation_length = observations.uniform(0.03, 0.18)
        correlation_strength = observations.uniform(0.2, 0.85)
        time_correlation = np.exp(-np.abs(coordinate[:, None] - coordinate[None, :]) / correlation_length)
        rank_one = np.cos(np.pi * coordinate + observations.uniform(-0.5, 0.5))
        cov = (1.0 - correlation_strength) * np.eye(56) + correlation_strength * time_correlation
        cov += observations.uniform(0.0, 0.25) * np.outer(rank_one, rank_one)
        standard_deviation = noise[row] * (0.65 + 0.35 * np.cos(2.0 * np.pi * coordinate) ** 2)
        cov *= np.outer(standard_deviation, standard_deviation)
        signal = kernel(beta[row], local_tau, EDGES) @ spectral_mass[row]
        observed = signal + np.linalg.cholesky(cov) @ observations.normal(size=56)
        tau.append(local_tau)
        covariance.append(cov)
        correlation.append(observed)
        noiseless.append(signal)
    permutation = shuffling.permutation(count)
    sample_id = identifiers.integers(0, np.iinfo(np.uint64).max, count, dtype=np.uint64)
    inputs = {
        "sample_id": sample_id[permutation],
        "omega_edges": EDGES,
        "beta": beta[permutation],
        "tau": np.stack(tau)[permutation],
        "correlation": np.stack(correlation)[permutation],
        "covariance": np.stack(covariance)[permutation],
    }
    labels = {
        "sample_id": inputs["sample_id"],
        "spectral_mass": spectral_mass[permutation],
        "family_id": family[permutation],
        **observables(spectral_mass[permutation], EDGES),
    }
    location = ROOT / ("evaluator/hidden" if name == "heldout" else "participant/input")
    np.savez_compressed(location / f"{name}_input.npz", **inputs)
    np.savez_compressed(location / f"{name}_labels.npz", **labels)
    if name == "validation":
        np.savez_compressed(ROOT / "evaluator/hidden/validation_privileged.npz", basis=np.stack(private_basis)[permutation], noiseless=np.stack(noiseless)[permutation])
    return {
        "name": name,
        "count": count,
        "per_family": per_family,
        "seed": seed,
        "input_sha256": hashlib.sha256((location / f"{name}_input.npz").read_bytes()).hexdigest(),
        "labels_sha256": hashlib.sha256((location / f"{name}_labels.npz").read_bytes()).hexdigest(),
        "ordered_id_sha256": hashlib.sha256(inputs["sample_id"].tobytes()).hexdigest(),
    }


def main():
    manifest_path = ROOT / "evaluator/hidden/split_manifest.json"
    if manifest_path.exists():
        raise SystemExit("refusing to overwrite a fixed split")
    seeds = {"train": 851172391, "validation": 2347573091, "heldout": 12900573944712258001}
    sizes = {"train": 256, "validation": 32, "heldout": 32}
    splits = [make_split(name, sizes[name], seeds[name]) for name in seeds]
    manifest = {
        "schema": "alf-spectral-v1",
        "generation_date": "2026-08-28",
        "families": list(FAMILY_NAMES),
        "independence": "independent split SeedSequences; separate spectrum, observation, shuffle, ID streams",
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "splits": splits,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
