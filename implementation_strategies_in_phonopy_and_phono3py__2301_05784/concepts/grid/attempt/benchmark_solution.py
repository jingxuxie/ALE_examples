"""Reproducible large-grid accuracy and resource checks."""

import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import resource
import time

import numpy as np

import solve


def benchmark():
    random = np.random.default_rng(413)
    dimensions = (48, 49, 45)
    matrix = np.array([[48, 13, -7], [0, 49, 19], [0, 0, 45]])
    addresses = np.indices(dimensions).reshape(3, -1).T
    random.shuffle(addresses)
    fractional = addresses @ np.linalg.inv(matrix).T
    angular = 2 * np.pi * fractional
    frequencies = np.column_stack([
        5 * np.sqrt(np.sum(np.sin(angular) ** 2, axis=1)),
        10 + np.cos(angular[:, 0]) + 0.5 * np.cos(angular[:, 1]),
        20 + 1e-6 * (np.cos(angular[:, 0]) + np.cos(angular[:, 1])),
        np.where(addresses[:, 0] % 4, 25., 26.),
    ])
    samples = np.unique(np.concatenate([
        np.linspace(-0.131, 27.123, 257),
        20 + np.linspace(-2.13e-6, 2.07e-6, 157),
    ]))
    data = {
        'grid_matrix': matrix,
        'grid_addresses': addresses,
        'reciprocal_lattice': np.array([[0.4, 0.38, -0.19], [0, 0.07, 0.033], [0, 0, 0.22]]),
        'query_addresses': random.integers(-10000, 10000, (300, 3)),
        'tie_tolerance': np.array(1e-11),
        'frequencies': frequencies,
        'sampling_points': samples,
    }
    started = time.perf_counter()
    output = solve.solve(data)
    elapsed = time.perf_counter() - started
    print('large grid:', len(addresses), 'points,', frequencies.shape[1], 'branches,', len(samples), 'thresholds', flush=True)
    print('elapsed seconds:', elapsed, 'peak RSS KiB:', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, flush=True)
    for values in output.values():
        assert np.all(np.isfinite(values))
    np.testing.assert_allclose(output['cumulative'][0], 0, atol=0)
    np.testing.assert_allclose(output['cumulative'][-1], 1, atol=0)
    assert np.min(np.diff(output['cumulative'], axis=0)) > -5e-14
    assert np.all(output['dos'] >= 0)

    adjugate, determinant = solve.adjugate(matrix)
    vertices = solve.periodic_vertices(addresses, adjugate, determinant)
    microcell = data['reciprocal_lattice'] @ np.linalg.inv(matrix)
    diagonals = np.array([[1, 1, 1], [-1, 1, 1], [1, -1, 1], [1, 1, -1]]) @ microcell.T
    selected = np.argmin(np.sum(diagonals ** 2, axis=1))
    tetrahedra = vertices[:, solve.TETRAHEDRA[selected]].reshape(-1, 4)
    for branch in range(frequencies.shape[1]):
        corners = np.sort(frequencies[tetrahedra, branch], axis=1)
        threshold_indices = np.linspace(0, len(samples) - 1, 9).astype(int)
        if branch == 2:
            inside = np.flatnonzero(np.abs(samples - 20) < 2.1e-6)
            threshold_indices = inside[np.linspace(0, len(inside) - 1, 9).astype(int)]
        thresholds = samples[threshold_indices]
        expected_cumulative = np.zeros(len(thresholds), dtype=np.longdouble)
        expected_density = np.zeros(len(thresholds), dtype=np.longdouble)
        for threshold_index, threshold in enumerate(thresholds):
            complete = corners[:, 3] < threshold
            expected_cumulative[threshold_index] = np.count_nonzero(complete)
            for region in range(3):
                inside = (corners[:, region] < threshold) & (threshold < corners[:, region + 1])
                active = corners[inside].astype(np.longdouble)
                if len(active):
                    values = solve.interval_coefficients(
                        active, np.full(len(active), threshold, dtype=np.longdouble), np.zeros(len(active), dtype=np.longdouble), region)
                    expected_cumulative[threshold_index] += values[0].sum()
                    expected_density[threshold_index] += values[4].sum()
        expected_cumulative /= len(corners)
        expected_density /= len(corners)
        actual_cumulative = output['cumulative'][threshold_indices, branch]
        actual_density = output['dos'][threshold_indices, branch]
        cumulative_error = float(np.max(np.abs(actual_cumulative - expected_cumulative)))
        density_error = float(np.max(np.abs(actual_density - expected_density)))
        print('branch', branch, 'long-double direct CDF error', cumulative_error,
              'DOS relative max error', density_error / max(1, np.max(expected_density)), flush=True)
        np.testing.assert_allclose(actual_cumulative, expected_cumulative, rtol=2e-12, atol=1e-13)
        np.testing.assert_allclose(actual_density, expected_density, rtol=2e-11, atol=1e-12)
    print('Large-grid checks passed.', flush=True)


if __name__ == '__main__':
    benchmark()
