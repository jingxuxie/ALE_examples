import json
import math
import os
from pathlib import Path

import numpy as np


ASSETS = Path(os.environ.get('ASSETS', '../../participant'))
INSTANCES = json.loads((ASSETS / 'input/instances.json').read_text())['instances']


def target(instance):
    data = instance['target_projector']
    return np.array(data['real']) + 1j * np.array(data['imag'])


def rotate(matrix, first, second, theta, phi):
    result = matrix.copy()
    cosine = np.cos(theta)
    sine = np.sin(theta) * np.exp(1j * phi)
    result[first] = cosine * matrix[first] - sine.conjugate() * matrix[second]
    result[second] = sine * matrix[first] + cosine * matrix[second]
    columns = result[:, [first, second]].copy()
    result[:, first] = cosine * columns[:, 0] - sine * columns[:, 1]
    result[:, second] = sine.conjugate() * columns[:, 0] + cosine * columns[:, 1]
    return result


def candidates(matrix, edges):
    size = len(matrix)
    for first, second in edges:
        angles = []
        for column in range(size):
            if column in (first, second):
                continue
            upper, lower = matrix[first, column], matrix[second, column]
            if min(abs(upper), abs(lower)) < 1e-10:
                continue
            theta = math.atan2(abs(lower), abs(upper))
            phi = np.angle(-lower / upper)
            angles.append((theta, phi))
            angles.append((theta - math.pi / 2, phi))
        upper = matrix[first, first].real
        lower = matrix[second, second].real
        cross = matrix[first, second]
        if abs(cross) > 1e-12:
            theta = 0.5 * math.atan2(2 * abs(cross), lower - upper)
            phi = -np.angle(cross)
            angles.append((theta, phi))
            angles.append((theta - math.pi / 2, phi))
        unique = set()
        for theta, phi in angles:
            if abs(theta) < 1e-10:
                continue
            signature = (round(theta, 9), round(phi, 9))
            if signature in unique:
                continue
            unique.add(signature)
            yield (first, second, float(theta), float(phi))


def metrics(matrix, initial):
    mask = np.abs(matrix) > 1e-9
    np.fill_diagonal(mask, False)
    sparsity = np.count_nonzero(mask)
    diagonal = matrix.diagonal().real
    impurity = np.sum(diagonal * (1 - diagonal))
    distance = np.linalg.norm(matrix - initial)
    return sparsity, impurity, distance


def schedule(gates, size):
    last = [-1] * size
    layers = []
    for first, second, theta, phi in gates:
        layer = max(last[first], last[second]) + 1
        while len(layers) <= layer:
            layers.append([])
        layers[layer].append(dict(u=int(first), v=int(second), theta=float(theta), phi=float(phi)))
        last[first] = last[second] = layer
    return layers


def greedy(instance):
    matrix = target(instance)
    initial = np.diag([float(mode in instance['initial_occupied']) for mode in range(len(matrix))])
    gates = []
    print(instance['id'], metrics(matrix, initial), flush=True)
    for step in range(instance['budgets']['max_gates']):
        choices = []
        for gate in candidates(matrix, instance['edges']):
            result = rotate(matrix, *gate)
            score = metrics(result, initial)
            choices.append((score, gate, result))
        score, gate, matrix = min(choices, key=lambda item: (item[0][0], round(item[0][1], 9), round(item[0][2], 9), abs(item[1][2])))
        gates.append(gate)
        print(step, gate[:2], tuple(round(value, 8) for value in gate[2:]), tuple(round(value, 8) for value in score), flush=True)
        if score[0] == 0:
            break
    print('final occupation', np.round(matrix.diagonal().real, 4), flush=True)
    return gates, matrix


if __name__ == '__main__':
    for instance in INSTANCES:
        gates, matrix = greedy(instance)
        Path(instance['id'] + '_peel.json').write_text(json.dumps(gates))
