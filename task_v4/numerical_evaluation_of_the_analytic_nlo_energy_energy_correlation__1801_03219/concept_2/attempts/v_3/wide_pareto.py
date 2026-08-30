import itertools
import json
import os
import time
from pathlib import Path

from polish import polish
from grade_screen import measure

started = time.time()
prefix = os.environ.get('WIDE_PREFIX', 'wide_pareto')
floor = float(os.environ.get('WIDE_FLOOR', '.10'))
data = json.loads(Path('global_checkpoint.json').read_text())
data.extend(json.loads(Path('masks_checkpoint.json').read_text()))
data.sort(reverse=True, key=lambda item: item[0])
seen = set()
selected = []
for potential, serial, seed, masks, signs in data:
    key = seed['bin'], tuple(map(tuple, masks))
    if key in seen:
        continue
    seen.add(key)
    selected.append((seed, masks))
    if len(selected) == 200:
        break
best = 0
candidates = []


def attempt(seed, masks):
    global best
    potential, average, candidate, success = polish(seed, masks, count=512, grading=True, mean_weight=.5, minimum_floor=floor)
    if potential < floor - 1e-5:
        return
    score = (potential + average) / 2
    candidates.append((score, candidate, masks))
    if score < best - 1e-5:
        return
    result = measure(candidate, trace=True)
    actual_score = (result['worst'] + result['average']) / 2
    valid_claims = all(family['error'] >= max(20 * family['target']['tolerance'], 50 * family['target']['estimated_error']) for family in result['families'].values())
    print('candidate', seed['bin'], seed['tilt'], seed['curvature'], masks, result['worst'], result['average'], valid_claims, success, time.time() - started, flush=True)
    if actual_score > best and valid_claims:
        best = actual_score
        Path(prefix + '_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
        Path(prefix + '_report.json').write_text(json.dumps(result, indent=2) + '\n')


for seed, masks in selected:
    attempt(seed, masks)
candidates.sort(reverse=True, key=lambda item: item[0])
seen = set()
patterns = []
for score, seed, masks in candidates:
    key = seed['bin'], tuple(map(tuple, masks))
    if key in seen:
        continue
    seen.add(key)
    patterns.append((seed, masks))
    if len(patterns) == 10:
        break
for seed, masks in patterns:
    for tilt, curvature in itertools.product((-4, 0, 4), repeat=2):
        attempt(dict(seed, tilt=tilt, curvature=curvature), masks)
candidates.sort(reverse=True, key=lambda item: item[0])
Path(prefix + '_candidates.json').write_text(json.dumps(candidates))
print('done', best, time.time() - started, flush=True)
