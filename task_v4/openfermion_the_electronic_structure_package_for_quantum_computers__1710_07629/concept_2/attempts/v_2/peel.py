import argparse
import json
import math
from pathlib import Path
import time

import numpy as np

from synthesize import candidates, inverse_circuit, load_instances, projector, rotate


def options(matrix, edges):
    nonzeros = np.count_nonzero(abs(matrix) > 1e-9)
    results = []
    for first, second, theta, phi in candidates(matrix, edges):
        for angle in (theta, theta - np.sign(theta) * math.pi / 2):
            gate = first, second, angle, phi
            trial = rotate(matrix, *gate)
            gain = nonzeros - np.count_nonzero(abs(trial) > 1e-9)
            if gain >= 2:
                results.append((gain, gate, trial))
    return results


def peel(instance, width=100, limit=50):
    target = projector(instance)
    initial = np.zeros(len(target))
    initial[instance['initial_occupied']] = 1
    states = [(target, [])]
    started = time.time()
    for step in range(limit):
        expanded = []
        seen = set()
        for matrix, gates in states:
            for gain, gate, trial in options(matrix, instance['edges']):
                key = np.round(trial, 8).tobytes()
                if key in seen:
                    continue
                seen.add(key)
                nonzeros = np.count_nonzero(abs(trial) > 1e-9)
                distance = np.linalg.norm(trial - np.diag(initial))
                purity = np.sum(np.diag(trial).real ** 2)
                score = nonzeros + 0.1 * distance - 0.01 * purity
                expanded.append((score, trial, gates + [gate]))
                if distance < 1e-8:
                    circuit = inverse_circuit(instance, gates + [gate])
                    Path(instance['id'] + '_peeled.json').write_text(json.dumps(circuit))
                    print('SOLVED', instance['id'], step + 1, len(circuit['layers']), distance, flush=True)
                    return
        if not expanded:
            print('STALLED', instance['id'], step, flush=True)
            return
        expanded.sort(key=lambda entry: entry[0])
        states = [(entry[1], entry[2]) for entry in expanded[:width]]
        print('PEEL', instance['id'], step + 1, 'states', len(expanded), 'nnz',
              np.count_nonzero(abs(states[0][0]) > 1e-9), 'distance', np.linalg.norm(states[0][0] - np.diag(initial)),
              'elapsed', round(time.time() - started, 1), flush=True)
        np.save(instance['id'] + '_peel_residual.npy', states[0][0])
        Path(instance['id'] + '_peel_partial.json').write_text(json.dumps(inverse_circuit(instance, states[0][1])))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', required=True)
    parser.add_argument('--width', type=int, default=50)
    arguments = parser.parse_args()
    instance = next(instance for instance in load_instances() if instance['id'] == arguments.instance)
    peel(instance, arguments.width, instance['budgets']['max_gates'])


if __name__ == '__main__':
    main()
