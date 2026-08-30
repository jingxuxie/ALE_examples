import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import numpy as np
from scipy.linalg import eigh
from native import lowest
from optimizer import Clock

random = np.random.default_rng(227)
for trial in range(16):
    left = int(random.integers(1, 8))
    dimension = int(random.integers(3, 8))
    right = int(random.integers(1, 8))
    left_charge = random.integers(0, 2, size=left)
    right_charge = random.integers(0, 2, size=right)
    physical_charge = np.arange(dimension) % 2
    matrices = []
    for charges in (physical_charge, left_charge, right_charge):
        matrix = random.normal(size=(len(charges), len(charges))) * .2
        matrix += matrix.T
        matrix[charges[:, None] == charges[None, :]] = 0.
        matrices.append(matrix)
    position, left_position, right_position = matrices
    shape = left, dimension, right
    full_diagonal = random.uniform(1., 4., size=shape)
    allowed = np.flatnonzero((left_charge[:, None, None] ^ physical_charge[None, :, None] ^ right_charge[None, None, :]).ravel() == 0)
    def action(vector):
        tensor = np.zeros(left*dimension*right)
        tensor[allowed] = vector
        tensor = tensor.reshape(shape)
        positioned = np.einsum('pq,aqb->apb', position, tensor)
        image = full_diagonal*tensor
        image -= .7*np.einsum('ab,bpr->apr', left_position, positioned)
        image -= .9*np.einsum('apr,rs->aps', positioned, right_position)
        return image.ravel()[allowed]
    matrix = np.column_stack([action(vector) for vector in np.eye(len(allowed))])
    reference = eigh(matrix, subset_by_index=(0, 0), check_finite=False)[0][0]
    clock = Clock(dict(budget_seconds=5., wall_seconds=10.), time.process_time(), time.monotonic())
    vector, energy = lowest(left, dimension, right, full_diagonal, position,
                            left_position, right_position, .7, .9, allowed,
                            np.diag(matrix).copy(), random.normal(size=len(allowed)),
                            1e-11, 200, clock)
    residual = np.linalg.norm(action(vector)-energy*vector)
    assert abs(energy-reference) < 1e-10 and residual < 1e-8, (trial, energy, reference, residual)
    print(trial, shape, len(allowed), abs(energy-reference), residual, flush=True)
print('All 16 shuffled-charge and odd-dimension checks passed.', flush=True)
