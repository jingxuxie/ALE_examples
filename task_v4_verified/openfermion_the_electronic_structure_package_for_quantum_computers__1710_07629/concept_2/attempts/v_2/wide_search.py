import argparse
import json
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
    parser.add_argument('--tag', default='wide')
    parser.add_argument('--seconds', type=int, default=600)
    arguments = parser.parse_args()
    circuit = json.loads(Path(arguments.circuit).read_text())
    instance = next(instance for instance in load_instances() if instance['id'] == circuit['id'])
    gates = simplify(instance, [gate for layer in circuit['layers'] for gate in layer])
    edges = [(gate['u'], gate['v']) for gate in gates]
    parameters = gate_parameters(gates)
    parameters, best, _ = fit(instance, edges, parameters, max_evaluations=300)
    started = time.time()
    unique = set()
    candidates = []
    for score, position, edge in insertion_candidates(instance, edges, parameters):
        trial_edges = edges[:position] + [edge] + edges[position:]
        trial_parameters = np.insert(parameters.reshape(-1, 2), position, [0.001, -0.001], axis=0).ravel()
        key = fingerprint(parameters_gates(trial_edges, trial_parameters), instance['n_modes'])
        if key in unique:
            continue
        unique.add(key)
        fitted, error, _ = fit(instance, trial_edges, trial_parameters, max_evaluations=300)
        candidates.append((error, trial_edges, fitted, position, edge))
        if len(candidates) >= 20:
            break
    candidates.sort(key=lambda entry: entry[0])
    for candidate_index, (error, trial_edges, fitted, position, edge) in enumerate(candidates):
        print('ENLARGED', candidate_index, error, position, edge, flush=True)
        trial_gates = simplify(instance, parameters_gates(trial_edges, fitted))
        trial_edges = [(gate['u'], gate['v']) for gate in trial_gates]
        fitted = gate_parameters(trial_gates).reshape(-1, 2)
        choices = np.argsort(np.linalg.norm(fitted, axis=1))
        for removal in choices:
            reduced_edges = trial_edges[:removal] + trial_edges[removal + 1:]
            reduced_parameters = np.delete(fitted, removal, axis=0).ravel()
            optimized, final_error, _ = fit(instance, reduced_edges, reduced_parameters, max_evaluations=250)
            if final_error < best * (1 - 1e-8):
                best = final_error
                final_gates = simplify(instance, parameters_gates(reduced_edges, optimized))
                result = dict(id=instance['id'], layers=schedule(final_gates, instance['n_modes']))
                Path(f"{instance['id']}_{arguments.tag}.json.best").write_text(json.dumps(result))
                print('WIDE', candidate_index, removal, final_error, len(final_gates), len(result['layers']), 'elapsed', round(time.time() - started), flush=True)
                if final_error < 1e-8:
                    Path(f"{instance['id']}_{arguments.tag}.json").write_text(json.dumps(result))
                    if len(final_gates) <= instance['budgets']['max_gates'] and len(result['layers']) <= instance['budgets']['max_depth']:
                        return
            if time.time() - started > arguments.seconds:
                return


if __name__ == '__main__':
    main()
