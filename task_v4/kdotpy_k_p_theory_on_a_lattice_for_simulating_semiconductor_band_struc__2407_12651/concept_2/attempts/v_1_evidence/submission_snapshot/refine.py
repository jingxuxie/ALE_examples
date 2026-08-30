import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import argparse
from functools import lru_cache
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time
import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent / 'participant/workspace'))
from model import LOWER, UPPER, coefficients, sample, diagnose


def optimize(job):
    filename, size, index, settings = job
    initial = np.array(json.loads(Path(filename).read_text())['parameters'])
    started = time.monotonic()

    @lru_cache(maxsize=128)
    def metrics(key):
        parameters = np.frombuffer(key, dtype=np.float64)
        hamiltonian, derivative_x, derivative_y = sample(parameters, size)
        energies, frames = np.linalg.eigh(hamiltonian)
        target = frames[..., :, 0]
        matrix_x = np.einsum('...a,...ab,...bm->...m', target.conj(), derivative_x, frames)
        matrix_y = np.einsum('...a,...ab,...bm->...m', target.conj(), derivative_y, frames)
        separations = energies[..., 1:] - energies[..., :1]
        contributions = -2 * np.imag(matrix_x[..., 1:] * matrix_y[..., 1:].conj()) / separations ** 2
        integrals = contributions.mean(axis=(0, 1)) * 2 * np.pi
        optical = ((abs(matrix_x[..., 1:])**2 + abs(matrix_y[..., 1:])**2) / separations**2).mean(axis=(0, 1))
        lipschitz = sum(np.linalg.norm(block, 2) for block in coefficients(parameters)[1:])
        gaps = separations[..., 0].ravel() - 2 * np.pi * lipschitz / 49
        mean = np.cumsum(integrals)[[1, 2, 3]].mean()
        return integrals, optical, gaps, mean

    def objective(parameters):
        integrals, optical, gaps, mean = metrics(parameters.tobytes())
        return 100 * np.sum(integrals[2:4]**2)

    def constraints(parameters):
        integrals, optical, gaps, mean = metrics(parameters.tobytes())
        return np.r_[mean - settings['plateau_low'], settings['plateau_high'] - mean,
                     (optical[:4] - settings['optical']) * 10,
                     gaps - settings['gap'], integrals.sum() - .998, 1.002 - integrals.sum()]

    counter = 0
    def callback(parameters):
        nonlocal counter
        counter += 1
        if counter % 25 == 0:
            print(json.dumps({'index': index, 'iteration': counter,
                              'objective': objective(parameters),
                              'constraint_min': float(constraints(parameters).min())}), flush=True)

    span = UPPER - LOWER
    solution = minimize(lambda normalized: objective(LOWER + span * normalized),
                        (initial - LOWER) / span, method='SLSQP', bounds=[(0., 1.)] * 25,
                        constraints={'type': 'ineq', 'fun': lambda normalized: constraints(LOWER + span * normalized)},
                        callback=lambda normalized: callback(LOWER + span * normalized),
                        options={'maxiter': 300, 'ftol': 1e-12, 'eps': 1e-6})
    solution.x = np.clip(LOWER + span * solution.x, LOWER, UPPER)
    final = diagnose(solution.x, 49)
    payload = {'parameters': solution.x.tolist(), 'diagnostic': final,
               'cost': float(solution.fun), 'message': solution.message,
               'source': filename, 'elapsed': time.monotonic() - started}
    (ROOT / f'refined_{index}.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload), flush=True)
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+')
    parser.add_argument('--size', type=int, default=25)
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--optical', type=float, default=.0165)
    parser.add_argument('--gap', type=float, default=.135)
    parser.add_argument('--plateau-low', type=float, default=.25)
    parser.add_argument('--plateau-high', type=float, default=.39)
    options = parser.parse_args()
    settings = {name: getattr(options, name) for name in ('optical', 'gap', 'plateau_low', 'plateau_high')}
    jobs = [(filename, options.size, index + options.start, settings)
            for index, filename in enumerate(options.files)]
    with mp.Pool(min(4, len(jobs))) as pool:
        pool.map(optimize, jobs)
