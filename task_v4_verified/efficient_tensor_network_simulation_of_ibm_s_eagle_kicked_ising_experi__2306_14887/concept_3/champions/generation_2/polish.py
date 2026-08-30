import json
import subprocess
import sys
import numpy as np
from optimize import ROOT, Ensemble, load, save
from robustness import make_pool, unique, adversaries
from minimax import fit

pool = unique(make_pool()+json.loads((ROOT/'stress_scenarios.json').read_text())['scenarios'])
core = [scenario for scenario in make_pool() if scenario['name'].startswith('corner_') and
        scenario['name'].endswith(tuple(f'_field_{field}' for field in range(5)))]
for epoch in range(4):
    angles = load(ROOT/'pulses.json')
    scores = Ensemble(pool).evaluate(angles,False)
    initial = [pool[index] for index in np.argsort(scores)[:96]]
    pool = unique(pool+adversaries(angles,starts=512,iterations=24,seed=92047+epoch,initial=initial))
    ensemble = Ensemble(pool)
    scores = ensemble.evaluate(angles,False)
    best_score = float(scores.min())
    print('POLISH',epoch,'new adversarial min',best_score,'pool',len(pool),flush=True)
    (ROOT/'stress_scenarios.json').write_text(json.dumps({'scenarios':pool}))
    if epoch and best_score >= .952:
        break
    for iteration in range(3):
        training = unique(core+[pool[index] for index in np.argsort(scores)[:160]])
        angles = fit(angles,training,f'polish_{epoch}_{iteration}.json',iterations=350)
        scores = ensemble.evaluate(angles,False)
        print('POLISH FIT',epoch,iteration,'min',scores.min(),flush=True)
        if scores.min() > best_score:
            best_score = float(scores.min())
            save(angles,'robust_best.json')
            save(angles)
        if Ensemble(training).evaluate(angles,False).min()-scores.min() < 1e-7:
            break
    subprocess.run([sys.executable,'-u',str(ROOT/'scan_fields.py')],check=True)
    pool = unique(pool+json.loads((ROOT/'stress_scenarios.json').read_text())['scenarios'])
