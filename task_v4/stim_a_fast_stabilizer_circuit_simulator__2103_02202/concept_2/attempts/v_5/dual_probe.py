import json
import random
import time
from pathlib import Path
from probe import COLUMNS


def kernel_basis():
    basis = {}
    kernels = []
    for fault, initial in enumerate(COLUMNS):
        value = initial
        support = 1 << fault
        while value:
            pivot = value.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = value, support
                break
            value ^= basis[pivot][0]
            support ^= basis[pivot][1]
        if not value:
            kernels.append(support)
    return kernels


def main():
    kernels = kernel_basis()
    checks = [sum(((kernel >> fault) & 1) << index for index, kernel in enumerate(kernels)) for fault in range(512)]
    Path('dual_columns.txt').write_text(''.join(' '.join(f'{(column >> shift) & ((1 << 64) - 1):016x}' for shift in range(0, 320, 64)) + ' 1\n' for column in checks))
    generator = random.Random(8754)
    residual = 14
    pivots = 320 - residual
    split = pivots + (512 - pivots) // 2
    best = 513
    started = time.monotonic()
    for trial in range(200):
        permutation = list(range(512))
        generator.shuffle(permutation)
        columns = [checks[fault] for fault in permutation]
        for pivot in range(pivots):
            mask = 1 << pivot
            position = next(index for index in range(pivot, 512) if columns[index] & mask)
            columns[pivot], columns[position] = columns[position], columns[pivot]
            permutation[pivot], permutation[position] = permutation[position], permutation[pivot]
            change = columns[pivot] ^ mask
            columns = [value ^ change if value & mask else value for value in columns]
        heads = {}
        for first in range(pivots, split):
            for second in range(first + 1, split):
                value = columns[first] ^ columns[second]
                heads.setdefault(value >> pivots, []).append((value, first, second))
        for first in range(split, 512):
            for second in range(first + 1, 512):
                value = columns[first] ^ columns[second]
                for left_value, left_first, left_second in heads.get(value >> pivots, ()):
                    result = value ^ left_value
                    weight = result.bit_count() + 4
                    if weight < best:
                        best = weight
                        support = [permutation[index] for index in [first, second, left_first, left_second]]
                        support.extend(permutation[index] for index in range(pivots) if (result >> index) & 1)
                        print('dual best', best, 'trial', trial, 'seconds', time.monotonic() - started, flush=True)
                        Path('dual_best.json').write_text(json.dumps({'faults': sorted(support)}))
                        if best <= 32:
                            return
        if trial % 20 == 0:
            print('dual progress', trial, best, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
