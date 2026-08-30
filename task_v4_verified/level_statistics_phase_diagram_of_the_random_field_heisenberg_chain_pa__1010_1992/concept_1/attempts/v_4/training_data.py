import json
from pathlib import Path
import numpy as np


def load(variant='full', final=False):
    cases = json.loads(Path('dataset.json').read_text())
    data = np.load('dataset.npz')
    blocks = [data['features']]
    if 'quantum' in variant or variant == 'full':
        blocks.append(data['quantum'])
    if 'structure' in variant or variant in ('full', 'algebra'):
        blocks.append(data['structure'])
    features = np.column_stack(blocks)
    if variant == 'algebra':
        features = features[:, np.r_[0:226, 594:889]]
    target = np.array([case['f'] for case in cases])
    public = np.arange(2240, 2400)
    extra = np.array([index for index, case in enumerate(cases)
                      if case['id'].startswith('simulation_')
                      and int(case['id'].split('_')[-1]) >= 150
                      and int(case['id'].split('_')[-1]) % 5 == 0], dtype=int)
    if final:
        extra = np.array([index for index, case in enumerate(cases)
                          if case['id'].startswith('simulation_')
                          and int(case['id'].split('_')[-1]) >= 1600], dtype=int)
        train = np.setdiff1d(np.arange(len(cases)), extra)
    else:
        train = np.setdiff1d(np.arange(len(cases)), np.concatenate([public, extra]))
    return cases, features, target, train, public, extra
