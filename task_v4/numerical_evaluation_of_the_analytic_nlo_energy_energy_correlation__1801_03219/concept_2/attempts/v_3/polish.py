import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import null_space
from scipy.optimize import minimize

from fractional import samples
from optimize import cached_checks, quantize, measure, kernel


def polish(seed, masks, count=4096, mean_weight=0, minimum_floor=0, grading=False):
    rows = []
    error_sum = np.zeros((3, 24))
    for channel, leaves in enumerate(masks):
        parents = set()
        for leaf in leaves:
            constraint, errors = cached_checks(seed, leaf)
            error_sum[channel] += errors[channel]
            rows.extend([constraint[channel], constraint[channel + 3]])
            if leaf // 2 not in parents:
                rows.append(constraint[channel + 6])
                parents.add(leaf // 2)
    rows = np.array(rows)
    rows /= np.linalg.norm(rows, axis=1)[:, None]
    null = null_space(rows, rcond=1e-12)
    dimension = null.shape[1]
    coefficients = np.array(seed['cosine'] + seed['sine']) / 1e10
    signs = np.sign(error_sum @ coefficients)
    basis_matrix, l1_weights, means = samples(seed, count)
    reduced_basis = basis_matrix @ null
    if grading:
        from grade_screen import grid
        coarse_basis, coarse_weights = grid(seed, 24, 32)
        fine_basis, fine_weights = grid(seed, 36, 64)
        coarse_basis = coarse_basis @ null
        fine_basis = fine_basis @ null
        coarse_weights = abs(coarse_weights) / means[:, None]
        fine_weights = abs(fine_weights) / means[:, None]
    errors = (error_sum / means[:, None] * signs[:, None] * 1e6) @ null
    coordinate = null.T @ coefficients
    coordinate /= (errors @ coordinate)[0]
    last = None
    cached = None

    def quantities(parameters):
        nonlocal last, cached
        if last is None or not np.array_equal(parameters, last):
            values = reduced_basis @ parameters[:dimension]
            l1 = l1_weights @ abs(values)
            l1_gradient = (l1_weights * np.sign(values)) @ reduced_basis
            if grading:
                coarse_values = coarse_basis @ parameters[:dimension]
                fine_values = fine_basis @ parameters[:dimension]
                coarse_l1 = coarse_weights @ abs(coarse_values)
                fine_l1 = fine_weights @ abs(fine_values)
                coarse_gradient = (coarse_weights * np.sign(coarse_values)) @ coarse_basis
                fine_gradient = (fine_weights * np.sign(fine_values)) @ fine_basis
                coarse_multiplier = np.where(coarse_l1 > fine_l1, 5, -4)
                fine_multiplier = 1 - coarse_multiplier
                l1 = coarse_multiplier * coarse_l1 + fine_multiplier * fine_l1
                l1_gradient = coarse_multiplier[:, None] * coarse_gradient + fine_multiplier[:, None] * fine_gradient
            true_errors = errors @ parameters[:dimension]
            ratios = true_errors / (10 * l1)
            gradients = (errors * l1[:, None] - true_errors[:, None] * l1_gradient) / (10 * l1[:, None]**2)
            last = parameters.copy()
            cached = l1, l1_gradient, true_errors, ratios, gradients
        return cached

    def objective(parameters):
        l1, l1_gradient, true_errors, ratios, gradients = quantities(parameters)
        return -(1 - mean_weight) * parameters[-1] - mean_weight * ratios.mean()

    def objective_gradient(parameters):
        l1, l1_gradient, true_errors, ratios, gradients = quantities(parameters)
        return np.r_[-mean_weight * gradients.mean(axis=0), -(1 - mean_weight)]

    def inequalities(parameters):
        l1, l1_gradient, true_errors, ratios, gradients = quantities(parameters)
        return ratios - parameters[-1]

    def inequality_gradient(parameters):
        l1, l1_gradient, true_errors, ratios, gradients = quantities(parameters)
        return np.c_[gradients, -np.ones(3)]

    initial = np.r_[coordinate, 0.0]
    initial[-1] = min(quantities(initial)[3])
    result = minimize(objective, initial, jac=objective_gradient, method='SLSQP',
                      bounds=[(None, None)] * dimension + [(minimum_floor, None)],
                      constraints=[dict(type='eq', fun=lambda parameters: errors[0] @ parameters[:dimension] - 1,
                                        jac=lambda parameters: np.r_[errors[0], 0]),
                                   dict(type='ineq', fun=inequalities, jac=inequality_gradient)],
                      options=dict(maxiter=500, ftol=1e-12))
    candidate = quantize(seed, null @ result.x[:dimension])
    ratios = quantities(result.x)[3]
    return min(ratios), float(ratios.mean()), candidate, result.success


def run():
    started = time.time()
    data = []
    for source in ('irls_candidates.json', 'beam_candidates.json'):
        data.extend(json.loads(Path(source).read_text())[:100])
    data.sort(key=lambda item: item[0], reverse=True)
    candidates = []
    seen = set()
    for potential, seed, masks, signs in data:
        key = seed['bin'], seed['tilt'], seed['curvature'], tuple(map(tuple, masks))
        if key in seen:
            continue
        seen.add(key)
        potential, average, candidate, success = polish(seed, masks, count=4096)
        candidates.append((potential, average, candidate, masks))
        print('polish', key, potential, average, success, time.time() - started, flush=True)
    candidates.sort(reverse=True, key=lambda item: item[0])
    Path('polish_candidates.json').write_text(json.dumps(candidates))
    best = 0
    for potential, average, candidate, masks in candidates[:40]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
        print('screen', candidate['bin'], candidate['tilt'], candidate['curvature'], masks, potential, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path('polish_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path('polish_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
