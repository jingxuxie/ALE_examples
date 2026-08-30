import json
import time
import numpy as np
from search import ROOT, evaluate, write_submission
from optimize import full

results = []
seen = set()
for filename in ['population_10.json', 'population_20.json', 'riskpopulation_30.json']:
    if not (ROOT / filename).exists():
        continue
    while True:
        try:
            records = json.loads((ROOT / filename).read_text())
            break
        except json.JSONDecodeError:
            time.sleep(.1)
    for index, (_, word, values) in enumerate(records):
        if tuple(word) in seen:
            continue
        seen.add(tuple(word))
        summary, _ = evaluate(*full(np.array(word), np.array(values)))
        name = filename.replace('.json', '') + '_' + str(index) + '.json'
        write_submission(*full(np.array(word), np.array(values)), name=name)
        results.append((summary['max'], summary['core'], name, summary))
        print(name, summary, flush=True)
results.sort()
print('RANKING', flush=True)
for record in results[:15]:
    print(record, flush=True)
(ROOT / 'candidate_ranking.json').write_text(json.dumps(results))
