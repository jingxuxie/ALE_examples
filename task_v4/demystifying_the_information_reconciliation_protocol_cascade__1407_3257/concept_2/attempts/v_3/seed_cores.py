import json
import random
import sys
import time
from pathlib import Path

root = Path('/tmp/cascade-c2-g2-v3-mirk7s27/attempts/v_3')
signatures = [list(map(int, line.split())) for line in (root / 'signatures.txt').read_text().splitlines()]
masks = [sum(1 << (64 * pass_index + block) for pass_index, block in enumerate(row)) for row in signatures]
started = time.monotonic()
start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
stop = int(sys.argv[2]) if len(sys.argv) > 2 else 1000000
common = [0xCA5CADE, 0xC45CADE, 0xC0FFEE, 0xDEADBEEF, 314159, 271828, 1337, 42, 760142, 2024, 2025, 2026]
common += [year * 10000 + month * 100 + day for year in [2024, 2025, 2026] for month in range(1, 13) for day in range(1, 32)]

def test(errors, seed, pair_count, variant):
    syndrome = 0
    for position in errors:
        syndrome ^= masks[position]
    if syndrome or len(set(errors)) != len(errors):
        return False
    print('FOUND', seed, pair_count, variant, errors, flush=True)
    (root / 'seed_core.json').write_text(json.dumps({'errors': errors}) + '\n')
    return True

for seed_index, seed in enumerate(common + list(range(start, stop))):
    for pair_count in [8, 6, 9, 4, 5, 7]:
        generator = random.Random(seed)
        blocks = generator.sample(range(64), pair_count)
        state = generator.getstate()
        errors = []
        for block in blocks:
            errors.extend(128 * block + offset for offset in generator.sample(range(128), 2))
        if test(errors, seed, pair_count, 'sample'):
            sys.exit(0)
        generator.setstate(state)
        errors = []
        for block in blocks:
            offset = generator.randrange(64) * 2
            errors.extend([128 * block + offset, 128 * block + offset + 1])
        if test(errors, seed, pair_count, 'adjacent_even'):
            sys.exit(0)
        generator.setstate(state)
        errors = []
        for block in blocks:
            offset = generator.randrange(127)
            errors.extend([128 * block + offset, 128 * block + offset + 1])
        if test(errors, seed, pair_count, 'adjacent'):
            sys.exit(0)
    if seed_index % 10000 == 0:
        print('PROGRESS', seed_index, seed, time.monotonic() - started, flush=True)
