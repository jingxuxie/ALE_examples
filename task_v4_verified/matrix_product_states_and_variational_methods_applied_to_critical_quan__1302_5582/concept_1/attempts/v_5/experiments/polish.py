import os
import sys
import time
os.environ['OPENBLAS_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import numpy as np
from contractor import load_mps, save_mps, measure, hamiltonian_terms
from optimizer import local_basis, right_canonical, restore_basis, Clock
from fast import physical_action, left_step, right_step, site_update, center_energy
from relaxation import accelerate

request = json.load(open(sys.argv[1]))
tensors = load_mps(sys.argv[2], request)
onsite, positions = hamiltonian_terms(request)
transforms = local_basis(onsite, positions, True)
tensors = [physical_action(transform.T, tensor) for transform, tensor in zip(transforms, tensors)]
charges = [np.array([0])]
for tensor in tensors:
    allowed = charges[-1][:, None] ^ (np.arange(request['local_dim'])[None, :] % 2)
    norms = np.array([np.sum(tensor[allowed == charge]**2, axis=0) for charge in (0, 1)])
    charges.append(np.argmax(norms, axis=0))
right_canonical(tensors, charges)
length = len(tensors)
couplings = request['coupling']
empty = (np.zeros((1, 1)), np.zeros((1, 1)))
right_environments = [None]*length+[empty]
for site in range(length-1, -1, -1):
    right_environments[site] = right_step(right_environments[site+1], tensors[site], onsite[site], positions[site], couplings[site] if site+1 < length else 0.0)
clock = Clock(request, 0.0, time.monotonic())
energy = right_environments[0][0][0, 0]
best_energy = energy
best_tensors = [tensor.copy() for tensor in tensors]
amount = 1.0
stable = 0
for sweep in range(1000):
    previous_energy = energy
    previous = [tensor.copy() for tensor in tensors]
    left_environments = [empty]
    for site in range(length):
        site_update(tensors, charges, site, left_environments[site], right_environments[site+1], onsite, positions, couplings, 1, request['bond_cap'], 0.0, 1e-11, 8, clock)
        left_environments.append(left_step(left_environments[site], tensors[site], onsite[site], positions[site], couplings[site-1] if site else 0.0))
    for site in range(length-1, -1, -1):
        energy = site_update(tensors, charges, site, left_environments[site], right_environments[site+1], onsite, positions, couplings, -1, request['bond_cap'], 0.0, 1e-11, 8, clock)
        right_environments[site] = right_step(right_environments[site+1], tensors[site], onsite[site], positions[site], couplings[site] if site+1 < length else 0.0)
    tensors, charges, right_environments, energy, amount = accelerate(tensors, previous, charges, right_environments, onsite, positions, couplings, previous_energy, energy, amount, clock)
    print(sweep, energy, time.process_time(), flush=True)
    if energy < best_energy:
        best_energy = energy
        best_tensors = [tensor.copy() for tensor in tensors]
    stable = stable+1 if abs(previous_energy-energy) < 5e-14 else 0
    if clock.remaining() < 1 or (sweep > 12 and stable >= 8):
        break
state = restore_basis(best_tensors, transforms)
save_mps(sys.argv[3], state)
print('RESULT', time.process_time(), json.dumps(measure(state, request)), flush=True)
