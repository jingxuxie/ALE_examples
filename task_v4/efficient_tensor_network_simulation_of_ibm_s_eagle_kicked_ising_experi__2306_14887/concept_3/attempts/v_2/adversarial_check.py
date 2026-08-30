import json
import os
import numpy as np
from optimize import ROOT, Ensemble, load
from robustness import make_pool, unique, adversaries

angles = load(ROOT/'pulses.json')
pool = make_pool()
if (ROOT/'stress_scenarios.json').exists():
    pool = unique(pool+json.loads((ROOT/'stress_scenarios.json').read_text())['scenarios'])
scores = Ensemble(pool).evaluate(angles,False)
initial = [pool[index] for index in np.argsort(scores)[:48]]
added = adversaries(angles,starts=int(os.environ.get('ADVERSARIAL_STARTS',128)),iterations=30,seed=7109413,initial=initial)
pool = unique(pool+added)
scores = Ensemble(pool).evaluate(angles,False)
print('expanded adversarial minimum',scores.min(),'count',len(pool),'worst',pool[int(np.argmin(scores))],flush=True)
(ROOT/'stress_scenarios.json').write_text(json.dumps({'scenarios':pool}))
(ROOT/'adversarial_validation.json').write_text(json.dumps({'count':len(pool),'minimum_fidelity':float(scores.min()),'worst_scenario':pool[int(np.argmin(scores))]},indent=2)+'\n')
