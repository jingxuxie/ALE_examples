import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import ctypes
import itertools
import time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/openfermion_the_electronic_structure_package_for_quantum_computers__1710_07629/concept_3/participant/input')
LIBRARY = ctypes.CDLL(str(ROOT / 'hubbard.so'))
POINTER = ctypes.POINTER(ctypes.c_double)
LIBRARY.ground_energy.argtypes = [ctypes.c_int] * 3 + [POINTER] * 5 + [ctypes.c_int, ctypes.c_double, POINTER]
LIBRARY.ground_energy.restype = ctypes.c_double

def pointer(array):
    return array.ctypes.data_as(POINTER) if array is not None else None

def trial(sites, particles, orbitals):
    states = sorted(itertools.combinations(range(sites), particles), key=lambda occupied: sum(1 << site for site in occupied))
    matrices = orbitals[np.array(states), :particles]
    return np.ascontiguousarray(np.linalg.det(matrices))

def calculate(hopping, interaction, potential, steps=60, tolerance=1e-7, use_trial=True):
    sites = len(interaction)
    half = sites // 2
    arrays = [np.ascontiguousarray(array) for array in (hopping, interaction, potential)]
    if use_trial:
        _, orbitals = np.linalg.eigh(-hopping + np.diag(potential + (interaction - np.mean(interaction)) * 0.5))
        trials = {particles: trial(sites, particles, orbitals) for particles in (half - 1, half, half + 1)}
    else:
        trials = {particles: None for particles in (half - 1, half, half + 1)}
    energies = []
    histories = []
    for up, down in [(half, half), (half + 1, half), (half, half - 1), (half + 1, half - 1)]:
        history = np.full(steps, np.nan)
        energy = LIBRARY.ground_energy(sites, up, down, *[pointer(array) for array in arrays],
                                      pointer(trials[up]), pointer(trials[down]), steps, tolerance, pointer(history))
        energies.append(energy)
        histories.append(history)
    return np.array([energies[1] + energies[2] - 2 * energies[0], energies[3] - energies[0]]), np.array(histories)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=16)
    parser.add_argument('--steps', type=int, default=60)
    parser.add_argument('--tolerance', type=float, default=1e-7)
    parser.add_argument('--random', action='store_true')
    args = parser.parse_args()
    data = np.load(ASSETS / 'validation.npz')
    results = []
    histories = []
    start = time.perf_counter()
    for index in range(args.count):
        sites = int(data['n_sites'][index])
        tick = time.perf_counter()
        result, history = calculate(data['hopping'][index, :sites, :sites], data['interaction'][index, :sites],
                                    data['potential'][index, :sites], args.steps, args.tolerance, not args.random)
        print(index, sites, int(data['family'][index]), 'time', round(time.perf_counter() - tick, 4),
              'error', result - data['gaps'][index], 'iterations', np.sum(np.isfinite(history), axis=1) * 5 + 5, flush=True)
        results.append(result)
        histories.append(history)
    results = np.array(results)
    print('TOTAL', time.perf_counter() - start, 'RMSE', np.mean((results - data['gaps'][:args.count]) ** 2, axis=0) ** 0.5, flush=True)
    np.savez(ROOT / f'benchmark_{args.steps}.npz', predictions=results, histories=histories)
