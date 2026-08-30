import itertools
import json
import time
from pathlib import Path

import numpy as np

from optimize import optimize, BINS, measure, kernel

started = time.time()
candidates = []
for bin_name in BINS:
    witness = dict(version=1, bin=bin_name, band_start=53, tilt=0, curvature=0)
    for leaves in itertools.product(range(8), repeat=3):
        result = optimize(witness, [(leaf,) for leaf in leaves])
        if result is None:
            continue
        candidate, predicted, residual = result
        potential = min(abs(predicted) / np.array([8, 1, 3]))
        candidates.append((potential, candidate, leaves, predicted.tolist(), residual))
    print('bin', bin_name, time.time() - started, flush=True)
candidates.sort(key=lambda item: item[0], reverse=True)
Path('different_candidates.json').write_text(json.dumps(candidates))
best = 0
for potential, candidate, leaves, predicted, residual in candidates[:100]:
    result = measure(candidate, trace=True, kernel=kernel)
    margin = result['worst_screen_margin']
    summary = [(details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for details in result['families'].values()]
    print('screen', candidate['bin'], leaves, potential, residual, margin, summary, flush=True)
    if margin > best:
        best = margin
        Path('different_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
        Path('different_report.json').write_text(json.dumps(result, indent=2) + '\n')
print('done', best, time.time() - started, flush=True)
