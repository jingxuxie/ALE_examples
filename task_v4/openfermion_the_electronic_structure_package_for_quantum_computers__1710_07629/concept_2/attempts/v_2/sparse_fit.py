import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from optimize import Objective, fit, gate_parameters, parameters_gates
from synthesize import load_instances, projector, schedule
from compress import simplify


def color_graph(instance, generator):
    edges = [tuple(edge) for edge in instance['edges']]
    for attempt in range(10000):
        remaining = edges.copy()
        generator.shuffle(remaining)
        matchings = []
        while remaining:
            matching = []
            used = set()
            for edge in remaining:
                if not used.intersection(edge):
                    matching.append(edge)
                    used.update(edge)
            remaining = [edge for edge in remaining if edge not in matching]
            matchings.append(matching)
        if len(matchings) == 3:
            return matchings
    return matchings


def sparse_fit(instance, seed, rounds, time_limit, tail_path=None, compact=False):
    generator = np.random.default_rng(seed)
    matchings = color_graph(instance, generator)
    edges = [edge for repetition in range(rounds) for matching in matchings for edge in matching]
    parameters = generator.normal(0, 0.02, 2 * len(edges))
    if tail_path:
        tail_circuit = json.loads(Path(tail_path).read_text())
        tail = [gate for layer in tail_circuit['layers'] for gate in layer]
        edges.extend([(gate['u'], gate['v']) for gate in tail])
        parameters = np.concatenate((parameters, gate_parameters(tail)))
    objective = Objective(instance, edges)
    started = time.time()
    weights = np.ones(len(edges))
    best = (float('inf'), None)
    for stage in range(20):
        strength = 0.001 if stage < 5 else 0.0001
        smoothing = 0.0001 if stage < 5 else 0.00001

        def penalized(parameters):
            value, gradient = objective.fast_value_gradient(parameters)
            pairs = parameters.reshape(-1, 2)
            norms = np.sqrt(np.sum(pairs ** 2, axis=1) + smoothing ** 2)
            value += strength * np.dot(weights, norms)
            gradient += (strength * weights[:, None] * pairs / norms[:, None]).ravel()
            return value, gradient

        result = minimize(penalized, parameters, method='L-BFGS-B', jac=True,
                          options=dict(maxiter=1800, ftol=1e-14, gtol=1e-9, maxcor=30, maxls=50))
        parameters = result.x
        norms = np.linalg.norm(parameters.reshape(-1, 2), axis=1)
        value = objective.fast_value_gradient(parameters)[0]
        print(instance['id'], seed, 'stage', stage, 'elapsed', round(time.time() - started, 1),
              'error', np.sqrt(4 * value), 'nonzero', np.count_nonzero(norms > 0.01),
              'large', np.count_nonzero(norms > 0.1), 'niter', result.nit, flush=True)
        keep = norms > (0.008 if stage < 5 else 0.001)
        reduced_edges = [edge for edge, retained in zip(edges, keep) if retained]
        reduced_parameters = parameters.reshape(-1, 2)[keep].ravel()
        if len(reduced_edges) < best[0] + 10:
            fitted, error, evaluations = fit(instance, reduced_edges, reduced_parameters, max_evaluations=200)
            gates = simplify(instance, parameters_gates(reduced_edges, fitted))
            circuit = dict(id=instance['id'], layers=schedule(gates, instance['n_modes']))
            Path(f"{instance['id']}_approx_{seed}.json").write_text(json.dumps(circuit))
            print('FIT', instance['id'], seed, 'gates', len(gates), 'depth', len(circuit['layers']),
                  'error', error, 'evaluations', evaluations, flush=True)
            if error < 1e-8:
                Path(f"{instance['id']}_sparse_{seed}.json").write_text(json.dumps(circuit))
                best = (len(gates), circuit)
                if len(gates) <= instance['budgets']['max_gates'] and len(circuit['layers']) <= instance['budgets']['max_depth']:
                    return circuit
        weights = 0.03 / (norms + 0.03)
        if compact and stage >= 2:
            retained = norms > 0.0005
            edges = [edge for edge, keep_edge in zip(edges, retained) if keep_edge]
            parameters = parameters.reshape(-1, 2)[retained].ravel()
            weights = weights[retained]
            objective = Objective(instance, edges)
        if time.time() - started > time_limit:
            break
    return best[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', required=True)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--rounds', type=int, default=5)
    parser.add_argument('--seconds', type=int, default=900)
    parser.add_argument('--tail')
    parser.add_argument('--compact', action='store_true')
    parser.add_argument('--support-only', action='store_true')
    arguments = parser.parse_args()
    instance = next(instance for instance in load_instances() if instance['id'] == arguments.instance)
    if arguments.support_only:
        target = projector(instance)
        instance['edges'] = [edge for edge in instance['edges'] if abs(target[tuple(edge)]) > 1e-12]
    sparse_fit(instance, arguments.seed, arguments.rounds, arguments.seconds, arguments.tail, arguments.compact)


if __name__ == '__main__':
    main()
