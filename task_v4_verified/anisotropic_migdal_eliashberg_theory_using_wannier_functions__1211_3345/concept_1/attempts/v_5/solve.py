import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import argparse
import time
import numpy as np
from scipy.sparse.linalg import LinearOperator, gmres
from scipy.sparse.csgraph import connected_components
from scipy.interpolate import CubicSpline
from fast_model import Model


class BudgetStop(Exception):
    def __init__(self, delta, renormalization):
        self.result = delta, renormalization


def solve(instance, verbose=False, budget=10.5, use_coarse=True, normal_z=None):
    try:
        return solve_inner(instance, verbose, budget, use_coarse, normal_z)
    except BudgetStop as error:
        return error.result


def solve_inner(instance, verbose, budget, use_coarse, normal_z):
    started = time.process_time()
    deadline = started + budget
    seed = None
    model = None
    if use_coarse and int(instance['n_freq']) >= 8192:
        coarse = dict(instance)
        coarse_count = min(8192, int(instance['n_freq']) // 4)
        coarse['n_freq'] = coarse_count
        resolved = len(instance['omega']) > 5
        coarse_normal_z = None
        if resolved:
            model = Model(instance)
            tail_weight = 2 * np.sum(1. / (2 * np.arange(coarse_count, model.n_freq) + 1))
            effective_coulomb = np.linalg.solve(np.eye(model.shape[0]) + tail_weight * model.weighted_coulomb,
                                                model.weighted_coulomb)
            coarse['coulomb'] = effective_coulomb / model.weights[None, :]
            coarse['initial_delta'] = instance['initial_delta'][:, :coarse_count].copy()
            coarse_normal_z = model.normal_z[:, :coarse_count]
        else:
            ratio = int(instance['n_freq']) / coarse_count
            coarse['temperature'] = float(instance['temperature']) * ratio
            coarse_positions = (np.arange(coarse_count) + 0.5) * ratio - 0.5
            coarse['initial_delta'] = np.array([np.interp(coarse_positions, np.arange(int(instance['n_freq'])), row)
                                                 for row in instance['initial_delta']])
        coarse_delta, coarse_z = solve(coarse, budget=2.5, use_coarse=False, normal_z=coarse_normal_z)
        if np.max(coarse_delta[:, 0]) > 0.2 * np.pi * coarse['temperature'] and np.all(coarse_delta[:, 0] > 0):
            if resolved:
                coarse_ratio = coarse_delta / np.hypot(model.frequencies[:coarse_count], coarse_delta)
                tail_pair = -2 * np.pi * model.temperature * (effective_coulomb @ coarse_ratio.sum(axis=1))
                matching = coarse_delta[:, -1] * model.normal_z[:, coarse_count - 1] - tail_pair
                seed = np.empty(model.shape)
                seed[:, :coarse_count] = coarse_delta
                seed[:, coarse_count:] = (tail_pair[:, None] + matching[:, None] *
                    (model.frequencies[coarse_count - 1] / model.frequencies[coarse_count:]) ** 2) / model.normal_z[:, coarse_count:]
            else:
                seed = CubicSpline(coarse_positions, coarse_delta, axis=1)(np.arange(int(instance['n_freq'])))
    if model is None:
        model = Model(instance)
    if normal_z is not None:
        model.normal_z = normal_z
    delta = np.array(instance['initial_delta'] if seed is None else seed, order='C', copy=True)
    if np.any(delta[:, 0] <= 0) or not np.all(np.isfinite(delta)):
        seed = None
        phonon_scale = np.max(model.omega)
        delta = np.tile(0.4 * phonon_scale / (1 + (model.frequencies / phonon_scale) ** 2), (model.shape[0], 1))
    renormalization, mapped = model.map(delta)
    if seed is not None:
        integrated = np.sum(instance['coupling'], axis=0)
        diagonal = np.sqrt(np.diag(integrated))
        count, groups = connected_components(integrated > 0.001 * diagonal[:, None] * diagonal[None, :])
        jacobian = model.linearize(delta, renormalization, mapped)
        metric = model.weights[:, None] * renormalization / model.frequencies
        changed = False
        for group in range(count):
            selected = groups == group
            if np.max(delta[selected, 0]) >= np.pi * model.temperature:
                continue
            direction = np.zeros_like(delta)
            direction[selected] = delta[selected]
            change = jacobian(direction)
            quotient = np.sum(direction * change * metric) / np.sum(direction ** 2 * metric)
            if quotient < 0.03:
                delta[selected] *= np.pi * model.temperature / np.max(delta[selected, 0])
                changed = True
        if changed:
            renormalization, mapped = model.map(delta)
    square_weights = np.sqrt(model.weights)
    repulsion = np.linalg.eigvalsh(instance['coulomb'] * square_weights[:, None] * square_weights[None, :])[-1]
    harmonic_sum = np.sum(1. / (2 * np.arange(model.n_freq) + 1))
    mixing = min(0.7, 1.7 / (1 + 2 * repulsion * harmonic_sum))
    for warmup in range(20 if seed is None else 2):
        if time.process_time() > deadline:
            return delta, renormalization
        fraction = mixing
        negative = mapped[:, 0] < 0
        if np.any(negative):
            fraction = min(fraction, 0.9 * np.min(delta[negative, 0] / (delta[negative, 0] - mapped[negative, 0])))
        delta = (1 - fraction) * delta + fraction * mapped
        renormalization, mapped = model.map(delta)
    last_step = np.inf
    regular_steps = 0
    floor = np.pi * model.temperature * 1e-10
    restart = 24 if delta.size > 300000 else 35
    linear_tolerance = 2e-5 if delta.size > 200000 else 2e-7
    for iteration in range(80):
        if time.process_time() > deadline:
            break
        amplitude = delta[:, :1].copy()
        shape = delta / amplitude
        residual = (delta - mapped) / amplitude
        scale = np.maximum(np.max(np.abs(delta), axis=1, keepdims=True), floor)
        norm = np.max(np.abs(delta - mapped) / scale)
        if norm < 1e-9 and last_step < 1e-4:
            break
        jacobian = model.linearize(delta, renormalization, mapped)

        def product(direction):
            if time.process_time() > deadline:
                raise BudgetStop(delta, renormalization)
            direction = direction.reshape(model.shape)
            return (jacobian(amplitude * direction) / amplitude - residual * direction[:, :1]).ravel()

        regular = regular_steps > 0
        deflated_correction = None
        if not regular:
            operator = LinearOperator((delta.size, delta.size), matvec=product, dtype=float)
            correction, info = gmres(operator, -residual.ravel(), tol=linear_tolerance, atol=1e-15,
                                     restart=restart, maxiter=3)
            correction = correction.reshape(model.shape)
            relative = correction[:, :1]
            deflated_correction = correction
            regular = np.min(relative) < -2 or np.max(relative) > 2
        if regular:
            regular_steps = max(0, regular_steps - 1)
            def regular_product(direction):
                if time.process_time() > deadline:
                    raise BudgetStop(delta, renormalization)
                return (jacobian(amplitude * direction.reshape(model.shape)) / amplitude).ravel()
            operator = LinearOperator((delta.size, delta.size), matvec=regular_product, dtype=float)
            correction, info = gmres(operator, -residual.ravel(), tol=linear_tolerance, atol=1e-15,
                                     restart=restart, maxiter=3)
            correction = correction.reshape(model.shape)
            relative = correction[:, :1]
            if np.min(relative) < -1.0001 and deflated_correction is not None:
                correction = deflated_correction
                relative = correction[:, :1]
                regular = False
        if not np.all(np.isfinite(correction)):
            delta = 0.5 * (delta + mapped)
            renormalization, mapped = model.map(delta)
            continue
        if verbose:
            print(iteration, 'norm', norm, 'amplitudes', amplitude.ravel(),
                  'step', relative.ravel(), 'gmres', info, 'calls', model.count,
                  'cpu', time.process_time()-started, flush=True)
        if norm < 1e-11 and np.max(np.abs(correction)) < 1e-5:
            break
        limit = 0.9999 if regular else 0.49
        fraction = min(1., limit / max(limit, float(-np.min(relative))))
        for backtrack in range(12):
            if regular:
                candidate = delta + fraction * amplitude * correction
                next_amplitude = candidate[:, :1]
            else:
                next_amplitude = amplitude * np.sqrt(1 + 2 * fraction * relative)
                candidate = next_amplitude * (shape + fraction * (correction - shape * relative))
            next_z, next_mapped = model.map(candidate)
            next_scale = scale if regular else np.maximum(np.max(np.abs(candidate), axis=1, keepdims=True), floor)
            next_norm = np.max(np.abs(candidate - next_mapped) / next_scale)
            if next_norm < norm * (1 - 0.01 * fraction) or next_norm < 2e-14:
                break
            fraction *= 0.5
        delta, renormalization, mapped = candidate, next_z, next_mapped
        last_step = np.max(np.abs(correction))
        if not regular and fraction < 0.3 and np.max(relative) < 0.1:
            regular_steps = 3
        if time.process_time() - started > budget:
            break
    return delta, renormalization


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as archive:
        instance = {key: np.array(archive[key]) for key in archive.files}
    delta, renormalization = solve(instance, verbose=args.verbose)
    with open(args.output, 'wb') as stream:
        np.savez(stream, delta=delta, z=renormalization)


if __name__ == '__main__':
    main()
