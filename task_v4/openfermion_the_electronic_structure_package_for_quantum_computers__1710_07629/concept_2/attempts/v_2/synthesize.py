import argparse
import json
import math
from pathlib import Path
import time

import numpy as np


PARTICIPANT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/openfermion_the_electronic_structure_package_for_quantum_computers__1710_07629/concept_2/participant')


def load_instances():
    return json.loads((PARTICIPANT / 'input/instances.json').read_text())['instances']


def projector(instance):
    return np.array(instance['target_projector']['real']) + 1j * np.array(instance['target_projector']['imag'])


def rotate(matrix, first, second, theta, phi):
    result = matrix.copy()
    cosine = np.cos(theta)
    factor = np.sin(theta) * np.exp(1j * phi)
    upper = result[first].copy()
    lower = result[second].copy()
    result[first] = cosine * upper - factor.conjugate() * lower
    result[second] = factor * upper + cosine * lower
    upper = result[:, first].copy()
    lower = result[:, second].copy()
    result[:, first] = cosine * upper - factor * lower
    result[:, second] = factor.conjugate() * upper + cosine * lower
    return result


def candidates(matrix, edges, tolerance=1e-10):
    size = len(matrix)
    for first, second in edges:
        choices = []
        for column in range(size):
            if column == first or column == second:
                continue
            upper, lower = matrix[first, column], matrix[second, column]
            if min(abs(upper), abs(lower)) < tolerance:
                continue
            theta = math.atan2(abs(lower), abs(upper))
            phi = float(np.angle(-lower / upper))
            if theta > math.pi / 4:
                theta -= math.pi / 2
            choices.append((theta, phi))
        cross = matrix[first, second]
        if abs(cross) > tolerance:
            difference = float((matrix[first, first] - matrix[second, second]).real)
            theta = 0.5 * math.atan2(-2 * abs(cross), difference)
            if theta < -math.pi / 4:
                theta += math.pi / 2
            choices.append((theta, float(-np.angle(cross))))
        seen = set()
        for theta, phi in choices:
            factor = np.sin(theta) * np.exp(1j * phi)
            fingerprint = (round(factor.real, 8), round(factor.imag, 8))
            if fingerprint in seen or abs(theta) < tolerance:
                continue
            seen.add(fingerprint)
            yield first, second, theta, phi


def schedule(gates, size):
    last = [-1] * size
    layers = []
    for gate in gates:
        first, second = gate['u'], gate['v']
        index = max(last[first], last[second]) + 1
        while len(layers) <= index:
            layers.append([])
        layers[index].append(gate)
        last[first] = last[second] = index
    return layers


def inverse_circuit(instance, gates):
    sequence = [dict(u=int(first), v=int(second), theta=float(-theta), phi=float(phi))
                for first, second, theta, phi in reversed(gates)]
    return dict(id=instance['id'], layers=schedule(sequence, instance['n_modes']))


def greedy(instance, max_steps=100, random_seed=0, verbose=True):
    matrix = projector(instance)
    initial = np.zeros(len(matrix))
    initial[instance['initial_occupied']] = 1
    generator = np.random.default_rng(random_seed)
    gates = []
    tolerance = 1e-9
    for step in range(max_steps):
        nonzeros = np.count_nonzero(np.abs(matrix) > tolerance)
        offdiagonal = matrix - np.diag(np.diag(matrix))
        if np.linalg.norm(offdiagonal) < 1e-8:
            break
        best = None
        for gate in candidates(matrix, instance['edges']):
            trial = rotate(matrix, *gate)
            trial_nonzeros = np.count_nonzero(np.abs(trial) > tolerance)
            purity = np.sum(np.real(np.diag(trial)) ** 2)
            distance = np.linalg.norm(np.diag(trial).real - initial)
            score = (nonzeros - trial_nonzeros, purity - 0.02 * distance)
            if random_seed:
                score = (score[0], score[1] + generator.uniform(0, 0.3))
            if best is None or score > best[0]:
                best = score, gate, trial
        if best is None:
            break
        score, gate, matrix = best
        gates.append(gate)
        if verbose:
            print(instance['id'], step, 'gain', score[0], 'edge', gate[:2], 'angle', gate[2],
                  'nnz', np.count_nonzero(abs(matrix) > tolerance), 'error', np.linalg.norm(matrix - np.diag(initial)), flush=True)
        if score[0] <= 0:
            break
    return gates, matrix


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance')
    arguments = parser.parse_args()
    for instance in load_instances():
        if arguments.instance and instance['id'] != arguments.instance:
            continue
        print('START', instance['id'], flush=True)
        gates, matrix = greedy(instance)
        circuit = inverse_circuit(instance, gates)
        Path(instance['id'] + '_greedy.json').write_text(json.dumps(circuit, indent=2))
        np.save(instance['id'] + '_residual.npy', matrix)
        print('END', instance['id'], 'gates', len(gates), 'depth', len(circuit['layers']), 'diagonal', np.diag(matrix).real, flush=True)


if __name__ == '__main__':
    main()
