import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time

target_index = int(sys.argv[1])
seconds = float(sys.argv[2])
randomizer = random.Random(int(sys.argv[3]))
target = json.load(open(Path(os.environ['P']) / 'input/instances.json'))['targets'][target_index]
name = target['name']
size = target['n_qubits']
durations = {(control, destination): ticks for control, destination, ticks in target['native_cx']}
expected = [sum(value << column for column, value in enumerate(row)) for row in target['matrix']]

def read(path):
    return [tuple(map(int, line.split())) for line in Path(path).read_text().splitlines()[1:]]

def matrix(gates):
    rows = [1 << vertex for vertex in range(size)]
    for control, destination in gates:
        rows[destination] ^= rows[control]
    return rows

def depth(gates):
    ready = [0] * size
    for control, destination in gates:
        ready[control] = ready[destination] = max(ready[control], ready[destination]) + durations[control, destination]
    return max(ready)

def quality(gates):
    return max(len(gates) / target['max_cx'], depth(gates) / target['max_weighted_depth']) + .0001 * (len(gates) + depth(gates))

def write(path, gates):
    Path(path).write_text(f'{len(gates)} {depth(gates)}\n' + ''.join(f'{control} {destination}\n' for control, destination in gates))

def commutes(first, second):
    return first[0] != second[1] and first[1] != second[0]

best_path = Path(name + '_windowbest.txt')
source_path = Path(name + '_best.txt')
best = read(source_path)
if best_path.exists() and quality(read(best_path)) < quality(best):
    best = read(best_path)
write(best_path, best)
current = list(best)
started = time.monotonic()
trial = 0
print('initial', name, len(best), depth(best), flush=True)
while time.monotonic() - started < seconds:
    trial += 1
    external = read(source_path)
    if quality(external) < quality(best):
        best = external
        current = list(best)
        write(best_path, best)
        print('external', name, len(best), depth(best), flush=True)
    if trial % 8 == 1:
        current = list(best)
        for iteration in range(8):
            for position in range(len(current)-1):
                if randomizer.random() < .5 and commutes(current[position], current[position+1]):
                    current[position], current[position+1] = current[position+1], current[position]
    length = randomizer.choice([12, 18, 24, 32, 45, 60])
    length = min(length, len(current))
    start = randomizer.randrange(len(current)-length+1)
    end = start + length
    fragment = current[start:end]
    fragment_rows = matrix(fragment)
    matrix_path = name + '_window_matrix.txt'
    Path(matrix_path).write_text(' '.join(map(str, fragment_rows)) + f'\n{length*2} {depth(fragment)*2}\n')
    result_path = Path(name + '_window.txt')
    result_path.unlink(missing_ok=True)
    distance_weight = randomizer.choice([.1, .3, .8, 1.5])
    inverse_factor = randomizer.choice([0, .3, 1, 3])
    scale = (1 + distance_weight) * (1 + inverse_factor)
    command = ['./block', str(target_index), str(randomizer.choice([20, 50, 100])), str(distance_weight), str(randomizer.choice([0, 1, -1])), str(inverse_factor), str(randomizer.uniform(.1, 1) * scale), str(randomizer.choice([0, .1, .5, 1, 2]) * scale), 'window', str(randomizer.randrange(1000000000)), '.05', str(randomizer.choice([0, 1, 1])), matrix_path]
    try:
        with open(name + '_window_run.log', 'w') as log:
            subprocess.run(command, stdout=log, stderr=log, timeout=10)
    except subprocess.TimeoutExpired:
        continue
    if not result_path.exists():
        continue
    replacement = read(result_path)
    if matrix(replacement) != fragment_rows:
        raise ValueError('Wrong window matrix')
    candidate = current[:start] + replacement + current[end:]
    if quality(candidate) <= quality(current):
        current = candidate
    if quality(current) < quality(best):
        if matrix(current) != expected:
            raise ValueError('Wrong full matrix')
        best = list(current)
        write(best_path, best)
        print('BEST', name, trial, len(best), depth(best), 'time', round(time.monotonic()-started, 1), flush=True)
        if len(best) <= target['max_cx'] and depth(best) <= target['max_weighted_depth']:
            print('PASSED', name, flush=True)
            break
    if trial % 20 == 0:
        print('progress', name, trial, len(best), depth(best), 'time', round(time.monotonic()-started, 1), flush=True)
