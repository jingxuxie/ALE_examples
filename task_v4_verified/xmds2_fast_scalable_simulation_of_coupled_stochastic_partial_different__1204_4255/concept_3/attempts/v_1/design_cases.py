import json
from pathlib import Path

import numpy as np
from scipy.linalg import hadamard
from scipy.stats import qmc

from optimize import PROTOCOL, PUBLIC


def write_cases():
    bounds = PROTOCOL['uncertainty']
    names = list(bounds)
    cases = list(PUBLIC)

    def add(family, coordinates):
        values = dict(PROTOCOL['nominal'])
        for name, coordinate in coordinates.items():
            lower, upper = bounds[name]
            values[name] = (lower + upper) / 2 + coordinate * (upper - lower) / 2
        cases.append(dict(id=family + '_%02d' % len(cases), family=family, **values))

    for signs in hadamard(4)[:, 1:]:
        add('interaction', dict(zip(['g', 'self_ratio', 'cross_ratio'], signs.tolist())))
    for signs in hadamard(4)[:, 1:]:
        add('calibration', dict(zip(['rf_gain', 'bias', 'gradient'], signs.tolist())))
    add('calibration', {'bias': -1.})
    add('calibration', {'bias': 1.})
    for signs in hadamard(4)[:, 1:]:
        add('trap', dict(zip(['trap_x', 'trap_y', 'gradient'], signs.tolist())))
    signs = hadamard(16)[:, [1, 2, 4, 8, 3, 5, 9, 14]]
    for row in signs:
        add('joint', dict(zip(names, row.tolist())))
    for row in qmc.Sobol(8, scramble=True, seed=913).random_base2(3)[:5]:
        add('joint', dict(zip(names, (2 * row - 1).tolist())))
    Path('training_cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    print('training cases', len(cases))


if __name__ == '__main__':
    write_cases()
