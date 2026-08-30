import itertools
import json
import time
import numpy as np
from optimize import ROOT, Ensemble, load, encode, fidelities
from robustness import make_pool, unique, decode

angles = load(ROOT/'pulses.json')
pool = make_pool()
if (ROOT/'stress_scenarios.json').exists():
    pool = unique(pool+json.loads((ROOT/'stress_scenarios.json').read_text())['scenarios'])
pool_scores = Ensemble(pool).evaluate(angles,False)
calibrations = []
for first,second,common in itertools.product([-1,1],repeat=3):
    calibrations.append(np.array([first*.025,second*.025,common*.015]+[common*.005]*12))
for index in np.argsort(pool_scores):
    calibration = np.array(encode(pool[index])[:15])
    if not any(np.array_equal(calibration,existing) for existing in calibrations):
        calibrations.append(calibration)
    if len(calibrations) >= 16:
        break
masks = np.arange(2048,dtype=np.uint16) << 1
fields = .01*(1-2*((masks[:,None] >> np.arange(12)) & 1).astype(np.int64))
started = time.time()
hard_cases, hard_scores, summaries = [],[],[]
for calibration_index, calibration in enumerate(calibrations):
    scores = []
    scenarios = [decode(np.r_[calibration,field],f'field_scan_{calibration_index}_{index}') for index,field in enumerate(fields)]
    for offset in range(0,len(scenarios),256):
        scores.extend(Ensemble(scenarios[offset:offset+256]).evaluate(angles,False).tolist())
    indices = np.argsort(scores)[:4]
    hard_cases.extend(scenarios[index] for index in indices)
    hard_scores.extend(scores[index] for index in indices)
    summaries.append({'calibration':calibration.tolist(),'minimum_fidelity':min(scores),'worst_scenario':scenarios[int(indices[0])]})
    print('field scan',calibration_index,'min',min(scores),'seconds',time.time()-started,flush=True)
reference = fidelities(angles.reshape(24,2),hard_cases)
error = float(np.max(abs(reference-np.array(hard_scores))))
assert error < 1e-10
pool = unique(pool+hard_cases)
(ROOT/'stress_scenarios.json').write_text(json.dumps({'scenarios':pool}))
report = {'count':len(calibrations)*len(fields),'minimum_fidelity':min(hard_scores),'public_simulator_maximum_discrepancy':error,
          'note':'All static drift-sign corners modulo the exact global drift-sign symmetry, for 16 selected calibrations; not the private suite.',
          'calibrations':summaries,'runtime_seconds':time.time()-started}
(ROOT/'field_scan_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('FIELD SCAN FINAL',report['minimum_fidelity'],'reference error',error,flush=True)
