import json
import sys
import numpy as np
from search import ROOT, NAMES, load_instances, evaluate
from optimize import full
from refine import Objective
from validate import generate

public = load_instances()
synthetic = generate(60, seed=781293)
instances = []
for family in range(8):
    instances.extend(public[family * 6:(family + 1) * 6])
    instances.extend(synthetic[family * 60:(family + 1) * 60])
objective = Objective(instances)
validation = generate(240, seed=981294)
results = []
for index, filename in enumerate(sys.argv[1:]):
    artifact = json.loads((ROOT / filename).read_text())
    word = np.array([NAMES.index(stage['component']) for stage in artifact['stages'][:17]])
    values = np.array([stage['coefficient'] for stage in artifact['stages'][:17]])
    values[-1] /= 2
    label = 'prob_' + filename.replace('.json', '')
    print('PROBFIT', filename, flush=True)
    values = objective.optimize(word, values, seconds=180, penalty=-3, label=label)
    train_summary, _ = evaluate(*full(word, values), verbose=True)
    summary, ratios = evaluate(*full(word, values), instances=validation, verbose=True)
    failure_rates = np.any(ratios > 1, axis=1).reshape(8, -1).mean(axis=1)
    probability = np.prod((1 - failure_rates) ** 12)
    print('FAILURE RATES', failure_rates, 'PROBABILITY', probability, flush=True)
    np.savez(ROOT / (label + '_validation.npz'), ratios=ratios)
    results.append((float(probability), label + '.json', train_summary, summary, failure_rates.tolist()))
    results.sort(reverse=True)
    (ROOT / 'prob_ranking.json').write_text(json.dumps(results))
print('finished', flush=True)
