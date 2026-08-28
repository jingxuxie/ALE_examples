import os
import time

import solve
import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import expm


def potential(links, weights, time_value):
    basis = np.array([1, np.sin(2 * np.pi * time_value),
                      np.cos(2 * np.pi * time_value)])
    total = 0.0
    for path, coefficient in zip(solve.PATHS, weights):
        position = [0, 0]
        product = np.broadcast_to(np.eye(links.shape[-1]),
                                  links.shape[:2] + links.shape[-2:])
        for edge in path:
            axis = abs(edge) - 1
            if edge < 0:
                position[axis] -= 1
            factor = np.roll(links[:, :, axis],
                             tuple(-value for value in position), axis=(0, 1))
            if edge < 0:
                factor = factor.conj().swapaxes(-1, -2)
            product = product @ factor
            if edge > 0:
                position[axis] += 1
        trace = np.trace(product, axis1=-2, axis2=-1) / links.shape[-1]
        square = np.trace(product @ product, axis1=-2,
                          axis2=-1).real / links.shape[-1]
        features = np.stack((trace.real, trace.real**2, trace.imag**2,
                             square), axis=-1)
        total += np.sum(features * (basis @ coefficient))
    return total


def components(vector, generators):
    gram = -np.einsum('aij,bji->ab', generators, generators).real
    pairing = -np.einsum('aij,...ji->...a', generators, vector).real
    return pairing @ np.linalg.inv(gram)


def force_check(data, result):
    links = data['links']
    generators = data['generators']
    value = potential(links, data['weights'], data['t0'])
    step = 0.001
    derivative = np.empty(links.shape[:3] + (len(generators),))
    divergence = 0.0
    transformations = [[expm(multiplier * step * generator)
                         for multiplier in (-2, -1, 1, 2)]
                       for generator in generators]
    for location in np.ndindex(links.shape[:3]):
        for generator_index, transforms in enumerate(transformations):
            samples = []
            for transform in transforms:
                perturbed = links.copy()
                perturbed[location] = transform @ links[location]
                samples.append(potential(perturbed, data['weights'], data['t0']))
            minus2, minus1, plus1, plus2 = samples
            derivative[location + (generator_index,)] = (
                minus2 - 8 * minus1 + 8 * plus1 - plus2) / (12 * step)
            divergence += (-minus2 + 16 * minus1 - 30 * value +
                           16 * plus1 - plus2) / (12 * step**2)
    vector_components = components(result['vector'], generators)
    force_error = np.linalg.norm(vector_components - derivative) / max(
        np.linalg.norm(derivative), 1e-12)
    divergence_error = abs(divergence - result['divergence']) / max(
        abs(divergence), 1)
    print('force/divergence errors', force_error, divergence_error, flush=True)
    assert force_error < 2e-7
    assert divergence_error < 2e-7


