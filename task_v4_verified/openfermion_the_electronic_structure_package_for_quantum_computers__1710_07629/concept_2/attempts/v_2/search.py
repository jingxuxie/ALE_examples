import argparse
import json
from pathlib import Path
import time

import numpy as np

from compress import simplify
from optimize import Objective, coefficients, fit, gate_parameters, parameters_gates
from synthesize import load_instances, projector, schedule


def insertion_candidates(instance, edges, parameters):
    objective = Objective(instance, edges)
    residual, jacobian = objective.compute(parameters)
    left, singular, _ = np.linalg.svd(jacobian, full_matrices=False)
    tangent = left[:, singular > 1e-8]
    cosine, factor, _, _ = coefficients(parameters)
    frame = objective.initial.copy()
    frames = [frame.copy()]
    for index, (first, second) in enumerate(edges):
        upper, lower = frame[first].copy(), frame[second].copy()
        frame[first] = cosine[index] * upper - factor[index].conjugate() * lower
        frame[second] = factor[index] * upper + cosine[index] * lower
        frames.append(frame.copy())
    backward = objective.vacant.copy()
    columns = []
    choices = []
    for position in range(len(edges), -1, -1):
        frame = frames[position]
        for first, second in instance['edges']:
            edge = (first, second)
            if position < len(edges) and edge == tuple(edges[position]):
                continue
            if position and edge == tuple(edges[position - 1]):
                continue
            cross_first = backward[:, first, None] * frame[second]
            cross_second = backward[:, second, None] * frame[first]
            horizontal = -cross_first + cross_second
            vertical = 1j * (cross_first + cross_second)
            columns.append(np.concatenate((horizontal.real.ravel(), horizontal.imag.ravel())))
            columns.append(np.concatenate((vertical.real.ravel(), vertical.imag.ravel())))
            choices.append((position, edge))
        if position:
            index = position - 1
            first, second = edges[index]
            upper, lower = backward[:, first].copy(), backward[:, second].copy()
            backward[:, first] = cosine[index] * upper + factor[index] * lower
            backward[:, second] = -factor[index].conjugate() * upper + cosine[index] * lower
    derivatives = np.array(columns).T
    derivatives -= tangent @ (tangent.T @ derivatives)
    horizontal = derivatives[:, ::2]
    vertical = derivatives[:, 1::2]
    diagonal_first = np.sum(horizontal ** 2, axis=0) + 1e-6
    diagonal_second = np.sum(vertical ** 2, axis=0) + 1e-6
    cross = np.sum(horizontal * vertical, axis=0)
    gradient_first = residual @ horizontal
    gradient_second = residual @ vertical
    determinant = diagonal_first * diagonal_second - cross ** 2
    scores = (diagonal_second * gradient_first ** 2 + diagonal_first * gradient_second ** 2 - 2 * cross * gradient_first * gradient_second) / determinant
    ranked = np.argsort(scores)[::-1]
    return [(float(scores[index]), *choices[index]) for index in ranked]


def remove_best(instance, edges, parameters, count=12, forbidden=None, max_depth=None):
    pairs = parameters.reshape(-1, 2)
    norms = np.linalg.norm(pairs, axis=1)
    ordering = np.argsort(norms)
    best = None
    for index in ordering[:count]:
        if index == forbidden:
            continue
        trial_edges = edges[:index] + edges[index + 1:]
        trial_parameters = np.delete(pairs, index, axis=0).ravel()
        if max_depth is not None and len(schedule(parameters_gates(trial_edges, trial_parameters), instance['n_modes'])) > max_depth:
            continue
        fitted, error, _ = fit(instance, trial_edges, trial_parameters, max_evaluations=80, tolerance=1e-10)
        if best is None or error < best[0]:
            best = error, trial_edges, fitted, int(index)
        if error < 1e-10:
            break
    return best


