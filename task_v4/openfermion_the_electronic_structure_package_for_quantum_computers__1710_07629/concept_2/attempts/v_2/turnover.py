import argparse
import itertools
import json
import math
from pathlib import Path
import time

import numpy as np

from compress import simplify, wrap
from synthesize import load_instances, schedule


def apply_rows(matrix, first, second, theta, phase):
    cosine = math.cos(theta)
    factor = math.sin(theta) * np.exp(1j * phase)
    upper, lower = matrix[first].copy(), matrix[second].copy()
    matrix[first] = cosine * upper - factor.conjugate() * lower
    matrix[second] = factor * upper + cosine * lower


def triples(gates, neighborhoods):
    result = []
    for nodes in neighborhoods:
        intersecting = [index for index, gate in enumerate(gates) if gate['u'] in nodes or gate['v'] in nodes]
        for offset in range(len(intersecting) - 2):
            positions = intersecting[offset:offset + 3]
            edges = [frozenset((gates[index]['u'], gates[index]['v'])) for index in positions]
            if edges[0] == edges[2] and edges[0] != edges[1] and edges[0] | edges[1] == nodes:
                result.append(positions)
    return result


def turn(gates, positions):
    first_gate, middle_gate, final_gate = [gates[index] for index in positions]
    first_edge = {first_gate['u'], first_gate['v']}
    middle_edge = {middle_gate['u'], middle_gate['v']}
    shared = next(iter(first_edge & middle_edge))
    outer_first = next(iter(first_edge - {shared}))
    outer_second = next(iter(middle_edge - {shared}))
    nodes = [outer_first, shared, outer_second]
    matrix = np.eye(3, dtype=complex)
    for gate in (first_gate, middle_gate, final_gate):
        apply_rows(matrix, nodes.index(gate['u']), nodes.index(gate['v']), gate['theta'], gate['phi'])
    elimination = []
    for first, second, column in ((1, 2, 0), (0, 1, 0), (1, 2, 1)):
        upper, lower = matrix[first, column], matrix[second, column]
        theta = math.atan2(abs(lower), abs(upper))
        phase = float(np.angle(-lower / upper)) if abs(upper) > 1e-14 else 0.0
        apply_rows(matrix, first, second, theta, phase)
        elimination.append(dict(u=nodes[first], v=nodes[second], theta=-theta, phi=phase))
    diagonal = {node: float(np.angle(matrix[index, index])) for index, node in enumerate(nodes)}
    result = [dict(gate) for gate in gates]
    for gate in result[:positions[0]]:
        gate['phi'] = wrap(gate['phi'] + diagonal.get(gate['v'], 0) - diagonal.get(gate['u'], 0))
    for position, gate in zip(positions, reversed(elimination)):
        result[position] = gate
    return result


def fingerprint(gates, size):
    layers = schedule(gates, size)
    return tuple(tuple(sorted((min(gate['u'], gate['v']), max(gate['u'], gate['v'])) for gate in layer)) for layer in layers)


def optimize(instance, circuit, seconds, seed, output):
    generator = np.random.default_rng(seed)
    neighborhoods = set()
    for first_edge, second_edge in itertools.combinations(instance['edges'], 2):
        nodes = frozenset(first_edge) | frozenset(second_edge)
        if len(nodes) == 3:
            neighborhoods.add(nodes)
    gates = simplify(instance, [gate for layer in circuit['layers'] for gate in layer])
    size = instance['n_modes']
    best = len(gates), len(schedule(gates, size))
    best_gates = gates.copy()
    started = time.time()
    seen = set()
    last_improvement = 0
    for iteration in range(1000000):
        if time.time() - started > seconds:
            break
        choices = triples(gates, neighborhoods)
        if not choices:
            break
        generator.shuffle(choices)
        candidates = []
        for positions in choices:
            trial = simplify(instance, turn(gates, positions))
            key = fingerprint(trial, size)
            if key in seen:
                continue
            depth = len(key)
            candidates.append((len(trial), depth, trial, key))
            if len(trial) < len(gates):
                break
        if not candidates:
            seen.clear()
            gates = [dict(gate) for gate in best_gates]
            continue
        candidates.sort(key=lambda entry: (entry[0], entry[1] + generator.uniform(0, 5)))
        count, depth, gates, key = candidates[0]
        seen.add(key)
        if (count, depth) < best:
            best = count, depth
            best_gates = [dict(gate) for gate in gates]
            last_improvement = iteration
            result = dict(id=instance['id'], layers=schedule(gates, size))
            Path(output).write_text(json.dumps(result))
            print('TURNOVER', instance['id'], iteration, count, depth, 'elapsed', round(time.time() - started, 1), flush=True)
            if count <= instance['budgets']['max_gates'] and depth <= instance['budgets']['max_depth']:
                return result
        if iteration - last_improvement > 1000:
            gates = [dict(gate) for gate in best_gates]
            seen.clear()
            last_improvement = iteration
    result = dict(id=instance['id'], layers=schedule(best_gates, size))
    Path(output).write_text(json.dumps(result))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('circuit')
    parser.add_argument('--seconds', type=int, default=400)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--output')
    arguments = parser.parse_args()
    circuit = json.loads(Path(arguments.circuit).read_text())
    instance = next(instance for instance in load_instances() if instance['id'] == circuit['id'])
    optimize(instance, circuit, arguments.seconds, arguments.seed, arguments.output or instance['id'] + '_turned.json')


if __name__ == '__main__':
    main()
