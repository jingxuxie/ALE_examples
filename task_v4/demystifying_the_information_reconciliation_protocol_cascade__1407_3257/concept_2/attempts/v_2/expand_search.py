import collections
import glob
import json
import random


rows = [list(map(int, line.split())) for line in open('signatures.txt')][1:]
columns = [sum(1 << (64 * dimension + block) for dimension, block in enumerate(signature)) for signature in rows]
generator = random.Random(8359)
for name in glob.glob('*_best_*.json'):
    errors = json.load(open(name))
    counts = collections.Counter(64 * dimension + block for bit in errors for dimension, block in enumerate(rows[bit]))
    for variant in range(8):
        scores = []
        for bit, signature in enumerate(rows):
            score = 0
            for dimension, block in enumerate(signature):
                count = counts[64 * dimension + block]
                score += (count > 0) if variant % 2 == 0 else min(count, 2)
            scores.append((score + generator.random(), bit))
        order = errors + [bit for score, bit in sorted(scores, reverse=True) if bit not in errors][:384]
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
            if not value and support and 8 <= support.bit_count() <= 18:
                core = [position for position in range(8192) if support >> position & 1]
                print('FOUND', name, variant, core, flush=True)
                json.dump(core, open('expand_core.json', 'w'))
                raise SystemExit
    print('checked', name, flush=True)
