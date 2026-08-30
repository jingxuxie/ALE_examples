import itertools
import json

from scipy.stats import qmc

from optimize import OUT, PROTOCOL, PUBLIC

families = PUBLIC.copy()
for family, keys in (('interaction', ('g', 'self_ratio', 'cross_ratio')), ('calibration', ('rf_gain', 'bias', 'gradient')), ('trap', ('trap_x', 'trap_y', 'gradient'))):
    for index, sides in enumerate(itertools.product((0, 1), repeat=3)):
        case = PUBLIC[0].copy()
        case.update(id=family + '_%02d' % index, family=family)
        case.update({key: PROTOCOL['uncertainty'][key][side] for key, side in zip(keys, sides)})
        families.append(case)
(OUT / 'families.json').write_text(json.dumps(families, indent=2) + '\n')
random_cases = []
for index, point in enumerate(qmc.Sobol(8, scramble=True, seed=986).random_base2(6)):
    case = dict(id='interior_%02d' % index, family='joint')
    case.update({key: limits[0] + value * (limits[1] - limits[0]) for (key, limits), value in zip(PROTOCOL['uncertainty'].items(), point)})
    random_cases.append(case)
(OUT / 'interiors.json').write_text(json.dumps(random_cases, indent=2) + '\n')
