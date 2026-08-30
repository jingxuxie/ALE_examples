import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import null_space
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, eye, hstack, vstack

from optimize import BINS, COLOR, basis, response, cached_checks, kernel, measure, quantize

sample_cache = {}


def samples(witness, count=512):
    key = (witness['bin'], witness['band_start'], witness['tilt'], witness['curvature'], count)
    if key not in sample_cache:
        points = (np.arange(count) + 0.5) / count
        lower, upper = BINS[witness['bin']]
        envelope = abs(2 * (upper - lower) * kernel(lower + (upper - lower) * points) * COLOR * response(points, witness)[:, None])
        means = envelope.mean(axis=0)
        sample_cache[key] = basis(points, witness), envelope.T / (means[:, None] * count), means
    return sample_cache[key]


def solve(witness, masks, signs=(1, 1, -1), count=512):
    rows = []
    errors = []
    channels = []
    for channel, leaves in enumerate(masks):
        if not leaves:
            continue
        parents = set()
        error_sum = np.zeros(24)
        for leaf in leaves:
            constraint, error = cached_checks(witness, leaf)
            error_sum += error[channel]
            rows.extend([constraint[channel], constraint[channel + 3]])
            if leaf // 2 not in parents:
                rows.append(constraint[channel + 6])
                parents.add(leaf // 2)
        errors.append(error_sum)
        channels.append(channel)
    rows = np.array(rows)
    rows /= np.linalg.norm(rows, axis=1)[:, None]
    null = null_space(rows, rcond=1e-12)
    dimension = null.shape[1]
    if dimension == 0:
        return None
    basis_matrix, l1_weights, means = samples(witness, count)
    reduced_basis = csr_matrix(basis_matrix @ null)
    objective_errors = np.array(errors) / means[channels, None] * 1e6 * np.array(signs)[channels, None]
    reduced_errors = csr_matrix(objective_errors @ null)
    inequalities = vstack([
        hstack([reduced_basis, -eye(count), csr_matrix((count, 1))]),
        hstack([-reduced_basis, -eye(count), csr_matrix((count, 1))]),
        hstack([csr_matrix((len(channels), dimension)), csr_matrix(l1_weights[channels]), csr_matrix((len(channels), 1))]),
        hstack([-reduced_errors, csr_matrix((len(channels), count)), np.ones((len(channels), 1))]),
    ]).tocsr()
    bounds = np.r_[np.zeros(2 * count), np.ones(len(channels)), np.zeros(len(channels))]
    result = linprog(np.r_[np.zeros(dimension + count), -1], A_ub=inequalities, b_ub=bounds, method='highs',
                     bounds=[(None, None)] * dimension + [(0, None)] * count + [(None, None)],
                     options=dict(primal_feasibility_tolerance=1e-9, dual_feasibility_tolerance=1e-9))
    if not result.success:
        return None
    coefficients = null @ result.x[:dimension]
    try:
        candidate = quantize(witness, coefficients)
    except ValueError:
        return None
    return -result.fun / 10, candidate


def run():
    started = time.time()
    candidates = []
    mode = sys.argv[1] if len(sys.argv) > 1 else 'single'
    for bin_name in BINS:
        witness = dict(version=1, bin=bin_name, band_start=53, tilt=0, curvature=0)
        if mode == 'single':
            selections = [[leaves, (), ()] for count in range(1, 5) for leaves in itertools.combinations(range(8), count)]
        elif mode == 'same':
            selections = [[leaves] * 3 for count in range(1, 4) for leaves in itertools.combinations(range(8), count)]
        elif mode == 'different':
            selections = [[(leaf,) for leaf in leaves] for leaves in itertools.product(range(8), repeat=3)]
        for masks in selections:
            sign_options = [(1, 1, -1)] if mode != 'different' else [(1, second, third) for second in (-1, 1) for third in (-1, 1)]
            for signs in sign_options:
                result = solve(witness, masks, signs=signs, count=384)
                if result is not None:
                    potential, candidate = result
                    candidates.append((potential, candidate, masks))
        print('bin', bin_name, len(candidates), sorted([item[0] for item in candidates])[-5:], time.time() - started, flush=True)
    candidates.sort(key=lambda item: item[0], reverse=True)
    Path('fractional_' + mode + '_candidates.json').write_text(json.dumps(candidates))
    best = 0
    for potential, candidate, masks in candidates[:30]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
        print('screen', candidate['bin'], masks, potential, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path('fractional_' + mode + '_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path('fractional_' + mode + '_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
