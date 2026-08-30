import argparse
import concurrent.futures
import json
import time

import numpy as np

import solution
from acquisition import UNKNOWN, acquire, prior
from experiment import ORDERS, SUBSETS, practice, report, transform


def evaluate(task):
    index, table, orbitals, family = task
    solution.STARTED = time.process_time()
    energy = np.where(ORDERS <= 3, table, 0)
    terms = transform(energy)
    terms[ORDERS >= 4] = 0
    mean = solution.predict_prior(energy, orbitals, family)
    covariance = prior(terms, fifth_weight=2)
    queries, _, cost = acquire(terms, covariance, mean=mean, power=.8, return_queries=True, quints=0)
    energy[queries] = table[queries]
    design = SUBSETS[queries][:, UNKNOWN].astype(float)
    weights = np.linalg.solve(design @ covariance @ design.T + np.eye(len(queries)) * 1e-20, design @ covariance @ np.ones(len(UNKNOWN)))
    measured = energy[queries] - SUBSETS[queries] @ terms
    tail = mean[UNKNOWN].sum() + weights @ (measured - design @ mean[UNKNOWN])
    fallback_error = float(terms.sum() + tail - table[255])
    uncertainty = np.sqrt(max(0, covariance.sum() - weights @ (design @ covariance @ np.ones(len(UNKNOWN)))))
    tail = solution.physical_tail(energy, orbitals, family, terms, queries, weights, tail, uncertainty)
    return dict(index=int(index), family=int(family), error=float(terms.sum() + tail - table[255]), fallback=fallback_error, cpu=time.process_time() - solution.STARTED)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--practice', action='store_true')
    parser.add_argument('--count', type=int, default=300)
    parser.add_argument('--output', default='final_validation.json')
    parser.add_argument('--source', default='train.npz')
    arguments = parser.parse_args()
    if arguments.practice:
        energy, orbitals, families = practice()
    else:
        data = np.load(arguments.source)
        energy, orbitals, families = data['energies'][-1800:][:arguments.count], data['orbitals'][-1800:][:arguments.count], data['families'][-1800:][:arguments.count]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(evaluate, [(index, *row) for index, row in enumerate(zip(energy, orbitals, families))]))
    report(np.array([record['error'] for record in records]), families, 'solution')
    report(np.array([record['fallback'] for record in records]), families, 'fallback')
    print('CPU', sum(record['cpu'] for record in records), flush=True)
    with open(arguments.output, 'w') as handle:
        json.dump(records, handle, indent=2)


if __name__ == '__main__':
    main()
