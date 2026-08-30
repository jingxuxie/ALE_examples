import json
import time
from pathlib import Path

from polish import polish
from grade_screen import measure

started = time.time()
data = json.loads(Path('polish_candidates.json').read_text())[:35]
best = 0
best_worst = 0
candidates = []
for potential, average, seed, masks in data:
    for mean_weight, floor in ((1, .112), (.5, .105), (1, .108)):
        potential, average, candidate, success = polish(seed, masks, count=512, grading=True, mean_weight=mean_weight, minimum_floor=floor)
        if potential < floor - 1e-5:
            continue
        result = measure(candidate, trace=True)
        score = (result['worst'] + result['average']) / 2
        candidates.append((score, result['worst'], result['average'], candidate, masks))
        print(seed['bin'], seed['tilt'], seed['curvature'], masks, mean_weight, floor, result['worst'], result['average'], success, time.time() - started, flush=True)
        if score > best:
            best = score
            Path('pareto_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path('pareto_report.json').write_text(json.dumps(result, indent=2) + '\n')
        if result['worst'] > best_worst:
            best_worst = result['worst']
            Path('pareto_worst_witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path('pareto_worst_report.json').write_text(json.dumps(result, indent=2) + '\n')
Path('pareto_candidates.json').write_text(json.dumps(sorted(candidates, key=lambda item: item[0], reverse=True)))
print('done', best, best_worst, time.time() - started, flush=True)
