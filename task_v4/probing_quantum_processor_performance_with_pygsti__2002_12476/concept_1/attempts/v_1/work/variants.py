import itertools
import json
from pathlib import Path

import numpy as np

from optimize import Problem, COSTS, FAMILIES, BASELINE, sparse_risks


def main():
    problem = Problem(np.load('qmc_training.npz'), tail=3, boost=1.2)
    validation = np.load('qmc_test.npz')
    features = validation['features']
    families = validation['families']
    baseline = sparse_risks(features, BASELINE)
    baseline_mean = np.mean([baseline[families == family].mean() for family in FAMILIES])
    for parent in ['design_initial.json', 'design_search.json', 'design_qmc.json']:
        initial = np.array(json.loads(Path(parent).read_text())['batches'], dtype=float)
        for flags in itertools.product([0, 1], repeat=4):
            selected = np.flatnonzero(initial)
            values = initial[selected].copy()
            for enabled, (removed, added) in zip(flags, [(87, 124), (562, 752), (606, 781), (736, 440)]):
                if enabled and removed in selected:
                    position = np.flatnonzero(selected == removed)[0]
                    selected[position] = added
                    values[position] *= COSTS[removed] / COSTS[added]
            values, objective = problem.optimize(selected, values)
            batch = np.zeros(len(COSTS))
            batch[selected] = values
            risk = sparse_risks(features, batch)
            overall = 1 - np.mean([risk[families == family].mean() for family in FAMILIES]) / baseline_mean
            ratios = risk / baseline
            mask = families == 'mixed'
            code = ''.join(map(str, flags))
            name = parent.replace('.json', '') + '_' + code
            np.save(name + '.npy', batch)
            print(name, objective, 'score', overall, 'mixed', 1-risk[mask].mean()/baseline[mask].mean(),
                  'tail', np.quantile(ratios[mask], [.95, .99, 1]), flush=True)


if __name__ == '__main__':
    main()
