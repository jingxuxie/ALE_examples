import heapq
import itertools
import json
import os
import time
from pathlib import Path

import numpy as np
from scipy.linalg import null_space

from fractional import samples, solve
from optimize import BINS, cached_checks, measure, kernel, quantize


def direction(vectors):
    gram = vectors @ vectors.T
    best = float('inf')
    weights = None
    for channel in range(3):
        if gram[channel, channel] < best:
            best = gram[channel, channel]
            weights = np.eye(3)[channel]
    for first, second in ((0, 1), (0, 2), (1, 2)):
        denominator = gram[first, first] + gram[second, second] - 2 * gram[first, second]
        if denominator <= 0:
            continue
        fraction = np.clip((gram[second, second] - gram[first, second]) / denominator, 0, 1)
        candidate = np.zeros(3)
        candidate[first] = fraction
        candidate[second] = 1 - fraction
        value = candidate @ gram @ candidate
        if value < best:
            best, weights = value, candidate
    try:
        candidate = np.linalg.solve(gram, np.ones(3))
        candidate /= candidate.sum()
        if np.min(candidate) >= 0:
            value = candidate @ gram @ candidate
            if value < best:
                best, weights = value, candidate
    except np.linalg.LinAlgError:
        pass
    return weights @ vectors


def run():
    from irls import solve as fast_solve
    started = time.time()
    band_start = int(os.environ.get('MASK_BAND', '53'))
    tilt = int(os.environ.get('MASK_TILT', '0'))
    curvature = int(os.environ.get('MASK_CURVATURE', '0'))
    prefix = os.environ.get('MASK_PREFIX', 'masks')
    deep = os.environ.get('MASK_DEEP') == '1'
    selections = [(leaf,) for leaf in range(8)] + list(itertools.combinations(range(8), 2))
    candidates = []
    serial = 0
    for bin_name in BINS:
        witness = dict(version=1, bin=bin_name, band_start=band_start, tilt=tilt, curvature=curvature)
        basis_matrix, l1_weights, means = samples(witness, 384)
        per_channel = []
        for channel in range(3):
            choices = []
            for leaves in selections:
                rows = []
                errors = np.zeros(24)
                parents = set()
                for leaf in leaves:
                    constraint, error = cached_checks(witness, leaf)
                    errors += error[channel]
                    rows.extend([constraint[channel], constraint[channel + 3]])
                    if leaf // 2 not in parents:
                        rows.append(constraint[channel + 6])
                        parents.add(leaf // 2)
                rows = np.array(rows)
                rows /= np.linalg.norm(rows, axis=1)[:, None]
                choices.append((rows, errors / means[channel], leaves))
            per_channel.append(choices)
        for choices in itertools.product(*per_channel):
            rows = np.concatenate([choice[0] for choice in choices])
            errors = np.array([choice[1] for choice in choices])
            null = null_space(rows, rcond=1e-12)
            if null.shape[1] == 0:
                continue
            vectors = errors @ null
            for signs in ((1, 1, -1), (1, 1, 1), (1, -1, -1), (1, -1, 1)):
                if deep and signs != (1, 1, -1):
                    continue
                coefficients = null @ direction(vectors * np.array(signs)[:, None])
                norm = np.abs(coefficients).sum()
                if norm < 1e-20:
                    continue
                coefficients /= norm
                true_errors = abs(errors @ coefficients)
                l1 = l1_weights @ abs(basis_matrix @ coefficients)
                potential = min(true_errors / l1) / 1e-5
                refined_candidate = None
                if deep:
                    if potential < .025:
                        continue
                    masks = [choice[2] for choice in choices]
                    refinement = fast_solve(witness, masks, signs=signs, count=512, iterations=12)
                    if refinement is None:
                        continue
                    potential, refined_candidate = refinement
                if len(candidates) < 600 or potential > candidates[0][0]:
                    try:
                        candidate = refined_candidate or quantize(witness, coefficients)
                    except ValueError:
                        continue
                    masks = [choice[2] for choice in choices]
                    item = (potential, serial, candidate, masks, signs)
                    serial += 1
                    heapq.heappush(candidates, item)
                    if len(candidates) > 600:
                        heapq.heappop(candidates)
        print('bin', bin_name, candidates[0][0], max(item[0] for item in candidates), time.time() - started, flush=True)
        Path(prefix + '_checkpoint.json').write_text(json.dumps(sorted(candidates, reverse=True)))
    candidates.sort(reverse=True)
    polished = []
    for potential, serial, candidate, masks, signs in candidates[:200]:
        result = fast_solve(candidate, masks, signs=signs, count=768)
        if result is not None:
            potential, candidate = result
            polished.append((potential, candidate, masks, signs))
    polished.sort(key=lambda item: item[0], reverse=True)
    Path(prefix + '_candidates.json').write_text(json.dumps(polished))
    best = 0
    for potential, candidate, masks, signs in polished[:50]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
        print('screen', candidate['bin'], masks, potential, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path(prefix + '_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path(prefix + '_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
