import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import json
import sys
from pathlib import Path
import numpy as np
from experimental import Model, design

episodes = json.load(open('../../participant/input/training.json'))['episodes']
cache = {}
for path in sys.argv[1:]:
    records = json.load(open(path))
    risks = []
    oracle_risks = []
    for record in records:
        key = (record['episode'], record['repeat'])
        if key not in cache:
            episode = episodes[record['episode']]
            model = Model(episode['spec'])
            rng = np.random.default_rng(189328 + key[0] * 5791 + key[1] * 357293)
            truth = rng.uniform(model.bounds[:, 0], model.bounds[:, 1])
            fisher = model.fisher(truth)
            fractions = design(model, truth, np.zeros(29), 40000)
            inverse = np.linalg.inv(np.einsum('a,akl->kl', fractions * 40000, fisher))
            cache[key] = fisher, model.groups, model.groups @ np.diag(inverse)
        fisher, groups, oracle = cache[key]
        inverse = np.linalg.inv(np.einsum('a,akl->kl', record['allocations'], fisher))
        risks.append(groups @ np.diag(inverse))
        oracle_risks.append(oracle)
    risks = np.array(risks)
    oracle_risks = np.array(oracle_risks)
    print(path, len(records))
    cells = []
    for regime in ('chain_hooks', 'patch_crosstalk', 'burst_aliases'):
        mask = np.array([record['regime'] == regime for record in records])
        pooled = np.sqrt(risks[mask].mean(axis=0))
        print(regime, pooled.round(5).tolist(), 'oracle', np.sqrt(oracle_risks[mask].mean(axis=0)).round(5).tolist())
        cells.extend(pooled)
    print('mean', np.mean(cells), 'variance overhead', np.mean(risks / oracle_risks))
