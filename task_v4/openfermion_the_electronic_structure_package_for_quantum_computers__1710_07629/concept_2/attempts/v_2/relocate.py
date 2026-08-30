import argparse
import json
from pathlib import Path
import time

import numpy as np

from compress import simplify
from optimize import fit, gate_parameters, parameters_gates
from synthesize import load_instances, schedule
from turnover import fingerprint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('circuit')
    parser.add_argument('--seconds', type=int, default=600)
    parser.add_argument('--tag', default='relocated')
    parser.add_argument('--seed', type=int, default=0)
    arguments = parser.parse_args()
    circuit = json.loads(Path(arguments.circuit).read_text())
    instance = next(instance for instance in load_instances() if instance['id'] == circuit['id'])
    gates = simplify(instance, [gate for layer in circuit['layers'] for gate in layer])
    edges = [(gate['u'], gate['v']) for gate in gates]
    parameters, best, _ = fit(instance, edges, gate_parameters(gates), max_evaluations=300)
    generator = np.random.default_rng(arguments.seed)
    started = time.time()
    for round_index in range(10):
        base_edges = edges.copy()
        base_parameters = parameters.reshape(-1, 2).copy()
        visited = {fingerprint(parameters_gates(base_edges, base_parameters.ravel()), instance['n_modes'])}
        moves = [(removed, inserted) for removed in range(len(edges)) for inserted in range(len(edges)) if removed != inserted]
        generator.shuffle(moves)
        moves.sort(key=lambda move: abs(move[0] - move[1]))
        improvement = False
        for iteration, (removed, inserted) in enumerate(moves):
            order = list(range(len(base_edges)))
            order.insert(inserted, order.pop(removed))
            trial_edges = [base_edges[index] for index in order]
            trial_parameters = base_parameters[order].ravel()
            key = fingerprint(parameters_gates(trial_edges, trial_parameters), instance['n_modes'])
            if key in visited or len(key) > instance['budgets']['max_depth'] + 1:
                continue
            visited.add(key)
            fitted, error, _ = fit(instance, trial_edges, trial_parameters, max_evaluations=150)
            if error < best * (1 - 1e-6):
                best, edges, parameters = error, trial_edges, fitted
                result_gates = simplify(instance, parameters_gates(edges, parameters))
                result = dict(id=instance['id'], layers=schedule(result_gates, instance['n_modes']))
                Path(f"{instance['id']}_{arguments.tag}.json.best").write_text(json.dumps(result))
                improvement = True
                print('MOVE', instance['id'], round_index, iteration, removed, inserted, error,
                      len(result_gates), len(result['layers']), 'elapsed', round(time.time() - started), flush=True)
                if error < 1e-8:
                    Path(f"{instance['id']}_{arguments.tag}.json").write_text(json.dumps(result))
                    if len(result_gates) <= instance['budgets']['max_gates'] and len(result['layers']) <= instance['budgets']['max_depth']:
                        return
            if time.time() - started > arguments.seconds:
                return
        if not improvement:
            return


if __name__ == '__main__':
    main()
