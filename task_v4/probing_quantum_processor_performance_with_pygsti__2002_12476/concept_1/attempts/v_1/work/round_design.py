import argparse
import json
from pathlib import Path

import numpy as np

from optimize import Problem, COSTS, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('continuous')
    parser.add_argument('--data', default='stress_training.npz')
    parser.add_argument('--tail', type=float, default=5)
    parser.add_argument('--boost', type=float, default=1.2)
    parser.add_argument('--output', default='design_rounded.json')
    args = parser.parse_args()
    problem = Problem(np.load(args.data), tail=args.tail, boost=args.boost)
    batches = np.load(args.continuous)
    selected = np.flatnonzero(batches > 1e-6)
    values, objective = problem.optimize(selected, batches[selected])
    features = problem.features[:, selected]
    information = features.transpose(0, 2, 1) @ (values[None, :, None] * features)
    covariance = np.linalg.inv(information + np.eye(14) * 1e-10)
    risk = np.trace(covariance[:, :12, :12], axis1=1, axis2=2)
    _, weights = problem.aggregate(risk, True)
    transformed = features @ covariance
    leverage = transformed @ features.transpose(0, 2, 1)
    core = transformed[:, :, :12] @ transformed[:, :, :12].transpose(0, 2, 1)
    hessian = 2 * np.einsum('sij,sij,s->ij', leverage, core, weights)
    first_derivative = -np.sum(transformed[:, :, :12] ** 2, axis=2)
    second_weights = 2 * problem.tail * problem.scenario_weights / problem.baseline_risks ** 2 * (risk / problem.baseline_risks > 0.55)
    hessian += np.einsum('si,sj,s->ij', first_derivative, first_derivative, second_weights)
    gradient = first_derivative.T @ weights
    lower = np.maximum(np.floor(values + 1e-7), 1).astype(int)
    variable = np.flatnonzero(lower < 48)
    if len(variable) > 21:
        raise ValueError('Too many rounding variables')
    candidates = []
    for start in range(0, 2 ** len(variable), 32768):
        numbers = np.arange(start, min(start + 32768, 2 ** len(variable)), dtype=np.uint32)
        allocations = np.tile(lower, (len(numbers), 1))
        allocations[:, variable] += ((numbers[:, None] >> np.arange(len(variable))) & 1).astype(int)
        legal = allocations @ COSTS[selected] + 12000 * len(selected) <= 1600000
        allocations = allocations[legal]
        difference = allocations - values
        approximation = difference @ gradient + 0.5 * np.einsum('bi,ij,bj->b', difference, hessian, difference, optimize=True)
        for position in np.argsort(approximation)[:40]:
            candidates.append((approximation[position], allocations[position]))
    candidates.sort(key=lambda candidate: candidate[0])
    best_value = np.inf
    best = None
    for approximation, candidate in candidates[:40]:
        value = problem.evaluate(candidate, selected)
        if value < best_value:
            best_value, best = value, candidate
    result = np.zeros(len(COSTS), dtype=int)
    result[selected] = best
    result = problem.integer(result.astype(float))
    Path(args.output).write_text(json.dumps({'batches': result.tolist()}) + '\n')
    print('continuous objective', objective, 'rounded objective', problem.evaluate(result), flush=True)
    report(result, args.output)


if __name__ == '__main__':
    main()
