"""Independent numerical and analytic checks for the solver."""

import itertools
import time

import numpy as np
from scipy.interpolate import BSpline

import solve


def spline_reference(energies, samples):
    cumulative = np.zeros(len(samples))
    density = np.zeros(len(samples))
    for corners in energies:
        if corners[0] == corners[3]:
            cumulative += samples > corners[0]
            continue
        spline = BSpline.basis_element(corners, extrapolate=False)
        antiderivative = spline.antiderivative()
        inside = (samples > corners[0]) & (samples < corners[3])
        factor = 3 / (corners[3] - corners[0])
        density[inside] += factor * spline(samples[inside])
        cumulative[inside] += factor * (
            antiderivative(samples[inside]) - antiderivative(corners[0]))
        cumulative[samples > corners[3]] += 1
    return cumulative / len(energies), density / len(energies)


def test_tetrahedra():
    random = np.random.default_rng(1717)
    samples = np.sort(random.uniform(-0.2, 1.2, 231))
    families = [
        np.sort(random.uniform(0, 1, (500, 4)), axis=1),
        np.array(list(itertools.combinations_with_replacement([0, 0.25, 0.75, 1], 4))),
        np.array([[0, 1e-14, 0.75, 1], [0, 0.75, 0.75 + 1e-14, 1],
                  [0, 0.25, 1 - 1e-14, 1], [0, 1e-15, 2e-15, 1],
                  [0, 1 - 2e-15, 1 - 1e-15, 1]]),
    ]
    for family, energies in enumerate(families):
        actual = solve.integrate_tetrahedra(energies, samples)
        expected = spline_reference(energies, samples)
        errors = [np.max(np.abs(first - second)) for first, second in zip(actual, expected)]
        print('tetrahedra family', family, 'max errors', errors)
        for first, second in zip(actual, expected):
            np.testing.assert_allclose(first, second, rtol=2e-12, atol=2e-13)
    for sample_count in [1, 2, 3, 7, 64, 257, 4097]:
        energies = np.sort(random.uniform(0, 1, (37, 4)), axis=1)
        thresholds = np.sort(random.uniform(-10, 10, sample_count))
        actual = solve.integrate_tetrahedra(energies, thresholds)
        expected = spline_reference(energies, thresholds)
        for first, second in zip(actual, expected):
            np.testing.assert_allclose(first, second, rtol=2e-12, atol=2e-13)
    energies = np.array([[0, 0, 1, 1], [0, 0, 0, 1], [0, 1, 1, 1]])
    thresholds = np.linspace(0.001, 0.999, 1001)
    cumulative, density = solve.integrate_tetrahedra(energies, thresholds)
    np.testing.assert_allclose(cumulative, thresholds, atol=2e-15)
    np.testing.assert_allclose(density, np.ones(len(thresholds)), atol=3e-15)
    for offset, width in [(0, 1e-10), (1, 1e-8), (20, 1e-6), (-100, 1e-5)]:
        energies = offset + width * np.sort(random.uniform(0, 1, (100, 4)), axis=1)
        thresholds = offset + width * np.sort(random.uniform(-0.1, 1.1, 157))
        actual = solve.integrate_tetrahedra(energies, thresholds)
        expected = spline_reference(energies, thresholds)
        for first, second in zip(actual, expected):
            np.testing.assert_allclose(first, second, rtol=3e-11, atol=2e-12 / width)
    energies = np.concatenate([
        np.sort(random.uniform(-1, 11, (100, 4)), axis=1),
        9 + 1e-9 * np.sort(random.uniform(0, 6, (100, 4)), axis=1),
    ])
    thresholds = np.sort(np.concatenate([
        np.linspace(-2, 12, 121), 9 + 1e-9 * np.linspace(-0.51, 6.13, 157),
    ]))
    actual = solve.integrate_tetrahedra(energies, thresholds)
    expected = spline_reference(energies, thresholds)
    for first, second in zip(actual, expected):
        np.testing.assert_allclose(first, second, rtol=2e-12, atol=2e-13)
    print('analytic, repeated, narrow, and irregular-threshold tetrahedra passed')