def search(instance, circuit, output, seconds, seed, quick=False, depth_limit=False):
    generator = np.random.default_rng(seed)
    gates = simplify(instance, [gate for layer in circuit['layers'] for gate in layer])
    edges = [(gate['u'], gate['v']) for gate in gates]
    parameters = gate_parameters(gates)
    budget = instance['budgets']['max_gates']
    max_depth = instance['budgets']['max_depth'] if depth_limit else None
    started = time.time()
    while len(edges) > budget:
        error, edges, parameters, removed = remove_best(instance, edges, parameters, count=min(len(edges), 18) if quick else len(edges))
        gates = simplify(instance, parameters_gates(edges, parameters))
        edges = [(gate['u'], gate['v']) for gate in gates]
        parameters = gate_parameters(gates)
        print('REDUCE', instance['id'], len(edges), 'error', error, 'removed', removed, 'elapsed', round(time.time() - started), flush=True)
    parameters, error, _ = fit(instance, edges, parameters, max_evaluations=300)
    best = error, edges.copy(), parameters.copy()
    failures = 0
    for iteration in range(1000):
        gates = simplify(instance, parameters_gates(edges, parameters))
        edges = [(gate['u'], gate['v']) for gate in gates]
        parameters = gate_parameters(gates)
        circuit = dict(id=instance['id'], layers=schedule(gates, instance['n_modes']))
        if error < 1e-8:
            Path(output).write_text(json.dumps(circuit))
            print('EXACT', instance['id'], len(gates), len(circuit['layers']), error, flush=True)
            if len(circuit['layers']) <= instance['budgets']['max_depth']:
                return circuit
        if time.time() - started > seconds:
            break
        candidates = insertion_candidates(instance, edges, parameters)
        trial_best = None
        used = set()
        for score, position, edge in candidates:
            if edge in used:
                continue
            used.add(edge)
            trial_edges = edges[:position] + [edge] + edges[position:]
            trial_parameters = np.insert(parameters.reshape(-1, 2), position, [0.001, -0.001], axis=0).ravel()
            fitted, enlarged_error, _ = fit(instance, trial_edges, trial_parameters, max_evaluations=130, tolerance=1e-11)
            enlarged_gates = simplify(instance, parameters_gates(trial_edges, fitted))
            trial_edges = [(gate['u'], gate['v']) for gate in enlarged_gates]
            fitted = gate_parameters(enlarged_gates)
            if len(trial_edges) <= budget:
                reduced = enlarged_error, trial_edges, fitted, -1
                if max_depth is not None and len(schedule(enlarged_gates, instance['n_modes'])) > max_depth:
                    reduced = None
            else:
                reduced = remove_best(instance, trial_edges, fitted, count=len(trial_edges) if depth_limit else min(len(trial_edges), 20), max_depth=max_depth)
            if reduced is None:
                if len(used) >= 12:
                    break
                continue
            if trial_best is None or reduced[0] < trial_best[0]:
                trial_best = reduced
            if reduced[0] < error * 0.8 or len(used) >= 3:
                break
        if trial_best is None:
            break
        new_error, new_edges, new_parameters, removed = trial_best
        if new_error < error * (1 - 1e-7):
            error, edges, parameters = new_error, new_edges, new_parameters
            failures = 0
        else:
            failures += 1
            if failures >= 2:
                error, edges, parameters = best[0], best[1].copy(), best[2].copy()
                choices = np.arange(len(edges)) if depth_limit else np.argsort(np.linalg.norm(parameters.reshape(-1, 2), axis=1))[:max(8, len(edges) // 3)]
                removal = int(generator.choice(choices))
                old_edge = edges.pop(removal)
                parameters = np.delete(parameters.reshape(-1, 2), removal, axis=0).ravel()
                _, position, edge = candidates[int(generator.integers(min(50, len(candidates))))]
                if depth_limit and generator.uniform() < 0.6:
                    edge = old_edge
                    position = int(generator.integers(len(edges) + 1))
                position = min(position, len(edges))
                edges.insert(position, edge)
                parameters = np.insert(parameters.reshape(-1, 2), position, generator.normal(0, 0.2, 2), axis=0).ravel()
                if max_depth is not None and len(schedule(parameters_gates(edges, parameters), instance['n_modes'])) > max_depth:
                    error, edges, parameters = best[0], best[1].copy(), best[2].copy()
                parameters, error, _ = fit(instance, edges, parameters, max_evaluations=180)
                failures = 0
        if error < best[0]:
            best = error, edges.copy(), parameters.copy()
            snapshot = dict(id=instance['id'], layers=schedule(parameters_gates(edges, parameters), instance['n_modes']))
            Path(output + '.best').write_text(json.dumps(snapshot))
        print('SEARCH', instance['id'], iteration, 'error', error, 'best', best[0], 'depth', len(circuit['layers']), 'elapsed', round(time.time() - started), flush=True)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('circuit')
    parser.add_argument('--seconds', type=int, default=900)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--output')
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--support-only', action='store_true')
    parser.add_argument('--depth-limit', action='store_true')
    arguments = parser.parse_args()
    circuit = json.loads(Path(arguments.circuit).read_text())
    instance = next(instance for instance in load_instances() if instance['id'] == circuit['id'])
    if arguments.support_only:
        target = projector(instance)
        instance['edges'] = [edge for edge in instance['edges'] if abs(target[tuple(edge)]) > 1e-12]
        permitted = {frozenset(edge) for edge in instance['edges']}
        circuit['layers'] = [[gate for gate in layer if frozenset((gate['u'], gate['v'])) in permitted] for layer in circuit['layers']]
        circuit['layers'] = [layer for layer in circuit['layers'] if layer]
    search(instance, circuit, arguments.output or instance['id'] + '_searched.json', arguments.seconds, arguments.seed, arguments.quick, arguments.depth_limit)


if __name__ == '__main__':
    main()
