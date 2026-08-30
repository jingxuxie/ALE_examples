import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from exact import LIMIT, LOWER, evaluate
from optimize import Model


def refine(witness, maxiter=200, gradweight=100, output=None, verbose=True):
    model = Model(witness)
    initial = model.pack()
    split = np.r_[np.maximum(initial[:120], 0), np.maximum(-initial[:120], 0), initial[120]]
    row_jac = np.zeros((15, 241))
    row_jac[LOWER[0] - 1, np.arange(120)] = -1
    row_jac[LOWER[0] - 1, np.arange(120) + 120] = -1
    best = witness
    best_score = evaluate(witness)['core_score']
    start = time.time()
    count = 0

    def merge(parameters):
        return np.r_[parameters[:120] - parameters[120:240], parameters[240]]

    def transform(derivative):
        return np.concatenate([derivative[..., :120], -derivative[..., :120], derivative[..., 120:]], axis=-1)

    def objective(parameters):
        value, derivative = model.objective(merge(parameters), gradweight)
        return value, transform(derivative)

    def constraints(parameters):
        original = merge(parameters)
        values = model.constraints(original)
        values[:15] = LIMIT - 2e-12 + row_jac[:, :240] @ parameters[:240]
        return values

    def constraints_jac(parameters):
        original = merge(parameters)
        jacobian = transform(model.constraints_jac(original))
        jacobian[:15] = row_jac
        return jacobian

    def callback(parameters):
        nonlocal best, best_score, count
        count += 1
        if count % 10 == 0:
            current = model.unpack(merge(parameters))
            report = evaluate(current)
            if report['core_score'] > best_score:
                best, best_score = current, report['core_score']
                if output:
                    Path(output).write_text(json.dumps(best))
            if verbose:
                print(count, model.calls, round(time.time() - start, 1),
                      {key: round(report[key], 7) for key in ['reward_variance', 'gradient_infinity',
                      'entropy', 'energy_error_per_spin', 'target_sector_mass', 'proposal_sector_mass', 'core_score']}, flush=True)

    result = minimize(objective, split, method='SLSQP', jac=True,
                      bounds=[(0, LIMIT)] * 240 + [(1, 3)],
                      constraints={'type': 'ineq', 'fun': constraints, 'jac': constraints_jac},
                      callback=callback, options={'maxiter': maxiter, 'ftol': 1e-11, 'disp': verbose})
    final = model.unpack(merge(result.x))
    report = evaluate(final)
    if report['core_score'] > best_score:
        best, best_score = final, report['core_score']
    if output:
        Path(output).write_text(json.dumps(best))
        Path(str(output).replace('.json', '_last.json')).write_text(json.dumps(final))
    if verbose:
        print(json.dumps(report, indent=2), flush=True)
    return best, final


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--output', default='refined.json')
    parser.add_argument('--maxiter', type=int, default=200)
    parser.add_argument('--gradweight', type=float, default=100.0)
    arguments = parser.parse_args()
    refine(json.loads(Path(arguments.source).read_text()), arguments.maxiter, arguments.gradweight, arguments.output)
