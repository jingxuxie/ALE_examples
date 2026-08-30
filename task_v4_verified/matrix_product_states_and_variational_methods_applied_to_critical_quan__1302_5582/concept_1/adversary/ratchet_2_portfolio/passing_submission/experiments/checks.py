import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MPS_NATIVE'] = '1'
os.environ['MPS_EDGES'] = '1'
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import numpy as np
from scipy.linalg import eigh
from native import lowest
from optimizer import Clock, optimize
from contractor import hamiltonian_terms, measure, save_mps, load_mps

rng = np.random.default_rng(8432)
for constrained in (False, True):
    left, dimension, right = 4, 6, 3
    shape = (left, dimension, right)
    local_position = rng.normal(size=(dimension, dimension))
    left_position = rng.normal(size=(left, left))
    right_position = rng.normal(size=(right, right))
    matrices = [local_position, left_position, right_position]
    for matrix in matrices:
        matrix[:] = .3 * (matrix + matrix.T)
        if constrained:
            parity = np.arange(len(matrix)) % 2
            matrix[parity[:, None] == parity[None, :]] = 0.
    full_diagonal = rng.uniform(2, 8, size=shape)
    allowed = None
    if constrained:
        allowed = np.flatnonzero(((np.arange(left)[:, None, None] + np.arange(dimension)[None, :, None] + np.arange(right)[None, None, :]) % 2 == 0).ravel())
    size = np.prod(shape) if allowed is None else len(allowed)
    def unpack(vector):
        full = np.zeros(np.prod(shape))
        if allowed is None:
            full[:] = vector
        else:
            full[allowed] = vector
        return full.reshape(shape)
    def action(vector):
        tensor = unpack(vector)
        positioned = np.einsum('pq,aqb->apb', local_position, tensor)
        result = full_diagonal * tensor
        result -= .8 * np.einsum('ac,cpb->apb', left_position, positioned)
        result -= .6 * np.einsum('apc,cb->apb', positioned, right_position)
        return result.ravel() if allowed is None else result.ravel()[allowed]
    exact_matrix = np.column_stack([action(vector) for vector in np.eye(size)])
    exact_energy = eigh(exact_matrix, subset_by_index=(0, 0))[0][0]
    diagonal = np.diag(exact_matrix).copy()
    start = rng.normal(size=size)
    clock = Clock(dict(budget_seconds=10., wall_seconds=20.), time.process_time(), time.monotonic())
    vector, energy = lowest(left, dimension, right, full_diagonal, local_position,
                            left_position, right_position, .8, .6, allowed, diagonal,
                            start, 1e-11, 120, clock)
    assert abs(energy-exact_energy) < 1e-10, (energy, exact_energy)
    assert np.linalg.norm(action(vector)-energy*vector) < 1e-8
    print('native dense check', constrained, energy, flush=True)

for sector in ('any', 'even', 'odd'):
    request = dict(version=1, case_id='exact-check', seed=4, n_sites=4, local_dim=4,
                   bond_cap=16, sector=sector, omega=[.8, 1.1, .9, 1.3],
                   mass2=[-.07, -.03, .01, -.04], lambda4=[.1, .12, .2, .17],
                   field=[.001, -.002, .003, -.001] if sector == 'any' else [0.]*4,
                   coupling=[.4, .8, .6], budget_seconds=8., wall_seconds=30.)
    onsite, positions = hamiltonian_terms(request)
    dimension = request['local_dim']
    length = request['n_sites']
    def embed(operators):
        result = np.ones((1, 1))
        for site in range(length):
            result = np.kron(result, operators.get(site, np.eye(dimension)))
        return result
    exact_matrix = sum(embed({site: onsite[site]}) for site in range(length))
    exact_matrix -= sum(request['coupling'][site]*embed({site:positions[site], site+1:positions[site+1]}) for site in range(length-1))
    if sector != 'any':
        parities = np.indices((dimension,)*length).sum(axis=0).ravel()%2
        selected = np.flatnonzero(parities == int(sector == 'odd'))
        exact_matrix = exact_matrix[np.ix_(selected, selected)]
    exact_energy = eigh(exact_matrix, subset_by_index=(0,0))[0][0]
    tensors = optimize(request)
    save_mps('experiments/exact_check.npz', tensors)
    result = measure(load_mps('experiments/exact_check.npz', request), request)
    assert abs(result['energy']-exact_energy) < 1e-9, (sector, result, exact_energy)
    print('exact MPS check', sector, result, 'exact', exact_energy, flush=True)
print('All numerical checks passed.', flush=True)
