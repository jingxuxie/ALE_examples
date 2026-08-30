import heapq
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import null_space

from fractional import samples, solve
from optimize import BINS, cached_checks, measure, kernel, quantize


def run():
    started = time.time()
    mode = sys.argv[1] if len(sys.argv) > 1 else 'same'
    selections = [leaves for count in range(1, 9 if mode == 'single' else 3) for leaves in itertools.combinations(range(8), count)]
    candidates = []
    serial = 0
    for bin_name in BINS:
        for band_start in (53, 52, 51, 49):
            for tilt, curvature in itertools.product(range(-4, 5), repeat=2):
                witness = dict(version=1, bin=bin_name, band_start=band_start, tilt=tilt, curvature=curvature)
                basis_matrix, l1_weights, means = samples(witness, 384)
                check_data = [cached_checks(witness, leaf) for leaf in range(8)]
                for leaves in selections:
                    rows = []
                    error_sum = np.zeros((3, 24))
                    parents = set()
                    for leaf in leaves:
                        constraint, errors = check_data[leaf]
                        error_sum += errors
                        if mode == 'single':
                            rows.extend([constraint[0], constraint[3]])
                        else:
                            rows.extend(constraint[:6])
                        if leaf // 2 not in parents:
                            rows.extend(constraint[6:7] if mode == 'single' else constraint[6:])
                            parents.add(leaf // 2)
                    rows = np.array(rows)
                    rows /= np.linalg.norm(rows, axis=1)[:, None]
                    null = null_space(rows, rcond=1e-12)
                    if null.shape[1] == 0:
                        continue
                    coefficients = null @ (null.T @ error_sum[0])
                    norm = abs(coefficients).sum()
                    if norm < 1e-20:
                        continue
                    coefficients /= norm
                    true_errors = abs(error_sum @ coefficients) / means
                    l1 = l1_weights @ abs(basis_matrix @ coefficients)
                    ratios = true_errors / l1 / 1e-5
                    potential = ratios[0] if mode == 'single' else min(ratios)
                    if len(candidates) < 400 or potential > candidates[0][0]:
                        try:
                            candidate = quantize(witness, coefficients)
                        except ValueError:
                            continue
                        masks = [leaves, (), ()] if mode == 'single' else [leaves] * 3
                        item = (potential, serial, candidate, masks)
                        serial += 1
                        heapq.heappush(candidates, item)
                        if len(candidates) > 400:
                            heapq.heappop(candidates)
            print('band', bin_name, band_start, candidates[0][0], max(item[0] for item in candidates), time.time() - started, flush=True)
            Path('response_' + mode + '_checkpoint.json').write_text(json.dumps(sorted(candidates, reverse=True)))
    candidates.sort(reverse=True)
    polished = []
    for potential, serial, candidate, masks in candidates[:100]:
        result = solve(candidate, masks, count=768)
        if result is not None:
            potential, candidate = result
            polished.append((potential, candidate, masks))
    polished.sort(key=lambda item: item[0], reverse=True)
    Path('response_' + mode + '_candidates.json').write_text(json.dumps(polished))
    best = 0
    for potential, candidate, masks in polished[:30]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
        print('screen', candidate['bin'], candidate['band_start'], candidate['tilt'], candidate['curvature'], masks, potential, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path('response_' + mode + '_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path('response_' + mode + '_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
