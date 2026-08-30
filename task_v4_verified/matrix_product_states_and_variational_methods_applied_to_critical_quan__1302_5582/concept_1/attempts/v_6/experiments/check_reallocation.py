import os
import sys
import time

os.environ.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from contractor import hamiltonian_terms, measure
from optimizer import Clock, local_basis, right_canonical, restore_basis
from fast import left_step, right_step
from variational import allocate_pair


for seed in range(6):
    rng = np.random.default_rng(seed)
    length, dimension, cap = 6, 4, 3
    request = dict(n_sites=length, local_dim=dimension, bond_cap=cap,
                   sector='odd' if seed % 2 else 'even', omega=rng.uniform(0.6, 1.6, length).tolist(),
                   mass2=rng.uniform(-0.2, 0.02, length).tolist(),
                   lambda4=rng.uniform(0.05, 0.3, length).tolist(),
                   coupling=rng.uniform(0.05, 1.5, length - 1).tolist(), field=[0.0] * length,
                   budget_seconds=100, wall_seconds=200)
    clock = Clock(request, time.process_time(), time.monotonic())
    onsite, positions = hamiltonian_terms(request)
    transforms = local_basis(onsite, positions, True)
    charges = [np.array([0])] + [np.array([0, 0, 1]) for site in range(length - 1)] + [np.array([seed % 2])]
    tensors = []
    for site in range(length):
        allowed = (charges[site][:, None, None] ^ (np.arange(dimension)[None, :, None] % 2)
                   ^ charges[site + 1][None, None, :]) == 0
        tensors.append(rng.normal(size=allowed.shape) * allowed)
    right_canonical(tensors, charges)
    empty = (np.zeros((1, 1)), np.zeros((1, 1)))
    right_environments = [None] * (length + 1)
    right_environments[length] = empty
    for site in range(length - 1, -1, -1):
        right_environments[site] = right_step(right_environments[site + 1], tensors[site],
            onsite[site], positions[site], request['coupling'][site] if site + 1 < length else 0.0)
    left_environments = [empty]
    previous = measure(restore_basis(tensors, transforms), request)['energy']
    for site in range(length - 1):
        energy = allocate_pair(tensors, charges, site, left_environments[site], right_environments[site + 2],
            onsite, positions, request['coupling'], cap, clock, (left_environments, right_environments))
        left_environments.append(left_step(left_environments[site], tensors[site], onsite[site], positions[site],
            request['coupling'][site - 1] if site else 0.0))
        actual = measure(restore_basis(tensors, transforms), request)['energy']
        assert actual <= previous + 1e-9, (seed, site, previous, actual)
        assert abs(actual - energy) < 1e-9, (seed, site, energy, actual)
        previous = actual
    print('seed', seed, 'energy', previous, 'charges', [int(np.sum(charge)) for charge in charges], flush=True)
print('All random-state reallocation and environment checks passed.')
