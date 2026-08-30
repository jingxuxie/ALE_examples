import argparse
import itertools
import json
import math
from pathlib import Path
import time
from collections import deque

import numpy as np

from synthesize import inverse_circuit, load_instances, projector, rotate, schedule


class FockSpace:
    def __init__(self, instance):
        self.instance = instance
        self.size = instance['n_modes']
        self.particles = instance['n_particles']
        self.subsets = np.array(list(itertools.combinations(range(self.size), self.particles)))
        masks = np.sum(1 << self.subsets, axis=1)
        indexed = {int(mask): index for index, mask in enumerate(masks)}
        self.pairs = []
        for first, second in instance['edges']:
            selected = np.flatnonzero(((masks >> first) & 1) & (1 - ((masks >> second) & 1)))
            other_masks = masks[selected] ^ (1 << first) ^ (1 << second)
            others = np.array([indexed[int(mask)] for mask in other_masks])
            between = ((1 << second) - 1) ^ ((1 << (first + 1)) - 1)
            signs = np.array([(-1) ** int(int(mask & between).bit_count()) for mask in masks[selected]])
            self.pairs.append((selected, others, signs))
        initial_mask = sum(1 << mode for mode in instance['initial_occupied'])
        self.initial_index = indexed[initial_mask]
        self.tolerance = 3e-12

    def amplitudes(self, matrix):
        _, vectors = np.linalg.eigh(matrix)
        frame = vectors[:, -self.particles:]
        return np.linalg.det(frame[self.subsets])

    def options(self, amplitudes, maximum=30):
        choices = []
        minimum_count = 1 if np.count_nonzero(abs(amplitudes) > self.tolerance) <= 64 else 2
        for edge_index, (selected, others, signs) in enumerate(self.pairs):
            upper, lower = amplitudes[selected], signs * amplitudes[others]
            present = (abs(upper) > self.tolerance) & (abs(lower) > self.tolerance)
            if np.count_nonzero(present) < minimum_count:
                continue
            ratios = -lower[present] / upper[present]
            radii = abs(ratios)
            theta = np.arctan(radii)
            theta[theta > math.pi / 4] -= math.pi / 2
            factors = np.sin(theta) * ratios / radii
            quantized = np.rint(np.stack((factors.real, factors.imag), axis=1) * 1e7).astype(np.int64)
            _, representatives, inverse, counts = np.unique(quantized, return_index=True, return_inverse=True, return_counts=True, axis=0)
            repeated = np.flatnonzero(counts >= minimum_count)
            if len(repeated) > 80:
                repeated = repeated[np.argsort(counts[repeated])[-80:]]
            original_count = np.count_nonzero(abs(upper) > self.tolerance) + np.count_nonzero(abs(lower) > self.tolerance)
            for group in repeated:
                members = inverse == group
                group_upper, group_lower = upper[present][members], lower[present][members]
                ratio = -np.vdot(group_upper, group_lower) / np.vdot(group_upper, group_upper)
                angle = math.atan(abs(ratio))
                if angle > math.pi / 4:
                    angle -= math.pi / 2
                factor = math.sin(angle) * ratio / abs(ratio)
                angle = math.asin(min(1, abs(factor)))
                phase = float(np.angle(factor))
                for theta in (angle, angle - math.pi / 2):
                    cosine = math.cos(theta)
                    factor = math.sin(theta) * np.exp(1j * phase)
                    transformed_upper = cosine * upper - factor.conjugate() * lower
                    transformed_lower = factor * upper + cosine * lower
                    resulting_count = np.count_nonzero(abs(transformed_upper) > self.tolerance) + np.count_nonzero(abs(transformed_lower) > self.tolerance)
                    gain = original_count - resulting_count
                    if gain >= 1:
                        choices.append((gain, edge_index, theta, phase))
        choices.sort(reverse=True)
        return choices[:maximum]

    def apply(self, amplitudes, edge_index, theta, phase):
        selected, others, signs = self.pairs[edge_index]
        upper, lower = amplitudes[selected], signs * amplitudes[others]
        factor = math.sin(theta) * np.exp(1j * phase)
        cosine = math.cos(theta)
        result = amplitudes.copy()
        result[selected] = cosine * upper - factor.conjugate() * lower
        result[others] = signs * (factor * upper + cosine * lower)
        return result


