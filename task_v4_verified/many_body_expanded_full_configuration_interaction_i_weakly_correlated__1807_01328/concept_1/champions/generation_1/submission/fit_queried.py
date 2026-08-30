import time

import numpy as np

from acquisition import CANDIDATES, COSTS, DESIGN, UNKNOWN, acquire, prior
from experiment import ORDERS, report, transform
from physical import Physical


def main():
    data = np.load('train.npz')
    energy, orbitals, families = data['energies'][-1800:], data['orbitals'][-1800:], data['families'][-1800:]
    terms = transform(energy)
    errors = []
    tested = []
    started = time.time()
    for index in range(120):
        if families[index] not in [1, 2, 5]:
            continue
        covariance = prior(terms[index], fifth_weight=2)
        queries, estimate, cost = acquire(terms[index], covariance, power=0.8, return_queries=True)
        observed = np.r_[np.flatnonzero((ORDERS >= 1) & (ORDERS <= 3)), queries]
        problem = Physical(energy[index], orbitals[index], observed=observed)
        problem.ridge = 0.01
        result = problem.fit(0, iterations=400)
        prediction = transform(problem.predict(result.x, np.arange(256)))
        selected = np.array([np.flatnonzero(CANDIDATES == mask)[0] for mask in queries])
        design = DESIGN[selected]
        weights = np.linalg.solve(design @ covariance @ design.T + np.eye(len(queries)) * 1e-20, design @ covariance @ np.ones(len(UNKNOWN)))
        correction = weights @ (design @ (terms[index, UNKNOWN] - prediction[UNKNOWN]))
        raw_error = prediction[UNKNOWN].sum() - terms[index, UNKNOWN].sum()
        error = raw_error + correction
        errors.append(error)
        tested.append(index)
        print(index, families[index], 'fit', np.linalg.norm(result.fun[:len(observed)]), 'raw', raw_error * 1e6, 'corrected', error * 1e6, 'seconds', time.time() - started, flush=True)
        if len(errors) % 12 == 0:
            report(np.array(errors), families[tested], 'physical corrected')
    np.savez('physical_validation.npz', errors=errors, indices=tested)


if __name__ == '__main__':
    main()
