import copy
import json
import os
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import numpy as np

from test_solver import make_case
from solve import solve


def main():
    case = make_case('spin1_chain', 32, 343)
    case['single_ion'] = [-0.25] * case['length']
    case['field'] = [0.07 * (-1) ** site + 0.02 * np.sin(0.3 * site) for site in range(case['length'])]
    for bond in case['bonds']:
        bond['jxy'] = 0.5
        bond['jz'] = 0.6
    flipped = copy.deepcopy(case)
    flipped['field'] = [-field for field in case['field']]
    flipped['excited_sector'] = -case['excited_sector']
    first = solve(case, budget=160, verbose=True)
    second = solve(flipped, budget=160, verbose=True)
    errors = {key: float(np.max(np.abs(np.asarray(first[key]) - second[key])))
              for key in ['energy', 'gap', 'correlations']}
    Path(__file__).with_name('symmetry_check.json').write_text(json.dumps(
        {'first': first, 'flipped': second, 'errors': errors}))
    print(errors, flush=True)
    assert max(errors.values()) < 2e-7


if __name__ == '__main__':
    main()
