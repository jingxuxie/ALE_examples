import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contractor import hamiltonian_terms, measure
from engine import optimize
from benchmark import uniform


def exact(request):
    onsite, positions = hamiltonian_terms(request)
    length = request['n_sites']
    dimension = request['local_dim']
    matrix = np.zeros((dimension ** length,) * 2)
    for site in range(length):
        matrix += np.kron(np.kron(np.eye(dimension ** site), onsite[site]), np.eye(dimension ** (length - site - 1)))
        if site + 1 < length:
            matrix -= request['coupling'][site] * np.kron(np.kron(np.eye(dimension ** site), np.kron(positions[site], positions[site + 1])), np.eye(dimension ** (length - site - 2)))
    if request['sector'] != 'any':
        parity = np.indices((dimension,) * length).sum(axis=0).ravel() % 2
        indices = np.flatnonzero(parity == (request['sector'] == 'odd'))
        matrix = matrix[np.ix_(indices, indices)]
    return eigh(matrix, eigvals_only=True, subset_by_index=[0, 0])[0]


for sector in ('even', 'odd', 'any'):
    for mass in (.4, -.7, -2.8):
        request = uniform('exact', 4, 4, 16, mass, 1.4, 1.2, .7, sector)
        request['budget_seconds'] = time.process_time() + 10
        if sector == 'any':
            request['field'] = [.004, .002, -.001, -.003]
        reference = exact(request)
        result = measure(optimize(request), request)
        print(sector, mass, reference, result, 'error', result['energy'] - reference, flush=True)
        assert abs(result['energy'] - reference) < 1e-8
print('Exact checks passed')
