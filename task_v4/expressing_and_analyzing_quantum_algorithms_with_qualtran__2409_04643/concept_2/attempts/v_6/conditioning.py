import argparse
import time

import numpy as np

from search import dump
from target_method import fft_complementary_polynomial


def sensitivity(polynomial, complement):
    state = np.array([polynomial, complement], dtype=np.clongdouble)
    tangent = np.zeros((2, len(polynomial), 2), dtype=np.clongdouble)
    tangent[1, -1, 0] = 1
    tangent[1, -1, 1] = 1j
    losses = []
    for degree in reversed(range(1, len(polynomial))):
        leading = state[:, -1]
        leading_tangent = tangent[:, -1, :]
        norm = np.sqrt(np.vdot(leading, leading).real)
        norm_tangent = np.real(leading.conj() @ leading_tangent) / norm
        direction = leading / norm
        direction_tangent = leading_tangent / norm - np.outer(leading, norm_tangent) / norm ** 2
        rotation = np.array([[direction[0], -direction[1].conjugate()], [direction[1], direction[0].conjugate()]])
        rotation_tangent = np.array([[direction_tangent[0], -direction_tangent[1].conj()], [direction_tangent[1], direction_tangent[0].conj()]])
        tangent = np.einsum('ij,jkn->ikn', rotation.conj().T, tangent) + np.einsum('jin,jk->ikn', rotation_tangent.conj(), state)
        state = rotation.conj().T @ state
        losses.append(tangent[0, 0].copy())
        state = np.array([state[0, 1:], state[1, :-1]])
        tangent = np.array([tangent[0, 1:], tangent[1, :-1]])
    return np.linalg.norm(np.array(losses), axis=0).astype(float)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=50)
    parser.add_argument('--count', type=int, default=10000)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    maximum = 0
    started = time.monotonic()
    for trial in range(args.count):
        polynomial = np.exp(1j * rng.uniform(-np.pi, np.pi, 13))
        polynomial[11] *= rng.uniform(11.5, 13.69)
        secondary = rng.integers(0, 11)
        polynomial[secondary] *= rng.uniform(3.5, 5.5)
        polynomial[secondary] = abs(polynomial[secondary]) * 1j * polynomial[11] / abs(polynomial[11])
        energy = np.vdot(polynomial, polynomial).real
        if min(abs(polynomial)) < 0.25 * np.sqrt(energy / len(polynomial)) or abs(np.sum(polynomial ** 2)) > 0.8 * energy:
            continue
        polynomial *= np.sqrt(rng.uniform(0.08, 0.30) / energy)
        if np.max(abs(np.fft.fft(polynomial, 4096))) > 0.797:
            continue
        complement = fft_complementary_polynomial(polynomial, tolerance=0, num_modes=4096)
        gain = max(sensitivity(polynomial, complement))
        if gain > maximum:
            maximum = gain
            dump(polynomial, f'condition-{args.seed}.json')
            print('BEST', args.seed, trial, gain, 'energy', np.vdot(polynomial, polynomial).real, 'secondary', secondary, 'mags', abs(polynomial), 'time', time.monotonic() - started, flush=True)
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
