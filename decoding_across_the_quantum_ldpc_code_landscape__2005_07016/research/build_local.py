import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'research/vendor'))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/ale-ldpc-mpl')
import numpy as np
import scipy.sparse as sparse
import stim
from ldpc import BpDecoder, BpOsdDecoder
from ldpc.bplsd_decoder import BpLsdDecoder
from ldpc.ckt_noise.dem_matrices import detector_error_model_to_check_matrices

PILOT = ROOT / 'pilots/01_local_recovery'


def row_reduce(matrix):
    reduced = np.array(matrix, dtype=np.uint8, copy=True)
    pivots = []
    for column in range(reduced.shape[1]):
        possible = np.flatnonzero(reduced[len(pivots):, column])
        if not len(possible):
            continue
        chosen = int(possible[0]) + len(pivots)
        reduced[[len(pivots), chosen]] = reduced[[chosen, len(pivots)]]
        others = np.flatnonzero(reduced[:, column])
        others = others[others != len(pivots)]
        reduced[others] ^= reduced[len(pivots)]
        pivots.append(column)
        if len(pivots) == reduced.shape[0]:
            break
    return reduced, pivots


def regular_pcm(length, seed):
    random = np.random.default_rng(seed)
    checks = length // 2
    for trial in range(10000):
        rows = np.repeat(np.arange(checks), 6)
        columns = random.permutation(np.repeat(np.arange(length), 3))
        matrix = sparse.coo_matrix((np.ones(len(rows), dtype=np.uint8), (rows, columns)), shape=(checks, length)).tocsr()
        if np.any(matrix.data != 1):
            continue
        column_matrix = matrix.tocsc()
        supports = [tuple(column_matrix.indices[column_matrix.indptr[column]:column_matrix.indptr[column + 1]]) for column in range(length)]
        if len(set(supports)) != length:
            continue
        reduced, pivots = row_reduce(matrix.toarray())
        if len(pivots) == checks:
            free = np.array([column for column in range(length) if column not in pivots])
            kernel = np.zeros((len(free), length), dtype=np.uint8)
            kernel[:, free] = np.eye(len(free), dtype=np.uint8)
            kernel[:, pivots] = reduced[:checks, free].T
            return matrix, sparse.csr_matrix(kernel), free
    raise RuntimeError('No simple full-rank regular graph generated')


def hgp(length, seed):
    first, kernel, _ = regular_pcm(length, seed)
    second, _, free = regular_pcm(length, seed + 1)
    checks, bits = first.shape
    parity = sparse.hstack((sparse.kron(sparse.eye(bits, dtype=np.uint8), second), sparse.kron(first.T, sparse.eye(checks, dtype=np.uint8))), format='csr')
    quotient = sparse.coo_matrix((np.ones(len(free), dtype=np.uint8), (np.arange(len(free)), free)), shape=(len(free), bits)).tocsr()
    logical = sparse.hstack((sparse.kron(kernel, quotient), sparse.csr_matrix((len(free) ** 2, checks ** 2), dtype=np.uint8)), format='csr')
    stabilizer = sparse.hstack((sparse.kron(first, sparse.eye(bits, dtype=np.uint8)), sparse.kron(sparse.eye(checks, dtype=np.uint8), second.T)), format='csr')
    assert not np.any((parity @ stabilizer.T).data % 2)
    assert not np.any((logical @ stabilizer.T).data % 2)
    return parity.astype(np.uint8), logical.astype(np.uint8)


def save_case(path, parity, priors, syndrome):
    matrix = parity.tocoo()
    np.savez_compressed(path, h_rows=matrix.row.astype(np.int32), h_cols=matrix.col.astype(np.int32), h_shape=np.array(matrix.shape), priors=priors, syndromes=syndrome.astype(np.uint8))


