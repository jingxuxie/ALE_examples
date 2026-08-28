import argparse
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

import numpy as np
import scipy.sparse as sp

from validate import toric


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cold', action='store_true')
    parser.add_argument('--shots', type=int, default=400)
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    rng = np.random.default_rng(38203)
    base, logical = toric(25, 32)
    base = base.tocoo()
    checks, variables = 20000, 250000
    mapping = np.concatenate([np.tile(np.arange(base.shape[1]), 4), np.arange(10000)])
    multiplicities = np.bincount(mapping, minlength=base.shape[1])
    probabilities = (1 - (1 - 2 * .001) ** multiplicities) / 2
    faults = (rng.random((args.shots, base.shape[1])) < probabilities).astype(np.uint8)
    column_permutation = rng.permutation(variables).astype(np.int32)
    row_permutation = rng.permutation(checks).astype(np.int32)
    expanded = base.tocsc()[:, mapping].tocoo()
    rows = row_permutation[expanded.row]
    columns = column_permutation[expanded.col]
    syndromes = np.zeros((args.shots, checks), dtype=np.uint8)
    syndromes[:, row_permutation] = (base @ faults.T).T % 2
    observables = np.zeros((variables, 2), dtype=np.uint8)
    observables[column_permutation] = logical[:, mapping].T
    truth = faults @ logical.T % 2
    priors = np.full(variables, .001)
    budget = 30.
    library = directory / 'decoder_native.so'
    if args.cold and library.exists():
        library.unlink()
    with tempfile.TemporaryDirectory(prefix='validation-', dir=directory) as temporary:
        case = Path(temporary) / 'case.npz'
        answer = Path(temporary) / 'answer.npz'
        np.savez_compressed(case, h_rows=rows, h_cols=columns, h_shape=np.array([checks, variables]),
                            priors=priors, syndromes=syndromes, budget_seconds=np.array(budget))
        previous = resource.getrusage(resource.RUSAGE_CHILDREN)
        started = time.perf_counter()
        subprocess.run([sys.executable, str(directory / 'solve.py'), '--input', str(case), '--output', str(answer)],
                       check=True, env=dict(os.environ, DECODER_STATS='1'))
        wall = time.perf_counter() - started
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = usage.ru_utime + usage.ru_stime - previous.ru_utime - previous.ru_stime
        with np.load(answer, allow_pickle=False) as result:
            corrections = result['corrections']
        assert corrections.shape == (args.shots, variables)
        assert corrections.dtype == np.uint8 and np.all(corrections <= 1)
        parity = sp.coo_matrix((np.ones(len(rows), dtype=np.uint8), (rows, columns)), shape=(checks, variables)).tocsr()
        valid = np.all((parity @ corrections.T).T % 2 == syndromes, axis=1)
        recovered = np.all(corrections @ observables % 2 == truth, axis=1)
        print('Full-size CLI:', corrections.shape, 'valid:', int(valid.sum()), 'logical:', int((valid & recovered).sum()),
              'CPU:', round(cpu, 3), 'wall:', round(wall, 3), 'peak KiB:', usage.ru_maxrss, flush=True)
        assert valid.all() and recovered.mean() >= .98
        assert cpu <= budget and wall <= max(60, 3 * budget)
        assert usage.ru_maxrss < 1.5 * 1024 * 1024


if __name__ == '__main__':
    main()
