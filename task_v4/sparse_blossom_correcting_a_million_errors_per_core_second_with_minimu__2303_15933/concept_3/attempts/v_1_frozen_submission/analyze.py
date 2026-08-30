import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import json
import sys
from pathlib import Path

import numpy as np
from scipy.special import ndtr

from solution import Model


episodes = json.loads(Path('../../participant/input/training.json').read_text())['episodes']
information = [Model(episode['spec']).fisher(np.log(episode['rates'])) for episode in episodes]
for filename in sys.argv[1:]:
    results = json.loads(Path(filename).read_text())
    cells = {}
    actual = {}
    clipped = {}
    for result in results:
        index = result['episode']
        spec = episodes[index]['spec']
        model = Model(spec)
        covariance = np.linalg.inv(np.einsum('a,akl->kl', result['used'], information[index]))
        variance = covariance.diagonal()
        standard = np.sqrt(variance)
        lower = (model.bounds[:, 0] - np.log(episodes[index]['rates'])) / standard
        upper = (model.bounds[:, 1] - np.log(episodes[index]['rates'])) / standard
        density_low = np.exp(-0.5 * lower ** 2) / np.sqrt(2 * np.pi)
        density_high = np.exp(-0.5 * upper ** 2) / np.sqrt(2 * np.pi)
        clipped_variance = variance * (ndtr(upper) - ndtr(lower) + lower * density_low - upper * density_high
                                       + lower ** 2 * ndtr(lower) + upper ** 2 * ndtr(-upper))
        for channel, predicted, bounded in zip(spec['channels'], variance, clipped_variance):
            cell = (spec['regime'], channel['family'])
            cells.setdefault(cell, []).append(predicted)
            clipped.setdefault(cell, []).append(bounded)
        for family, score in result['scores'].items():
            actual.setdefault((spec['regime'], family), []).append(score ** 2)
    summary = {}
    for name, values in [('actual', actual), ('predicted', cells), ('clipped', clipped)]:
        scores = {str(key): float(np.sqrt(np.mean(value))) for key, value in values.items()}
        summary[name] = dict(mean=float(np.mean(list(scores.values()))), worst=max(scores.values()), cells=scores)
    print(filename, json.dumps(summary), flush=True)
