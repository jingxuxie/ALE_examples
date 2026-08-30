import argparse
import json
import math
from pathlib import Path
import time

import numpy as np

from compress import simplify
from optimize import fit, gate_parameters, parameters_gates
from search import insertion_candidates
from synthesize import load_instances, schedule
from turnover import fingerprint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('circuit')
    parser.add_argument('--seconds', type=int, default=300)
    parser.add_argument('--seed', type=int, default=0)
    arguments = parser.parse_args()
    circuit = json.loads(Path(arguments.circuit).read_text())
    instance = next(instance for instance in load_instances() if instance['id'] == circuit['id'])
    gates = simplify(instance, [gate for layer in circuit['layers'] for gate in layer])
    edges = [(gate['u'], gate['v']) for gate in gates]
    parameters, error, _ = fit(instance, edges, gate_parameters(gates), max_evaluations=300)
    best = error, edges.copy(), parameters.copy()
    generator = np.random.default_rng(arguments.seed)
    started = time.time()
    candidates = insertion_candidates(instance, edges, parameters)
    seen = set()
    for iteration in range(100000):
        if time.time() - started > arguments.seconds:
            break
        if iteration and iteration % 100 == 0:
            error, edges, parameters = best[0], best[1].copy(), best[2].copy()
            candidates = insertion_candidates(instance, edges, parameters)
        removal = int(generator.integers(len(edges)))
        old_edge = edges[removal]
        old_parameters = parameters.reshape(-1, 2)[removal].copy()
        trial_edges = edges[:removal] + edges[removal + 1:]
        trial_parameters = np.delete(parameters.reshape(-1, 2), removal, axis=0)
        if generator.uniform() < 0.45:
            edge = old_edge
            position = int(generator.integers(len(trial_edges) + 1))
            addition = old_parameters
        else:
            rank = min(len(candidates) - 1, int(generator.exponential(50)))
            _, position, edge = candidates[rank]
            position = max(0, min(len(trial_edges), position - int(position > removal)))
            addition = generator.normal(0, 0.03, 2)
        trial_edges.insert(position, edge)
        trial_parameters = np.insert(trial_parameters, position, addition, axis=0).ravel()
        key = fingerprint(parameters_gates(trial_edges, trial_parameters), instance['n_modes'])
        if key in seen or len(key) > instance['budgets']['max_depth']:
            continue
        seen.add(key)
        fitted, trial_error, _ = fit(instance, trial_edges, trial_parameters, max_evaluations=90, tolerance=1e-10)
        temperature = max(1e-6, best[0] ** 2 * 0.25) * (1 - (iteration % 100) / 125)
        if trial_error < error or generator.uniform() < math.exp(min(0, (error ** 2 - trial_error ** 2) / temperature)):
            error, edges, parameters = trial_error, trial_edges, fitted
            candidates = insertion_candidates(instance, edges, parameters)
        if trial_error < best[0] * (1 - 1e-7):
            best = trial_error, trial_edges.copy(), fitted.copy()
            final_gates = simplify(instance, parameters_gates(trial_edges, fitted))
            result = dict(id=instance['id'], layers=schedule(final_gates, instance['n_modes']))
            Path(f"{instance['id']}_anneal_{arguments.seed}.json.best").write_text(json.dumps(result))
            print('ANNEAL', instance['id'], iteration, trial_error, len(final_gates), len(result['layers']), 'elapsed', round(time.time() - started), flush=True)
            if trial_error < 1e-8:
                Path(f"{instance['id']}_anneal_{arguments.seed}.json").write_text(json.dumps(result))
                return


if __name__ == '__main__':
    main()
