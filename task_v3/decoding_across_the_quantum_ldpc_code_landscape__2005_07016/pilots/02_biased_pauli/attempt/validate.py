import argparse
import os
import time
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np
import solve


FRAMES = np.array([[[1, 0], [0, 1]], [[0, 1], [1, 0]],
                   [[1, 1], [0, 1]], [[1, 0], [1, 1]],
                   [[0, 1], [1, 1]], [[1, 1], [1, 0]]], dtype=np.uint8)


def row_basis(matrix):
    reduced = matrix.copy()
    pivots = []
    rank = 0
    for column in range(matrix.shape[1]):
        candidates = np.flatnonzero(reduced[rank:, column])
        if not len(candidates):
            continue
        selected = rank + candidates[0]
        reduced[[rank, selected]] = reduced[[selected, rank]]
        affected = np.flatnonzero(reduced[:, column])
        affected = affected[affected != rank]
        reduced[affected] ^= reduced[rank]
        pivots.append(column)
        rank += 1
    return reduced[:rank], pivots


def in_span(vectors, basis):
    matrix, pivots = basis
    reduced = vectors ^ ((vectors[:, pivots] @ matrix) & 1)
    return ~np.any(reduced, axis=1)


def make_case(hx, hz, shots, rate, bias, pattern, seed):
    rng = np.random.default_rng(seed)
    size = hx.shape[1]
    frame = FRAMES[rng.integers(6, size=size)]
    permutation = rng.permutation(size)
    if pattern == 'random':
        dominant = rng.integers(1, 4, size=size)
    elif pattern == 'sectors':
        dominant = np.where(np.arange(size) < size // 2, 1, 2)
    elif pattern == 'mixed':
        dominant = rng.integers(1, 4, size=size)
    else:
        dominant = np.full(size, {'x': 1, 'z': 2, 'y': 3}[pattern])
    rates = np.clip(rate * rng.uniform(.9, 1.1, size=size), .01, .16)
    canonical_probs = np.zeros((size, 4))
    canonical_probs[:, 0] = 1 - rates
    canonical_probs[:, 1:] = (rates / (bias + 2))[:, None]
    canonical_probs[np.arange(size), dominant] *= bias
    if pattern == 'mixed':
        weights = np.exp(rng.uniform(0, np.log(bias), size=(size, 3)))
        canonical_probs[:, 1:] = rates[:, None] * weights / weights.sum(axis=1)[:, None]
    uniform = rng.random((shots, size))
    errors = np.sum(uniform[:, :, None] > np.cumsum(canonical_probs, axis=1)[None, :, :], axis=2).astype(np.uint8)
    error_x = errors & 1
    error_z = errors >> 1
    syndrome = np.concatenate(((error_z @ hx.T) & 1, (error_x @ hz.T) & 1), axis=1)
    canonical_gx = np.concatenate((hx, np.zeros_like(hz)), axis=0)
    canonical_gz = np.concatenate((np.zeros_like(hx), hz), axis=0)
    gx, gz = np.empty_like(canonical_gx), np.empty_like(canonical_gz)
    gx[:, permutation] = canonical_gx * frame[:, 0, 0] ^ canonical_gz * frame[:, 0, 1]
    gz[:, permutation] = canonical_gx * frame[:, 1, 0] ^ canonical_gz * frame[:, 1, 1]
    physical_probs = np.empty_like(canonical_probs)
    pauli_index = np.array([0, 1, 3, 2])
    for state in range(4):
        physical_x = (state & 1) * frame[:, 0, 0] ^ (state >> 1) * frame[:, 0, 1]
        physical_z = (state & 1) * frame[:, 1, 0] ^ (state >> 1) * frame[:, 1, 1]
        physical_probs[permutation, pauli_index[physical_x + 2 * physical_z]] = canonical_probs[:, state]
    case = dict(schema_version=np.array(1), base_hx=hx, base_hz=hz, gx=gx, gz=gz,
                frame=frame, permutation=permutation, pauli_probs=physical_probs, syndrome=syndrome)
    return case, error_x, error_z


def check(case, correction_x, correction_z, error_x, error_z, bases):
    actual = ((correction_x @ case['gz'].T) ^ (correction_z @ case['gx'].T)) & 1
    assert np.array_equal(actual, case['syndrome']), 'Syndrome mismatch'
    frame = case['frame']
    physical_x = correction_x[:, case['permutation']]
    physical_z = correction_z[:, case['permutation']]
    canonical_x = physical_x * frame[:, 1, 1] ^ physical_z * frame[:, 0, 1]
    canonical_z = physical_x * frame[:, 1, 0] ^ physical_z * frame[:, 0, 0]
    success_x = in_span(canonical_x ^ error_x, bases[0])
    success_z = in_span(canonical_z ^ error_z, bases[1])
    return success_x & success_z


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--shots', type=int, default=64)
    parser.add_argument('--modes', default='22,100')
    parser.add_argument('--size', default='416,882')
    parser.add_argument('--suite', default='standard')
    parser.add_argument('--save', action='store_true')
    parser.add_argument('--seed', type=int, default=12345)
    args = parser.parse_args()
    parent = Path(__file__).resolve().parent.parent / 'participant' / 'input' / 'codes'
    tests = [(0.08, 10, 'x'), (0.08, 10, 'y'), (0.12, 20, 'random'),
             (0.12, 50, 'y'), (0.08, 1, 'random'), (0.16, 50, 'random')]
    if args.suite == 'hard':
        tests = [(0.12, 10, 'x'), (0.16, 10, 'y'), (0.16, 4, 'random'),
                 (0.12, 1, 'random'), (0.16, 100, 'x'), (0.16, 100, 'y')]
    if args.suite == 'transfer':
        tests = [(0.04, 100, 'mixed'), (0.10, 4, 'sectors'), (0.14, 30, 'sectors'),
                 (0.14, 100, 'mixed'), (0.10, 100, 'random'), (0.15, 2, 'mixed')]
    if args.suite == 'extremes':
        tests = [(0.01, 100, 'mixed'), (0.08, 10, 'z')]
    for size in map(int, args.size.split(',')):
        with np.load(parent / ('lp%d.npz' % size)) as code:
            hx, hz = code['base_hx'], code['base_hz']
        bases = row_basis(hx), row_basis(hz)
        print('code', size, 'k', size - len(bases[0][1]) - len(bases[1][1]), flush=True)
        for test_index, (rate, bias, pattern) in enumerate(tests):
            case, error_x, error_z = make_case(hx, hz, args.shots, rate, bias, pattern, args.seed + test_index + size)
            if args.save:
                np.savez('synthetic_%d_%s_%d.npz' % (size, args.suite, test_index), **case)
            scores, successes = [], []
            for mode in args.modes.split(','):
                os.environ['DECODER_MODE'] = mode
                start = time.process_time()
                correction_x, correction_z = solve.decode(case)
                elapsed = time.process_time() - start
                success = check(case, correction_x, correction_z, error_x, error_z, bases)
                pauli_index = np.array([0, 1, 3, 2])
                states = pauli_index[correction_x + 2 * correction_z]
                scores.append(-np.log(case['pauli_probs'][np.arange(size)[None, :], states]).sum(axis=1))
                successes.append(success)
                print('n=%d p=%.3f bias=%d axis=%s mode=%s success=%d/%d cpu=%.3f' %
                      (size, rate, bias, pattern, mode, success.sum(), args.shots, elapsed), flush=True)
            selected = np.argmin(scores, axis=0)
            successes = np.array(successes)
            print('ensemble min_energy=%d oracle=%d/%d' %
                  (successes[selected, np.arange(args.shots)].sum(), successes.any(axis=0).sum(), args.shots), flush=True)


if __name__ == '__main__':
    main()
