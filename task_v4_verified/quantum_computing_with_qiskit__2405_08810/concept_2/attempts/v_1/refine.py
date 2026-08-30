import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

target_index = int(sys.argv[1])
seconds = float(sys.argv[2])
randomizer = random.Random(int(sys.argv[3]))
tag = sys.argv[4] if len(sys.argv) > 4 else 'refine'
round_seconds = sys.argv[5] if len(sys.argv) > 5 else '30'
target = json.load(open(Path(os.environ['P']) / 'input/instances.json'))['targets'][target_index]
name = target['name']
durations = {(control, destination): ticks for control, destination, ticks in target['native_cx']}
expected = [sum(value << column for column, value in enumerate(row)) for row in target['matrix']]

def metrics(path):
    gates = [tuple(map(int, line.split())) for line in Path(path).read_text().splitlines()[1:]]
    rows = [1 << vertex for vertex in range(target['n_qubits'])]
    ready = [0] * target['n_qubits']
    for control, destination in gates:
        rows[destination] ^= rows[control]
        ready[control] = ready[destination] = max(ready[control], ready[destination]) + durations[control, destination]
    if rows != expected:
        raise ValueError('Wrong matrix')
    count, depth = len(gates), max(ready)
    passed = count <= target['max_cx'] and depth <= target['max_weighted_depth']
    quality = (.9 if passed else max(count / target['max_cx'], depth / target['max_weighted_depth'])) + .0001*(count+depth)
    return quality, count, depth, passed

best_path = Path(name + '_' + tag + 'best.txt')
best = (float('inf'), 0, 0, False)
started = time.monotonic()
iteration = 0
while time.monotonic() - started < seconds:
    iteration += 1
    for path in Path('.').glob(name + '_*.txt'):
        try:
            candidate = metrics(path)
        except (ValueError, IndexError, KeyError):
            continue
        if candidate[0] < best[0]:
            best = candidate
            if path != best_path:
                shutil.copyfile(path, best_path)
            print('BEST', name, iteration, best, 'source', path, 'time', round(time.monotonic()-started, 1), flush=True)
    if best[3]:
        print('PASSED', name, flush=True)
        break
    count_cost = randomizer.choice([-1, -1, 0, 100])
    if best[1] > target['max_cx']:
        count_cost = 100
    temperature = randomizer.choice([.02, .05, .1, .2])
    transposed = randomizer.randrange(2)
    with open(name + '_' + tag + '_run.log', 'w') as log:
        subprocess.run(['./optimize', str(target_index), str(best_path), round_seconds, tag + '_candidate', str(randomizer.randrange(1000000000)), str(count_cost), str(temperature), str(transposed)], stdout=log, stderr=log, timeout=90)
