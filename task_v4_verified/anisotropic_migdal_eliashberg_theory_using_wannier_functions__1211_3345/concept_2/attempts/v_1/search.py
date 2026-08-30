import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import qr
from scipy.optimize import Bounds, LinearConstraint, linprog, minimize

PARTICIPANT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/anisotropic_migdal_eliashberg_theory_using_wannier_functions__1211_3345/concept_2/participant')
sys.dont_write_bytecode = True
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
from physics import EliashbergSolver, constraint_report, load_instance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=48)
    parser.add_argument('--starts', type=int, default=8)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'witness.npz')
    arguments = parser.parse_args()
    started = time.monotonic()
    instance = load_instance(PARTICIPANT / 'input')
    config = instance['config']
    rows, columns = np.triu_indices(8, 1)
    edges = len(rows)
    variables = 3 * edges
    reference = instance['reference'][:, rows, columns].ravel()
    incidence = np.zeros((8, edges))
    incidence[rows, np.arange(edges)] = instance['weights'][columns]
    incidence[columns, np.arange(edges)] = instance['weights'][rows]
    equality = np.vstack([np.kron(np.eye(3), incidence), np.tile(np.eye(edges), (1, 3))])
    target = np.concatenate([
        (instance['row_sums'] - instance['diagonal'] * instance['weights']).ravel(),
        instance['static'][rows, columns],
    ])
    _, triangular, pivot = qr(equality.T, pivoting=True, mode='economic')
    rank = np.linalg.matrix_rank(triangular)
    equality, target = equality[pivot[:rank]], target[pivot[:rank]]
    bounds = Bounds(np.full(variables, config['entry_lower']), np.full(variables, config['entry_upper']))
    linear_constraint = LinearConstraint(equality, target, target)
    energies = instance['energies_mev'] * np.array([1.05, 1, 0.95])
    solver = EliashbergSolver(instance['weights'], instance['row_sums'], energies, config)

    def unpack(values):
        modes = np.zeros((3, 8, 8))
        modes[:, np.arange(8), np.arange(8)] = instance['diagonal']
        modes[:, rows, columns] = values.reshape(3, edges)
        modes[:, columns, rows] = values.reshape(3, edges)
        return modes

    def temperature(values):
        return solver.critical_temperature(unpack(values), arguments.count)['tc_kelvin']

    def eigengrad(values, fixed_temperature):
        result = solver.eigenpair(unpack(values), fixed_temperature, arguments.count, gradient=True)
        return result['eigenvalue'], 2 * result['gradient'][:, rows, columns].ravel()

    def vertex(gradient):
        result = linprog(gradient, A_eq=equality, b_eq=target,
                         bounds=list(zip(bounds.lb, bounds.ub)), method='highs')
        if not result.success:
            raise RuntimeError(result.message)
        return result.x

    baseline_temperature = temperature(reference)
    print('baseline', baseline_temperature, 'rank', rank, 'elapsed', time.monotonic() - started, flush=True)
    low = reference.copy()
    low_temperature = baseline_temperature
    for outer in range(5):
        result = minimize(lambda values: eigengrad(values, low_temperature), low,
                          method='SLSQP', jac=True, bounds=bounds,
                          constraints=[linear_constraint],
                          options={'ftol': 2e-12, 'maxiter': 500})
        low = result.x
        updated_temperature = temperature(low)
        print('low', outer, result.success, result.message, result.nit, updated_temperature,
              'elapsed', time.monotonic() - started, flush=True)
        if abs(updated_temperature - low_temperature) < 1e-7:
            break
        low_temperature = updated_temperature

    generator = np.random.default_rng(872612)
    best_high = reference.copy()
    best_temperature = baseline_temperature
    summaries = []
    for start in range(arguments.starts):
        high = reference.copy() if start == 0 else vertex(generator.normal(size=variables))
        high_temperature = temperature(high)
        for iteration in range(40):
            eigenvalue, gradient = eigengrad(high, high_temperature)
            proposed = vertex(-gradient)
            gap = gradient @ (proposed - high)
            if gap < 1e-11:
                break
            high = proposed
            high_temperature = temperature(high)
        print('high', start, iteration, high_temperature, 'ratio', high_temperature / low_temperature,
              'elapsed', time.monotonic() - started, flush=True)
        summaries.append({'start': start, 'temperature': high_temperature})
        if high_temperature > best_temperature:
            best_high, best_temperature = high.copy(), high_temperature
            kernels = np.stack([unpack(best_high), unpack(low)])
            report, canonical = constraint_report(kernels, instance)
            if not report['admissible']:
                raise RuntimeError(report)
            np.savez_compressed(arguments.output, kernels=canonical)
            print('saved', arguments.output, report, flush=True)
    metadata = {'count': arguments.count, 'family': 'compressed_spectrum',
                'baseline_temperature': baseline_temperature,
                'high_temperature': best_temperature, 'low_temperature': low_temperature,
                'ratio': best_temperature / low_temperature, 'starts': summaries}
    arguments.output.with_suffix('.search.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
