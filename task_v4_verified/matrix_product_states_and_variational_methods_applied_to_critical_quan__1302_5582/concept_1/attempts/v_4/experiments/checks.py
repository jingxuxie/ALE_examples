import os
import sys
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.linalg import eigh
from contractor import hamiltonian_terms, measure
import fast
import optimizer

random = np.random.default_rng(453)
tensor = random.normal(size=(5, 6, 7))
onsite = random.normal(size=(6, 6))
onsite += onsite.T
position = random.normal(size=(6, 6))
position += position.T
for side, size in [('left', 5), ('right', 7)]:
    environment = [random.normal(size=(size, size)) for index in range(2)]
    environment = [matrix + matrix.T for matrix in environment]
    expected = getattr(optimizer, side + '_step')(environment, tensor, onsite, position, .7)
    observed = getattr(fast, side + '_step')(environment, tensor, onsite, position, .7)
    assert np.max(np.abs(np.array(expected) - np.array(observed))) < 1e-10


def embed(operator, site, length, dimension):
    return np.kron(np.kron(np.eye(dimension**site), operator), np.eye(dimension**(length-site-1)))


for dimension, length, sector in [(4, 4, 'any'), (4, 4, 'even'), (4, 4, 'odd'),
                                  (5, 3, 'any'), (5, 3, 'even'), (5, 3, 'odd'),
                                  (8, 3, 'any')]:
    request = dict(n_sites=length, local_dim=dimension, bond_cap=16,
                   omega=[.7, 1.1, 1.3, .9], mass2=[-.1, -.03, .01, -.15],
                   lambda4=[.1, .08, .2, .05], coupling=[.5, 1.2, .4],
                   field=[.002, -.003, .001, .002] if sector == 'any' else [0.0]*length,
                   sector=sector, budget_seconds=6., wall_seconds=30.)
    for key in ['omega', 'mass2', 'lambda4', 'field']:
        request[key] = request[key][:length]
    request['coupling'] = request['coupling'][:length-1]
    if dimension == 8:
        request.update(omega=[.55]*length, mass2=[-.2]*length, lambda4=[.05]*length,
                       coupling=[.05]*(length-1), field=[0.0]*length)
    onsite, positions = hamiltonian_terms(request)
    hamiltonian = sum(embed(matrix, site, length, dimension) for site, matrix in enumerate(onsite))
    for site, coupling in enumerate(request['coupling']):
        hamiltonian -= coupling * embed(positions[site], site, length, dimension) @ embed(positions[site+1], site+1, length, dimension)
    if sector != 'any':
        parity = np.arange(dimension) % 2
        for site in range(length-1):
            parity = (parity[:, None] ^ (np.arange(dimension)[None, :] % 2)).ravel()
        indices = np.flatnonzero(parity == int(sector == 'odd'))
        hamiltonian = hamiltonian[np.ix_(indices, indices)]
    exact = eigh(hamiltonian, subset_by_index=(0, 0), eigvals_only=True)[0]
    result = measure(fast.optimize(request), request)
    print(sector, exact, result, flush=True)
    assert abs(result['energy'] - exact) < 1e-8
print('All algebra and exact-diagonalization checks passed.')
