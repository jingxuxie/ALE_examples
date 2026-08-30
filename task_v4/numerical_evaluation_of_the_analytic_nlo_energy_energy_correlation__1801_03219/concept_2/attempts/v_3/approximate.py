import heapq
import itertools
import json
import time
from pathlib import Path

import numpy as np

from fractional import samples
from masks import direction
from optimize import BINS, cached_checks, measure, kernel
from problem import validate


def minimum_norm(witness, coefficients):
    coefficients = np.asarray(coefficients, dtype=float)
    coefficients *= np.sqrt(.02000001) / np.linalg.norm(coefficients)
    integers = np.rint(coefficients * 1e10).astype(np.int64)
    candidate = dict(witness, cosine=integers[:12].tolist(), sine=integers[12:].tolist())
    validate(candidate)
    return candidate


def run():
    started = time.time()
    selections = [leaves for count in range(1, 9) for leaves in itertools.combinations(range(8), count)]
    candidates = []
    serial = 0
    for bin_name in BINS:
        for tilt, curvature in itertools.product((-4, 0, 4), repeat=2):
            witness = dict(version=1, bin=bin_name, band_start=53, tilt=tilt, curvature=curvature)
            basis_matrix, l1_weights, means = samples(witness, 512)
            check_data = [cached_checks(witness, leaf) for leaf in range(8)]
            for leaves in selections:
                rows = []
                widths = []
                error_sum = np.zeros((3, 24))
                parents = set()
                budget = 1.3e-8 / len(leaves)
                for leaf in leaves:
                    constraint, errors = check_data[leaf]
                    error_sum += errors
                    rows.extend(constraint[:6])
                    variation = means * .08 / 8
                    widths.extend(budget ** (2 / 3) * variation ** (1 / 3) / 200)
                    widths.extend([budget] * 3)
                    if leaf // 2 not in parents:
                        rows.extend(constraint[6:])
                        widths.extend([2 * budget] * 3)
                        parents.add(leaf // 2)
                rows = np.array(rows) / np.array(widths)[:, None]
                left, singular, right = np.linalg.svd(rows, full_matrices=True)
                singular = np.r_[singular, np.zeros(max(0, 24 - len(singular)))]
                for threshold in (1, 3, 10, 30, 100):
                    null = right[singular < threshold].T
                    if null.shape[1] == 0:
                        continue
                    vectors = (error_sum / means[:, None] * np.array([1, 1, -1])[:, None]) @ null
                    coefficients = null @ direction(vectors)
                    norm = np.linalg.norm(coefficients)
                    if norm < 1e-20:
                        continue
                    coefficients *= np.sqrt(.02000001) / norm
                    residual = np.max(abs(rows @ coefficients))
                    if residual > 4 or abs(coefficients).sum() > 1:
                        continue
                    ratios = abs(error_sum @ coefficients) / means / (l1_weights @ abs(basis_matrix @ coefficients)) / 1e-5
                    potential = min(ratios)
                    rank_score = potential / max(1, residual)**.3
                    if len(candidates) < 500 or rank_score > candidates[0][0]:
                        candidate = minimum_norm(witness, coefficients)
                        item = (rank_score, serial, potential, candidate, [leaves] * 3, residual)
                        serial += 1
                        heapq.heappush(candidates, item)
                        if len(candidates) > 500:
                            heapq.heappop(candidates)
        print('bin', bin_name, candidates[0][0], max(item[0] for item in candidates), time.time() - started, flush=True)
        Path('approximate_checkpoint.json').write_text(json.dumps(sorted(candidates, reverse=True)))
    candidates.sort(reverse=True)
    Path('approximate_candidates.json').write_text(json.dumps(candidates))
    best = 0
    for rank_score, serial, potential, candidate, masks, residual in candidates[:100]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
        print('screen', candidate['bin'], candidate['tilt'], candidate['curvature'], masks, potential, residual, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path('approximate_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path('approximate_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
