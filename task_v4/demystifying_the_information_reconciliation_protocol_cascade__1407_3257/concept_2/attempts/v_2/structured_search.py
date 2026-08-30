import itertools
import json
import time


rows = [list(map(int, line.split())) for line in open('signatures.txt')][1:]
columns = [sum(1 << (64 * dimension + block) for dimension, block in enumerate(signature)) for signature in rows]
start = time.time()
for first, second in itertools.combinations(range(128), 2):
    basis = {}
    for block in range(64):
        left = 128 * block + first
        right = 128 * block + second
        value = columns[left] ^ columns[right]
        support = (1 << left) ^ (1 << right)
        while value:
            pivot = value.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = value, support
                break
            other, others = basis[pivot]
            value ^= other
            support ^= others
        if not value and support:
            errors = [bit for bit in range(8192) if support >> bit & 1]
            print('FOUND', first, second, len(errors), errors, flush=True)
            if 8 <= len(errors) <= 18:
                json.dump(errors, open('structured_core.json', 'w'))
                raise SystemExit
print('done', time.time() - start, flush=True)
