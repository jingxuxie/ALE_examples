import json
import os
import time

import numpy as np

from periodic import normalized
from spectra import walsh


def beam_subspaces(correlations, max_dimension=6, beam_size=300):
    rows = len(correlations)
    addresses = np.arange(rows)
    correlations = correlations.copy()
    correlations[0] = 0
    beam = [(float(correlations[0]), (0,))]
    results = []
    for dimension in range(1, max_dimension + 1):
        candidates = {}
        for score, subspace in beam:
            subspace_array = np.array(subspace)
            cosets = subspace_array[:, None] ^ addresses
            sums = correlations[cosets].sum(axis=0)
            representatives = np.min(cosets, axis=0) == addresses
            sums[~representatives] = -1e30
            sums[0] = -1e30
            best = np.argpartition(sums, -24)[-24:]
            for generator in best:
                extended = tuple(sorted(subspace + tuple(int(value ^ generator) for value in subspace)))
                candidates[extended] = score + sums[generator]
        beam = sorted(((score, subspace) for subspace, score in candidates.items()), reverse=True)[:beam_size]
        print('dim', dimension, 'best averages', [round(score / ((1 << dimension)-1), 3) for score, subspace in beam[:8]], flush=True)
        results.append(beam[:30])
    return results


if __name__ == '__main__':
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    for instance in suite['instances'][:3]:
        started = time.time()
        outputs, masks = normalized(instance)
        signs = 1 - 2 * outputs
        spectrum_sum = walsh(signs.sum(axis=0))
        spectrum_squares = sum(walsh(sign) ** 2 for sign in signs)
        correlations = walsh(spectrum_sum ** 2 - spectrum_squares).astype(float) / (len(signs[0]) * len(signs) * (len(signs)-1))
        print(instance['id'], 'mean', correlations[1:].mean(), 'max', correlations[1:].max(), flush=True)
        results = beam_subspaces(correlations)
        json.dump(results, open(instance['id'] + '_subspaces.json', 'w'))
        print('seconds', time.time() - started, flush=True)
