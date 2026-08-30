import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.linalg import null_space

from design import BINS, COLOR, FAMILIES, Kernel, basis, response, validate, checks, quantize, measure, kernel

check_cache = {}


def cached_checks(witness, leaf):
    key = (witness['bin'], witness['band_start'], witness['tilt'], witness['curvature'], leaf)
    if key not in check_cache:
        check_cache[key] = checks(witness, leaf)
    return check_cache[key]


def optimize(witness, masks, relaxed=True):
    rows = []
    widths = []
    errors = np.zeros((3, 24))
    for channel, leaves in enumerate(masks):
        parents = set()
        for leaf in leaves:
            constraint, error = cached_checks(witness, leaf)
            errors[channel] += error[channel]
            rows.extend([constraint[channel], constraint[channel + 3]])
            widths.extend([1e-8 / len(leaves), 2e-9 / len(leaves)])
            if leaf // 2 not in parents:
                rows.append(constraint[channel + 6])
                widths.append(4e-9 / len(leaves))
                parents.add(leaf // 2)
    rows = np.array(rows)
    widths = np.array(widths)
    scales = np.linalg.norm(rows, axis=1)
    rows /= scales[:, None]
    widths /= scales
    if not relaxed:
        widths *= 0
    objective = errors[0] / np.max(abs(errors[0]))
    stacked = np.concatenate((rows, -rows))
    inequalities = np.block([[stacked, -stacked], [np.ones((1, 24)), np.ones((1, 24))]])
    bounds = np.r_[widths, widths, 1]
    result = linprog(np.r_[-objective, objective], A_ub=inequalities, b_ub=bounds, bounds=(0, None), method='highs', options=dict(primal_feasibility_tolerance=1e-10, dual_feasibility_tolerance=1e-10))
    if not result.success:
        return None
    coefficients = result.x[:24] - result.x[24:]
    try:
        candidate = quantize(witness, coefficients)
    except ValueError:
        return None
    values = np.array(candidate['cosine'] + candidate['sine']) / 1e10
    return candidate, errors @ values, np.max(abs(rows @ values) - widths)


def run():
    started = time.time()
    candidates = []
    for bin_name in BINS:
        for band_start in (53, 52, 51, 49):
            witness = dict(version=1, bin=bin_name, band_start=band_start, tilt=0, curvature=0)
            selections = [(leaf,) for leaf in range(8)] + list(itertools.combinations(range(8), 2))
            for leaves in selections:
                result = optimize(witness, [leaves] * 3)
                if result is None:
                    continue
                candidate, predicted, residual = result
                candidates.append((min(abs(predicted)), candidate, leaves, predicted.tolist(), residual))
    candidates.sort(key=lambda item: item[0], reverse=True)
    Path('lp_candidates.json').write_text(json.dumps(candidates))
    print('optimized', len(candidates), time.time() - started, flush=True)
    best = 0
    for potential, candidate, leaves, predicted, residual in candidates[:60]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
        print('screen', candidate['bin'], candidate['band_start'], leaves, potential, residual, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path('lp_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path('lp_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
