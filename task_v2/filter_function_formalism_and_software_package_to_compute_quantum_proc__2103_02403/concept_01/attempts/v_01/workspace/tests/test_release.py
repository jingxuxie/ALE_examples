import copy

import numpy as np
from scipy.linalg import expm

from pipeline.physics import ideal_channel, liouvillian
from pipeline.predictor import hierarchy, predict, prepare, response, static_quadrature


def simple_case(kind='static', sigma=0.63, rate=0.7):
    case = dict(case_id='synthetic', noise=dict(kind=kind, sigma=[sigma],
                                             rates=[rate], mixing=[[1.0]]))
    arrays = dict(dt=np.array([1.3]), H=np.zeros((1, 2, 2), complex),
                  operators=np.array([np.diag([0.5, -0.5])]), sensitivity=np.ones((1, 1)),
                  blocks=np.array([0, 1]), computational=np.arange(2))
    return case, arrays


def noncommuting_case(kind='static'):
    case, arrays = simple_case(kind)
    arrays.update(dt=np.array([0.4, 0.7, 0.5]),
                  H=np.array([[[0.3, 0.6j], [-0.6j, -0.3]],
                              [[0.1, 0.7], [0.7, -0.1]],
                              [[0.5, 0.1 - 0.4j], [0.1 + 0.4j, -0.5]]]),
                  sensitivity=np.array([[1.0], [0.4], [-0.8]]), blocks=np.array([0, 1, 3]))
    return case, arrays


def test_static_gaussian_analytic():
    case, arrays = simple_case()
    channel, quadratic, diagnostics = predict(case, arrays)
    variance = (0.63 * 1.3) ** 2
    np.testing.assert_allclose(channel, np.diag([1, np.exp(-variance / 2),
                                               np.exp(-variance / 2), 1]), atol=2e-12)
    np.testing.assert_allclose(quadratic, np.diag([0, -variance / 2, -variance / 2, 0]), atol=2e-13)


def test_ou_commuting_analytic():
    case, arrays = simple_case('ou')
    channel, quadratic, diagnostics = predict(case, arrays)
    variance_half = 0.63 ** 2 * (1.3 / 0.7 + np.expm1(-0.7 * 1.3) / 0.7 ** 2)
    np.testing.assert_allclose(channel, np.diag([1, np.exp(-variance_half),
                                               np.exp(-variance_half), 1]), atol=2e-10)
    np.testing.assert_allclose(quadratic, np.diag([0, -variance_half, -variance_half, 0]), atol=2e-13)


def test_telegraph_analytic():
    case, arrays = simple_case('telegraph', sigma=1.1, rate=0.3)
    channel, quadratic, diagnostics = predict(case, arrays)
    root = np.sqrt(0.3 ** 2 - 1.1 ** 2 + 0j)
    coherence = (np.exp(-0.3 * 1.3) * (np.cosh(root * 1.3)
                                      + 0.3 / root * np.sinh(root * 1.3))).real
    np.testing.assert_allclose(channel, np.diag([1, coherence, coherence, 1]), atol=2e-13)
    variance_half = 1.1 ** 2 * (1.3 / 0.6 + np.expm1(-0.6 * 1.3) / 0.6 ** 2)
    np.testing.assert_allclose(quadratic, np.diag([0, -variance_half, -variance_half, 0]), atol=2e-13)


def test_white_analytic_and_factor():
    case, arrays = simple_case('white')
    channel, quadratic, diagnostics = predict(case, arrays)
    decay = 0.63 ** 2 * 1.3 / 2
    np.testing.assert_allclose(channel, np.diag([1, np.exp(-decay), np.exp(-decay), 1]), atol=2e-13)
    np.testing.assert_allclose(quadratic, np.diag([0, -decay, -decay, 0]), atol=2e-13)


def test_initial_frame_quadratic_finite_difference():
    case, arrays = noncommuting_case()
    operators, rates = prepare(case, arrays)
    quadratic = response(arrays, operators, rates)
    ideal = ideal_channel(arrays)
    estimates = []
    for scale in [0.02, 0.01]:
        channel, count = static_quadrature(arrays, operators * scale, 14)
        estimates.append((ideal.conj().T @ channel - np.eye(4)) / scale ** 2)
    extrapolated = (4 * estimates[1] - estimates[0]) / 3
    np.testing.assert_allclose(quadratic, extrapolated, atol=5e-10, rtol=5e-8)
    assert np.linalg.norm(quadratic - quadratic.conj().T) > 0.02


def test_gate_partition_and_segment_invariance():
    for kind in ['static', 'ou', 'telegraph', 'white', 'broadband']:
        case, arrays = noncommuting_case(kind)
        channel, quadratic, diagnostics = predict(case, arrays)
        repartitioned = dict(arrays, blocks=np.array([0, 3]))
        other, other_quadratic, diagnostics = predict(case, repartitioned)
        np.testing.assert_allclose(channel, other, atol=2e-12)
        np.testing.assert_allclose(quadratic, other_quadratic, atol=2e-12)
        subdivided = dict(arrays, dt=np.repeat(arrays['dt'] / 2, 2),
                          H=np.repeat(arrays['H'], 2, axis=0),
                          sensitivity=np.repeat(arrays['sensitivity'], 2, axis=0),
                          blocks=arrays['blocks'] * 2)
        other, other_quadratic, diagnostics = predict(case, subdivided)
        np.testing.assert_allclose(channel, other, atol=3e-11)
        np.testing.assert_allclose(quadratic, other_quadratic, atol=3e-11)


