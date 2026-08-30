import argparse
import json
import math
import os
import random
import time
from pathlib import Path

from engine import Samples


parser = argparse.ArgumentParser()
parser.add_argument('--minutes', type=float, default=10)
parser.add_argument('--seed', type=int, default=1701)
parser.add_argument('--count', type=int, default=2048)
parser.add_argument('--steps', type=int, default=2200)
arguments = parser.parse_args()
generator = random.Random(arguments.seed)
baseline = json.loads((Path(os.environ['P']) / 'baseline/design.json').read_text())['z_image']
validation = [Samples(scale, arguments.seed + 901 + scale, 16384 if scale == 1 else 4096, .32) for scale in range(1, 4)]
pool = [(0.0, baseline)]
seen = set()
started = time.monotonic()
best = 0.0
restart = 0
with open(f'search_{arguments.seed}.jsonl', 'a', buffering=1) as log:
    while time.monotonic() - started < arguments.minutes * 60:
        training = Samples(1, generator.randrange(1 << 50), arguments.count, .32)
        if restart % 5 == 4:
            axes = [generator.randrange(3) for _ in range(24)]
        else:
            axes = generator.choice(pool[:12])[1].copy()
            for _ in range(generator.randrange(1, 9)):
                axes[generator.randrange(24)] = generator.randrange(3)
        current = training.score(axes)
        local_best = current
        local_axes = axes.copy()
        for iteration in range(arguments.steps):
            temperature = .035 * (1 - iteration / arguments.steps) ** 2 + .001
            candidate = axes.copy()
            changes = generator.choices([1, 2, 3, 4, 6], [72, 18, 5, 4, 1])[0]
            for cell in generator.sample(range(24), changes):
                candidate[cell] = (candidate[cell] + generator.randrange(1, 3)) % 3
            score = training.score(candidate)
            if score > current or generator.random() < math.exp((score - current) / temperature):
                axes, current = candidate, score
            if current > local_best:
                local_best, local_axes = current, axes.copy()
        for _ in range(4):
            candidates = []
            for cell in range(24):
                for axis in range(3):
                    if axis == local_axes[cell]:
                        continue
                    candidate = local_axes.copy()
                    candidate[cell] = axis
                    candidates.append((training.score(candidate), candidate))
            score, candidate = max(candidates)
            if score <= local_best:
                break
            local_best, local_axes = score, candidate
        key = tuple(local_axes)
        if key not in seen:
            seen.add(key)
            scores = [samples.score(local_axes) for samples in validation]
            pool.append((scores[0], local_axes))
            pool.sort(reverse=True)
            pool = pool[:40]
            record = {'restart': restart, 'seconds': round(time.monotonic() - started, 2), 'train': local_best, 'scores_32': scores, 'z_image': local_axes}
            log.write(json.dumps(record) + '\n')
            print(json.dumps(record), flush=True)
            if scores[0] > best:
                best = scores[0]
                Path('best_small.json').write_text(json.dumps({'z_image': local_axes}) + '\n')
        restart += 1
