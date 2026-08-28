import argparse
import json
import os
from pathlib import Path
import time

import numpy as np

from repair import prepare_columns, repair
from solve import solve
from validate import compare


def build_case(data, scale, seed, frames):
    random = np.random.default_rng(seed)
    original = data['H']
    rows, columns = original.shape
    logicals = len(data['L'])
    matrix = np.zeros((2 * rows, 2 * columns), dtype=np.uint8)
    logical = np.zeros((2 * logicals, 2 * columns), dtype=np.uint8)
    matrix[:rows, :columns] = matrix[rows:, columns:] = original
    logical[:logicals, :columns] = logical[logicals:, columns:] = data['L']
    prior = np.minimum(.2, np.tile(data['prior'], 2) * scale * np.exp(random.normal(0, .15, 2 * columns)))
    weights = np.log((1 - prior) / prior)
    packed = prepare_columns(matrix)
    syndromes, soft, targets = [], [], []
    while len(syndromes) < frames:
        fault = (random.random(2 * columns) < prior).astype(np.uint8)
        syndrome = matrix @ fault % 2
        heuristic = weights + random.normal(0, 1.0, 2 * columns)
        baseline = repair(packed, syndrome, heuristic)
        target = logical @ fault % 2
        if np.array_equal(logical @ baseline % 2, target) or weights @ baseline <= weights @ fault:
            continue
        syndromes.append(syndrome)
        soft.append(heuristic)
        targets.append(target)
    roworder = random.permutation(2 * rows)
    colorder = random.permutation(2 * columns)
    return {'H': matrix[roworder][:, colorder], 'L': logical[:, colorder],
            'prior': prior[colorder], 'syndrome': np.asarray(syndromes)[:, roworder],
            'soft_llr': np.asarray(soft)[:, colorder]}, {'logical_target': np.asarray(targets)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frames', type=int, default=24)
    parser.add_argument('--scales', type=float, nargs='+', default=[1.0, 1.6])
    parser.add_argument('--modes', type=int, nargs='+', default=[0, 3])
    arguments = parser.parse_args()
    results = []
    with np.load(arguments.input, allow_pickle=False) as original:
        for scale in arguments.scales:
            data, labels = build_case(original, scale, 73491 + int(scale * 100), arguments.frames)
            name = 'synthetic_' + str(scale).replace('.', '_')
            np.savez_compressed(name + '.npz', **data)
            np.savez_compressed(name + '_labels.npz', **labels)
            for mode in arguments.modes:
                os.environ['DECODER_MODE'] = str(mode)
                started = time.perf_counter()
                predictions = solve(data)
                elapsed = time.perf_counter() - started
                result = dict(name=name, mode=mode, elapsed=elapsed,
                              **compare(data, labels, predictions))
                result['diagnostics'] = predictions['diagnostics'].tolist()
                results.append(result)
                print(json.dumps({key: value for key, value in result.items() if key != 'diagnostics'}), flush=True)
                np.savez_compressed(name + '_mode' + str(mode) + '_predictions.npz', **predictions)
                arguments.output.write_text(json.dumps(results, indent=2) + '\n')