def test_periodicity():
    random = np.random.default_rng(844)
    for dimensions in ([1, 1, 1], [2, 3, 4], [4, 3, 5], [6, 7, 8]):
        for repeat in range(10):
            left = np.eye(3, dtype=np.int64)
            right = np.eye(3, dtype=np.int64)
            for step in range(7):
                first, second = random.choice(3, 2, replace=False)
                left[:, first] += random.integers(-3, 4) * left[:, second]
                first, second = random.choice(3, 2, replace=False)
                right[:, first] += random.integers(-3, 4) * right[:, second]
            matrix = left @ np.diag(dimensions) @ right
            addresses = np.array(list(itertools.product(*(range(size) for size in dimensions)))) @ left.T
            addresses += random.integers(-1000, 1000, size=addresses.shape) @ matrix.T
            random.shuffle(addresses)
            adjugate, determinant = solve.adjugate(matrix)
            neighbors = solve.periodic_vertices(addresses, adjugate, determinant)
            for vertex in range(8):
                displacement = np.array([vertex & 1, (vertex >> 1) & 1, (vertex >> 2) & 1])
                differences = addresses + displacement - addresses[neighbors[:, vertex]]
                assert np.all((differences.astype(object) @ adjugate.T) % determinant == 0)
    print('arbitrary representatives, non-diagonal grids, and periodic neighbors passed')


def test_geometry():
    random = np.random.default_rng(8939)
    dimensions = np.diag([6, 8, 10])
    adjugate, determinant = solve.adjugate(dimensions)
    offsets_to_try = np.array(list(itertools.product(range(-5, 6), repeat=3)))
    for family in range(25):
        if family == 0:
            lattice = np.eye(3)
        elif family == 1:
            lattice = np.array([[1, 0.5, 0.5], [0, np.sqrt(0.75), 1 / np.sqrt(12)], [0, 0, np.sqrt(2 / 3)]])
        else:
            lattice = np.eye(3) + random.normal(0, 0.3, (3, 3))
            if np.linalg.cond(lattice) > 8:
                continue
        queries = random.integers(-50, 50, (100, 3))
        queries[:8] = np.array(list(itertools.product([0, 1], repeat=3))) * [3, 4, 5]
        tolerance = 1e-11
        offsets, shifts, distances = solve.closest_images(lattice, adjugate, determinant, queries, tolerance)
        for index, query in enumerate(queries):
            fractional = query / np.diag(dimensions)
            translations = -np.floor(fractional).astype(int)
            candidates = offsets_to_try + translations
            cartesian = (fractional + candidates) @ lattice.T
            distance = np.sum(cartesian ** 2, axis=1)
            best = distance.min()
            expected = sorted(map(tuple, candidates[distance <= best + tolerance]))
            actual = list(map(tuple, shifts[offsets[index]:offsets[index + 1]]))
            assert actual == expected, (family, query, actual, expected)
            np.testing.assert_allclose(distances[index], best, rtol=5e-14, atol=2e-15)
    lattice = np.array([[1., 1000., -37000.], [0., 1., 2300.], [0., 0., 1.]])
    queries = np.array([[3, 4, 5], [0, 0, 0], [12, -13, 33], [60000003, -79999996, 100000005]])
    offsets, shifts, distances = solve.closest_images(lattice, adjugate, determinant, queries, 1e-11)
    inverse, sign = solve.adjugate(lattice.astype(np.int64))
    inverse *= sign
    for index, query in enumerate(queries):
        cartesian = lattice.astype(np.longdouble) @ (query.astype(np.longdouble) / np.diag(dimensions))
        residue = cartesian - np.floor(cartesian)
        small_shifts = np.array(list(itertools.product([-1, 0], repeat=3)))
        distance = np.sum((residue + small_shifts) ** 2, axis=1)
        selected = small_shifts[distance <= distance.min() + 1e-11]
        expected = sorted(tuple(int(value) for value in inverse @ (candidate.astype(object) - np.floor(cartesian).astype(object))) for candidate in selected)
        actual = list(map(tuple, shifts[offsets[index]:offsets[index + 1]]))
        assert actual == expected, (query, actual, expected)
    assert np.max(np.abs(shifts)) > 1000000
    left = np.array([[1, 17, -3], [0, 1, 2], [0, 0, 1]])
    right = np.array([[1, 0, 0], [31, 1, 0], [7, -13, 1]])
    transformed_grid = left @ dimensions @ right
    transformed_adjugate, transformed_determinant = solve.adjugate(transformed_grid)
    inverse_right, sign = solve.adjugate(right)
    inverse_right *= sign
    queries = random.integers(-50, 50, (100, 3))
    for tolerance in [0., 1e-11, 0.1, 1.0]:
        baseline = solve.closest_images(np.eye(3), adjugate, determinant, queries, tolerance)
        transformed = solve.closest_images(right, transformed_adjugate, transformed_determinant, queries @ left.T, tolerance)
        np.testing.assert_array_equal(baseline[0], transformed[0])
        np.testing.assert_allclose(baseline[2], transformed[2], rtol=1e-14, atol=1e-15)
        for index in range(len(queries)):
            lower, upper = baseline[0][index:index + 2]
            expected = sorted(map(tuple, baseline[1][lower:upper] @ inverse_right.T))
            assert list(map(tuple, transformed[1][lower:upper])) == expected
    print('brute-force images, boundary ties, translations, and large shear passed')


