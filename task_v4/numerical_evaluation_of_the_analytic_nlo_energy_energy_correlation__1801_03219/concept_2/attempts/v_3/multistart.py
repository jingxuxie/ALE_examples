import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import null_space

from optimize import cached_checks, quantize
from polish import polish
from grade_screen import measure

started = time.time()
seed = json.loads(Path('pareto_witness.json').read_text())
masks = [[1, 4], [4, 7], [1, 7]]
rows = []
for channel, leaves in enumerate(masks):
    for leaf in leaves:
        constraints, errors = cached_checks(seed, leaf)
        rows.extend([constraints[channel], constraints[channel + 3], constraints[channel + 6]])
rows = np.array(rows)
rows /= np.linalg.norm(rows, axis=1)[:, None]
null = null_space(rows, rcond=1e-12)
coefficients = np.array(seed['cosine'] + seed['sine']) / 1e10
generator = np.random.default_rng(180103219)
best = 0
best_worst = 0
for trial in range(160):
    amplitude = (.001, .003, .01, .03, .1, .3, 1, 3)[trial % 8]
    delta = null @ generator.normal(size=null.shape[1])
    delta *= amplitude * np.linalg.norm(coefficients) / np.linalg.norm(delta)
    candidate = quantize(seed, coefficients + delta)
    mean_weight = 0 if trial % 3 == 0 else .5
    potential, average, candidate, success = polish(candidate, masks, count=512, grading=True,
                                                  mean_weight=mean_weight, minimum_floor=.10)
    if potential < .10 or (potential + average) / 2 < best - 1e-6 and potential < best_worst - 1e-6:
        continue
    result = measure(candidate, trace=True)
    score = (result['worst'] + result['average']) / 2
    print('trial', trial, amplitude, mean_weight, result['worst'], result['average'], success, time.time() - started, flush=True)
    if score > best:
        best = score
        Path('multistart_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
        Path('multistart_report.json').write_text(json.dumps(result, indent=2) + '\n')
    if result['worst'] > best_worst:
        best_worst = result['worst']
        Path('multistart_worst_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
        Path('multistart_worst_report.json').write_text(json.dumps(result, indent=2) + '\n')
print('done', best, best_worst, time.time() - started, flush=True)