def transport_checks(data, result, check_reverse=True, step=1e-5):
    field_type = solve.AbelianField if data['links'].shape[-1] == 1 else solve.MatrixField
    field = field_type(data['links'].shape, data['generators'])
    rng = np.random.default_rng(723)

    def integrate(links, weights, start, end):
        initial = field.pack(links)
        trajectory = solve_ivp(
            lambda time_value, state: np.asarray(field.rhs(time_value, state, weights)),
            (start, end), initial, method='DOP853', rtol=1e-11, atol=1e-13)
        assert trajectory.success
        final = trajectory.y[:, -1]
        state = field.final_state(final)
        objective = np.vdot(data['probe'], state).real + data['density_weight'] * final[-1]
        return state, final[-1], objective

    state, density, _ = integrate(data['links'], data['weights'],
                                 data['t0'], data['t1'])
    print('state/density refinement', np.linalg.norm(state - result['state']),
          abs(density - result['log_density']), flush=True)
    assert np.linalg.norm(state - result['state']) < 2e-7
    assert abs(density - result['log_density']) < 2e-7
    if check_reverse:
        reverse, reverse_density, _ = integrate(state, data['weights'],
                                                data['t1'], data['t0'])
        print('reverse state/density', np.linalg.norm(reverse - data['links']),
              abs(density + reverse_density), flush=True)
        assert np.linalg.norm(reverse - data['links']) < 2e-7
        assert abs(density + reverse_density) < 2e-7

    direction = rng.normal(size=data['weights'].shape)
    samples = [integrate(data['links'], data['weights'] + sign * step * direction,
                         data['t0'], data['t1'])[2] for sign in (-2, -1, 1, 2)]
    numerical = (samples[0] - 8 * samples[1] + 8 * samples[2] - samples[3]) / (12 * step)
    analytic = np.sum(direction * result['weight_gradient'])
    print('weight sensitivity', numerical, analytic,
          abs(numerical - analytic), flush=True)
    assert abs(numerical - analytic) < 2e-6 * max(abs(numerical), 1)

    direction = rng.normal(size=data['links'].shape[:3] + (len(data['generators']),))
    tangent = np.einsum('...a,aij->...ij', direction, data['generators'])
    samples = [integrate(expm(sign * step * tangent) @ data['links'], data['weights'],
                         data['t0'], data['t1'])[2] for sign in (-2, -1, 1, 2)]
    numerical = (samples[0] - 8 * samples[1] + 8 * samples[2] - samples[3]) / (12 * step)
    analytic = np.sum(direction * components(result['initial_gradient'], data['generators']))
    print('initial sensitivity', numerical, analytic,
          abs(numerical - analytic), flush=True)
    assert abs(numerical - analytic) < 2e-6 * max(abs(numerical), 1)
    state = result['state']
    unitarity = np.max(np.abs(state @ state.conj().swapaxes(-1, -2) -
                              np.eye(state.shape[-1])))
    determinant = np.max(np.abs(np.linalg.det(state) - 1)) if state.shape[-1] > 1 else 0
    print('group errors', unitarity, determinant, flush=True)
    assert max(unitarity, determinant) < 1e-12


def make_case(dimension, shape, anisotropic=False, reverse=False):
    rng = np.random.default_rng(90210 + dimension)
    if dimension == 1:
        generators = np.array([[[1.7j]]])
    elif dimension == 2:
        generators = np.array([[[0, 1j], [1j, 0]], [[0, 1], [-1, 0]],
                                [[1j, 0], [0, -1j]]])
    else:
        generators = np.load(os.environ['PART'] + '/input/smoke_1.npz')['generators']
    if anisotropic:
        mixing = np.eye(len(generators)) + 0.1 * rng.normal(
            size=(len(generators), len(generators)))
        generators = np.einsum('ab,bij->aij', mixing, generators)
    tangent = np.einsum('...a,aij->...ij', rng.normal(size=shape + (2, len(generators))),
                         generators)
    links = expm(tangent)
    probe = rng.normal(size=links.shape) + 1j * rng.normal(size=links.shape)
    probe /= np.linalg.norm(probe)
    return dict(links=links, generators=generators,
                weights=rng.normal(scale=0.09, size=(3, 3, 4)), probe=probe,
                t0=np.array(0.9 if reverse else -0.2),
                t1=np.array(0.35 if reverse else 0.35), density_weight=np.array(0.017))


