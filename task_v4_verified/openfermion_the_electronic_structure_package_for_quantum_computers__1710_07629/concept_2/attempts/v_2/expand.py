import argparse
import json
from pathlib import Path

import numpy as np

from compress import simplify
from optimize import fit, gate_parameters, parameters_gates
from search import insertion_candidates
from synthesize import load_instances, schedule
from turnover import fingerprint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('circuit')
    parser.add_argument('--tag', default='expanded')
    parser.add_argument('--depth-limit', action='store_true')
    arguments = parser.parse_args()
    circuit = json.loads(Path(arguments.circuit).read_text())
    instance = next(instance for instance in load_instances() if instance['id'] == circuit['id'])
    gates = simplify(instance, [gate for layer in circuit['layers'] for gate in layer])
    edges = [(gate['u'], gate['v']) for gate in gates]
    parameters = gate_parameters(gates)
    for iteration in range(12):
        parameters, error, _ = fit(instance, edges, parameters, max_evaluations=500)
        gates = simplify(instance, parameters_gates(edges, parameters))
        circuit = dict(id=instance['id'], layers=schedule(gates, instance['n_modes']))
        print('EXPAND', instance['id'], iteration, len(gates), len(circuit['layers']), error, flush=True)
        if error < 1e-8:
            Path(f"{instance['id']}_{arguments.tag}.json").write_text(json.dumps(circuit))
            return
        seen = set()
        best = None
        for score, position, edge in insertion_candidates(instance, edges, parameters):
            trial_edges = edges[:position] + [edge] + edges[position:]
            trial_parameters = np.insert(parameters.reshape(-1, 2), position, [0.001, -0.001], axis=0).ravel()
            key = fingerprint(parameters_gates(trial_edges, trial_parameters), instance['n_modes'])
            if key in seen or (arguments.depth_limit and len(key) > instance['budgets']['max_depth']):
                continue
            seen.add(key)
            fitted, trial_error, _ = fit(instance, trial_edges, trial_parameters, max_evaluations=300)
            if best is None or trial_error < best[0]:
                best = trial_error, trial_edges, fitted
            if len(seen) >= 12 or trial_error < 1e-9:
                break
        if best is None:
            return
        error, edges, parameters = best


if __name__ == '__main__':
    main()
