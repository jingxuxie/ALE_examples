import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from exact import LIMIT, LOWER, evaluate
from optimize import Model


def minimax(witness, maxiter=150, output=None, verbose=True, strict=None, sector_limit=.001):
    model = Model(witness)
    original = model.pack()
    report = evaluate(witness)
    best_score = report['core_score']
    best = witness
    split = np.r_[np.maximum(original[:120], 0), np.maximum(-original[:120], 0),
                  original[120], 1 / best_score]
    row_jac = np.zeros((15, 242))
    row_jac[LOWER[0] - 1, np.arange(120)] = -1
    row_jac[LOWER[0] - 1, np.arange(120) + 120] = -1
    last_hessian = None
    last_hessian_parameters = None
    start = time.time()
    counter = 0

    def merge(parameters):
        return np.r_[parameters[:120] - parameters[120:240], parameters[240]]

    def transform(derivative):
        return np.concatenate([derivative[..., :120], -derivative[..., :120], derivative[..., 120:]], axis=-1)

    def hessian(parameters):
        nonlocal last_hessian, last_hessian_parameters
        if last_hessian_parameters is not None and np.array_equal(parameters, last_hessian_parameters):
            return last_hessian
        model.calc(parameters)
        residual = (model.spins + 1) / 2 - model.conditional
        scores = np.ascontiguousarray(residual[:, LOWER[0]] * model.spins[:, LOWER[1]])
        matrix = scores.T @ ((model.probq * (model.centered + 1))[:, None] * scores)
        for position in range(1, 16):
            indices = np.flatnonzero(LOWER[0] == position)
            curvature = -model.probq * model.centered * model.conditional[:, position] * (1 - model.conditional[:, position])
            block = model.spins[:, :position].T @ (curvature[:, None] * model.spins[:, :position])
            matrix[np.ix_(indices, indices)] += block
        last_hessian = np.column_stack([matrix, model.gradenergy])
        last_hessian_parameters = parameters.copy()
        return last_hessian

    def constraints(parameters):
        values, derivatives = model.calc(merge(parameters))
        slack = parameters[-1]
        return np.r_[LIMIT - 2e-12 + row_jac[:, :240] @ parameters[:240],
                     slack - values[0] / .05,
                     values[1] / 3 - 1 / slack,
                     values[2] / .4 - 1 / slack,
                     slack - values[3] / .32, slack + values[3] / .32,
                     values[4] / .35 - 1 / slack,
                     slack - values[5] / sector_limit,
                     slack - model.gradkl / .003,
                     slack + model.gradkl / .003]

    def constraints_jac(parameters):
        original = merge(parameters)
        values, derivatives = model.calc(original)
        slack = parameters[-1]
        hess = hessian(original)
        jacobian = np.vstack([-derivatives[0] / .05, derivatives[1] / 3, derivatives[2] / .4,
                              -derivatives[3] / .32, derivatives[3] / .32, derivatives[4] / .35,
                              -derivatives[5] / sector_limit, -hess / .003, hess / .003])
        slack_derivative = np.r_[1, 1 / slack ** 2, 1 / slack ** 2, 1, 1, 1 / slack ** 2, 1,
                                 np.ones(240)]
        return np.vstack([row_jac, np.column_stack([transform(jacobian), slack_derivative])])

    def callback(parameters):
        nonlocal counter, best, best_score
        counter += 1
        if counter % 5 == 0:
            current = model.unpack(merge(parameters))
            report = evaluate(current)
            if report['core_score'] > best_score:
                best, best_score = current, report['core_score']
                if output:
                    Path(output).write_text(json.dumps(best))
            if verbose:
                print(counter, model.calls, round(time.time() - start, 1), round(parameters[-1], 7),
                      {key: round(report[key], 7) for key in ['reward_variance', 'gradient_infinity',
                      'entropy', 'energy_error_per_spin', 'target_sector_mass', 'proposal_sector_mass', 'core_score']}, flush=True)

    objective_jacobian = np.r_[np.zeros(241), 1.0]

    def objective(parameters):
        if strict is None:
            return parameters[-1], objective_jacobian
        if strict == 'constant':
            return 0.0, np.zeros(242)
        values, derivatives = model.calc(merge(parameters))
        index = 0 if strict == 'variance' else 2
        return values[index], np.r_[transform(derivatives[index]), 0.0]

    result = minimize(objective, split,
                      method='SLSQP', jac=True,
                      bounds=[(0, LIMIT)] * 240 + [(1, 3), (1, 1) if strict else (.1, 1e8)],
                      constraints={'type': 'ineq', 'fun': constraints, 'jac': constraints_jac},
                      callback=callback, options={'maxiter': maxiter, 'ftol': 2e-10, 'disp': verbose})
    final = model.unpack(merge(result.x))
    report = evaluate(final)
    if report['core_score'] > best_score:
        best = final
    if output:
        Path(output).write_text(json.dumps(best))
        Path(str(output).replace('.json', '_last.json')).write_text(json.dumps(final))
    if verbose:
        print(json.dumps(report, indent=2), flush=True)
    return best


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--output', default='minimax.json')
    parser.add_argument('--maxiter', type=int, default=150)
    parser.add_argument('--strict', choices=['variance', 'kl', 'constant'])
    parser.add_argument('--sector-limit', type=float, default=.001)
    arguments = parser.parse_args()
    minimax(json.loads(Path(arguments.source).read_text()), arguments.maxiter, arguments.output,
            strict=arguments.strict, sector_limit=arguments.sector_limit)