def identity_checks(dimension, anisotropic=False):
    data = make_case(dimension, (4, 5), anisotropic, True)
    data['links'] = np.broadcast_to(np.eye(dimension, dtype=complex), data['links'].shape).copy()
    data['weights'] *= 0.25
    start, end = data['t0'], data['t1']
    integrals = np.array([end - start,
                          (np.cos(2 * np.pi * start) - np.cos(2 * np.pi * end)) / (2 * np.pi),
                          (np.sin(2 * np.pi * end) - np.sin(2 * np.pi * start)) / (2 * np.pi)])
    basis = np.array([1, np.sin(2 * np.pi * start), np.cos(2 * np.pi * start)])
    feature = np.array([1, 2, -2 if dimension == 1 else 0, 4])
    integrated_coefficients = np.einsum('t,ptf->pf', integrals, data['weights']) @ feature
    coefficients = np.einsum('t,ptf->pf', basis, data['weights']) @ feature
    generators = data['generators']
    gram = -np.einsum('aij,bji->ab', generators, generators).real
    casimir = np.trace(gram) / dimension
    shape = data['links'].shape[:2]
    volume = np.prod(shape)
    laplacians = []
    for path in solve.PATHS:
        incidence = np.zeros((volume, 2 * volume))
        for start_site in np.ndindex(shape):
            row = np.ravel_multi_index(start_site, shape)
            position = list(start_site)
            for edge in path:
                axis = abs(edge) - 1
                sign = 1 if edge > 0 else -1
                if edge < 0:
                    position[axis] -= 1
                location = (position[0] % shape[0], position[1] % shape[1], axis)
                incidence[row, np.ravel_multi_index(location, shape + (2,))] += sign
                if edge > 0:
                    position[axis] += 1
        laplacians.append(incidence.T @ incidence)
    for first in laplacians:
        for second in laplacians:
            assert np.linalg.norm(first @ second - second @ first) < 1e-10
    hessian_integral = -np.kron(sum(coefficient * laplacian for coefficient, laplacian in
                                    zip(integrated_coefficients, laplacians)), gram) / dimension
    terminal = np.einsum('...ij,aij->...a', data['probe'].conj(), generators).real
    initial_components = (expm(hessian_integral) @ terminal.ravel()).reshape(terminal.shape)
    initial_gradient = np.einsum('...a,aij->...ij', initial_components, generators)
    lengths = np.array([len(path) for path in solve.PATHS])
    references = {
        'vector': np.zeros_like(data['links']),
        'divergence': -volume * casimir * np.dot(lengths, coefficients),
        'state': data['links'],
        'log_density': volume * casimir * np.dot(lengths, integrated_coefficients),
        'weight_gradient': data['density_weight'] * volume * casimir *
                           lengths[:, None, None] * integrals[None, :, None] * feature[None, None, :],
        'initial_gradient': initial_gradient,
    }
    result = solve.solve(data)
    for key, expected in references.items():
        error = np.linalg.norm(result[key] - expected) / max(np.linalg.norm(expected), 1)
        print('identity', dimension, anisotropic, key, error, flush=True)
        assert error < 2e-8


if __name__ == '__main__':
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'smoke'
    if mode == 'smoke':
        for index in range(2):
            print('SMOKE', index, flush=True)
            data = dict(np.load(os.environ['PART'] + f'/input/smoke_{index}.npz'))
            result = dict(np.load(f'smoke_{index}_out.npz'))
            force_check(data, result)
            transport_checks(data, result)
    elif mode == 'generate':
        for dimension in (1, 2, 3):
            for anisotropic in ((False,) if dimension == 1 else (False, True)):
                name = f'case_{dimension}_{"general" if anisotropic else "iso"}'
                np.savez(name + '.npz', **make_case(dimension, (4, 5), anisotropic, True))
        for dimension in (1, 2, 3):
            np.savez(f'large_{dimension}.npz', **make_case(dimension, (16, 16), False, True))
        np.savez('large_general.npz', **make_case(3, (16, 16), True, True))
    elif mode == 'case':
        name = sys.argv[2]
        data = dict(np.load(name + '.npz'))
        result = dict(np.load(name + '_out.npz'))
        force_check(data, result)
        transport_checks(data, result)
    elif mode == 'large':
        for name in ('large_1', 'large_2', 'large_3', 'large_general'):
            print('FULL-SIZE VALIDATION', name, flush=True)
            data = dict(np.load(name + '.npz'))
            result = dict(np.load(name + '_out.npz'))
            transport_checks(data, result, check_reverse=False, step=1e-6)
    elif mode == 'identity':
        for dimension in (1, 2, 3):
            identity_checks(dimension)
        identity_checks(3, True)
