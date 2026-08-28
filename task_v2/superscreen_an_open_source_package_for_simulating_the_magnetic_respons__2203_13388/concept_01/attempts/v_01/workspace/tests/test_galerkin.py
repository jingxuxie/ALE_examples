import numpy as np

from qualification.galerkin import (MU0, SheetModel, adaptive_pair, evaluate_field, integrate_pair,
                                    quadrature, triangle_integrals)
from qualification.model import DeviceCase


TRIANGLE = np.array([[0., 0., 0.], [1.1, 0., 0.], [0.2, 0.8, 0.]])


def test_analytic_triangle_against_independent_area_quadrature():
    barycentric, weights = quadrature(70)
    positions = barycentric @ TRIANGLE
    for observer in (np.array([0.3, 0.2, 0.6]), np.array([2., -1., -0.3])):
        displacement = observer - positions
        radii = np.linalg.norm(displacement, axis=1)
        expected_potential = 0.44 * np.sum(weights / radii)
        expected_field = 0.44 * np.sum(weights[:, None] * displacement / radii[:, None] ** 3, axis=0)
        actual = triangle_integrals(observer, TRIANGLE)
        np.testing.assert_allclose(actual[0], expected_potential, rtol=2e-12)
        np.testing.assert_allclose(actual[1:], expected_field, rtol=2e-12, atol=2e-14)


def test_sheet_jump_and_principal_value():
    center = TRIANGLE.mean(axis=0)
    observers = center + np.array([[0., 0., 1e-9], [0., 0., -1e-9], [0., 0., 0.]])
    current = np.array([[[1.3, -0.7]]])
    field = evaluate_field(observers, TRIANGLE[None], current)[0]
    expected = MU0 * np.array([-0.7, -1.3, 0.])
    np.testing.assert_allclose(field[0] - field[1], expected, rtol=1e-8, atol=1e-12)
    np.testing.assert_allclose(field[2], (field[0] + field[1]) / 2, atol=1e-12)


def boundary_self_integral(vertices):
    nodes, weights = np.polynomial.legendre.leggauss(100)
    nodes, weights = (nodes + 1) / 2, weights / 2
    edges = np.roll(vertices, -1, axis=0) - vertices
    lengths = np.linalg.norm(edges, axis=1)
    normals = np.column_stack((edges[:, 1], -edges[:, 0], edges[:, 2])) / lengths[:, None]
    value = -np.sum(lengths ** 3) / 3
    for first in range(3):
        second = (first + 1) % 3
        away_first = -edges[first]
        away_second = edges[second]
        integrand = (np.linalg.norm(away_first - nodes[:, None] * away_second, axis=1)
                     + np.linalg.norm(nodes[:, None] * away_first - away_second, axis=1))
        pair = lengths[first] * lengths[second] * np.dot(weights, integrand) / 3
        value -= 2 * np.dot(normals[first], normals[second]) * pair
    return value


def test_self_energy_against_boundary_reduction():
    exact = boundary_self_integral(TRIANGLE)
    errors = []
    for order in (4, 12, 40):
        barycentric, weights = quadrature(order)
        numeric = integrate_pair(TRIANGLE, TRIANGLE, 0.44, barycentric, weights)
        errors.append(abs(numeric / exact - 1))
    assert errors[2] < errors[1] < errors[0]
    assert errors[2] < 2e-6


def disk_case():
    points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [-1., 0., 0.], [0., -1., 0.]])
    return DeviceCase({'points': points, 'triangles': np.array([[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 1]]),
                       'region': np.array([0, -1, -1, -1, -1]), 'point_film': np.zeros(5, dtype=int),
                       'triangle_film': np.zeros(4, dtype=int), 'lambdas': np.full(4, 0.2),
                       'drive_H': np.zeros((1, 5)), 'vortex_load': np.array([[1., 0., 0., 0., 0.]]),
                       'prescribed_current': np.empty((1, 0)), 'target_fluxoid': np.empty((1, 0)),
                       'observers': np.array([[0., 0., 0.3]])}, {'id': 'disk', 'family': 'test'})


