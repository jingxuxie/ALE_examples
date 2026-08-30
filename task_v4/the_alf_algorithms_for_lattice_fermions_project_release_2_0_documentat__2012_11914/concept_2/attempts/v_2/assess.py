import json
import subprocess
import sys
import time
import numpy as np
from search import ROOT, NAMES, evaluate, write_submission
from optimize import full
from refine import Objective
from validate import generate

def read_json(filename):
    while True:
        try:
            return json.loads((ROOT / filename).read_text())
        except json.JSONDecodeError:
            time.sleep(.1)

filenames = ['prob_guarded_candidate_4_max.json', 'prob_guarded_candidate_6_max.json', 'guarded_candidate_4_max.json', 'guarded_candidate_6_max.json']
if (ROOT / 'new_ranking.json').exists():
    filenames.extend(record[2] for record in read_json('new_ranking.json')[:5])
raw = []
for filename in ['prunepopulation_100.json', 'structuredpopulation.json', 'population_90.json', 'population_91.json']:
    if (ROOT / filename).exists():
        for index, (_, word, values) in enumerate(read_json(filename)[:8]):
            name = 'final_' + filename.replace('.json', '') + '_' + str(index)
            raw.append((name, np.array(word), np.array(values)))
objective = Objective()
seen = set()
for name, word, values in raw:
    if tuple(word) in seen:
        continue
    seen.add(tuple(word))
    summary, _ = evaluate(*full(word, values))
    print('RAW', name, summary, flush=True)
    if summary['core'] < 1.60 or summary['max'] > 1.30:
        continue
    write_submission(*full(word, values), name=name + '.json')
    filenames.append(name + '.json')
    values = objective.optimize(word, values, seconds=60, penalty=-2, label=name + '_refined')
    filenames.append(name + '_refined.json')
synthetic = generate(120, seed=781624)
results = []
for filename in filenames:
    if not (ROOT / filename).exists():
        continue
    artifact = read_json(filename)
    word = np.array([NAMES.index(stage['component']) for stage in artifact['stages']])
    values = np.array([stage['coefficient'] for stage in artifact['stages']])
    training, _ = evaluate(word, values)
    if training['core'] < 1.8 or training['worst'] < 1.35 or training['max'] > 1:
        print('REJECT PUBLIC', filename, training, flush=True)
        continue
    summary, ratios = evaluate(word, values, instances=synthetic)
    failure_rates = np.any(ratios > 1, axis=1).reshape(8, -1).mean(axis=1)
    probability = float(np.prod((1 - failure_rates) ** 12))
    if summary['core'] < 1.85 or summary['worst'] < 1.45:
        probability *= .01
    record = (probability, filename, training, summary, failure_rates.tolist())
    print('ASSESSED', record, flush=True)
    results.append(record)
    results.sort(reverse=True)
    (ROOT / 'assessment.json').write_text(json.dumps(results, indent=2))
    np.savez(ROOT / (filename.replace('.json', '') + '_assessment.npz'), ratios=ratios)
assert results
winner = results[0]
print('WINNER', winner, flush=True)
subprocess.run([sys.executable, str(ROOT / 'finalize.py'), winner[1]], check=True)
