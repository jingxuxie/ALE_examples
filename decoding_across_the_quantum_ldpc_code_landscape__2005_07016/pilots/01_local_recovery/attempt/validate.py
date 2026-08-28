import argparse
import ctypes
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp


def native_decode(parity, priors, syndromes, budget=30):
    parity.eliminate_zeros()
    matrix = parity.tocoo()
    rows = np.ascontiguousarray(matrix.row, dtype=np.int32)
    columns = np.ascontiguousarray(matrix.col, dtype=np.int32)
    priors = np.ascontiguousarray(priors, dtype=np.float64)
    syndromes = np.ascontiguousarray(syndromes, dtype=np.uint8)
    answer = np.zeros((len(syndromes), parity.shape[1]), dtype=np.uint8)
    stats = np.zeros(8, dtype=np.float64)
    library = ctypes.CDLL(str(Path(__file__).resolve().parent / 'decoder_native.so'))
    library.decode.argtypes = [ctypes.c_int] * 4 + [ctypes.c_void_p] * 5 + [ctypes.c_double, ctypes.c_void_p]
    started = time.process_time()
    result = library.decode(*parity.shape, matrix.nnz, len(syndromes), rows.ctypes.data,
                            columns.ctypes.data, priors.ctypes.data, syndromes.ctypes.data,
                            answer.ctypes.data, budget, stats.ctypes.data)
    assert result == 0
    return answer, time.process_time() - started, stats


def weak_decode(parity, priors, syndromes):
    matrix = parity.tocsr()
    columns = matrix.indices
    starts = matrix.indptr[:-1]
    lengths = np.diff(matrix.indptr)
    assert np.all(lengths > 0)
    channel = np.log((1 - priors) / priors)
    answers = []
    for syndrome in syndromes:
        incoming = channel[columns].copy()
        for iteration in range(30):
            magnitudes = np.abs(incoming)
            minimum = np.minimum.reduceat(magnitudes, starts)
            repeated = np.repeat(minimum, lengths)
            minima = magnitudes == repeated
            counts = np.add.reduceat(minima.astype(int), starts)
            second = np.minimum.reduceat(np.where(minima, 40., magnitudes), starts)
            second[counts > 1] = minimum[counts > 1]
            signs = np.where(incoming < 0, -1., 1.)
            parity_sign = np.multiply.reduceat(signs, starts) * (1 - 2 * syndrome.astype(float))
            outgoing = .625 * np.repeat(parity_sign, lengths) * signs * np.where(minima, np.repeat(second, lengths), repeated)
            posterior = channel + np.bincount(columns, weights=outgoing, minlength=matrix.shape[1])
            hard = (posterior < 0).astype(np.uint8)
            if np.array_equal(matrix @ hard % 2, syndrome):
                break
            incoming = np.clip(posterior[columns] - outgoing, -40, 40)
        answers.append(hard)
    return np.array(answers)


def classical(checks, variables, degree, rng):
    rows = np.concatenate([rng.choice(checks, degree, replace=False) for column in range(variables)])
    return sp.coo_matrix((np.ones(len(rows), dtype=np.uint8), (rows, np.repeat(np.arange(variables), degree))), shape=(checks, variables)).tocsr()


