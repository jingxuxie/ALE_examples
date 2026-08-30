from evaluate import *
from scipy.linalg import hadamard

cases = holdouts()
Path('holdout_cases.json').write_text(json.dumps(cases, indent=2))
balanced = [case for case in cases if case['family'] != 'joint']
for index, row in enumerate(hadamard(16)[:, 1:9]):
    case = dict(PROTOCOL['nominal'], id='joint_hadamard_' + str(index), family='joint')
    for key, sign in zip(PROTOCOL['uncertainty'], row):
        case[key] = PROTOCOL['uncertainty'][key][int(sign > 0)]
    balanced.append(case)
for case in balanced:
    case['weight'] = 1 / sum(other['family'] == case['family'] for other in balanced)
Path('balanced_cases.json').write_text(json.dumps(balanced, indent=2))
corners = [dict(case) for case in balanced if case['family'] != 'joint']
for case in corners:
    case.pop('weight', None)
for index in range(256):
    case = dict(PROTOCOL['nominal'], id='joint_corner_' + str(index), family='joint')
    for offset, key in enumerate(PROTOCOL['uncertainty']):
        case[key] = PROTOCOL['uncertainty'][key][(index >> offset) & 1]
    corners.append(case)
Path('corner_cases.json').write_text(json.dumps(corners, indent=2))
