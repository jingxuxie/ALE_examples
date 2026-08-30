import os
import time

START_TIME = time.monotonic()
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'

import json
import sys
from pathlib import Path
import numpy as np
from scipy.special import logsumexp
from regional import LocalMixture, configurations, regions
from optimization import FullRefinement


def initialize(instance, deadline, verbose=False):
    count = int(instance['n'])
    couplings = np.asarray(instance['couplings'], dtype=np.float64)
    fields = np.asarray(instance['fields'], dtype=np.float64)
    blocks = regions(couplings)
    spins = configurations(count)
    log_target = 0.5 * np.sum((spins @ couplings) * spins, axis=1) + spins @ fields
    log_target -= logsumexp(log_target)
    target = np.exp(log_target)
    rng = np.random.default_rng(3818)
    fits = []
    regularization = 0.01 if len(blocks) > 3 else 0.001
    for block_index, block in enumerate(blocks):
        indices = (spins[:, block] > 0).astype(np.int32) @ (1 << np.arange(len(block)))
        marginal = np.bincount(indices, weights=target, minlength=1 << len(block))
        log_local = np.log(np.maximum(marginal, 1e-300))
        log_local -= logsumexp(log_local)
        best = None
        best_score = np.inf
        block_deadline = time.monotonic() + max(0.2, (deadline - time.monotonic()) / (len(blocks) - block_index))
        for trial in range(10):
            if trial and time.monotonic() > block_deadline:
                break
            orders = [rng.permutation(len(block)), rng.permutation(len(block))]
            fit = LocalMixture(log_local, orders)
            fit.fit(1000, regularization=regularization, deadline=block_deadline)
            score = fit.evaluate(fit.parameters, regularization=regularization)[0]
            if score < best_score:
                best = fit
                best_score = score
        local_weights, local_biases = best.artifact()
        fits.append((best.orders, local_weights, local_biases))
        if verbose:
            print('region', block, best.last, 'elapsed', time.monotonic() - START_TIME, file=sys.stderr, flush=True)
    codes = [1, 2, 4, 7] if len(blocks) == 4 else [1, 2, 4, 3, 5, 6, 7]
    weights = np.zeros((8, count, count))
    biases = np.zeros((8, count))
    orders = []
    for component in range(8):
        order = []
        for block, code, fit in zip(blocks, codes, fits):
            choice = (component & code).bit_count() % 2
            local_orders, local_weights, local_biases = fit
            weights[component][np.ix_(block, block)] = local_weights[choice]
            biases[component, block] = local_biases[choice]
            order.extend(np.asarray(block)[local_orders[choice]].tolist())
        orders.append(order)
    norms = np.abs(biases) + np.abs(weights).sum(axis=2)
    scaling = np.minimum(1, 59 / np.maximum(1, norms))
    return {'mixing': [0.125] * 8, 'weights': (weights * scaling[:, :, None]).tolist(),
            'biases': (biases * scaling).tolist(), 'orders': orders}


def write_model(destination, model):
    temporary = destination.with_name(destination.name + '.tmp')
    temporary.write_text(json.dumps(model, separators=(',', ':'), allow_nan=False))
    os.replace(temporary, destination)


def main():
    if len(sys.argv) != 3:
        raise SystemExit('Usage: python solve.py INSTANCE.json MODEL.json')
    instance = json.loads(Path(sys.argv[1]).read_text())
    destination = Path(sys.argv[2])
    verbose = os.environ.get('SOLVE_VERBOSE', '0') == '1'
    deadline = START_TIME + 105
    model = initialize(instance, min(deadline - 30, START_TIME + 24), verbose)
    write_model(destination, model)
    remaining = deadline - time.monotonic()
    if remaining > 6:
        optimizer = FullRefinement(instance, model, seconds=remaining, threads=4, verbose=verbose)
        model = optimizer.fit()
        write_model(destination, model)


if __name__ == '__main__':
    main()
