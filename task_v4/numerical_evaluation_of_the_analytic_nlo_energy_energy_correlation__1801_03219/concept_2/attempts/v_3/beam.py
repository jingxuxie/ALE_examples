import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import null_space

from fractional import samples
from masks import direction
from optimize import BINS, cached_checks, quantize, measure, kernel
from irls import solve


def neighbors(masks):
    for channel in range(3):
        original = set(masks[channel])
        possibilities = []
        if len(original) < 4:
            possibilities.extend(original | {leaf} for leaf in range(8) if leaf not in original)
        if len(original) > 1:
            possibilities.extend(original - {leaf} for leaf in original)
        possibilities.extend((original - {old}) | {new} for old in original for new in range(8) if new not in original)
        for leaves in possibilities:
            candidate = list(masks)
            candidate[channel] = tuple(sorted(leaves))
            yield tuple(candidate)


def run():
    started = time.time()
    data = json.loads(Path('masks_checkpoint.json').read_text())
    all_candidates = []
    for bin_name in ('backward', 'central', 'collinear'):
        for tilt, curvature in ((4, -4), (-4, 4), (0, 0)):
            witness = dict(version=1, bin=bin_name, band_start=53, tilt=tilt, curvature=curvature)
            basis_matrix, l1_weights, means = samples(witness, 512)
            cache = {}
            seeds = list(dict.fromkeys(tuple(map(tuple, item[3])) for item in data if item[2]['bin'] == bin_name))[:100]
            scores = []
            checked = set()
            for generation in range(3):
                patterns = set(seeds)
                for masks in seeds:
                    patterns.update(neighbors(masks))
                for masks in patterns - checked:
                    checked.add(masks)
                    rows = []
                    errors = []
                    for channel, leaves in enumerate(masks):
                        key = channel, leaves
                        if key not in cache:
                            part_rows = []
                            error_sum = np.zeros(24)
                            parents = set()
                            for leaf in leaves:
                                constraint, error = cached_checks(witness, leaf)
                                error_sum += error[channel]
                                part_rows.extend([constraint[channel], constraint[channel + 3]])
                                if leaf // 2 not in parents:
                                    part_rows.append(constraint[channel + 6])
                                    parents.add(leaf // 2)
                            part_rows = np.array(part_rows)
                            part_rows /= np.linalg.norm(part_rows, axis=1)[:, None]
                            cache[key] = part_rows, error_sum / means[channel]
                        part_rows, error_sum = cache[key]
                        rows.extend(part_rows)
                        errors.append(error_sum)
                    null = null_space(np.array(rows), rcond=1e-12)
                    if null.shape[1] == 0:
                        continue
                    errors = np.array(errors)
                    vectors = errors @ null
                    best = None
                    for signs in ((1, 1, -1), (1, 1, 1), (1, -1, -1), (1, -1, 1)):
                        coefficients = null @ direction(vectors * np.array(signs)[:, None])
                        norm = abs(coefficients).sum()
                        if norm < 1e-20:
                            continue
                        coefficients /= norm
                        ratios = abs(errors @ coefficients) / (l1_weights @ abs(basis_matrix @ coefficients)) / 1e-5
                        potential = min(ratios)
                        if best is None or potential > best[0]:
                            best = potential, masks, signs
                    if best is not None:
                        scores.append(best)
                scores.sort(reverse=True)
                seeds = [item[1] for item in scores[:120]]
                print('generation', bin_name, tilt, curvature, generation, len(checked), scores[0], time.time() - started, flush=True)
            for potential, masks, signs in scores[:100]:
                result = solve(witness, masks, signs=signs, iterations=35)
                if result is not None:
                    potential, candidate = result
                    all_candidates.append((potential, candidate, masks, signs))
            all_candidates.sort(key=lambda item: item[0], reverse=True)
            Path('beam_checkpoint.json').write_text(json.dumps(all_candidates[:500]))
    Path('beam_candidates.json').write_text(json.dumps(all_candidates[:500]))
    best = 0
    for potential, candidate, masks, signs in all_candidates[:50]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
        print('screen', candidate['bin'], candidate['tilt'], candidate['curvature'], masks, potential, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path('beam_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path('beam_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
