import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import null_space

from fractional import samples
from masks import direction
from optimize import cached_checks, quantize, measure, kernel, BINS


def solve(witness, masks, signs=(1, 1, -1), count=768, iterations=35):
    rows = []
    errors = []
    for channel, leaves in enumerate(masks):
        error_sum = np.zeros(24)
        parents = set()
        for leaf in leaves:
            constraint, error = cached_checks(witness, leaf)
            error_sum += error[channel]
            rows.extend([constraint[channel], constraint[channel + 3]])
            if leaf // 2 not in parents:
                rows.append(constraint[channel + 6])
                parents.add(leaf // 2)
        errors.append(error_sum)
    rows = np.array(rows)
    rows /= np.linalg.norm(rows, axis=1)[:, None]
    null = null_space(rows, rcond=1e-12)
    dimension = null.shape[1]
    if dimension == 0:
        return None
    basis_matrix, l1_weights, means = samples(witness, count)
    reduced_basis = basis_matrix @ null
    errors = np.array(errors) / means[:, None] * 1e6 * np.array(signs)[:, None]
    vectors = errors @ null
    coordinate = direction(vectors)
    best = 0
    best_coefficients = None
    envelope = l1_weights.mean(axis=0)
    for iteration in range(iterations):
        minimum_error = np.min(vectors @ coordinate)
        if minimum_error < 1e-20:
            break
        coordinate /= minimum_error
        values = reduced_basis @ coordinate
        ratios = vectors @ coordinate / (l1_weights @ abs(values)) / 10
        potential = min(ratios)
        if potential > best:
            best = potential
            best_coefficients = null @ coordinate
        smoothing = np.sqrt(np.mean(values**2)) * max(1e-6, .05 * .7**iteration)
        weights = envelope / np.sqrt(values**2 + smoothing**2)
        hessian = reduced_basis.T @ (weights[:, None] * reduced_basis)
        hessian += np.eye(dimension) * np.trace(hessian) * 1e-14
        cholesky = np.linalg.cholesky(hessian)
        whitened = np.linalg.solve(cholesky, vectors.T).T
        coordinate = np.linalg.solve(cholesky.T, direction(whitened))
    if best_coefficients is None:
        return None
    try:
        candidate = quantize(witness, best_coefficients)
    except ValueError:
        return None
    return best, candidate


def run():
    started = time.time()
    data = json.loads(Path('masks_checkpoint.json').read_text())
    patterns = {}
    for potential, serial, candidate, masks, signs in data:
        key = (candidate['bin'], tuple(map(tuple, masks)), tuple(signs))
        if key not in patterns:
            patterns[key] = (candidate, masks, signs)
    selected = []
    for bin_name in BINS:
        selected.extend([item for key, item in patterns.items() if key[0] == bin_name][:20])
    candidates = []
    for pattern_index, (seed, masks, signs) in enumerate(selected):
        for band_start in (53, 52):
            for tilt, curvature in itertools.product(range(-4, 5), repeat=2):
                witness = dict(seed, band_start=band_start, tilt=tilt, curvature=curvature)
                result = solve(witness, masks, signs=signs, count=512, iterations=25)
                if result is not None:
                    potential, candidate = result
                    candidates.append((potential, candidate, masks, signs))
        print('pattern', pattern_index, seed['bin'], masks, max(item[0] for item in candidates), time.time() - started, flush=True)
        Path('irls_checkpoint.json').write_text(json.dumps(sorted(candidates, key=lambda item: item[0], reverse=True)[:500]))
    candidates.sort(key=lambda item: item[0], reverse=True)
    Path('irls_candidates.json').write_text(json.dumps(candidates[:500]))
    best = 0
    for potential, candidate, masks, signs in candidates[:50]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
        print('screen', candidate['bin'], candidate['band_start'], candidate['tilt'], candidate['curvature'], masks, potential, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path('irls_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path('irls_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