def route_basis(instance, occupied):
    source = sum(1 << mode for mode in instance['initial_occupied'])
    target = sum(1 << mode for mode in occupied)
    queue = deque([source])
    parents = {source: None}
    while queue and target not in parents:
        current = queue.popleft()
        for first, second in instance['edges']:
            if ((current >> first) & 1) == ((current >> second) & 1):
                continue
            following = current ^ (1 << first) ^ (1 << second)
            if following not in parents:
                parents[following] = current, first, second
                queue.append(following)
    result = []
    current = target
    while parents[current] is not None:
        current, first, second = parents[current]
        result.append(dict(u=first, v=second, theta=math.pi / 2, phi=0.0))
    return list(reversed(result))


def search(instance, width, seconds, weight=0.0, tag='base'):
    space = FockSpace(instance)
    target = projector(instance)
    amplitudes = space.amplitudes(target)
    initial = np.zeros(len(target))
    initial[instance['initial_occupied']] = 1
    states = [(target, amplitudes, [])]
    stem = instance['id'] + '_fock_' + tag
    print('INITIAL', instance['id'], len(amplitudes), np.count_nonzero(abs(amplitudes) > space.tolerance), flush=True)
    started = time.time()
    for step in range(instance['budgets']['max_gates']):
        expanded = []
        seen = set()
        for matrix, amplitudes, gates in states:
            current_nonzeros = np.count_nonzero(abs(amplitudes) > space.tolerance)
            choices = space.options(amplitudes)
            for gain, edge_index, theta, phase in choices:
                first, second = instance['edges'][edge_index]
                trial = rotate(matrix, first, second, theta, phase)
                key = np.rint(np.concatenate((trial.real.ravel(), trial.imag.ravel())) * 1e8).astype(np.int64).tobytes()
                if key in seen:
                    continue
                seen.add(key)
                nonzeros = current_nonzeros - gain
                distance = np.linalg.norm(trial - np.diag(initial))
                new_gates = gates + [(first, second, theta, phase)]
                partial = inverse_circuit(instance, new_gates)
                depth = len(partial['layers'])
                if depth > instance['budgets']['max_depth'] + 2:
                    continue
                score = math.log1p(nonzeros) + weight * distance ** 2 + 0.002 * depth + 1e-7 * distance
                if distance < 1e-8:
                    circuit = inverse_circuit(instance, new_gates)
                    Path(stem + '.json').write_text(json.dumps(circuit))
                    print('SOLVED', instance['id'], len(new_gates), len(circuit['layers']), distance, flush=True)
                    return
                if np.linalg.norm(trial - np.diag(np.diag(trial))) < 1e-8:
                    occupied = np.flatnonzero(np.diag(trial).real > 0.5)
                    prefix = route_basis(instance, occupied)
                    circuit = inverse_circuit(instance, new_gates)
                    sequence = prefix + [gate for layer in circuit['layers'] for gate in layer]
                    circuit['layers'] = schedule(sequence, instance['n_modes'])
                    Path(stem + '_routed.json').write_text(json.dumps(circuit))
                    print('ROUTED', instance['id'], len(sequence), len(circuit['layers']), flush=True)
                    if len(sequence) <= instance['budgets']['max_gates'] and len(circuit['layers']) <= instance['budgets']['max_depth']:
                        return
                expanded.append((score, trial, amplitudes, new_gates, edge_index, theta, phase))
        if not expanded:
            print('STALLED', instance['id'], step, flush=True)
            return
        expanded.sort(key=lambda entry: entry[0])
        states = [(entry[1], space.apply(entry[2], entry[4], entry[5], entry[6]), entry[3]) for entry in expanded[:width]]
        matrix, amplitudes, gates = states[0]
        print('FOCK', instance['id'], step + 1, 'states', len(expanded), 'nnz', np.count_nonzero(abs(amplitudes) > space.tolerance),
              'error', np.linalg.norm(matrix - np.diag(initial)), 'elapsed', round(time.time() - started, 1), flush=True)
        Path(stem + '_partial.json').write_text(json.dumps(inverse_circuit(instance, gates)))
        np.save(stem + '_residual.npy', matrix)
        if time.time() - started > seconds:
            return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', required=True)
    parser.add_argument('--width', type=int, default=10)
    parser.add_argument('--seconds', type=int, default=600)
    parser.add_argument('--weight', type=float, default=0.0)
    parser.add_argument('--tag', default='base')
    arguments = parser.parse_args()
    instance = next(instance for instance in load_instances() if instance['id'] == arguments.instance)
    search(instance, arguments.width, arguments.seconds, arguments.weight, arguments.tag)


if __name__ == '__main__':
    main()
