import itertools
import json
import os
import time
from pathlib import Path

from irls import solve
from polish import polish
from grade_screen import measure

started = time.time()
prefix = os.environ.get('NOVEL_PREFIX', 'novel')
bin_name = os.environ.get('NOVEL_BIN')
while True:
    try:
        data = json.loads(Path('global_checkpoint.json').read_text())
        if bin_name is None or any(item[2]['bin'] == bin_name for item in data):
            break
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    time.sleep(5)
selected = []
seen = set()
for potential, serial, seed, masks, signs in data:
    if bin_name is not None and seed['bin'] != bin_name:
        continue
    if max(map(len, masks)) <= 2:
        continue
    key = seed['bin'], tuple(map(tuple, masks)), tuple(signs)
    if key in seen:
        continue
    selected.append((seed, masks, signs))
    seen.add(key)
    if len(selected) == 40:
        break
candidates = []
for pattern, (seed, masks, signs) in enumerate(selected):
    for tilt, curvature in itertools.product(range(-4, 5), repeat=2):
        witness = dict(seed, tilt=tilt, curvature=curvature)
        result = solve(witness, masks, signs=signs, count=768, iterations=30)
        if result is not None:
            potential, candidate = result
            candidates.append((potential, candidate, masks))
    print('pattern', pattern, masks, max(item[0] for item in candidates), time.time() - started, flush=True)
candidates.sort(key=lambda item: item[0], reverse=True)
Path(prefix + '_candidates.json').write_text(json.dumps(candidates[:500]))
best = 0
for potential, seed, masks in candidates[:50]:
    potential, average, candidate, success = polish(seed, masks, grading=True, count=512)
    result = measure(candidate, trace=True)
    print('screen', seed['bin'], seed['tilt'], seed['curvature'], masks, result['worst'], result['average'], flush=True)
    if result['worst'] > best:
        best = result['worst']
        Path(prefix + '_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
        Path(prefix + '_report.json').write_text(json.dumps(result, indent=2) + '\n')
print('done', best, time.time() - started, flush=True)
