from analyze import SUITE, np, anf, rank
from relations import truth_bits
from itertools import combinations
from collections import Counter
import json

for inst in SUITE:
    width, outputs = inst['n'], inst['m']
    fixed_count = 3 if width < 12 else 4
    remaining = width - fixed_count
    degree2 = truth_bits([mask.bit_count() >= 2 for mask in range(1 << remaining)])
    degree3 = truth_bits([mask.bit_count() >= 3 for mask in range(1 << remaining)])
    table = np.array(inst['table'])
    results = []
    for fixed_bits in combinations(range(width), fixed_count):
        other_bits = [bit for bit in range(width) if bit not in fixed_bits]
        coefficient_vectors = []
        for fixed_address in range(1 << fixed_count):
            fixed_offset = sum(((fixed_address >> index) & 1) << bit for index, bit in enumerate(fixed_bits))
            addresses = [fixed_offset | sum(((address >> index) & 1) << bit for index, bit in enumerate(other_bits)) for address in range(1 << remaining)]
            coeff = anf(table[addresses])
            coefficient_vectors.extend(truth_bits((coeff >> bit) & 1) for bit in range(outputs))
        quadratic_dimension = rank([vector & degree2 for vector in coefficient_vectors]) - rank([vector & degree3 for vector in coefficient_vectors])
        results.append((quadratic_dimension, fixed_bits))
    print(inst['id'], Counter(result[0] for result in results), sorted(results, reverse=True)[:12], flush=True)
