import os
import sys
import time

os.environ.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy.linalg import eigh

from contractor import hamiltonian_terms, measure
from production import optimize


def embed(operators):
    product = np.ones((1, 1))
    for operator in operators:
        product = np.kron(product, operator)
    return product


request = dict(version=1, case_id='exact-check', seed=4, n_sites=4,
               local_dim=4, bond_cap=16, omega=[0.7, 0.8, 1.0, 0.6],
               mass2=[-0.02, -0.06, -0.09, 0.01], lambda4=[0.06, 0.1, 0.08, 0.2],
               coupling=[1.0, 0.1, 1.3], field=[0.0] * 4,
               sector='even', budget_seconds=3, wall_seconds=20)
onsite, positions = hamiltonian_terms(request)
identity = np.eye(4)
matrix = np.zeros((256, 256))
for site in range(4):
    operators = [identity] * 4
    operators[site] = onsite[site]
    matrix += embed(operators)
for site in range(3):
    operators = [identity] * 4
    operators[site] = positions[site]
    operators[site + 1] = positions[site + 1]
    matrix -= request['coupling'][site] * embed(operators)
parity = np.array([sum(np.unravel_index(index, (4,) * 4)) % 2 for index in range(256)])
for sector, charge in [('even', 0), ('odd', 1)]:
    request['sector'] = sector
    indices = np.flatnonzero(parity == charge)
    exact_energy = eigh(matrix[np.ix_(indices, indices)], eigvals_only=True)[0]
    started = time.process_time()
    state = optimize(request)
    measurement = measure(state, request)
    error = measurement['energy'] - exact_energy
    print(sector, 'exact', exact_energy, 'MPS', measurement, 'error', error,
          'cpu', time.process_time() - started, flush=True)
    assert abs(error) < 2e-8
    assert abs(measurement['parity'] - (1 - 2 * charge)) < 1e-12
