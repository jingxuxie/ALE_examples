import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
from physics import sector


def exact(fields, driver='evr', precision='float64'):
    states, spins, exchange, mode = sector(len(fields))
    dimension = len(states)
    matrix = np.array(exchange, dtype=precision, order='F')
    matrix[np.diag_indices(dimension)] += spins @ fields
    options = dict(check_finite=False, overwrite_a=True, driver=driver)
    if driver != 'evd':
        options['subset_by_index'] = [dimension // 3, 2 * dimension // 3 - 1]
    energies, vectors = eigh(matrix, **options)
    if driver == 'evd':
        vectors = vectors[:, dimension // 3:2 * dimension // 3]
    probabilities = vectors ** 2
    real_mode = probabilities.T @ mode.real
    imag_mode = probabilities.T @ mode.imag
    norm_mode = probabilities.T @ (np.abs(mode) ** 2)
    return float(np.mean(1 - (real_mode ** 2 + imag_mode ** 2) / norm_mode))


def main():
    source = Path(__file__).resolve().parents[2] / 'participant/input/validation.jsonl'
    cases = [json.loads(line) for line in source.read_text().splitlines()]
    for length in (10, 12):
        sector(length)
        selected = [case for case in cases if case['L'] == length]
        for driver, precision in [('evr', 'float64'), ('evd', 'float64'), ('evr', 'float32'), ('evd', 'float32')]:
            started = time.monotonic()
            with ThreadPoolExecutor(max_workers=4) as executor:
                predictions = list(executor.map(lambda case: exact(case['fields'], driver, precision), selected))
            residual = np.array(predictions) - [case['f'] for case in selected]
            print(length, driver, precision, 'seconds', time.monotonic() - started, 'rmse', np.sqrt(np.mean(residual ** 2)), 'max', np.max(np.abs(residual)), flush=True)


if __name__ == '__main__':
    main()
