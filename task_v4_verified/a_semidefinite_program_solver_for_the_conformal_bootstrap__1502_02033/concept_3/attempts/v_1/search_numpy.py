import json
import sys

import numpy as np


patterns = json.load(open('patterns.json'))
by_prefix = {}
for pattern in patterns:
    by_prefix.setdefault(tuple(pattern['values'][:6]), []).append(pattern)
start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
end = int(sys.argv[2]) if len(sys.argv) > 2 else 1000000
for seed in range(start, end):
    generator = np.random.default_rng(seed)
    prefix = tuple(generator.integers(-5, 6, size=6).tolist())
    if prefix not in by_prefix:
        continue
    values = list(prefix) + generator.integers(-5, 6, size=114).tolist()
    for pattern in by_prefix[prefix]:
        if pattern['values'] == values[:len(pattern['values'])]:
            print('FULLMATCH', seed, pattern, flush=True)
    print('candidate', seed, flush=True)
print('DONE', start, end, flush=True)
