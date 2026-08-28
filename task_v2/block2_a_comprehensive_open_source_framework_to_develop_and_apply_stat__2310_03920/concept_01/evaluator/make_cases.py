import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def spin_hop(strength, phase=0, mixing=0):
    phase_factor = np.exp(1j * phase)
    matrix = phase_factor * np.array([[-strength, mixing], [-mixing, -strength]])
    return [[[float(value.real), float(value.imag)] for value in row] for row in matrix]


def make_case(family, size, hidden=False):
    case = {'id': family + ('_transfer' if hidden else '_dev'), 'family': family,
            'n_sites': size, 'sector': {'kind': 'number_sz', 'value': size, 'twosz': 0},
            'onsite': {'before': [0.0] * size, 'after': [0.0] * size},
            'interaction': [0.0] * size, 'zeeman': [0.0] * size, 'edges': [],
            'pairing': [], 'density_edges': [], 'phonons': [], 'region': list(range(size // 2)),
            'times': [round(value, 8) for value in np.linspace(0, 1.2, 7)],
            'layout': list(range(size))}
    if family == 'impurity':
        impurity = size // 2 - 1
        case['interaction'][impurity] = 2.4 if hidden else 1.6
        case['onsite']['before'][impurity] = -case['interaction'][impurity] / 2 + 0.1
        case['onsite']['after'] = [value + (-0.35 if site < impurity else 0.35 if site > impurity else 0)
                                  for site, value in enumerate(case['onsite']['before'])]
        for site in range(size - 1):
            strength = 0.42 if impurity in [site, site + 1] else 1
            case['edges'].append({'sites': [site, site + 1], 'before': spin_hop(strength), 'after': spin_hop(strength)})
    elif family == 'ladder':
        case['interaction'] = [3.5] * size
        case['sector']['value'] = size - 2
        case['region'] = [site for site in range(size) if site // 2 < size // 4]
        for site in range(size):
            case['onsite']['before'][site] = 0.09 * (site % 2)
            case['onsite']['after'][site] = case['onsite']['before'][site] + (0.5 if site in case['region'] else -0.3)
            targets = [(site + 2, 1.0)] if site + 2 < size else []
            if site % 2 == 0:
                targets.append((site + 1, 0.72))
                if site + 3 < size:
                    targets.append((site + 3, 0.22))
            for target, strength in targets:
                case['edges'].append({'sites': [site, target], 'before': spin_hop(strength), 'after': spin_hop(strength)})
        case['density_edges'] = [{'sites': [site, site + 2], 'strength': 0.25} for site in range(size - 2)]
    elif family == 'spin_orbit':
        case['sector'] = {'kind': 'number', 'value': size - 2}
        case['interaction'] = [1.8 if site % 2 else 2.2 for site in range(size)]
        case['zeeman'] = [0.18 + 0.03 * (site % 3) for site in range(size)]
        case['onsite']['before'] = [0.17 * np.cos(2 * np.pi * site / size) for site in range(size)]
        case['onsite']['after'] = [value + (0.35 if site in case['region'] else -0.35) for site, value in enumerate(case['onsite']['before'])]
        for site in range(size):
            case['edges'].append({'sites': [site, (site + 1) % size], 'before': spin_hop(0.9, 0.7 / size, 0.28),
                                  'after': spin_hop(0.9, 1.4 / size, 0.28)})
    elif family == 'paired':
        case['sector'] = {'kind': 'parity', 'value': 0}
        case['interaction'] = [0.85] * size
        case['onsite']['before'] = [-0.34 + 0.04 * (site % 2) for site in range(size)]
        case['onsite']['after'] = [value + (0.28 if site in case['region'] else -0.22) for site, value in enumerate(case['onsite']['before'])]
        for site in range(size - 1):
            case['edges'].append({'sites': [site, site + 1], 'before': spin_hop(0.7, 0, 0.12), 'after': spin_hop(0.7, 0.12, 0.12)})
        for site in range(size):
            after = 0.45 * np.exp(1j * (0.65 if site in case['region'] else -0.45))
            case['pairing'].append({'sites': [site, site], 'spins': [0, 1], 'before': [0.45, 0],
                                    'after': [float(after.real), float(after.imag)]})
        if hidden:
            for site in range(0, size - 1, 2):
                case['pairing'].append({'sites': [site, site + 1], 'spins': [0, 0], 'before': [0.06, 0.03], 'after': [0.02, 0.08]})
    elif family == 'vibronic':
        case['interaction'] = [1.4] * size
        case['onsite']['before'] = [-0.7] * size
        case['onsite']['after'] = [-0.7 + (0.45 if site in case['region'] else -0.45) for site in range(size)]
        for site in range(size - 1):
            case['edges'].append({'sites': [site, site + 1], 'before': spin_hop(0.8), 'after': spin_hop(0.8)})
        for site in range(size):
            case['phonons'].append({'site': site, 'levels': 5 if hidden else 4, 'omega': 0.7 + 0.08 * (site % 2),
                                     'coupling': {'before': 0.3, 'after': 0.42}, 'offset': 1.0})
    else:
        raise ValueError(family)
    if hidden:
        case['layout'] = list(range(size - 1, -1, -2)) + list(range(size - 2, -1, -2))
        case['layout'].extend(range(size, size + len(case['phonons'])))
    else:
        case['layout'].extend(range(size, size + len(case['phonons'])))
    return case


def main():
    for family, public_size, hidden_size in [('impurity', 6, 14), ('ladder', 6, 10), ('spin_orbit', 6, 10), ('paired', 6, 12), ('vibronic', 4, 6)]:
        for hidden, size in [(False, public_size), (True, hidden_size)]:
            folder = ROOT / ('evaluator/hidden/cases' if hidden else 'participant/v_01/input/cases')
            folder.mkdir(parents=True, exist_ok=True)
            case = make_case(family, size, hidden)
            (folder / (case['id'] + '.json')).write_text(json.dumps(case, indent=2))


if __name__ == '__main__':
    main()
