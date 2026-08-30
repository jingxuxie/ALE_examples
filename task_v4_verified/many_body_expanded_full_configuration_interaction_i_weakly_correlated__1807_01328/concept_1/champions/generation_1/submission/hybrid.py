import argparse
import concurrent.futures
import json
import os
import time

import numpy as np

from acquisition import CANDIDATES, DESIGN, UNKNOWN, acquire, prior
from experiment import MASKS, ORDERS, SUBSETS, practice, report, transform
from physical import Physical


def solve_one(task):
    index, energy, orbitals, family, mean = task
    started = time.process_time()
    terms = transform(energy)
    covariance = prior(terms, fifth_weight=2)
    queries, gp_estimate, cost = acquire(terms, covariance, mean=mean, power=0.8, return_queries=True, force_six=bool(os.getenv('SIX')))
    selected = np.array([np.flatnonzero(CANDIDATES == mask)[0] for mask in queries])
    design = DESIGN[selected]
    weights = np.linalg.solve(design @ covariance @ design.T + np.eye(len(queries)) * 1e-20, design @ covariance @ np.ones(len(UNKNOWN)))
    uncertainty = np.sqrt(max(0, np.sum(covariance) - weights @ (design @ covariance @ np.ones(len(UNKNOWN)))))
    gp_error = gp_estimate - terms[UNKNOWN].sum()
    record = dict(index=int(index), family=int(family), gp_error=float(gp_error), uncertainty=float(uncertainty), cost=int(cost), fits=[])
    if family in [1, 2, 5] or uncertainty > 1e-4:
        observed = np.r_[np.flatnonzero((ORDERS >= 1) & (ORDERS <= 3)), queries]
        problem = Physical(energy, orbitals, observed=observed, density_scale=0.15 if family == 5 else 0.07)
        problem.ridge = 0.01
        best_fit = np.inf
        for seed in range(4):
            result = problem.fit(seed, iterations=300, reduced=bool(os.getenv('REDUCED')), normalize=bool(os.getenv('NORMALIZE')))
            fit = float(np.linalg.norm(result.fun[:len(observed)]))
            fitted = problem.predict(result.x, np.r_[observed, 255])
            predicted = np.zeros(256)
            predicted[observed] = fitted[:-1]
            predicted[255] = fitted[-1]
            predicted_low = transform(predicted)
            predicted_low[ORDERS > 3] = 0
            predicted_tail = predicted - SUBSETS @ predicted_low
            correction = weights @ (design @ terms[UNKNOWN] - predicted_tail[queries])
            error = predicted_tail[255] + correction - terms[UNKNOWN].sum()
            record['fits'].append(dict(seed=seed, fit=fit, error=float(error), difference=float(error - gp_error), iterations=int(result.nfev)))
            best_fit = min(fit, best_fit)
            if best_fit < 0.08:
                break
    record['cpu'] = time.process_time() - started
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=600)
    parser.add_argument('--practice', action='store_true')
    parser.add_argument('--output', default='hybrid.json')
    arguments = parser.parse_args()
    if arguments.practice:
        energy, orbitals, families = practice()
        means = np.zeros_like(energy)
    else:
        data = np.load('train.npz')
        energy, orbitals, families = data['energies'][-1800:][:arguments.count], data['orbitals'][-1800:][:arguments.count], data['families'][-1800:][:arguments.count]
        means = np.zeros_like(energy)
        for order in [4, 5]:
            prediction = np.load('neural_validation' + str(order) + '.npz')
            means[:, prediction['masks']] = prediction['predicted'][:len(energy)]
        means[(families == 0) | (families == 3) | (families == 4)] = 0
    tasks = [(index, table, orbital, family, mean) for index, (table, orbital, family, mean) in enumerate(zip(energy, orbitals, families, means))]
    records = []
    started = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        for record in executor.map(solve_one, tasks):
            records.append(record)
            print(record, flush=True)
    with open(arguments.output, 'w') as handle:
        json.dump(records, handle, indent=2)
    print('elapsed', time.time() - started, 'CPU', sum(record['cpu'] for record in records), flush=True)


if __name__ == '__main__':
    main()
