import os

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'

import argparse
import gzip
import json
from pathlib import Path
import pickle
import sys
import time

import numpy as np

from descriptors import feature_matrix
from fast_physics import prepare_sector, solve_fraction


ROOT = Path(__file__).resolve().parent


def read_cases(path):
    text = Path(path).read_text()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(payload, dict):
        return payload.get('cases', [payload])
    return payload


class Predictor:
    def __init__(self):
        with gzip.open(ROOT / 'model10.pkl.gz', 'rb') as stream:
            self.model10 = pickle.load(stream)
        with gzip.open(ROOT / 'model12.pkl.gz', 'rb') as stream:
            self.model12 = pickle.load(stream)
        self.sector = prepare_sector()
        warm_fields = np.linspace(-1, 1, 10).tolist()
        warm_features = feature_matrix([{'fields': warm_fields}, {'fields': np.linspace(-1, 1, 12)}]).astype(np.float32)
        self.model10.predict(warm_features[:1])
        self.model12.predict(warm_features[1:])
        solve_fraction(warm_fields, self.sector)

    def predict(self, cases, started=None, exact_limit=160):
        started = time.monotonic() if started is None else started
        if not cases:
            return {'predictions': []}
        features = feature_matrix(cases).astype(np.float32)
        estimates = np.empty(len(cases), dtype=np.float64)
        selected10 = [index for index, case in enumerate(cases) if case['L'] == 10]
        if selected10:
            features10 = features[selected10]
            estimates10 = self.model10.predict(features10)
            uncertainty = estimates10 * (1 - estimates10)
            estimates[selected10] = estimates10
            priority = np.argsort(uncertainty)[::-1]
            selected10 = [selected10[index] for index in priority]
        selected12 = [index for index, case in enumerate(cases) if case['L'] >= 12]
        if selected12:
            estimates[selected12] = self.model12.predict(features[selected12])
        for index in selected10[:exact_limit]:
            if time.monotonic() - started >= 1.25:
                break
            try:
                corrected = solve_fraction(cases[index]['fields'], self.sector)
            except RuntimeError:
                continue
            if np.isfinite(corrected):
                estimates[index] = corrected
        np.clip(estimates, 0, 1, out=estimates)
        return {'predictions': [{'id': case['id'], 'f': float(estimate)}
                                for case, estimate in zip(cases, estimates)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input')
    parser.add_argument('--output')
    arguments = parser.parse_args()
    if bool(arguments.input) != bool(arguments.output):
        parser.error('--input and --output must be supplied together')
    predictor = Predictor()
    if arguments.input:
        result = predictor.predict(read_cases(arguments.input))
        Path(arguments.output).write_text(json.dumps(result, allow_nan=False) + '\n')
    else:
        print('READY', flush=True)
        line = sys.stdin.readline()
        started = time.monotonic()
        cases = json.loads(line)['cases']
        result = predictor.predict(cases, started)
        print(json.dumps(result, allow_nan=False), flush=True)
    os._exit(0)


if __name__ == '__main__':
    main()
