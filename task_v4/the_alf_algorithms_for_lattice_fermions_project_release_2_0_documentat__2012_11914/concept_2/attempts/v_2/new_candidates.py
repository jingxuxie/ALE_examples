import json
import sys
import time
import numpy as np
from search import ROOT, evaluate, write_submission
from optimize import full
from refine import Objective
from validate import generate

label = sys.argv[1]
records = []
seen = set()
for filename in ['prunepopulation_99.json', 'structuredpopulation.json', 'riskpopulation_70.json', 'riskpopulation_80.json']:
    if not (ROOT / filename).exists():
        continue
    while True:
        try:
            population = json.loads((ROOT / filename).read_text())
            break
        except json.JSONDecodeError:
            time.sleep(.1)
    for index, (_, word, values) in enumerate(population[:20]):
        if tuple(word) in seen:
            continue
        seen.add(tuple(word))
        summary, _ = evaluate(*full(np.array(word), np.array(values)))
        name = label + '_' + filename.replace('.json', '') + '_' + str(index)
        write_submission(*full(np.array(word), np.array(values)), name=name + '.json')
        metric = summary['max'] + 2 * max(1.85 - summary['core'], 0)
        records.append((metric, word, values, name, summary))
        print('INITIAL', name, summary, flush=True)
records.sort()
objective = Objective()
synthetic = generate(120, seed=89011)
results = []
for index, (_, word, values, name, summary) in enumerate(records[:15]):
    print('REFINE', index, name, summary, flush=True)
    word, values = np.array(word), np.array(values)
    values = objective.optimize(word, values, seconds=120, penalty=-2, label=name + '_refined')
    summary, _ = evaluate(*full(word, values), verbose=True)
    validation, _ = evaluate(*full(word, values), instances=synthetic, verbose=True)
    results.append((validation['max'], validation['core'], name + '_refined.json', summary, validation))
    results.sort()
    (ROOT / (label + '_ranking.json')).write_text(json.dumps(results))
print('RANKING', results, flush=True)
