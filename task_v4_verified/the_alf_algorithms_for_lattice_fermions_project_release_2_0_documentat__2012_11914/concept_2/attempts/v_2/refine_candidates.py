import json
import numpy as np
from search import ROOT, NAMES, evaluate
from refine import Objective

objective = Objective()
records = json.loads((ROOT / 'candidate_ranking.json').read_text())
results = []
for rank, (_, _, filename, _) in enumerate(records[:15]):
    artifact = json.loads((ROOT / filename).read_text())
    word = np.array([NAMES.index(stage['component']) for stage in artifact['stages'][:17]])
    values = np.array([stage['coefficient'] for stage in artifact['stages'][:17]])
    values[-1] /= 2
    label = 'guarded_candidate_' + str(rank)
    print('CANDIDATE', rank, filename, flush=True)
    values = objective.optimize(word, values, seconds=120, penalty=1000, label=label)
    summary, _ = evaluate(np.r_[word, word[-2::-1]], np.r_[values[:16], 2 * values[-1], values[15::-1]], verbose=True)
    results.append((summary['max'], summary['core'], label + '.json', summary))
    values = objective.optimize(word, values, seconds=120, penalty=-1, label=label + '_max')
    summary, _ = evaluate(np.r_[word, word[-2::-1]], np.r_[values[:16], 2 * values[-1], values[15::-1]], verbose=True)
    results.append((summary['max'], summary['core'], label + '_max.json', summary))
    results.sort()
    (ROOT / 'refined_ranking.json').write_text(json.dumps(results))
print('RANKING', results, flush=True)
