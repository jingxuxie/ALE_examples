import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

target_index = int(sys.argv[1])
seconds = float(sys.argv[2])
seed = int(sys.argv[3])
causal = len(sys.argv) > 4
randomizer = random.Random(seed)
targets = json.load(open(Path(os.environ['P']) / 'input/instances.json'))['targets']
target = targets[target_index]
name = target['name']
duration = {(control, destination): ticks for control, destination, ticks in target['native_cx']}
expected = [sum(value << column for column, value in enumerate(row)) for row in target['matrix']]

def measure(path):
    lines = Path(path).read_text().splitlines()
    gates = [list(map(int, line.split())) for line in lines[1:]]
    ready = [0] * target['n_qubits']
    rows = [1 << vertex for vertex in range(target['n_qubits'])]
    for control, destination in gates:
        rows[destination] ^= rows[control]
        ready[control] = ready[destination] = max(ready[control], ready[destination]) + duration[control, destination]
    if rows != expected:
        raise ValueError('Wrong matrix: ' + str(path))
    count, depth = len(gates), max(ready)
    quality = max(count / target['max_cx'], depth / target['max_weighted_depth']) + .0001 * (count + depth)
    return quality, count, depth

best = (float('inf'), 0, 0)
best_path = Path(name + ('_causalbest.txt' if causal else '_best.txt'))
for path in Path('.').glob(name + '_*.txt'):
    if 'residual' in str(path):
        continue
    try:
        metrics = measure(path)
    except (ValueError, IndexError):
        continue
    if metrics[0] < best[0]:
        best = metrics
        if path != best_path:
            shutil.copyfile(path, best_path)
print('initial', name, best, flush=True)
started = time.monotonic()
trial = 0
while time.monotonic() - started < seconds:
    trial += 1
    width = randomizer.choice([30, 60, 100, 200]) if not causal else randomizer.choice([60, 100, 200, 400])
    distance_weight = math.exp(randomizer.uniform(math.log(.05), math.log(2)))
    diagonal_weight = randomizer.choice([-2, -1, 0, .5, 1])
    inverse_factor = randomizer.choice([0, .1, .3, 1, 3])
    scale = (1 + distance_weight) * (1 + inverse_factor)
    count_factor = randomizer.uniform(.05, 1.5) * scale
    depth_factor = randomizer.choice([0, .1, .3, .5, 1, 2]) * scale
    noise = randomizer.choice([0, .05, .15, .4])
    decay = randomizer.choice([0, 1, 1])
    output_suffix = 'causal' if causal else 'batch'
    candidate = Path(name + '_' + output_suffix + '.txt')
    candidate.unlink(missing_ok=True)
    command = ['./block', str(target_index), str(width), str(distance_weight), str(diagonal_weight), str(inverse_factor), str(count_factor), str(depth_factor), output_suffix, str(randomizer.randrange(1000000000)), str(noise), str(decay)]
    if causal:
        command.extend(['-', str(target['max_weighted_depth'] + randomizer.choice([10, 15, 20, 25])), '1'])
    try:
        with open(name + '_' + output_suffix + '_run.log', 'w') as log:
            subprocess.run(command, stdout=log, stderr=log, timeout=40 if causal else 20)
    except subprocess.TimeoutExpired:
        pass
    if candidate.exists():
        metrics = measure(candidate)
        optimized = Path(name + '_' + output_suffix + 'opt.txt')
        with open(name + '_' + output_suffix + '_opt.log', 'w') as log:
            subprocess.run(['./optimize', str(target_index), str(candidate), '1.2', output_suffix + 'opt', str(randomizer.randrange(1000000000)), '100'], stdout=log, stderr=log, timeout=20)
        if optimized.exists():
            metrics = measure(optimized)
            candidate = optimized
        if metrics[0] < best[0]:
            best = metrics
            shutil.copyfile(candidate, best_path)
            print('BEST', name, trial, best, 'time', round(time.monotonic()-started, 1), 'parameters', command[2:], flush=True)
        if metrics[1] <= target['max_cx'] and metrics[2] <= target['max_weighted_depth']:
            shutil.copyfile(candidate, best_path)
            print('PASSED', name, flush=True)
            break
    if trial % 10 == 0:
        print('progress', name, trial, best, 'time', round(time.monotonic()-started, 1), flush=True)
