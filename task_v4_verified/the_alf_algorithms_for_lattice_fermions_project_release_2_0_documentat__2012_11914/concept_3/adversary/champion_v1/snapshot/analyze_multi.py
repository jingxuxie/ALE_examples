import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from tune_nonparam import loss

cache = dict(np.load('multi_cache.npz'))
fits = dict(np.load('multi_fit_2.0.npz'))
nonparam = dict(np.load('multi_sweep.npz'))['0.15_20']
edges = np.linspace(-8, 8, 257)


def report(mass, name):
    errors = loss(mass, cache['truth'], edges)
    print(name, np.round(100 * np.exp(-np.array([errors[:128].mean(), errors[128:].mean()])), 3), flush=True)


for penalty in [0, 1, 2, 4, 8, 16]:
    for temperature in [1, 2, 5, 10]:
        criterion = fits['criterion'] + (penalty - 2) * np.repeat([3, 4, 5], 3)
        weights = np.exp(-.5 * (criterion - criterion.min(axis=1)[:, None]) / temperature)
        weights /= weights.sum(axis=1)[:, None]
        mass = np.sum(weights[:, :, None] * fits['mass'], axis=1)
        report(mass, (penalty, temperature))
for blend in [0, .2, .4, .6, .8, 1]:
    report(blend * nonparam + (1 - blend) * fits['prediction'], ('blend', blend))