def test_integrated_vortex_load_and_no_holes():
    case = disk_case()
    model = SheetModel(case)
    result = model.solve()
    assert result['inductance'].shape == (0, 0)
    assert result['hole_current'].shape == (1, 0)
    assert result['stream'][0, 0] > 0
    assert result['field'][0, 0, 2] > 0
    np.testing.assert_allclose(result['equilibrium_residual'], 0, atol=1e-13)
    case.data['vortex_load'] *= -0.7
    changed = model.solve(case)
    for key in ('stream', 'current', 'field'):
        np.testing.assert_allclose(changed[key], -0.7 * result[key], atol=1e-13)


def test_permuted_vertex_and_triangle_numbering():
    case = disk_case()
    expected = SheetModel(case).solve()
    permutation = np.array([3, 1, 0, 4, 2])
    inverse = np.argsort(permutation)
    reordered = dict(case.data)
    for key in ('points', 'region', 'point_film'):
        reordered[key] = reordered[key][permutation]
    for key in ('drive_H', 'vortex_load'):
        reordered[key] = reordered[key][:, permutation]
    reordered['triangles'] = inverse[case.triangles[::-1]]
    actual = SheetModel(DeviceCase(reordered, case.meta)).solve()
    np.testing.assert_allclose(actual['stream'][:, inverse], expected['stream'], atol=1e-13)
    np.testing.assert_allclose(actual['current'][:, ::-1], expected['current'], atol=1e-13)
    np.testing.assert_allclose(actual['field'], expected['field'], atol=1e-13)


def test_cross_sheet_adaptive_integral():
    shifted = TRIANGLE + np.array([0.07, -0.04, 0.0001])
    coarse_rule, coarse_weights = quadrature(6)
    fine_rule, fine_weights = quadrature(12)
    reference_rule, reference_weights = quadrature(100)
    actual = adaptive_pair(TRIANGLE, shifted, 0.44, coarse_rule, coarse_weights,
                           fine_rule, fine_weights, 2e-7, 3)
    expected = integrate_pair(TRIANGLE, shifted, 0.44, reference_rule, reference_weights)
    np.testing.assert_allclose(actual, expected, rtol=3e-6)


def annulus_case():
    angles = np.arange(8) * np.pi / 4
    points = np.concatenate([np.column_stack((radius * np.cos(angles), radius * np.sin(angles), np.zeros(8)))
                             for radius in (2., 1.4, 0.8)] + [np.zeros((1, 3))])
    triangles = []
    for ring in (0, 8):
        for index in range(8):
            following = (index + 1) % 8
            triangles.extend([[ring + index, ring + following, ring + following + 8],
                              [ring + index, ring + following + 8, ring + index + 8]])
    triangles.extend([[24, 16 + index, 16 + (index + 1) % 8] for index in range(8)])
    return DeviceCase({'points': points, 'triangles': np.array(triangles),
                       'region': np.repeat([-1, 0, 1], [8, 8, 9]), 'point_film': np.zeros(25, dtype=int),
                       'triangle_film': np.zeros(40, dtype=int), 'lambdas': np.repeat([0.2, 0.], [32, 8]),
                       'drive_H': np.array([np.zeros(25), np.full(25, 0.02)]),
                       'vortex_load': np.zeros((2, 25)), 'prescribed_current': np.array([[1.], [np.nan]]),
                       'target_fluxoid': np.array([[0.], [0.3]]), 'observers': np.array([[0., 0., 0.1]])},
                      {'id': 'annulus', 'family': 'test'})


def test_hole_constraints_and_energy_conjugacy():
    case = annulus_case()
    model = SheetModel(case)
    actual = model.solve()
    np.testing.assert_allclose(actual['hole_current'][0], 1.)
    np.testing.assert_allclose(actual['fluxoid'][1], 0.3, atol=1e-14)
    np.testing.assert_allclose(actual['fluxoid'][0], actual['inductance'][:, 0], atol=1e-14)
    np.testing.assert_allclose(actual['current'][:, -8:], 0., atol=0.)
    assert np.linalg.eigvalsh(model.matrix).min() > 0
    perturbed = DeviceCase(dict(case.data), case.meta)
    perturbed.data['prescribed_current'] = actual['hole_current'] + 1e-4
    perturbed_result = model.solve(perturbed)
    np.testing.assert_allclose(perturbed_result['fluxoid'] - actual['fluxoid'],
                               np.tile(1e-4 * actual['inductance'][:, 0], (2, 1)), atol=1e-13)
