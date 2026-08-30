import os
import sys
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import numpy as np
from native import lowest_site
from fast import lowest, physical_action
from solver import optimize
from contractor import hamiltonian_terms, measure, validate_mps


class Clock:
    def remaining(self):
        return 100.0


rng = np.random.default_rng(3678)
kernel_errors = []
for shape in [(1, 8, 12), (12, 14, 24), (24, 14, 24), (12, 8, 1)]:
    left, dimension, right = shape
    left_charge = np.arange(left) % 2
    physical_charge = np.arange(dimension) % 2
    right_charge = np.arange(right) % 2
    def operator(size, charge):
        matrix = rng.normal(size=(size, size))
        matrix = (matrix+matrix.T)*.05
        return matrix*((charge[:, None] ^ charge[None, :]) == 1)
    left_position = operator(left, left_charge)
    position = operator(dimension, physical_charge)
    right_position = operator(right, right_charge)
    diagonal = 10+rng.uniform(0, 4, shape)
    allowed = (left_charge[:, None, None] ^ physical_charge[None, :, None] ^ right_charge[None, None, :]) == 0
    current = rng.normal(size=shape)*allowed
    def matvec(vector):
        tensor = vector.reshape(shape)
        position_tensor = physical_action(position, tensor)
        return (diagonal*tensor-.8*(left_position @ position_tensor.reshape(left, -1)).reshape(shape)
                -1.1*(position_tensor.reshape(-1, right) @ right_position).reshape(shape)).ravel()
    for steps in [1, 4, 8, 24]:
        reference, reference_energy = lowest(matvec, diagonal.ravel(), current.ravel(), 1e-10, steps, Clock())
        actual, energy = lowest_site(diagonal.ravel(), current, left_position, position, right_position, .8, 1.1, 1e-10, steps)
        error = abs(energy-reference_energy)
        kernel_errors.append(error)
        assert error < 1e-9
        assert abs(reference @ actual) > 1-1e-8
        assert np.max(np.abs(actual.reshape(shape)[~allowed])) < 1e-14

request = dict(version=1, case_id='exact-check', seed=1, n_sites=4, local_dim=4,
    bond_cap=16, omega=[.6, 1.2, .9, 1.5], mass2=[-.1, -.07, .02, -.05],
    lambda4=[.12, .20, .08, .14], field=[0.0]*4, coupling=[.9, .17, 1.3],
    budget_seconds=6, wall_seconds=30)
onsite, positions = hamiltonian_terms(request)
identity = np.eye(4)
def product(operators):
    result = np.ones((1, 1))
    for operator in operators:
        result = np.kron(result, operator)
    return result
hamiltonian = np.zeros((256, 256))
for site in range(4):
    operators = [identity]*4
    operators[site] = onsite[site]
    hamiltonian += product(operators)
for site in range(3):
    operators = [identity]*4
    operators[site:site+2] = positions[site:site+2]
    hamiltonian -= request['coupling'][site]*product(operators)
parities = np.array([sum(np.unravel_index(index, (4,)*4)) % 2 for index in range(256)])
exact_errors = {}
for charge, sector in enumerate(['even', 'odd']):
    request['sector'] = sector
    indices = np.flatnonzero(parities == charge)
    exact = np.linalg.eigvalsh(hamiltonian[np.ix_(indices, indices)])[0]
    tensors = optimize(request)
    validate_mps(tensors, request)
    result = measure(tensors, request)
    exact_errors[sector] = result['energy']-exact
    assert abs(exact_errors[sector]) < 1e-9
    assert abs(result['parity']-(-1)**charge) < 1e-12
print(json.dumps(dict(native_equivalence_max_error=max(kernel_errors), exact_energy_errors=exact_errors, status='PASS'), indent=2))
