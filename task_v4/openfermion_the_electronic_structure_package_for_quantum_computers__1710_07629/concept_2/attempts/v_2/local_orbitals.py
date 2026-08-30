import argparse
import json
import math
from pathlib import Path
import time

import numpy as np

from synthesize import inverse_circuit, load_instances, projector, rotate


def connected(nodes, neighbors):
    if not nodes:
        return True
    visited = {next(iter(nodes))}
    pending = list(visited)
    while pending:
        node = pending.pop()
        for adjacent in neighbors[node] & nodes - visited:
            visited.add(adjacent)
            pending.append(adjacent)
    return visited == nodes


def subsets_of_size(active, neighbors, size):
    subsets = {frozenset((node,)) for node in active}
    for stage in range(1, size):
        grown = set()
        for subset in subsets:
            adjacent = set.union(*(neighbors[node] for node in subset)) & active - subset
            for node in adjacent:
                grown.add(subset | {node})
        subsets = grown
    return subsets


def eliminate(matrix, subset, root, vector, neighbors):
    parent = {root: None}
    queue = [root]
    for node in queue:
        for adjacent in sorted(neighbors[node] & set(subset)):
            if adjacent not in parent:
                parent[adjacent] = node
                queue.append(adjacent)
    amplitudes = np.zeros(len(matrix), dtype=complex)
    amplitudes[list(subset)] = vector
    gates = []
    result = matrix.copy()
    for second in reversed(queue[1:]):
        first = parent[second]
        upper, lower = amplitudes[first], amplitudes[second]
        if abs(lower) < 1e-12:
            continue
        theta = math.atan2(abs(lower), abs(upper))
        phi = float(np.angle(-lower / upper)) if abs(upper) > 1e-14 else 0.0
        result = rotate(result, first, second, theta, phi)
        factor = np.sin(theta) * np.exp(1j * phi)
        amplitudes[first] = np.cos(theta) * upper - factor.conjugate() * lower
        amplitudes[second] = factor * upper + np.cos(theta) * lower
        gates.append((first, second, theta, phi))
    return result, gates


def compile_local(instance, seed):
    generator = np.random.default_rng(seed)
    matrix = projector(instance)
    size = len(matrix)
    neighbors = [set() for node in range(size)]
    for first, second in instance['edges']:
        neighbors[first].add(second)
        neighbors[second].add(first)
    initial = np.zeros(size)
    initial[instance['initial_occupied']] = 1
    active = set(range(size))
    gates = []
    while active:
        pure = [node for node in active if abs(matrix[node, node] - initial[node]) < 1e-10]
        for node in pure:
            if connected(active - {node}, neighbors):
                active.remove(node)
        if not active:
            break
        removable = {node for node in active if connected(active - {node}, neighbors)}
        choices = []
        for subset_size in range(2, len(active) + 1):
            for subset in subsets_of_size(active, neighbors, subset_size):
                nodes = sorted(subset)
                eigenvalues, eigenvectors = np.linalg.eigh(matrix[np.ix_(nodes, nodes)])
                for occupation in (0, 1):
                    selected = np.abs(eigenvalues - occupation) < 1e-10
                    if not np.any(selected):
                        continue
                    subspace = eigenvectors[:, selected]
                    for root in subset & removable:
                        if initial[root] != occupation:
                            continue
                        root_index = nodes.index(root)
                        vector = subspace @ subspace[root_index].conjugate()
                        norm = np.linalg.norm(vector)
                        if norm < 1e-10:
                            continue
                        vector /= norm
                        degree = len(neighbors[root] & active)
                        score = degree + generator.uniform(0, 3) if seed else degree - abs(vector[root_index])
                        choices.append((score, nodes, root, vector))
            if choices:
                break
        if not choices:
            return None
        choices.sort(key=lambda choice: choice[0])
        score, nodes, root, vector = choices[0]
        matrix, new_gates = eliminate(matrix, nodes, root, vector, neighbors)
        gates.extend(new_gates)
        active.remove(root)
    error = float(np.linalg.norm(matrix - np.diag(initial)))
    circuit = inverse_circuit(instance, gates)
    return circuit, error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', required=True)
    parser.add_argument('--trials', type=int, default=100)
    arguments = parser.parse_args()
    instance = next(instance for instance in load_instances() if instance['id'] == arguments.instance)
    best = (float('inf'), float('inf'))
    started = time.time()
    for seed in range(arguments.trials):
        result = compile_local(instance, seed)
        if result is None:
            continue
        circuit, error = result
        count = sum(map(len, circuit['layers']))
        depth = len(circuit['layers'])
        if error < 1e-8 and (count, depth) < best:
            best = count, depth
            Path(instance['id'] + '_local.json').write_text(json.dumps(circuit))
            print('LOCAL', instance['id'], seed, count, depth, error, 'elapsed', round(time.time() - started, 1), flush=True)
        if count <= instance['budgets']['max_gates'] and depth <= instance['budgets']['max_depth'] and error < 1e-8:
            return


if __name__ == '__main__':
    main()
