import argparse
import itertools
import json
from pathlib import Path
import time

import numpy as np

from compress import simplify
from optimize import fit, gate_parameters, parameters_gates
from synthesize import load_instances, schedule


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('circuit')
    parser.add_argument('--seconds', type=int, default=650)
    parser.add_argument('--tag', default='0')
    arguments = parser.parse_args()
    circuit = json.loads(Path(arguments.circuit).read_text())
    instance = next(instance for instance in load_instances() if instance['id'] == circuit['id'])
    gates = simplify(instance, [gate for layer in circuit['layers'] for gate in layer])
    edges = [(gate['u'], gate['v']) for gate in gates]
    parameters = gate_parameters(gates).reshape(-1, 2)
    norms = np.linalg.norm(parameters, axis=1)
    removals = len(gates) - instance['budgets']['max_gates']
    choices = list(itertools.combinations(range(len(gates)), removals))
    choices.sort(key=lambda choice: sum(norms[list(choice)]))
    best = float('inf')
    started = time.time()
    for index, choice in enumerate(choices):
        keep = np.ones(len(gates), dtype=bool)
        keep[list(choice)] = False
        trial_edges = [edge for edge, retained in zip(edges, keep) if retained]
        fitted, error, evaluations = fit(instance, trial_edges, parameters[keep].ravel(), max_evaluations=200)
        if error < best:
            best = error
            result_gates = simplify(instance, parameters_gates(trial_edges, fitted))
            result = dict(id=instance['id'], layers=schedule(result_gates, instance['n_modes']))
            Path(f"{instance['id']}_drop_{arguments.tag}.json.best").write_text(json.dumps(result))
            print('DROP', instance['id'], index, choice, error, len(result_gates), len(result['layers']), 'elapsed', round(time.time() - started), flush=True)
            if error < 1e-8:
                Path(f"{instance['id']}_drop_{arguments.tag}.json").write_text(json.dumps(result))
                if len(result['layers']) <= instance['budgets']['max_depth']:
                    return
        if index % 100 == 0:
            print('PROGRESS', index, best, round(time.time() - started), flush=True)
        if time.time() - started > arguments.seconds:
            return


if __name__ == '__main__':
    main()
