import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import argparse
import json
from pathlib import Path
import time

import numpy as np

from physics import predict_instance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset', type=Path)
    parser.add_argument('output_prefix', type=Path)
    parser.add_argument('--steps', type=int, default=160)
    parser.add_argument('--tolerance', type=float, default=1e-8)
    arguments = parser.parse_args()
    with np.load(arguments.dataset, allow_pickle=False) as archive:
        data = dict(archive)
    predictions = []
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    for index, sites in enumerate(data['n_sites']):
        predictions.append(predict_instance(
            data['hopping'][index, :sites, :sites],
            data['interaction'][index, :sites],
            data['potential'][index, :sites],
            arguments.steps, arguments.tolerance,
        ))
        if (index + 1) % 128 == 0:
            print('completed', index + 1, 'elapsed', time.perf_counter() - start_wall, flush=True)
    elapsed_wall = time.perf_counter() - start_wall
    elapsed_cpu = time.process_time() - start_cpu
    residual = np.array(predictions) - data['gaps']
    report = {
        'examples': len(predictions),
        'wall_seconds': elapsed_wall,
        'cpu_seconds': elapsed_cpu,
        'rmse': np.sqrt(np.mean(residual ** 2, axis=0)).tolist(),
        'max_absolute_error': np.max(np.abs(residual), axis=0).tolist(),
        'families': {},
    }
    for family in range(4):
        selected = data['family'] == family
        report['families'][str(family)] = {
            'rmse': np.sqrt(np.mean(residual[selected] ** 2, axis=0)).tolist(),
            'max_absolute_error': np.max(np.abs(residual[selected]), axis=0).tolist(),
        }
    worst = np.argsort(np.max(np.abs(residual), axis=1))[-20:]
    report['worst_rows'] = [
        {'row': int(index), 'family': int(data['family'][index]),
         'n_sites': int(data['n_sites'][index]), 'gaps': data['gaps'][index].tolist(),
         'error': residual[index].tolist()}
        for index in worst
    ]
    arguments.output_prefix.with_suffix('.json').write_text(json.dumps({
        'schema_version': 1, 'predictions': predictions,
    }) + '\n')
    arguments.output_prefix.with_suffix('.report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