def generate(split, family, seed, shots, size, probability):
    random = np.random.default_rng(seed)
    if family == 'hgp':
        parity, logical = hgp(size, seed + 100000)
        priors = np.full(parity.shape[1], probability)
        modulation = random.uniform(0.6, 1.4, parity.shape[1])
        priors *= modulation
        errors = (random.random((shots, parity.shape[1])) < priors).astype(np.uint8)
        syndromes = (parity @ errors.T).T % 2
        truth = (logical @ errors.T).T % 2
    elif family == 'circuit_surface':
        circuit = stim.Circuit.generated('surface_code:rotated_memory_z', distance=size, rounds=size + 3, after_clifford_depolarization=probability, before_measure_flip_probability=probability, after_reset_flip_probability=probability)
        dem = circuit.detector_error_model(decompose_errors=False)
        matrices = detector_error_model_to_check_matrices(dem, allow_undecomposed_hyperedges=True)
        parity = matrices.check_matrix.astype(np.uint8)
        logical = matrices.observables_matrix.astype(np.uint8)
        priors = matrices.priors
        errors = (random.random((shots, parity.shape[1])) < priors).astype(np.uint8)
        syndromes = (parity @ errors.T).T % 2
        truth = (logical @ errors.T).T % 2
    else:
        source = ROOT / 'research/sources/ldpc/python_test/pcms'
        parity = sparse.load_npz(source / 'hx_400_16_6.npz').astype(np.uint8).tocsr()
        logical = sparse.load_npz(source / 'lx_400_16_6.npz').astype(np.uint8).tocsr()
        priors = np.full(parity.shape[1], probability)
        errors = (random.random((shots, parity.shape[1])) < priors).astype(np.uint8)
        syndromes = (parity @ errors.T).T % 2
        truth = (logical @ errors.T).T % 2
    parity.eliminate_zeros()
    logical.eliminate_zeros()
    permutation = random.permutation(parity.shape[1])
    check_permutation = random.permutation(parity.shape[0])
    parity = parity[check_permutation][:, permutation].tocsr()
    logical = logical[:, permutation].tocsr()
    priors = priors[permutation]
    syndromes = syndromes[:, check_permutation]
    name = f'{family}_{size}_{seed}'
    folder = PILOT / 'private/challenge_pool' / split
    folder.mkdir(parents=True, exist_ok=True)
    save_case(folder / f'{name}.npz', parity, priors, syndromes)
    settings = dict(error_channel=priors, max_iter=30, bp_method='minimum_sum', ms_scaling_factor=0.625, schedule='parallel')
    weak = BpDecoder(parity, **settings)
    strong = BpLsdDecoder(parity, lsd_method='lsd_cs', lsd_order=8, **settings)
    outputs = {}
    timings = {}
    for label, decoder in [('weak', weak), ('reference', strong)]:
        started = time.process_time()
        corrections = np.array([decoder.decode(syndrome).copy() for syndrome in syndromes], dtype=np.uint8)
        timings[label] = time.process_time() - started
        valid = np.all(((parity @ corrections.T).T % 2) == syndromes, axis=1)
        success = valid & np.all(((logical @ corrections.T).T % 2) == truth, axis=1)
        outputs[label] = dict(corrections=corrections, valid=valid, success=success)
    logical_coo = logical.tocoo()
    np.savez_compressed(PILOT / 'private/reference' / f'{name}.npz', logical_rows=logical_coo.row, logical_cols=logical_coo.col, logical_shape=np.array(logical.shape), truth=truth, reference=outputs['reference']['corrections'], weak=outputs['weak']['corrections'])
    result = dict(name=name, split=split, family=family, seed=seed, shots=shots, shape=list(parity.shape), nnz=int(parity.nnz), logical_bits=logical.shape[0], probability=probability, reference_seconds=timings['reference'], weak_seconds=timings['weak'], reference_accuracy=float(outputs['reference']['success'].mean()), weak_accuracy=float(outputs['weak']['success'].mean()), reference_valid=float(outputs['reference']['valid'].mean()), weak_valid=float(outputs['weak']['valid'].mean()), budget_seconds=max(30.0, 8.0 * timings['reference']), memory_mb=1536)
    print(json.dumps(result), flush=True)
    return result


def main():
    global PILOT
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', default='pilot', choices=['pilot', 'challenge', 'holdout', 'smoke'])
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--config', type=Path)
    arguments = parser.parse_args()
    if arguments.destination:
        PILOT = arguments.destination.resolve()
    if arguments.split == 'holdout' and not arguments.config:
        parser.error('Fresh holdout generation requires a post-attempt failure-region --config')
    for folder in ['participant/input', 'participant/workspace', 'private/reference', 'private/challenge_pool', 'attempt']:
        (PILOT / folder).mkdir(parents=True, exist_ok=True)
    definitions = {
        'smoke': [('hgp', 11701, 12, 12, 0.02)],
        'pilot': [('high_rate', 37101, 384, 400, 0.035), ('hgp', 37102, 192, 96, 0.012), ('circuit_surface', 37103, 128, 13, 0.0015)],
        'challenge': [('high_rate', 47201, 384, 400, 0.045), ('hgp', 47202, 128, 144, 0.015), ('circuit_surface', 47203, 128, 17, 0.0025)],
        'holdout': [('high_rate', 57301, 384, 400, 0.043), ('hgp', 57302, 128, 144, 0.015), ('circuit_surface', 57303, 128, 19, 0.0025)]
    }
    entries = definitions[arguments.split]
    if arguments.config:
        configuration = json.loads(arguments.config.read_text())
        if not configuration.get('region') or not configuration.get('discovered_from'):
            parser.error('Config must document the source-grounded region and inspected attempt report')
        entries = configuration['cases']
        (PILOT / 'private/reference/generation_region.json').write_text(json.dumps(configuration, indent=2))
    results = [generate(arguments.split, *entry) for entry in entries]
    (PILOT / 'private/reference' / f'{arguments.split}_manifest.json').write_text(json.dumps(results, indent=2))
    if arguments.split == 'smoke':
        for case in (PILOT / 'private/challenge_pool/smoke').glob('*.npz'):
            shutil.copy2(case, PILOT / 'participant/input/example.npz')


if __name__ == '__main__':
    main()