def test_flat_grid():
    data = {
        'grid_matrix': np.array([[1, 3, -7], [0, 1, 6], [0, 0, 1]]),
        'grid_addresses': np.array([[71, -33, 16]]),
        'query_addresses': np.array([[0, 0, 0], [4, -17, 900]]),
        'reciprocal_lattice': np.array([[1., 0.2, -0.3], [0., 0.9, 0.4], [0., 0., 1.2]]),
        'frequencies': np.array([[-0.1, 0., 7., 7.00000001]]),
        'sampling_points': np.array([-1., -0.01, 1., 7.000000005, 8.]),
        'tie_tolerance': np.array(1e-11),
    }
    output = solve.solve(data)
    assert set(output) == {'image_offsets', 'image_shifts', 'distance2', 'dos', 'cumulative'}
    np.testing.assert_array_equal(output['cumulative'], data['sampling_points'][:, None] > data['frequencies'])
    np.testing.assert_array_equal(output['dos'], 0)
    np.testing.assert_array_equal(output['distance2'], 0)
    print('one-point periodic interpolant and exact point masses passed')


def test_full_example():
    with np.load('../participant/input/example.npz') as archive:
        data = {key: archive[key] for key in archive.files}
    output = solve.solve(data)
    matrix = data['grid_matrix']
    inverse = np.linalg.inv(matrix)
    keys = np.rint((data['grid_addresses'] @ inverse.T % 1) * 100000000).astype(int)
    lookup = {tuple(key): index for index, key in enumerate(keys)}
    vertices = np.empty((len(keys), 8), dtype=int)
    for index, address in enumerate(data['grid_addresses']):
        for vertex in range(8):
            displaced = address + [vertex & 1, (vertex >> 1) & 1, (vertex >> 2) & 1]
            key = np.rint((inverse @ displaced % 1) * 100000000).astype(int) % 100000000
            vertices[index, vertex] = lookup[tuple(key)]
    microcell = data['reciprocal_lattice'] @ inverse
    diagonals = microcell @ np.array([[1, 1, 1], [-1, 1, 1], [1, -1, 1], [1, 1, -1]]).T
    selected = np.argmin(np.sum(diagonals ** 2, axis=0))
    for branch in range(data['frequencies'].shape[1]):
        energies = np.sort(data['frequencies'][vertices[:, solve.TETRAHEDRA[selected]].reshape(-1, 4), branch], axis=1)
        expected_cumulative, expected_density = spline_reference(energies, data['sampling_points'])
        print('example branch', branch, 'CDF error', np.max(np.abs(output['cumulative'][:, branch] - expected_cumulative)),
              'DOS error', np.max(np.abs(output['dos'][:, branch] - expected_density)))
        np.testing.assert_allclose(output['cumulative'][:, branch], expected_cumulative, rtol=1e-12, atol=1e-13)
        np.testing.assert_allclose(output['dos'][:, branch], expected_density, rtol=1e-12, atol=1e-13)
    print('complete example spectrum matches independent B-spline reference')


if __name__ == '__main__':
    started = time.perf_counter()
    test_tetrahedra()
    test_periodicity()
    test_geometry()
    test_flat_grid()
    test_full_example()
    print('All checks passed in', time.perf_counter() - started, 'seconds')
