import gzip
import json
import os
import time
from pathlib import Path

from engine import Samples


with gzip.open(Path(os.environ['P']) / 'input/scale_1.json.gz', 'rt') as stream:
    case = json.load(stream)
neighbors = [[None] * 3 for _ in range(24)]
for axis in range(3):
    phase = (axis + 2) % 3
    for qubit in range(24):
        for partner in range(24):
            if qubit != partner and case['columns'][phase * 24 + qubit][axis] == case['columns'][phase * 24 + partner][axis]:
                neighbors[qubit][axis] = partner
patterns = []


def enumerate_matchings(mask, axes):
    if mask == (1 << 24) - 1:
        patterns.append(axes.copy())
        return
    qubit = next(qubit for qubit in range(24) if not mask >> qubit & 1)
    for axis, partner in enumerate(neighbors[qubit]):
        if mask >> partner & 1:
            continue
        axes[qubit] = axes[partner] = axis
        enumerate_matchings(mask | (1 << qubit) | (1 << partner), axes)


enumerate_matchings(0, [-1] * 24)
Path('matchings.json').write_text(json.dumps(patterns))
print('matchings', len(patterns), flush=True)
training = Samples(1, 7347891, 4096, .32)
started = time.monotonic()
scores = sorted(((training.score(axes), axes) for axes in patterns), reverse=True)
print('screening', time.monotonic() - started, scores[:5], flush=True)
validation = [Samples(scale, 78567912 + scale, 32768 if scale == 1 else 8192, .32) for scale in range(1, 4)]
with open('matching_results.jsonl', 'w', buffering=1) as stream:
    for score, axes in scores[:100]:
        results = [sample.score(axes) for sample in validation]
        record = {'train': score, 'scores_32': results, 'z_image': axes}
        stream.write(json.dumps(record) + '\n')
        print(json.dumps(record), flush=True)
