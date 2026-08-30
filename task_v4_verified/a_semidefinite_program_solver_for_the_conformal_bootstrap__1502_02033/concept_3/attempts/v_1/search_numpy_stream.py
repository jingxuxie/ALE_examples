import json
import sys

import numpy as np


patterns = json.load(open('stream_patterns.json'))
packed_patterns = {int(value) for value in patterns}
start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
end = int(sys.argv[2]) if len(sys.argv) > 2 else 100000
weights = np.array([11 ** power for power in range(12)], dtype=np.int64)
for seed in range(start, end):
    generator = np.random.default_rng(seed)
    values = generator.integers(0, 11, size=400)
    packed = np.convolve(values, weights, mode='valid')
    matches = packed_patterns.intersection(packed.tolist())
    for value in matches:
        print('MATCH', seed, np.flatnonzero(packed == value).tolist(), value, patterns[str(value)], flush=True)
print('DONE', start, end, flush=True)
