import json
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


rows = np.loadtxt('signatures.txt', dtype=int, skiprows=1)
size = len(rows)
check_count = 384
row_indices = []
column_indices = []
entries = []
for bit, signature in enumerate(rows):
    for dimension, block in enumerate(signature):
        row_indices.append(64 * dimension + block)
        column_indices.append(bit)
        entries.append(1)
for check in range(check_count):
    row_indices.append(check)
    column_indices.append(size + check)
    entries.append(-2)
for bit in range(size):
    row_indices.append(check_count)
    column_indices.append(bit)
    entries.append(1)
matrix = coo_matrix((entries, (row_indices, column_indices)), shape=(check_count + 1, size + check_count)).tocsc()
lower = np.zeros(size + check_count)
upper = np.r_[np.ones(size), np.full(check_count, 9)]
objective = np.r_[np.ones(size), np.zeros(check_count)]
constraints = LinearConstraint(matrix, np.r_[np.zeros(check_count), 8], np.r_[np.zeros(check_count), 18])
print('Starting', time.time(), flush=True)
result = milp(objective, integrality=np.ones(size + check_count), bounds=Bounds(lower, upper), constraints=constraints, options={'time_limit': 300, 'disp': True})
print(result, flush=True)
if result.x is not None:
    errors = np.flatnonzero(result.x[:size] > 0.5).tolist()
    with open('milp_core.json', 'w') as stream:
        json.dump(errors, stream)
