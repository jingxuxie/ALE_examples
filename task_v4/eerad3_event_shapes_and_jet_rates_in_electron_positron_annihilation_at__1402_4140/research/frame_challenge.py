import ctypes
import json
from pathlib import Path

import mpmath as mp
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / 'concept_1'


def transform(momenta, frames, seed):
    generator = np.random.default_rng(seed)
    raw_axes = generator.normal(size=(len(momenta), 3))
    axes = raw_axes.astype(np.longdouble)
    axes /= np.sqrt(np.sum(axes ** 2, axis=1, keepdims=True))
    gamma = np.ones(len(momenta), dtype=np.longdouble)
    gamma[frames == 2] = 10.0 ** generator.uniform(1, 3, np.sum(frames == 2))
    gamma[frames == 3] = 10.0 ** generator.uniform(5, 8, np.sum(frames == 3))
    output = momenta.copy()
    canonical = np.flatnonzero(frames == 1)
    if len(canonical):
        vectors = momenta[canonical, :, :3].astype(np.longdouble)
        axis = vectors[:, 0].copy()
        axis /= np.sqrt(np.sum(axis * axis, axis=1, keepdims=True))
        axis *= generator.choice([-1, 1], len(canonical))[:, None]
        auxiliary = np.eye(3, dtype=np.longdouble)[np.argmin(np.abs(axis), axis=1)]
        first = np.cross(auxiliary, axis)
        first /= np.sqrt(np.sum(first * first, axis=1, keepdims=True))
        second = np.cross(axis, first)
        rotation = np.stack([first, second, axis], axis=1)
        output[canonical, :, :3] = np.einsum('nij,nkj->nki', rotation, vectors).astype(float)
    selected = np.flatnonzero(frames >= 2)
    if len(selected):
        spatial = momenta[selected, :, :3].astype(np.longdouble)
        energy = np.sqrt(np.sum(spatial * spatial, axis=2))
        direction = axes[selected, None, :]
        projection = np.sum(spatial * direction, axis=2)
        cross = np.cross(direction, spatial)
        transverse = np.cross(cross, direction)
        cross_squared = np.sum(cross * cross, axis=2)
        plus = np.where(projection < 0, cross_squared / (energy - projection), energy + projection)
        minus = np.where(projection > 0, cross_squared / (energy + projection), energy - projection)
        factor = gamma[selected] + np.sqrt(gamma[selected] ** 2 - 1)
        outgoing_energy = (factor[:, None] * plus + minus / factor[:, None]) / 2
        outgoing_projection = (factor[:, None] * plus - minus / factor[:, None]) / 2
        output[selected, :, :3] = np.asarray(transverse + outgoing_projection[:, :, None] * direction, dtype=float)
        output[selected, :, 3] = np.asarray(outgoing_energy, dtype=float)
    assert np.isfinite(output).all() and np.all(output[:, :, 3] > 0)
    return output, raw_axes, np.asarray(gamma, dtype=float)


def high_precision_check(original, transformed, raw_axes, gammas, frames):
    selected = np.flatnonzero(frames >= 2)
    maximum = 0.0
    with mp.workdps(100):
        for sample in selected[np.linspace(0, len(selected)-1, min(64, len(selected)), dtype=int)]:
            axis = [mp.mpf(float(value)) for value in raw_axes[sample]]
            length = mp.sqrt(sum(value * value for value in axis))
            axis = [value / length for value in axis]
            gamma = mp.mpf(float(gammas[sample]))
            boost = mp.sqrt(gamma * gamma - 1)
            for particle in range(5):
                spatial = [mp.mpf(float(value)) for value in original[sample, particle, :3]]
                energy = mp.sqrt(sum(value * value for value in spatial))
                projection = sum(left * right for left, right in zip(axis, spatial))
                expected = [spatial[index] + ((gamma-1)*projection + boost*energy)*axis[index] for index in range(3)]
                expected.append(gamma * energy + boost * projection)
                actual = transformed[sample, particle]
                error = max(abs(mp.mpf(float(value)) - target) for value, target in zip(actual, expected)) / expected[3]
                maximum = max(maximum, float(error))
    assert maximum < 2e-14, maximum
    return maximum


def main():
    data = np.load(CONCEPT / 'evaluator/hidden/test.npz')
    count = 2500
    momenta = np.concatenate([data['p'][:count]] * 4)
    labels = np.concatenate([data['log_weight'][:count]] * 4)
    frames = np.repeat(np.arange(4), count)
    moved, raw_axes, gammas = transform(momenta, frames, 844991)
    error = high_precision_check(momenta, moved, raw_axes, gammas, frames)
    library = ctypes.CDLL(str(CONCEPT / 'champions/generation_2/kernel.so'))
    pointer = ctypes.POINTER(ctypes.c_double)
    library.predict_kernel.argtypes = [pointer, pointer, ctypes.c_size_t]
    output = np.empty(len(momenta))
    inputs = np.ascontiguousarray(moved)
    library.predict_kernel(inputs.ctypes.data_as(pointer), output.ctypes.data_as(pointer), len(output))
    scores = {}
    for frame, name in enumerate(['CM', 'canonical_axes', 'moderate_boost', 'large_boost']):
        difference = output[frames == frame] - labels[frames == frame]
        scores[name] = {'finite_fraction': float(np.mean(np.isfinite(difference))),
                        'log_rmse': float(np.sqrt(np.mean(difference ** 2))) if np.isfinite(difference).all() else None,
                        'max_abs_log_error': float(np.max(np.abs(difference))) if np.isfinite(difference).all() else None}
    report = {'cases': len(momenta), 'frame_scores': scores,
              'boost_vs_100_digit_max_relative_vector_error': error,
              'root_cause': 'CM photon contraction and finite-precision frame-dependent kinematics; the target is a scalar function of authoritative normalized invariants'}
    (CONCEPT / 'adversary/generation_2_frame_search.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
