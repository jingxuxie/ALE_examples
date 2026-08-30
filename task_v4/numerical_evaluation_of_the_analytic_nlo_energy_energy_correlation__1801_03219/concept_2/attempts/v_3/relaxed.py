import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, eye, hstack, vstack

from fractional import samples
from optimize import cached_checks, measure, kernel, quantize
from target import panel
from problem import FAMILIES
from approximate import minimum_norm


def solve(witness, masks, seed, budget=1e-8, count=512):
    coefficients = np.array(seed['cosine'] + seed['sine']) / 1e10
    orthant = np.where(coefficients >= 0, 1.0, -1.0)
    rows = []
    widths = []
    errors = []
    for channel, leaves in enumerate(masks):
        parents = set()
        error_sum = np.zeros(24)
        for leaf in leaves:
            constraint, error = cached_checks(witness, leaf)
            error_sum += error[channel]
            details = panel(kernel.integrand(seed, FAMILIES[channel]), leaf / 8, (leaf + 1) / 8)
            variation = max(details['l1'], 1e-8)
            embedded_bound = (budget / len(leaves)) ** (2 / 3) * variation ** (1 / 3) / 200 * 0.9
            rows.extend([constraint[channel], constraint[channel + 3]])
            widths.extend([embedded_bound, budget / len(leaves)])
            if leaf // 2 not in parents:
                rows.append(constraint[channel + 6])
                widths.append(2 * budget / len(leaves))
                parents.add(leaf // 2)
        errors.append(error_sum)
    errors = np.array(errors)
    signs = np.sign(errors @ coefficients)
    if np.any(signs == 0):
        return None
    rows = np.array(rows)
    widths = np.array(widths)
    scales = np.linalg.norm(rows, axis=1)
    rows /= scales[:, None]
    widths /= scales
    basis_matrix, l1_weights, means = samples(witness, count)
    reduced_basis = csr_matrix(basis_matrix * orthant)
    objective_errors = errors / means[:, None] * 1e6 * signs[:, None]
    reduced_errors = csr_matrix(objective_errors * orthant)
    inequalities = vstack([
        hstack([reduced_basis, -eye(count), csr_matrix((count, 1))]),
        hstack([-reduced_basis, -eye(count), csr_matrix((count, 1))]),
        hstack([csr_matrix((3, 24)), csr_matrix(l1_weights), csr_matrix((3, 1))]),
        hstack([-reduced_errors, csr_matrix((3, count)), np.ones((3, 1))]),
        hstack([csr_matrix(rows * orthant - widths[:, None]), csr_matrix((len(rows), count + 1))]),
        hstack([csr_matrix(-rows * orthant - widths[:, None]), csr_matrix((len(rows), count + 1))]),
    ]).tocsr()
    bounds = np.r_[np.zeros(2 * count), np.ones(3), np.zeros(3 + 2 * len(rows))]
    result = linprog(np.r_[np.zeros(24 + count), -1], A_ub=inequalities, b_ub=bounds, method='highs',
                     bounds=[(0, None)] * (24 + count) + [(None, None)],
                     options=dict(primal_feasibility_tolerance=1e-10, dual_feasibility_tolerance=1e-10))
    if not result.success:
        return None
    coefficients = orthant * result.x[:24]
    try:
        candidate = minimum_norm(witness, coefficients)
    except ValueError:
        return None
    return -result.fun / 10, candidate


def run():
    started = time.time()
    prefix = os.environ.get('RELAXED_PREFIX', 'relaxed_minimum')
    sources = sys.argv[1:] or ['fractional_same_candidates.json', 'different_candidates.json']
    candidates = []
    for source in sources:
        data = json.loads(Path(source).read_text())
        for item in data[:100]:
            seed = item[1]
            masks = item[2]
            if isinstance(masks[0], int):
                masks = [[leaf] for leaf in masks]
            for budget in (8e-9, 2e-8, 3e-8):
                result = solve(seed, masks, seed, budget=budget, count=384)
                if result is not None:
                    potential, candidate = result
                    candidates.append((potential, candidate, masks, budget))
        print('source', source, len(candidates), time.time() - started, flush=True)
    candidates.sort(key=lambda item: item[0], reverse=True)
    Path(prefix + '_candidates.json').write_text(json.dumps(candidates))
    best = 0
    for potential, candidate, masks, budget in candidates[:100]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
        print('screen', candidate['bin'], masks, budget, potential, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path(prefix + '_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path(prefix + '_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
