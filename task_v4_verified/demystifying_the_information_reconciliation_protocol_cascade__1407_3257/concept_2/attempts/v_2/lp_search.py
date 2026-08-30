import json
import sys
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, vstack


seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
generator = np.random.default_rng(seed)
signatures = np.loadtxt('signatures.txt', dtype=int, skiprows=1)
size = len(signatures)
check_count = 384
variable_count = size + check_count
edge_bits = np.repeat(np.arange(size), 6)
edge_checks = (signatures + np.arange(6) * 64).reshape(-1)
edge_count = len(edge_bits)
row_indices = np.r_[edge_checks, np.arange(check_count)]
column_indices = np.r_[edge_bits, size + np.arange(check_count)]
data = np.r_[np.ones(edge_count), np.full(check_count, -2.0)]
equality = coo_matrix((data, (row_indices, column_indices)), shape=(check_count, variable_count)).tocsc()
row_indices = np.r_[np.arange(edge_count), np.arange(edge_count), np.full(size, edge_count)]
column_indices = np.r_[edge_bits, size + edge_checks, np.arange(size)]
data = np.r_[np.ones(edge_count), -np.ones(edge_count), np.ones(size)]
inequality = coo_matrix((data, (row_indices, column_indices)), shape=(edge_count + 1, variable_count)).tocsc()
upper = np.r_[np.zeros(edge_count), 18]
columns = [sum(1 << int(64 * dimension + block) for dimension, block in enumerate(signature)) for signature in signatures]

for trial in range(10):
    root = (seed + trial * 11) % 64
    bounds = np.c_[np.zeros(variable_count), np.ones(variable_count)]
    bounds[(seed + trial * 587) % size] = 1
    objective = np.r_[1 + 0.2 * generator.random(size), np.zeros(check_count)]
    for iteration in range(8):
        result = linprog(objective, A_ub=inequality, b_ub=upper, A_eq=equality, b_eq=np.zeros(check_count), bounds=bounds, method='highs', options={'time_limit': 60})
        if result.x is None:
            print('FAILED', root, iteration, result.message, flush=True)
            break
        values = result.x[:size]
        print('LP', root, iteration, 'weight', values.sum(), 'nonzero', np.count_nonzero(values > 1e-7), 'ones', np.count_nonzero(values > 1 - 1e-7), flush=True)
        order = np.argsort(-values)[:350].tolist()
        json.dump(order, open(f'lp_top_{seed}.json', 'w'))
        basis = {}
        for bit in order:
            value = columns[bit]
            support = 1 << bit
            while value:
                pivot = value.bit_length() - 1
                if pivot not in basis:
                    basis[pivot] = value, support
                    break
                other, others = basis[pivot]
                value ^= other
                support ^= others
            if not value and 8 <= support.bit_count() <= 18:
                core = [position for position in range(size) if support >> position & 1]
                print('FOUND', core, flush=True)
                json.dump(core, open(f'lp_core_{seed}.json', 'w'))
                raise SystemExit
        epsilon = max(0.01, 0.2 * 0.6 ** iteration)
        objective[:size] = (1 + 0.05 * generator.random(size)) / (epsilon + values)