def test_white_memory_reset_invariance():
    case, arrays = noncommuting_case('white')
    channel, quadratic, diagnostics = predict(case, arrays)
    other, other_quadratic, diagnostics = predict(case, arrays, 'no_memory')
    np.testing.assert_allclose(channel, other, atol=2e-13)
    np.testing.assert_allclose(quadratic, other_quadratic, atol=2e-13)


def test_same_covariance_different_noise_law():
    case, arrays = simple_case('telegraph', sigma=1.1, rate=0.3)
    telegraph, telegraph_quadratic, diagnostics = predict(case, arrays)
    gaussian_case = copy.deepcopy(case)
    gaussian_case['noise'].update(kind='ou', rates=[0.6])
    gaussian, gaussian_quadratic, diagnostics = predict(gaussian_case, arrays)
    np.testing.assert_allclose(telegraph_quadratic, gaussian_quadratic, atol=2e-13)
    assert np.linalg.norm(telegraph - gaussian) > 0.06


def test_correlated_latents_and_identity_noise():
    case, arrays = noncommuting_case()
    case['noise'].update(sigma=[0.4, 0.3, 0.5], mixing=[[1, -2, 0.5]])
    channel, quadratic, diagnostics = predict(case, arrays)
    single = copy.deepcopy(case)
    single['noise'].update(sigma=[np.sqrt(0.4 ** 2 + 0.6 ** 2 + 0.25 ** 2)], mixing=[[1]])
    other, other_quadratic, diagnostics = predict(single, arrays)
    np.testing.assert_allclose(channel, other, atol=2e-12)
    np.testing.assert_allclose(quadratic, other_quadratic, atol=2e-12)
    shifted = dict(arrays, operators=arrays['operators'] + 4.3 * np.eye(2))
    other, other_quadratic, diagnostics = predict(case, shifted)
    np.testing.assert_allclose(channel, other, atol=2e-12)
    np.testing.assert_allclose(quadratic, other_quadratic, atol=2e-12)


def test_complex_hamiltonian_vectorization():
    case, arrays = noncommuting_case()
    control = arrays['H'][0]
    duration = 0.43
    unitary = expm(-1j * control * duration)
    np.testing.assert_allclose(expm(liouvillian(control) * duration),
                               np.kron(unitary.conj(), unitary), atol=2e-14)


def test_leakage_not_projected_away():
    case, arrays = simple_case('static', sigma=0.37)
    arrays.update(H=np.zeros((1, 3, 3)), computational=np.array([0, 1]),
                  operators=np.array([[[0, 0, 0.5], [0, 0, 0], [0.5, 0, 0]]]))
    channel, quadratic, diagnostics = predict(case, arrays)
    assert channel.shape == (9, 9)
    state = np.diag([0.5, 0.5, 0]).reshape(-1, order='F')
    final = (channel @ state).reshape((3, 3), order='F')
    expected = (1 - np.exp(-(0.37 * 1.3) ** 2 / 2)) / 4
    np.testing.assert_allclose(final[2, 2], expected, atol=2e-13)


def test_zero_noise():
    case, arrays = noncommuting_case()
    case['noise']['sigma'] = [0.0]
    channel, quadratic, diagnostics = predict(case, arrays)
    np.testing.assert_allclose(channel, ideal_channel(arrays), atol=2e-14)
    np.testing.assert_allclose(quadratic, np.zeros((4, 4)), atol=2e-14)


def test_multiple_telegraph_components():
    case, arrays = simple_case('telegraph')
    case['noise'].update(sigma=[0.35, 0.4, 0.25], rates=[0.3, 0.7, 1.1],
                         mixing=[[1, -0.8, 0.6]])
    channel, quadratic, diagnostics = predict(case, arrays)
    coherence = 1.0
    for sigma, rate, mixing in zip(case['noise']['sigma'], case['noise']['rates'],
                                   case['noise']['mixing'][0]):
        root = np.sqrt(rate ** 2 - (sigma * mixing) ** 2 + 0j)
        coherence *= np.exp(-rate * 1.3) * (np.cosh(root * 1.3)
                                           + rate / root * np.sinh(root * 1.3))
    np.testing.assert_allclose(channel, np.diag([1, coherence, coherence, 1]), atol=2e-13)


def test_hermite_and_quadrature_independent_methods():
    case, arrays = noncommuting_case()
    operators, rates = prepare(case, arrays)
    quadrature, count = static_quadrature(arrays, operators, 20)
    hermite, count = hierarchy(arrays, operators, rates, 14)
    np.testing.assert_allclose(quadrature, hermite, atol=3e-12)
