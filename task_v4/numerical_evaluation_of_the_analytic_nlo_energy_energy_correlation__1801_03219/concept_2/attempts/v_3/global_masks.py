import heapq
import itertools
import json
import os
import time
from pathlib import Path

import numpy as np
from scipy.linalg import null_space

from fractional import samples
from masks import direction
from optimize import cached_checks, quantize, measure, kernel
from irls import solve


def run():
    started = time.time()
    prefix = os.environ.get('GLOBAL_PREFIX', 'global')
    tilt = int(os.environ.get('GLOBAL_TILT', '4'))
    curvature = int(os.environ.get('GLOBAL_CURVATURE', '-4'))
    bins = os.environ.get('GLOBAL_BINS', 'backward,central,collinear').split(',')
    selections = [leaves for count in range(1, 7) for leaves in itertools.combinations(range(8), count)]
    selections.sort(key=lambda leaves: 2 * len(leaves) + len(set(leaf // 2 for leaf in leaves)))
    candidates = []
    serial = 0
    for bin_name in bins:
        witness = dict(version=1, bin=bin_name, band_start=53, tilt=tilt, curvature=curvature)
        basis_matrix, l1_weights, means = samples(witness, 512)
        per_channel = []
        for channel in range(3):
            parts = []
            for leaves in selections:
                rows = []
                error_sum = np.zeros(24)
                parents = set()
                for leaf in leaves:
                    constraint, error = cached_checks(witness, leaf)
                    error_sum += error[channel]
                    rows.extend([constraint[channel], constraint[channel + 3]])
                    if leaf // 2 not in parents:
                        rows.append(constraint[channel + 6])
                        parents.add(leaf // 2)
                rows = np.array(rows)
                rows /= np.linalg.norm(rows, axis=1)[:, None]
                parts.append((rows, error_sum / means[channel], leaves))
            per_channel.append(parts)
        processed = 0
        for first, second in itertools.product(per_channel[0], per_channel[1]):
            fixed_rows = len(first[0]) + len(second[0])
            if fixed_rows + 3 >= 24:
                continue
            for third in per_channel[2]:
                if fixed_rows + len(third[0]) >= 24:
                    break
                processed += 1
                parts = first, second, third
                null = null_space(np.concatenate([part[0] for part in parts]), rcond=1e-12)
                if null.shape[1] == 0:
                    continue
                errors = np.array([part[1] for part in parts])
                vectors = errors @ null
                if null.shape[1] == 1:
                    coefficients = null[:, 0].copy()
                else:
                    coefficients = null @ direction(vectors * np.array([1, 1, -1])[:, None])
                norm = abs(coefficients).sum()
                if norm < 1e-20:
                    continue
                coefficients /= norm
                true_errors = errors @ coefficients
                l1 = l1_weights @ abs(basis_matrix @ coefficients)
                potential = min(abs(true_errors) / l1) / 1e-5
                if len(candidates) < 1200 or potential > candidates[0][0]:
                    try:
                        candidate = quantize(witness, coefficients)
                    except ValueError:
                        continue
                    signs = np.sign(true_errors).astype(int).tolist()
                    item = (potential, serial, candidate, [part[2] for part in parts], signs)
                    serial += 1
                    heapq.heappush(candidates, item)
                    if len(candidates) > 1200:
                        heapq.heappop(candidates)
        print('bin', bin_name, processed, candidates[0][0], max(item[0] for item in candidates), time.time() - started, flush=True)
        Path(prefix + '_checkpoint.json').write_text(json.dumps(sorted(candidates, reverse=True)))
    polished = []
    for potential, serial, candidate, masks, signs in sorted(candidates, reverse=True):
        result = solve(candidate, masks, signs=signs, count=1024, iterations=35)
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
