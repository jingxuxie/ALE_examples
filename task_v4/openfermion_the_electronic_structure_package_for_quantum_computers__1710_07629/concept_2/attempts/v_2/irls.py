import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import least_squares

from compress import simplify
from optimize import Objective, fit, parameters_gates
from sparse_fit import color_graph
from synthesize import load_instances, projector, schedule


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', required=True)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--rounds', type=int, default=6)
    arguments = parser.parse_args()
    instance = next(instance for instance in load_instances() if instance['id'] == arguments.instance)
    target = projector(instance)
    instance['edges'] = [edge for edge in instance['edges'] if abs(target[tuple(edge)]) > 1e-12]
    generator = np.random.default_rng(arguments.seed)
    matchings = color_graph(instance, generator)
    edges = [edge for repetition in range(arguments.rounds) for matching in matchings for edge in matching]
    parameters = generator.normal(0, 0.03, 2 * len(edges))
    objective = Objective(instance, edges)
    weights = np.ones(len(edges))
    started = time.time()
    for stage in range(40):
        strength = 1e-4 if stage < 2 else 1e-5 if stage < 15 else 1e-6
        scales = np.repeat(np.sqrt(strength * weights), 2)
        penalty_jacobian = np.diag(scales)

        def residual(parameters):
            return np.concatenate((objective.residual(parameters), scales * parameters))

        def jacobian(parameters):
            return np.concatenate((objective.jacobian(parameters), penalty_jacobian), axis=0)

        result = least_squares(residual, parameters, jac=jacobian, method='lm', max_nfev=200,
                               ftol=1e-10, gtol=1e-10, xtol=1e-10)
        parameters = result.x
        norms = np.linalg.norm(parameters.reshape(-1, 2), axis=1)
        error = np.linalg.norm(objective.residual(parameters)) * np.sqrt(2)
        print('IRLS', instance['id'], arguments.seed, stage, 'error', error, 'count', np.count_nonzero(norms > 0.001),
              'large', np.count_nonzero(norms > 0.03), 'elapsed', round(time.time() - started, 1), flush=True)
        if stage >= 5:
            keep = norms > 0.001
            fitted_edges = [edge for edge, retained in zip(edges, keep) if retained]
            fitted, fitted_error, _ = fit(instance, fitted_edges, parameters.reshape(-1, 2)[keep].ravel(), max_evaluations=150)
            gates = simplify(instance, parameters_gates(fitted_edges, fitted))
            circuit = dict(id=instance['id'], layers=schedule(gates, instance['n_modes']))
            Path(f"{instance['id']}_irls_approx_{arguments.seed}.json").write_text(json.dumps(circuit))
            print('FIT', len(gates), len(circuit['layers']), fitted_error, flush=True)
            if fitted_error < 1e-8:
                Path(f"{instance['id']}_irls_{arguments.seed}.json").write_text(json.dumps(circuit))
                if len(gates) <= instance['budgets']['max_gates'] and len(circuit['layers']) <= instance['budgets']['max_depth']:
                    return
        smoothing = 0.05 if stage < 5 else 0.01 if stage < 15 else 0.002
        weights = 1 / (norms ** 2 + smoothing ** 2)


if __name__ == '__main__':
    main()