def hgp(length, rng):
    first = classical(length // 2, length, 3, rng)
    second = classical(length // 2, length, 3, rng)
    parity = sp.hstack([sp.kron(first, sp.eye(length)), sp.kron(sp.eye(length // 2), second.T)], format='csr', dtype=np.uint8)
    stabilizers = sp.hstack([sp.kron(sp.eye(length), second), sp.kron(first.T, sp.eye(length // 2))], format='csr', dtype=np.uint8)
    return parity, stabilizers


def row_basis(matrix):
    matrix.eliminate_zeros()
    matrix = matrix.tocsr()
    basis = {}
    for row in range(matrix.shape[0]):
        value = sum(1 << int(column) for column in matrix.indices[matrix.indptr[row]:matrix.indptr[row + 1]])
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                break
    return basis


def in_span(vector, basis):
    value = int.from_bytes(np.packbits(vector, bitorder='little').tobytes(), 'little')
    while value:
        pivot = value.bit_length() - 1
        if pivot not in basis:
            return False
        value ^= basis[pivot]
    return True


def toric(length, depth=1):
    supports, logical = [], []
    for layer in range(depth):
        for vertical in range(length):
            for horizontal in range(length):
                node = (layer * length + vertical) * length + horizontal
                supports.append((node, (layer * length + vertical) * length + (horizontal + 1) % length))
                logical.append((horizontal == length - 1, False))
                supports.append((node, (layer * length + (vertical + 1) % length) * length + horizontal))
                logical.append((False, vertical == length - 1))
                if depth > 1:
                    supports.append((node, (((layer + 1) % depth) * length + vertical) * length + horizontal))
                    logical.append((False, False))
    rows = np.array(supports).ravel()
    parity = sp.coo_matrix((np.ones(len(rows), dtype=np.uint8), (rows, np.repeat(np.arange(len(supports)), 2))), shape=(length * length * depth, len(supports))).tocsr()
    return parity, np.array(logical, dtype=np.uint8).T


def run_case(name, parity, priors, shots, rng, stabilizers=None, logical=None, weak=True, budget=25):
    parity.eliminate_zeros()
    actual = (rng.random((shots, parity.shape[1])) < priors).astype(np.uint8)
    syndromes = np.asarray((parity @ actual.T).T % 2, dtype=np.uint8)
    basis = row_basis(stabilizers) if stabilizers is not None else None

    def measure(answer):
        valid = np.all((parity @ answer.T).T % 2 == syndromes, axis=1)
        delta = answer ^ actual
        if basis is not None:
            success = np.array([in_span(vector, basis) for vector in delta])
        elif logical is not None:
            success = np.all(delta @ logical.T % 2 == 0, axis=1)
        else:
            success = np.all(delta == 0, axis=1)
        return int(valid.sum()), int((valid & success).sum()), float(answer.sum(1).mean())

    answer, duration, stats = native_decode(parity, priors, syndromes, budget)
    print(name, parity.shape, 'native', measure(answer), 'cpu', round(duration, 3), 'stats', stats, flush=True)
    assert np.array_equal((parity @ answer.T).T % 2, syndromes), name
    if weak:
        baseline = weak_decode(parity, priors, syndromes)
        print(name, 'weak', measure(baseline), flush=True)
    return answer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--large', action='store_true')
    parser.add_argument('--shots', type=int, default=150)
    args = parser.parse_args()
    rng = np.random.default_rng(85071)
    for length in (12, 24, 40):
        parity, stabilizers = hgp(length, rng)
        run_case('hgp%d' % length, parity, rng.uniform(.015, .045, parity.shape[1]), args.shots, rng, stabilizers=stabilizers)
    for checks, variables, degree, probability in [(72, 180, 6, .022), (120, 300, 3, .025), (300, 1000, 4, .025), (1000, 3000, 4, .025)]:
        parity = classical(checks, variables, degree, rng)
        run_case('sparse%d' % variables, parity, rng.uniform(.5 * probability, 1.5 * probability, variables), args.shots, rng)
    for length, depth, probability in [(7, 1, .06), (11, 1, .07), (7, 5, .015), (11, 7, .015)]:
        parity, logical = toric(length, depth)
        run_case('toric%d-%d' % (length, depth), parity, np.full(parity.shape[1], probability), args.shots, rng, logical=logical)
    if args.large:
        parity, logical = toric(25, 25)
        run_case('large-detector', parity, np.full(parity.shape[1], .005), 100, rng, logical=logical, weak=False, budget=24)
        parity, stabilizers = hgp(160, rng)
        run_case('large-hgp', parity, np.full(parity.shape[1], .01), 50, rng, stabilizers=stabilizers, weak=False, budget=24)


if __name__ == '__main__':
    main()
