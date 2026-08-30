import argparse
import heapq
import itertools
import json
import os
import time
from pathlib import Path

from engine import Samples


parser = argparse.ArgumentParser()
parser.add_argument('--radius', type=int, default=4)
parser.add_argument('--count', type=int, default=256)
parser.add_argument('--start', default=os.environ['P'] + '/baseline/design.json')
parser.add_argument('--tag', default='near')
arguments = parser.parse_args()
baseline = json.loads(Path(arguments.start).read_text())['z_image']
training = Samples(1, 7364729, arguments.count, .32)
heap = []
started = time.monotonic()
for distance in range(1, arguments.radius + 1):
    for cells in itertools.combinations(range(24), distance):
        for changes in itertools.product((1, 2), repeat=distance):
            axes = baseline.copy()
            for cell, change in zip(cells, changes):
                axes[cell] = (axes[cell] + change) % 3
            score = training.score(axes)
            item = (score, axes)
            if len(heap) < 1000:
                heapq.heappush(heap, item)
            elif item > heap[0]:
                heapq.heapreplace(heap, item)
    print('distance', distance, 'seconds', time.monotonic() - started, 'best', max(heap), flush=True)
validation = Samples(1, 134786328, 16384, .32)
results = sorted(((validation.score(axes), axes) for _, axes in heap), reverse=True)
Path(arguments.tag + '_candidates.json').write_text(json.dumps(results))
samples = [Samples(scale, 5783219 + scale, 16384, .32) for scale in range(1, 4)]
with open(arguments.tag + '_results.jsonl', 'w', buffering=1) as stream:
    for score, axes in results[:30]:
        record = {'validation': score, 'scores_32': [sample.score(axes) for sample in samples], 'z_image': axes}
        stream.write(json.dumps(record) + '\n')
        print(json.dumps(record), flush=True)
