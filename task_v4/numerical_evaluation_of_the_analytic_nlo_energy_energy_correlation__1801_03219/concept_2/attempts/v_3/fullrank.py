import heapq
import itertools
import json
import os
import time
from pathlib import Path

import numpy as np

from approximate import minimum_norm
from fractional import samples
from masks import direction
from optimize import cached_checks, measure, kernel


def run():
    started = time.time()
    prefix = os.environ.get('FULL_PREFIX', 'fullrank')
    tilt = int(os.environ.get('FULL_TILT', '4'))
    curvature = int(os.environ.get('FULL_CURVATURE', '-4'))
    selections = [leaves for count in range(1, 4) for leaves in itertools.combinations(range(8), count)]
    candidates = []
    serial = 0
    for bin_name in ('backward', 'central', 'collinear'):
        witness = dict(version=1, bin=bin_name, band_start=53, tilt=tilt, curvature=curvature)
        basis_matrix, l1_weights, means = samples(witness, 512)
        per_channel = []
        for channel in range(3):
            parts = []
            for leaves in selections:
                rows = []
                widths = []
                error_sum = np.zeros(24)
                parents = set()
                budget = 1.3e-8 / len(leaves)
                variation = means[channel] * .08 / 8
                for leaf in leaves:
                    constraint, error = cached_checks(witness, leaf)
                    error_sum += error[channel]
                    rows.extend([constraint[channel], constraint[channel + 3]])
                    widths.extend([budget ** (2 / 3) * variation ** (1 / 3) / 200, budget])
                    if leaf // 2 not in parents:
                        rows.append(constraint[channel + 6])
                        widths.append(2 * budget)
                        parents.add(leaf // 2)
                parts.append((np.array(rows) / np.array(widths)[:, None], error_sum, leaves))
            per_channel.append(parts)
        processed = 0
        qualified = 0
        for parts in itertools.product(*per_channel):
            if sum(len(part[0]) for part in parts) < 24:
                continue
            processed += 1
            rows = np.concatenate([part[0] for part in parts])
            left, singular, right = np.linalg.svd(rows, full_matrices=False)
            if singular[-1] > 150:
                continue
            qualified += 1
            error_sum = np.array([part[1] for part in parts])
            for threshold in (3, 10, 30, 100):
                null = right[singular < threshold].T
                if null.shape[1] == 0:
                    continue
                vectors = error_sum / means[:, None] @ null
                if null.shape[1] == 1:
                    coefficients = null[:, 0].copy()
                else:
                    projected = null @ vectors[0]
                    signs = np.sign(error_sum @ projected)
                    coefficients = null @ direction(vectors * signs[:, None])
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
                if len(candidates) < 400 or rank_score > candidates[0][0]:
                    candidate = minimum_norm(witness, coefficients)
                    item = (rank_score, serial, potential, candidate, [part[2] for part in parts], residual)
                    serial += 1
                    heapq.heappush(candidates, item)
                    if len(candidates) > 400:
                        heapq.heappop(candidates)
        print('bin', bin_name, processed, qualified, max([item[0] for item in candidates], default=0), time.time() - started, flush=True)
        Path(prefix + '_checkpoint.json').write_text(json.dumps(sorted(candidates, reverse=True)))
    candidates.sort(reverse=True)
    best = 0
    for rank_score, serial, potential, candidate, masks, residual in candidates[:100]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
        print('screen', candidate['bin'], masks, potential, residual, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path(prefix + '_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path(prefix + '_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
