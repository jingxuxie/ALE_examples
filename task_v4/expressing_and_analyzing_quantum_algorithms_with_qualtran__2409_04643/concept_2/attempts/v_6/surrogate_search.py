import argparse
import json
import time
from pathlib import Path

import mpmath as mp
import numpy as np

from batch_search import batch_complement
from robust_search import score
from search import dump
from target_method import fft_complementary_polynomial


def accurate_complement(polynomial):
    initial = fft_complementary_polynomial(polynomial, tolerance=0, num_modes=4096)
    target = [mp.mpc(float(value.real), float(value.imag)) for value in polynomial]
    complement = [mp.mpc(float(value.real), float(value.imag)) for value in initial]
    complement[0] = mp.mpc(complement[0].real)
    length = len(target)
    variables = [(0, False)] + [(index, imaginary) for index in range(1, length) for imaginary in (False, True)]
    for iteration in range(4):
        residual = [sum(abs(value) ** 2 for value in target + complement) - 1]
        for lag in range(1, length):
            correlation = sum(array[index + lag] * mp.conj(array[index]) for array in (target, complement) for index in range(length - lag))
            residual.extend([correlation.real, correlation.imag])
        jacobian = mp.matrix(2 * length - 1)
        for column, (index, imaginary) in enumerate(variables):
            jacobian[0, column] = 2 * (complement[index].imag if imaginary else complement[index].real)
            for lag in range(1, length):
                derivative = mp.mpc(0)
                if index >= lag:
                    derivative += (1j if imaginary else 1) * mp.conj(complement[index - lag])
                if index + lag < length:
                    derivative += (-1j if imaginary else 1) * complement[index + lag]
                jacobian[2 * lag - 1, column] = derivative.real
                jacobian[2 * lag, column] = derivative.imag
        correction = mp.lu_solve(jacobian, mp.matrix(residual))
        for column, (index, imaginary) in enumerate(variables):
            complement[index] -= (1j if imaginary else 1) * correction[column]
    return target, complement


def extended(value):
    return np.clongdouble(np.longdouble(str(mp.re(value)))) + np.clongdouble(1j) * np.longdouble(str(mp.im(value)))


def linearization(polynomial):
    with mp.workdps(80):
        target, complement = accurate_complement(polynomial)
        length = len(polynomial)
        state = mp.matrix([target, complement])
        base = np.array([extended(value) for value in target + complement], dtype=np.clongdouble)
        tangent = np.zeros((2, length, 4 * length), dtype=np.clongdouble)
        for row in range(2):
            for index in range(length):
                tangent[row, index, 2 * (row * length + index)] = 1
                tangent[row, index, 2 * (row * length + index) + 1] = 1j
        losses = []
        for degree in reversed(range(1, length)):
            precise_norm = mp.sqrt(abs(state[0, degree]) ** 2 + abs(state[1, degree]) ** 2)
            direction = [state[row, degree] / precise_norm for row in range(2)]
            precise_rotation = mp.matrix([[direction[0], -mp.conj(direction[1])], [direction[1], mp.conj(direction[0])]])
            approximate_state = np.array([[extended(state[row, index]) for index in range(degree + 1)] for row in range(2)])
            rotation = np.array([[extended(precise_rotation[row, column]) for column in range(2)] for row in range(2)])
            leading = approximate_state[:, -1]
            norm = np.longdouble(str(precise_norm))
            leading_tangent = tangent[:, -1, :]
            norm_tangent = np.real(leading.conj() @ leading_tangent) / norm
            direction_tangent = leading_tangent / norm - np.outer(leading, norm_tangent) / norm ** 2
            rotation_tangent = np.array([[direction_tangent[0], -direction_tangent[1].conj()], [direction_tangent[1], direction_tangent[0].conj()]])
            tangent = np.einsum('ij,jkn->ikn', rotation.conj().T, tangent) + np.einsum('jin,jk->ikn', rotation_tangent.conj(), approximate_state)
            losses.append(tangent[0, 0].copy())
            tangent = np.array([tangent[0, 1:], tangent[1, :-1]])
            state = precise_rotation.H * state
            state = mp.matrix([[state[0, index + 1] for index in range(degree)], [state[1, index] for index in range(degree)]])
        return base, np.array(losses)


def predict(polynomials, complements, model):
    base, jacobian = model
    deviation = np.concatenate((polynomials, complements), axis=-1).astype(np.clongdouble) - base
    losses = np.einsum('bi,ji->bj', deviation.view(np.longdouble), jacobian)
    return np.sqrt(np.sum(np.abs(losses) ** 2, axis=-1)).astype(float)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=12000)
    parser.add_argument('--batches', type=int, default=10000)
    parser.add_argument('--batch-size', type=int, default=256)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    candidates = []
    for prefix in ['ulp', 'batch', 'surrogate']:
        for path in Path('.').glob(prefix + '-*.json'):
            polynomial = np.array([complex(*pair) for pair in json.loads(path.read_text())['P']])
            minimum, errors = score(polynomial, 0)
            candidates.append((minimum, polynomial, errors))
    best = max(candidates, key=lambda item: item[0])
    population = [best]
    maximum = best[0]
    gauge_factor = np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(13)))
    gauged = best[1].copy()
    gauged *= gauge_factor
    models = [linearization(best[1]), linearization(gauged)]
    configurations = [(8192, 0), (16384, 0), (16384, 1), (8192, 1), (4096, 0), (4096, 1)]
    predicted = []
    for modes, gauge in configurations:
        transformed = np.array([gauged if gauge else best[1]])
        predicted.append(float(predict(transformed, batch_complement(transformed, modes), models[gauge])[0]))
    print('CALIBRATION', 'actual', best[2], 'predicted', predicted, flush=True)
    if args.check:
        return
    started = time.monotonic()
    for batch in range(args.batches):
        polynomials = np.array([population[rng.integers(min(len(population), 32))][1] for _ in range(args.batch_size)])
        components = polynomials.view(np.float64)
        probabilities = rng.choice([1, 1, 2, 2, 3, 6, 13, 26], size=len(polynomials)) / 26
        mask = rng.random(components.shape) < probabilities[:, None]
        mask[np.arange(len(polynomials)), rng.integers(26, size=len(polynomials))] = True
        steps = rng.choice([-1.0, 1.0], size=components.shape) * 2.0 ** rng.integers(0, 14, size=components.shape)
        components += mask * steps * np.abs(np.spacing(components))
        indices = np.arange(len(polynomials))
        for modes, gauge in configurations:
            if len(indices) == 0:
                break
            transformed = polynomials[indices].copy()
            if gauge:
                for row in transformed:
                    row *= gauge_factor
            complements = batch_complement(transformed, modes)
            errors = predict(transformed, complements, models[gauge])
            indices = indices[errors >= maximum * 0.90]
        for index in indices:
            value, errors = score(polynomials[index], maximum * 0.90)
            if value >= maximum * 0.90:
                population.append((value, polynomials[index].copy(), errors))
            if value > maximum:
                maximum = value
                dump(polynomials[index], f'surrogate-{args.seed}.json')
                print('BEST', args.seed, batch, maximum, errors, 'time', time.monotonic() - started, flush=True)
        population.sort(key=lambda item: item[0], reverse=True)
        population = population[:64]
        if batch % 100 == 0:
            print('PROGRESS', args.seed, batch, maximum, 'survivors', len(indices), time.monotonic() - started, flush=True)
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
