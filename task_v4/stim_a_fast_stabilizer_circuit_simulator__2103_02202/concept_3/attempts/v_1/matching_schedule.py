import json
import math
import random

import numpy as np
from scipy.optimize import linear_sum_assignment

import greedy
import synthesize as syn

BLACK = [qubit for qubit in range(36) if (qubit // 6 + qubit % 6) % 2 == 0]
WHITE = [qubit for qubit in range(36) if qubit not in BLACK]
BLACK_INDEX = {qubit: index for index, qubit in enumerate(BLACK)}
WHITE_INDEX = {qubit: index for index, qubit in enumerate(WHITE)}


def schedule(original, seed):
    randomizer = random.Random(seed)
    gates = original if seed % 2 == 0 else original[::-1]
    predecessors = [set() for _ in gates]
    successors = [set() for _ in gates]
    groups = [[] for _ in range(36)]
    previous_groups = [[] for _ in range(36)]
    current_axes = [None] * 36
    pending = [0] * 36
    for index, (first, second, axis_first, axis_second) in enumerate(gates):
        for qubit, axis in ((first, axis_first), (second, axis_second)):
            pending[qubit] += 1
            if axis != current_axes[qubit]:
                previous_groups[qubit] = groups[qubit]
                groups[qubit] = []
                current_axes[qubit] = axis
            predecessors[index].update(previous_groups[qubit])
            groups[qubit].append(index)
    for index, dependencies in enumerate(predecessors):
        for predecessor in dependencies:
            successors[predecessor].add(index)
    height = [1] * len(gates)
    for index in reversed(range(len(gates))):
        height[index] += max((height[successor] for successor in successors[index]), default=0)
    ready = {index for index, dependencies in enumerate(predecessors) if not dependencies}
    layers = []
    exponent = (1, 2, 3, 4, 6, 8, 12, 20)[seed // 2 % 8]
    while ready:
        weights = np.zeros((18, 18))
        selected = {}
        maximum = max(height[index] for index in ready)
        for index in ready:
            first, second = gates[index][:2]
            black, white = (first, second) if first in BLACK_INDEX else (second, first)
            row, column = BLACK_INDEX[black], WHITE_INDEX[white]
            weight = (height[index] / maximum) ** exponent
            if seed // 16 % 2:
                weight += 20
            weight *= 1 + randomizer.random() * (0.15 if seed >= 64 else 0.001)
            if seed // 32 % 2:
                weight *= 1 + (pending[first] + pending[second]) / 200
            if weight > weights[row, column]:
                weights[row, column] = weight
                selected[row, column] = index
        rows, columns = linear_sum_assignment(-weights)
        chosen = [selected[row, column] for row, column in zip(rows, columns) if (row, column) in selected]
        assert chosen
        layers.append([gates[index] for index in chosen])
        for index in chosen:
            ready.remove(index)
            for qubit in gates[index][:2]:
                pending[qubit] -= 1
            for successor in successors[index]:
                predecessors[successor].remove(index)
                if not predecessors[successor]:
                    ready.add(successor)
    return layers if seed % 2 == 0 else layers[::-1]


def main():
    data = json.loads((greedy.OUT / 'best_generalized.json').read_text())
    gates, frames = data['gates'], data['frames']
    best = syn.schedule_generalized(gates)
    for seed in range(300):
        layers = schedule(gates, seed)
        if len(layers) < len(best):
            best = layers
            print('schedule', seed, len(best), flush=True)
    native = syn.correct_signs(syn.realize(best, frames))
    artifact = syn.schedule_native(native)
    instance = {name: json.loads((greedy.ROOT / 'input' / (name + '.json')).read_text()) for name in ('constraints', 'target')}
    checked = syn.check(artifact, instance)
    print(json.dumps(checked), flush=True)
    previous = json.loads((greedy.OUT / 'best_metrics.json').read_text())
    if checked['score'] > previous['score']:
        (greedy.OUT / 'circuit.json').write_text(json.dumps(artifact, separators=(',', ':')))
        (greedy.OUT / 'best_metrics.json').write_text(json.dumps(checked, indent=2))
        (greedy.OUT / 'best_generalized.json').write_text(json.dumps({'gates': [gate for layer in best for gate in layer], 'frames': frames}))


if __name__ == '__main__':
    main()
