import copy
import json
import time

import numpy as np

from loopaudit.backend import evaluate
from loopaudit.contract import decode


def main():
    settings = json.load(open('workspace/profiles.json'))
    requests = json.load(open('workspace/release.json'))
    seed = copy.deepcopy(requests['cases'][1]['integrals'][0])
    tests = []
    for invariant in [4.05, 4.5, 12, 40]:
        item = copy.deepcopy(seed)
        item['invariants'][0][2] = item['invariants'][2][0] = invariant
        item['id'] = 'cut_' + str(invariant)
        tests.append(item)
    item = copy.deepcopy(seed)
    item.update(id='weighted_cut_jet', weights=[2, 3, 1, 1], moments=[0, 1, 0, 2],
                directions=[{'masses2': [0.1, -0.1, 0.05, 0.2]}], orders=[[0], [1], [2], [3]])
    tests.append(item)
    item = copy.deepcopy(seed)
    item.update(id='unequal_cut', masses2=[0.2, 1.1, 1.8, 0.7], weights=[1, 2, 1, 2])
    tests.append(item)
    item = copy.deepcopy(seed)
    item.update(id='rank_deficient_timelike', masses2=[1, 1.2, 0.8, 1.1])
    momenta = np.array([0, 0.2, 1.7, 2.4])
    item['invariants'] = ((momenta[:, None] - momenta[None, :]) ** 2).tolist()
    tests.append(item)
    cases = []
    for item in tests:
        outcomes = {}
        for profile in ['production', 'direct']:
            result = evaluate(item, settings[profile])
            outcomes[profile] = result
            print(item['id'], profile, result['seconds'], result['estimated_error'], result['strategy'], flush=True)
        difference = max(np.max(abs(decode(outcomes['production']['coefficients'][key])
                                   - decode(outcomes['direct']['coefficients'][key])))
                         / max(np.max(abs(decode(value))), 1e-280)
                         for key, value in outcomes['direct']['coefficients'].items())
        print('cross contour difference', difference, flush=True)
        cases.append({'request': item, 'outcomes': outcomes, 'relative_difference': difference})
        json.dump(cases, open('stress.json', 'w'), indent=2)


if __name__ == '__main__':
    main()
