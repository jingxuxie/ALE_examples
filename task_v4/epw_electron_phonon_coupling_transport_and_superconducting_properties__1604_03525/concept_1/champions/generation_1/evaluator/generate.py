import argparse
import hashlib
import json
from pathlib import Path
import secrets

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
KB = 0.08617333262
OMEGA = (np.arange(192) + 0.5) * 0.625
WIDTH = np.full(192, 0.625)
INDICES = np.r_[np.arange(21), np.arange(22, 42, 2), [45, 50, 60, 70, 85, 100, 120, 150, 180]].astype(np.int64)


def spectrum(rng, family, omega=OMEGA, width=WIDTH):
    cutoff = np.exp(-((omega / 118.0) ** 18))
    onset = omega ** 2 / (omega ** 2 + 2.0 ** 2)
    components = []

    def acoustic(scale, power):
        components.append(omega ** 2 * np.exp(-(omega / scale) ** power) * cutoff)

    def optical(center, spread):
        skew = rng.uniform(-0.28, 0.28)
        distance = (omega - center) / spread
        components.append(np.exp(-0.5 * distance ** 2) * np.exp(skew * np.tanh(distance)) * onset * cutoff)

    if family == 0:
        acoustic(rng.uniform(7, 17), rng.uniform(2, 4))
        optical(rng.uniform(22, 43), rng.uniform(3, 7))
        optical(rng.uniform(55, 91), rng.uniform(4, 9))
        weights = np.array([rng.uniform(0.45, 0.75), rng.uniform(0.12, 0.35), rng.uniform(0.08, 0.25)])
    elif family == 1:
        acoustic(rng.uniform(12, 25), rng.uniform(2, 3.5))
        optical(rng.uniform(3.5, 11), rng.uniform(1.2, 2.8))
        optical(rng.uniform(23, 43), rng.uniform(3, 7))
        optical(rng.uniform(61, 98), rng.uniform(4, 9))
        weights = np.array([rng.uniform(0.12, 0.25), rng.uniform(0.35, 0.62), rng.uniform(0.12, 0.3), rng.uniform(0.07, 0.2)])
    elif family == 2:
        acoustic(rng.uniform(7, 20), rng.uniform(2, 4))
        center, separation = rng.uniform(29, 60), rng.uniform(6, 16)
        optical(center - separation / 2, rng.uniform(2, 4.5))
        optical(center + separation / 2, rng.uniform(2, 4.5))
        optical(rng.uniform(79, 103), rng.uniform(3, 8))
        weights = np.array([rng.uniform(0.12, 0.32), rng.uniform(0.2, 0.5), rng.uniform(0.2, 0.5), rng.uniform(0.08, 0.25)])
    else:
        acoustic(rng.uniform(10, 27), rng.uniform(2, 3.5))
        optical(rng.uniform(18, 39), rng.uniform(5, 10))
        optical(rng.uniform(46, 70), rng.uniform(5, 11))
        optical(rng.uniform(82, 104), rng.uniform(5, 10))
        weights = rng.uniform(0.12, 0.45, size=4)
    shapes = np.array(components)
    shapes /= (shapes * (2 * width / omega)).sum(axis=1, keepdims=True)
    weights /= weights.sum()
    coupling = rng.uniform(0.55, 2.4)
    return coupling * (weights @ shapes)


def make_split(seed, per_family):
    rng = np.random.default_rng(seed)
    family = np.repeat(np.arange(4, dtype=np.int64), per_family)
    rng.shuffle(family)
    alpha2f = np.array([spectrum(rng, int(code)) for code in family])
    count = len(family)
    temperature = rng.uniform(1.8, 6.0, count)
    nu = 2 * np.pi * KB * temperature[:, None] * INDICES
    rho = rng.uniform(0.3, 0.85, count)
    length = rng.uniform(1.5, 5.5, count)
    scale = np.exp(rng.uniform(np.log(0.0003), np.log(0.002), count))
    std = scale[:, None] * (0.35 + 0.65 / (1.0 + (nu / 75.0) ** 0.7))
    mass = alpha2f * (2 * WIDTH / OMEGA)
    clean = np.einsum('brj,bj->br', OMEGA ** 2 / (OMEGA ** 2 + nu[..., None] ** 2), mass)
    interaction = clean.copy()
    slots = np.arange(40)
    separation = np.abs(slots[:, None] - slots)
    for row in range(count):
        correlation = (1 - rho[row]) * np.eye(40) + rho[row] * np.exp(-separation / length[row])
        interaction[row] += std[row] * (np.linalg.cholesky(correlation) @ rng.normal(size=40))
    mask = np.ones((count, 40), dtype=bool)
    for row in range(count):
        missing = rng.choice(np.arange(1, 40), size=int(rng.integers(0, 11)), replace=False)
        mask[row, missing] = False
    interaction[~mask] = 0.0
    inputs = dict(omega_mev=OMEGA, domega_mev=WIDTH, matsubara_index=INDICES, temperature_k=temperature,
                  nu_mev=nu, interaction=interaction, mask=mask, noise_std=std, noise_rho=rho,
                  noise_length=length, mu_star=rng.uniform(0.09, 0.16, count))
    return inputs, dict(alpha2f=alpha2f, family=family)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rebuild', action='store_true')
    args = parser.parse_args()
    manifest_path = ROOT / 'evaluator/hidden/manifest.json'
    if manifest_path.exists() and not args.rebuild:
        raise SystemExit('Data already frozen; refusing overwrite without --rebuild')
    if manifest_path.exists():
        seeds = json.loads(manifest_path.read_text())['private_seeds']
    else:
        seeds = {name: secrets.randbits(96) for name in ('train', 'validation', 'test')}
    files = {}
    for name, per_family in [('train', 2048), ('validation', 128), ('test', 96)]:
        inputs, labels = make_split(seeds[name], per_family)
        folder = ROOT / ('evaluator/hidden' if name == 'test' else 'participant/input')
        folder.mkdir(parents=True, exist_ok=True)
        for suffix, arrays in [('input', inputs), ('labels', labels)]:
            path = folder / f'{name}_{suffix}.npz'
            np.savez_compressed(path, **arrays)
            files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        print(name, len(labels['family']), flush=True)
    manifest_path.write_text(json.dumps(dict(version='1.0', private_seeds=seeds, sha256=files,
                                            provenance='Smooth nonnegative phenomenological spectra; exact declared discrete forward model; independent Gaussian noise.'), indent=2) + '\n')


if __name__ == '__main__':
    main()
