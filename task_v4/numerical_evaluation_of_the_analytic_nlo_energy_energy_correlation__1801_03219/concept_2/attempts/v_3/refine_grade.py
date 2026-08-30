import json
import time
from pathlib import Path

from polish import polish
from grade_screen import measure

started = time.time()
candidates = json.loads(Path('polish_candidates.json').read_text())[:50]
best = 0
for potential, average, seed, masks in candidates:
    potential, average, candidate, success = polish(seed, masks, count=4096, grading=True)
    result = measure(candidate, trace=True)
    print(seed['bin'], seed['tilt'], seed['curvature'], masks, potential, result['worst'], result['average'], success, time.time() - started, flush=True)
    if result['worst'] > best:
        best = result['worst']
        Path('grade_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
        Path('grade_report.json').write_text(json.dumps(result, indent=2) + '\n')
print('done', best, time.time() - started, flush=True)
