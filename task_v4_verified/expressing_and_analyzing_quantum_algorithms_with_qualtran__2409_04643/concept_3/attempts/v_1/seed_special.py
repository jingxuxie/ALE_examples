import itertools
import random
import time

import numpy as np


MASKS = [1064, 1034, 2096, 1030, 41, 76, 304, 1044]


def scan(seed, length=16384, max_gap=384):
    random_generator = random.Random(seed)
    total = length + max_gap * 8 + 256
    stream = np.fromiter((random_generator.getrandbits(4) for repeat in range(total)), dtype=np.int64, count=total)
    stream[-1] = 0
    addresses = np.arange(total)
    accepted = [np.minimum.accumulate(np.where(stream < bound, addresses, total - 1)[::-1])[::-1] for bound in (12, 11, 10)]
    first_positions = accepted[0][:total-128]
    second_positions = accepted[1][first_positions + 1]
    third_positions = accepted[2][second_positions + 1]
    first, second, third = stream[first_positions], stream[second_positions], stream[third_positions]
    second_values = np.where(first == second, 11, second)
    third_values = np.where(third == second, np.where(first == 10, 11, 10), np.where(third == first, 11, third))
    samples = (1 << first) | (1 << second_values) | (1 << third_values)
    ends = third_positions + 1
    starts = np.flatnonzero(samples[:length] == MASKS[0])
    gaps = np.arange(max_gap + 1)
    start_grid, gap_grid = np.meshgrid(starts, gaps)
    paths, gaps = start_grid.ravel(), gap_grid.ravel()
    original = paths.copy()
    for mask in MASKS[1:]:
        paths = ends[paths] + gaps
        keep = samples[paths] == mask
        paths, gaps, original = paths[keep], gaps[keep], original[keep]
        if not len(paths):
            return []
    return list(zip(original.tolist(), gaps.tolist()))


if __name__ == '__main__':
    seeds = set()
    terms = ['reconvergent', 'reconv', 'recon', 'rc', 'r', 'lookup', 'compact', 'coherent', 'qualtran', 'synthesis', 'suite', 'quantum', '2409.04643', '2409_04643', 'circuits', 'xor_and']
    for term, separator in itertools.product(terms, ['', '_', '-', ':', '/', ' ']):
        seeds.add(term)
        for suffix in ['12', '12_8', '12:8', '12-8', '8', '2025', '2024', '2026', '3', '2']:
            seeds.add(term + separator + suffix)
            seeds.add(suffix + separator + term)
    bases = [20250308, 240904643, 24094643, 240904, 2409, 4643, 0xC0FFEE, 0xBADC0DE, 0xC0DEC0DE, 0xDEADBEEF, 314159265, 271828182, 8675309, 123456789, 987654321, 20250301, 20250517, 13371337, 0xA11CE, 0xA11F1E, 20240904, 20240904643, 31415926, 27182818, 314159, 271828, 42, 1234, 12345, 2025]
    for base in bases:
        for offset in range(-32, 129):
            seeds.add(base + offset)
    started = time.time()
    for index, seed in enumerate(sorted(seeds, key=str)):
        matches = scan(seed)
        if matches:
            print('MATCH', repr(seed), matches, flush=True)
        if index % 500 == 0:
            print('progress', index, len(seeds), 'seconds', time.time()-started, flush=True)
