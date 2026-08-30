import heapq
import itertools
import json
import time
from pathlib import Path

import numpy as np

from approximate import minimum_norm
from fractional import samples
from masks import direction
from optimize import BINS, cached_checks, measure, kernel


def run():
    started = time.time()
    candidates = []
    serial = 0
    for bin_name in BINS:
        smallest = float('inf')
        for tilt, curvature in itertools.product(range(-4, 5), repeat=2):
            witness = dict(version=1, bin=bin_name, band_start=53, tilt=tilt, curvature=curvature)
            basis_matrix, l1_weights, means = samples(witness, 512)
            for parents in itertools.combinations(range(4), 2):
                leaves = tuple(leaf for parent in parents for leaf in (2 * parent, 2 * parent + 1))
                choices = list(itertools.combinations(leaves, 3)) + [leaves]
                per_channel = []
                for channel in range(3):
                    parts = []
                    for selection in choices:
                        rows = []
                        widths = []
                        error_sum = np.zeros(24)
                        seen_parents = set()
                        budget = 1.3e-8 / len(selection)
                        variation = means[channel] * .08 / 8
                        for leaf in selection:
                            constraint, errors = cached_checks(witness, leaf)
                            error_sum += errors[channel]
                            rows.extend([constraint[channel], constraint[channel + 3]])
                            widths.extend([budget ** (2 / 3) * variation ** (1 / 3) / 200, budget])
                            if leaf // 2 not in seen_parents:
                                rows.append(constraint[channel + 6])
                                widths.append(2 * budget)
                                seen_parents.add(leaf // 2)
                        parts.append((np.array(rows) / np.array(widths)[:, None], error_sum, selection))
                    per_channel.append(parts)
                for parts in itertools.product(*per_channel):
                    rows = np.concatenate([part[0] for part in parts])
                    error_sum = np.array([part[1] for part in parts])
                    left, singular, right = np.linalg.svd(rows, full_matrices=False)
                    smallest = min(smallest, singular[-1])
                    if singular[-1] > 150:
                        continue
                    for threshold in (3, 10, 30, 100, 300):
                        null = right[singular < threshold].T
                        if null.shape[1] == 0:
                            continue
                        vectors = error_sum / means[:, None] @ null
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
                        if len(candidates) < 300 or rank_score > candidates[0][0]:
                            candidate = minimum_norm(witness, coefficients)
                            item = (rank_score, serial, potential, candidate, [part[2] for part in parts], residual)
                            serial += 1
                            heapq.heappush(candidates, item)
                            if len(candidates) > 300:
                                heapq.heappop(candidates)
        print('bin', bin_name, smallest, len(candidates), max([item[0] for item in candidates], default=0), time.time() - started, flush=True)
        Path('triples_checkpoint.json').write_text(json.dumps(sorted(candidates, reverse=True)))
    candidates.sort(reverse=True)
    best = 0
    for rank_score, serial, potential, candidate, masks, residual in candidates[:100]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
        print('screen', candidate['bin'], candidate['tilt'], candidate['curvature'], masks, potential, residual, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path('triples_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path('triples_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
