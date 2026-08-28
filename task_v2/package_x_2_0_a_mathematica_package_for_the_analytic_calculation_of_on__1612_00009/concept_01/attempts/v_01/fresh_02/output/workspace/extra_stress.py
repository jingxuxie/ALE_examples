import copy
import json
from pathlib import Path

import numpy as np

from loopaudit.backend import evaluate
from loopaudit.contract import decode


def main():
    root = Path(__file__).resolve().parent
    settings = json.loads((root / 'profiles.json').read_text())
    campaign = json.loads((root / 'release.json').read_text())
    tests = []
    for invariant in [4.0005, 4.005]:
        request = copy.deepcopy(campaign['cases'][1]['integrals'][0])
        request['id'] = 'near_threshold_' + str(invariant)
        request['invariants'][0][2] = request['invariants'][2][0] = invariant
        tests.append(request)
    request = copy.deepcopy(campaign['cases'][0]['integrals'][0])
    request.update(id='hierarchical_spacelike', masses2=[0.001, 1, 10, 100], weights=[3, 1, 1, 1], moments=[0, 0, 0, 0])
    tests.append(request)
    request = copy.deepcopy(campaign['cases'][1]['integrals'][0])
    request.update(id='maximum_weights_cut', weights=[3, 3, 3, 3], moments=[0, 1, 2, 1],
                   directions=[{'masses2': [0.1, -0.1, 0.05, 0.2]}], orders=[[0], [1], [2], [3]])
    tests.append(request)
    outcomes = []
    for request in tests:
        result = {'request': request, 'outcomes': {}}
        for profile in ['production', 'direct']:
            entry = evaluate(request, settings[profile])
            result['outcomes'][profile] = entry
            print(request['id'], profile, entry['seconds'], entry['estimated_error'], entry['strategy'], flush=True)
        result['relative_difference'] = max(
            np.max(abs(decode(entry) - decode(result['outcomes']['direct']['coefficients'][key])))
            / max(np.max(abs(decode(result['outcomes']['direct']['coefficients'][key]))), 1e-280)
            for key, entry in result['outcomes']['production']['coefficients'].items())
        print('difference', result['relative_difference'], flush=True)
        outcomes.append(result)
        (root.parent / 'extra_stress.json').write_text(json.dumps(outcomes, indent=2))


if __name__ == '__main__':
    main()
