import ctypes
from pathlib import Path

import numpy as np


def run():
    rng = np.random.default_rng(124977)
    count = 250000
    directions = rng.normal(size=(count, 5, 3))
    directions /= np.linalg.norm(directions, axis=2)[:, :, None]
    energies = rng.gamma(2, 1, (count, 5))
    families = np.arange(count) % 5
    energies[families == 1, 3] *= 10 ** rng.uniform(-4.5, -1, np.sum(families == 1))
    for family, pairs in [(2, [(2, 3)]), (3, [(2, 3), (0, 4)]), (4, [(2, 3), (2, 4)])]:
        indices = np.flatnonzero(families == family)
        for first, second in pairs:
            perturbation = 10 ** rng.uniform(-2.5, -0.35, len(indices))
            directions[indices, second] = directions[indices, first] + perturbation[:, None] * rng.normal(size=(len(indices), 3))
            directions[indices, second] /= np.linalg.norm(directions[indices, second], axis=1)[:, None]
    directions = directions.astype(np.longdouble)
    directions /= np.sqrt(np.sum(directions**2, axis=2))[:, :, None]
    energies = energies.astype(np.longdouble)
    spatial = energies[:, :, None] * directions
    invariants = np.stack([2 * energies[:, first] * energies[:, second] * (1 - np.sum(directions[:, first] * directions[:, second], axis=1)) for first in range(5) for second in range(first + 1, 5)], axis=1)
    mass2 = invariants.sum(axis=1)
    invariants /= mass2[:, None]
    momenta = np.concatenate([spatial, energies[:, :, None]], axis=2) / np.sqrt(mass2)[:, None, None]
    selected = invariants.min(axis=1) > 1e-10
    invariants = np.ascontiguousarray(invariants[selected], dtype=np.float64)
    momenta = np.ascontiguousarray(momenta[selected], dtype=np.float64)
    families = families[selected]
    pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
    library = ctypes.CDLL(str(Path(__file__).resolve().with_name('kernel.so')))
    library.predict.argtypes = [ctypes.c_size_t, pointer, pointer, pointer, ctypes.c_int]
    library.predict.restype = None
    results = []
    for mode in [0, 1]:
        output = np.empty(len(invariants))
        library.predict(len(output), invariants, momenta, output, mode)
        results.append(output)
    error = results[0] - results[1]
    print('stress count', len(error), 'rmse', np.mean(error**2)**0.5, 'max', np.max(abs(error)), flush=True)
    for family in range(5):
        group = error[families == family]
        print(family, np.mean(group**2)**0.5, np.max(abs(group)), flush=True)
    worst = np.argsort(abs(error))[-20:]
    print('worst', list(zip(worst, error[worst])), flush=True)


if __name__ == '__main__':
    run()
