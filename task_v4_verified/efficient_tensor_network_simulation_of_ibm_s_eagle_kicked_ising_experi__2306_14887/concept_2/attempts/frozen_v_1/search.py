import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import concurrent.futures
import json
from pathlib import Path
import sys
import time

import numpy as np

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/efficient_tensor_network_simulation_of_ibm_s_eagle_kicked_ising_experi__2306_14887/concept_2/participant')
sys.path.insert(0, str(ASSETS / 'workspace'))
import simulator
from protocol import load_spec, metrics, waveforms

OUT = Path(__file__).resolve().parent
SPEC = load_spec()


def witness(depth, knots):
    return dict(schema_version=1, depth=int(depth), knots=list(map(float, knots)), observable='zz1')


def assess(candidate, robust=False):
    records = {}
    for family, angles in waveforms(candidate, SPEC).items():
        if not robust and family != 'nominal':
            continue
        result = simulator.compare(angles)
        estimates = [result['mps'][str(chi)]['zz1'] for chi in SPEC['chis']]
        records[family] = metrics(result['exact']['zz1'], estimates, SPEC)
        records[family]['diagnostics'] = result['diagnostics']
    return records


def scan_constant(angle):
    begin = time.monotonic()
    states = [[np.array([1, 0], dtype=np.complex128).reshape(1, 2, 1)
               for site in range(12)] for chi in SPEC['chis']]
    exact = np.zeros(4096, dtype=np.complex128)
    exact[0] = 1
    diagonal, phase = simulator.diagonals()
    gate = simulator.rx(angle)
    records = []
    for depth in range(1, 49):
        for site in range(12):
            shaped = exact.reshape(1 << site, 2, -1)
            exact = np.einsum('ab,ibj->iaj', gate, shaped).reshape(-1)
        exact *= phase
        estimates = []
        for index, chi in enumerate(SPEC['chis']):
            tensors = [np.einsum('ab,ibj->iaj', gate, tensor) for tensor in states[index]]
            simulator.entangle_ring(tensors)
            simulator.compress(tensors, chi)
            states[index] = tensors
            if depth >= 12:
                estimates.append(simulator.measure(simulator.expand_mps(tensors))['zz1'])
        if depth >= 12:
            record = metrics(simulator.measure(exact)['zz1'], estimates, SPEC)
            records.append({'witness': witness(depth, [angle] * 6), 'nominal': record})
    return records, time.monotonic() - begin


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=float, default=0.2)
    parser.add_argument('--stop', type=float, default=1.44)
    parser.add_argument('--step', type=float, default=0.02)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--top', type=int, default=12)
    options = parser.parse_args()
    begin = time.monotonic()
    best = []
    angles = np.arange(options.start, options.stop + 1e-8, options.step)
    with concurrent.futures.ProcessPoolExecutor(max_workers=options.workers) as pool:
        futures = {pool.submit(scan_constant, float(angle)): angle for angle in angles}
        for future in concurrent.futures.as_completed(futures):
            records, elapsed = future.result()
            best.extend(records)
            best.sort(key=lambda record: record['nominal']['margin'], reverse=True)
            best = best[:options.top]
            (OUT / 'grid_best.json').write_text(json.dumps(best, indent=2) + '\n')
            current = best[0]
            print(json.dumps({'angle': float(futures[future]), 'seconds': elapsed,
                              'total_seconds': time.monotonic() - begin,
                              'best_margin': current['nominal']['margin'],
                              'best_depth': current['witness']['depth'],
                              'best_angle': current['witness']['knots'][0]}), flush=True)
    robust_best = None
    for candidate in best:
        records = assess(candidate['witness'], robust=True)
        margin = min(record['margin'] for record in records.values())
        print(json.dumps({'robust_margin': margin, 'witness': candidate['witness']}), flush=True)
        if robust_best is None or margin > robust_best['worst_margin']:
            robust_best = {'witness': candidate['witness'], 'worst_margin': margin, 'families': records}
            (OUT / 'witness.json').write_text(json.dumps(candidate['witness'], indent=2) + '\n')
            (OUT / 'validation.json').write_text(json.dumps(robust_best, indent=2) + '\n')
        if margin >= 1.1:
            break


if __name__ == '__main__':
    main()
