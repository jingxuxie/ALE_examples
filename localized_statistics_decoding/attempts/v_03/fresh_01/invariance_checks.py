import argparse
import json
import os
from pathlib import Path
import time

import numpy as np

from solve import solve
from validate import compare


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    arguments = parser.parse_args()
    random = np.random.default_rng(93745)
    with np.load(arguments.inputs / 'validation_large.npz', allow_pickle=False) as loaded:
        original = {key: loaded[key] for key in loaded.files}
    with np.load(arguments.inputs / 'validation_large_labels.npz', allow_pickle=False) as loaded:
        original_labels = {key: loaded[key] for key in loaded.files}
    roworder = random.permutation(original['H'].shape[0])
    colorder = random.permutation(original['H'].shape[1])
    permuted = {'H': original['H'][roworder][:, colorder], 'L': original['L'][:, colorder],
                'prior': original['prior'][colorder], 'syndrome': original['syndrome'][:, roworder],
                'soft_llr': original['soft_llr'][:, colorder]}
    duplicates = {'H': np.repeat(np.repeat(original['H'], 2, axis=1), 2, axis=0),
                  'L': np.repeat(original['L'], 2, axis=1),
                  'prior': np.repeat(original['prior'] / (1 + np.sqrt(1 - 2 * original['prior'])), 2),
                  'syndrome': np.repeat(original['syndrome'], 2, axis=1),
                  'soft_llr': np.repeat(original['soft_llr'], 2, axis=1)}
    matrix = np.zeros((288, 864), dtype=np.uint8)
    for column in range(864):
        degree = random.choice([3, 4, 5])
        matrix[random.choice(288, degree, replace=False), column] = 1
    logical = random.integers(0, 2, (8, 864), dtype=np.uint8)
    prior = random.uniform(.004, .032, 864)
    faults = (random.random((24, 864)) < prior).astype(np.uint8)
    generic = {'H': matrix, 'L': logical, 'prior': prior, 'syndrome': faults @ matrix.T % 2,
               'soft_llr': np.tile(np.log((1 - prior) / prior), (24, 1))}
    cases = [('permutation', permuted, original_labels),
             ('duplicates', duplicates, original_labels),
             ('generic_sparse', generic, {'logical_target': faults @ logical.T % 2})]
    results = []
    for name, data, labels in cases:
        started = time.perf_counter()
        predictions = solve(data)
        elapsed = time.perf_counter() - started
        result = dict(name=name, elapsed=elapsed, shape=list(data['H'].shape),
                      groups=int(predictions['groups']), **compare(data, labels, predictions))
        result['diagnostics'] = predictions['diagnostics'].tolist()
        results.append(result)
        print(json.dumps({key: value for key, value in result.items() if key != 'diagnostics'}), flush=True)
        np.savez_compressed(name + '_predictions.npz', **predictions)
        Path('invariance_results.json').write_text(json.dumps(results, indent=2) + '\n')
