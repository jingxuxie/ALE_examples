import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy.optimize import linprog
from scipy.linalg import solve


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
from hidden.engine import FREQUENCIES, certify_coefficients, sampled_basis, validate_pair


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--restarts', type=int, default=30)
    parser.add_argument('--grid', type=int, default=64)
    parser.add_argument('--seconds', type=float, default=900)
    args = parser.parse_args()
    start = time.monotonic()
    pairs = [(first, second) for first in range(18) for second in range(first, 18)
             if (FREQUENCIES[first] + FREQUENCIES[second]) % 2 == 0 and not (first < 2 and second < 2)]
    basis, _ = sampled_basis(args.grid)
    source, target = np.triu_indices(args.grid)
    columns = []
    for first, second in pairs:
        column = basis[source, first] * basis[target, second]
        if first != second:
            column += basis[source, second] * basis[target, first]
        columns.append(column)
    features = np.column_stack(columns)
    constraints = np.vstack([features, -features])
    bounds = np.concatenate([np.full(len(source), 4.98), np.full(len(source), 0.9)])
    generator = np.random.default_rng(83029)
    best = 1.0
    records = []
    solver_failures = []
    for restart in range(args.restarts):
        if time.monotonic() - start > args.seconds:
            break
        gradient = generator.normal(size=len(pairs))
        previous = 0.0
        for iteration in range(25):
            if time.monotonic() - start > args.seconds:
                break
            direction = gradient / max(np.max(np.abs(gradient)), 1e-12)
            result = linprog(-direction, A_ub=constraints, b_ub=bounds, bounds=[(-1, 1)] * len(pairs), method='highs')
            if not result.success:
                solver_failures.append({'restart': restart, 'iteration': iteration, 'message': result.message})
                break
            matrix = np.zeros((18, 18))
            for coefficient, (first, second) in zip(result.x, pairs):
                matrix[first, second] = matrix[second, first] = coefficient
            response = solve(np.eye(18) - matrix, np.eye(18)[:, :2], assume_a='pos')
            raw_ratio = float(np.trace(response[:2]) / 2)
            gradient_matrix = response @ response.T / 2
            gradient = np.array([gradient_matrix[first, second] * (1 if first == second else 2) for first, second in pairs])
            fine_basis, _ = sampled_basis(1024)
            values = 1 + fine_basis @ matrix @ fine_basis.T
            squared = FREQUENCIES[:, None] ** 2 + FREQUENCIES[None, :] ** 2
            error = (2 * np.pi / 1024) ** 2 * np.sum(np.abs(matrix) * squared) / 4
            minimum = float(values.min() - error)
            maximum = float(values.max() + error)
            contraction = min(1, 0.919999 / max(1 - minimum, 1e-9), 4.999999 / max(maximum - 1, 1e-9))
            candidate = matrix * contraction
            tensor, certificate = certify_coefficients(candidate)
            ratio = float(np.trace(tensor))
            if ratio > best:
                best = ratio
                artifact = {'schema_version': 1, 'kernel_a': np.zeros((18, 18)).tolist(), 'kernel_b': candidate.tolist()}
                directory = ROOT / 'adversary' / 'vertex_best'
                directory.mkdir(parents=True, exist_ok=True)
                (directory / 'witness.json').write_text(json.dumps(artifact, indent=2) + '\n')
                report = validate_pair((np.zeros((18, 18)), candidate))
                (directory / 'score.json').write_text(json.dumps(report, indent=2) + '\n')
                print(json.dumps({'restart': restart, 'iteration': iteration, 'trace_ratio': best,
                                  'raw_ratio': raw_ratio, 'contraction': contraction,
                                  'passed': report['passed'], 'elapsed_seconds': time.monotonic() - start}), flush=True)
            if abs(raw_ratio - previous) < 1e-9:
                break
            previous = raw_ratio
        records.append({'restart': restart, 'best_trace_ratio': best, 'elapsed_seconds': time.monotonic() - start})
    (ROOT / 'adversary' / 'vertex_search.json').write_text(json.dumps({'restarts': len(records), 'best_trace_ratio': best,
                                                                   'elapsed_seconds': time.monotonic() - start,
                                                                   'records': records, 'solver_failures': solver_failures}, indent=2) + '\n')


if __name__ == '__main__':
    main()
