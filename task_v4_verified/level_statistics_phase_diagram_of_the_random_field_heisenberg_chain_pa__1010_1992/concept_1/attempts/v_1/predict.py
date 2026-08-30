import os

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[variable] = '1'

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import json
from pathlib import Path
import sys
import time

import numpy as np

from descriptors import feature_matrix
from fast_physics import initialize_worker, predict_small
from native_forest import Forest


def surrogate(model, cases):
    features = np.asarray(feature_matrix(cases), dtype=np.float32)
    return model.predict(features)


def predict_cases(model, pool, cases, started):
    if not cases:
        return {'predictions': []}, 0
    estimates, uncertainty = surrogate(model, cases)
    indices = [index for index, case in enumerate(cases) if case['L'] == 10]
    indices.sort(key=lambda index: uncertainty[index], reverse=True)
    jobs = [(index, cases[index]['fields']) for index in indices]
    futures = [pool.submit(predict_small, job) for job in jobs]
    completed = 0
    remaining = max(0.0, started + 1.00 - time.perf_counter())
    try:
        for future in as_completed(futures, timeout=remaining):
            index, estimate = future.result()
            if estimate is not None and np.isfinite(estimate):
                estimates[index] = estimate
                completed += 1
    except TimeoutError:
        pass
    return {'predictions': [{'id': case['id'], 'f': float(estimate)}
                            for case, estimate in zip(cases, estimates)]}, completed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input')
    parser.add_argument('--output')
    parser.add_argument('--diagnostics', action='store_true')
    args = parser.parse_args()
    if bool(args.input) != bool(args.output):
        parser.error('--input and --output must be supplied together')
    model = Forest()
    surrogate(model, [{'L': 10, 'fields': np.linspace(-1, 1, 10)}])
    initialize_worker()
    pool = ThreadPoolExecutor(4)
    list(pool.map(predict_small, [(index, np.linspace(-1, 1, 10)) for index in range(8)]))
    if args.input:
        text = Path(args.input).read_text()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = [json.loads(line) for line in text.splitlines() if line.strip()]
        started = time.perf_counter()
    else:
        print('READY', flush=True)
        line = sys.stdin.readline()
        started = time.perf_counter()
        payload = json.loads(line)
    cases = payload['cases'] if isinstance(payload, dict) else payload
    result, completed = predict_cases(model, pool, cases, started)
    pool.shutdown(wait=True, cancel_futures=True)
    output = json.dumps(result, allow_nan=False, separators=(',', ':')) + '\n'
    if args.input:
        Path(args.output).write_text(output)
    else:
        sys.stdout.write(output)
        sys.stdout.flush()
    if args.diagnostics:
        print(json.dumps({'exact_small_cases': completed,
                          'response_seconds': time.perf_counter() - started}), file=sys.stderr, flush=True)
    os._exit(0)


if __name__ == '__main__':
    main()
