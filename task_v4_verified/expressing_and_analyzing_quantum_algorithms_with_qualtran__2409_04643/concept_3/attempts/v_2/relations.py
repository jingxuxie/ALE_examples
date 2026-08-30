from analyze import SUITE, np
from spectra import walsh
from itertools import combinations
import time

def truth_bits(values):
    return int.from_bytes(np.packbits(np.array(values, dtype=np.uint8), bitorder='little').tobytes(), 'little')

def monomials(width, degree):
    return [sum(1 << bit for bit in combo) for size in range(degree + 1) for combo in combinations(range(width), size)]

def columns(width):
    addresses = np.arange(1 << width)
    return [truth_bits((addresses & mask) == mask) for mask in range(1 << width)]

def nullspace(vectors):
    pivots = {}
    kernel = []
    for index, vector in enumerate(vectors):
        expression = 1 << index
        while vector:
            pivot = vector.bit_length() - 1
            if pivot in pivots:
                previous, combination = pivots[pivot]
                vector ^= previous
                expression ^= combination
            else:
                pivots[pivot] = vector, expression
                break
        if not vector:
            kernel.append(expression)
    return kernel

if __name__ == '__main__':
    for inst in SUITE:
        width = inst['n']
        table = np.array(inst['table'])
        cols = columns(width)
        print(inst['id'], flush=True)
        for bit in range(inst['m']):
            values = (table >> bit) & 1
            spectrum = walsh(1 - 2 * values)
            masks = [mask for mask in range(1 << width) if mask.bit_count() == 3]
            mask = max(masks, key=lambda mask: spectrum[mask])
            residual = truth_bits(values) ^ truth_bits([int(addr & mask).bit_count() % 2 for addr in range(len(table))])
            counts = []
            for degree in (1, 2, 3, 4):
                mons = monomials(width, degree)
                annihilate = len(nullspace([cols[mon] & residual for mon in mons]))
                inverse = len(nullspace([cols[mon] & (residual ^ cols[0]) for mon in mons]))
                counts.append((degree, annihilate, inverse))
            print(bit, 'annihilators', counts, flush=True)
            relations = []
            function = truth_bits(values)
            for degree in (1, 2, 3):
                lower = monomials(width, degree)
                higher = monomials(width, degree + 1)
                kernel = nullspace([cols[mon] for mon in higher] + [cols[mon] & function for mon in lower])
                relations.append((degree, len(kernel)))
            print('affine factor relations', relations, flush=True)
