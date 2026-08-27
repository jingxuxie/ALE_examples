import numpy as np


def coefficient(value):
    return complex(*value) if isinstance(value, list) else complex(value)


def electronic_terms(case, stage):
    terms = []
    for site in range(case['n_sites']):
        for symbol in ['cd', 'CD']:
            terms.append((symbol, [site, site], case['onsite'][stage][site]))
        terms.append(('cdCD', [site] * 4, case['interaction'][site]))
        terms.append(('cd', [site] * 2, case.get('zeeman', [0] * case['n_sites'])[site] / 2))
        terms.append(('CD', [site] * 2, -case.get('zeeman', [0] * case['n_sites'])[site] / 2))
    for edge in case['edges']:
        left, right = edge['sites']
        for spin_left in range(2):
            for spin_right in range(2):
                value = coefficient(edge[stage][spin_left][spin_right])
                creation, annihilation = 'cC'[spin_left], 'dD'[spin_right]
                terms.append((creation + annihilation, [left, right], value))
                terms.append(('cC'[spin_right] + 'dD'[spin_left], [right, left], value.conjugate()))
    for pair in case.get('pairing', []):
        left, right = pair['sites']
        spin_left, spin_right = pair['spins']
        value = coefficient(pair[stage])
        terms.append(('cC'[spin_left] + 'cC'[spin_right], [left, right], value))
        terms.append(('dD'[spin_right] + 'dD'[spin_left], [right, left], value.conjugate()))
    for edge in case.get('density_edges', []):
        left, right = edge['sites']
        for first in ['cd', 'CD']:
            for second in ['cd', 'CD']:
                terms.append((first + second, [left, left, right, right], edge['strength']))
    return [(ops, sites, complex(value)) for ops, sites, value in terms if abs(value) > 1e-15]


def hamiltonian_terms(case, stage):
    terms = electronic_terms(case, stage)
    for phonon_index, phonon in enumerate(case.get('phonons', [])):
        oscillator = case['n_sites'] + phonon_index
        electron = phonon['site']
        terms.append(('EF', [oscillator] * 2, phonon['omega']))
        for density in ['cd', 'CD']:
            for displacement in ['E', 'F']:
                terms.append((density + displacement, [electron, electron, oscillator], phonon['coupling'][stage]))
        for displacement in ['E', 'F']:
            terms.append((displacement, [oscillator], -phonon['offset'] * phonon['coupling'][stage]))
    return terms


def observables(case):
    region = set(case['region'])
    result = {'charge': [], 'number': [], 'spin': [], 'phonon': [], 'current': [], 'source': []}
    for site in range(case['n_sites']):
        for density in ['cd', 'CD']:
            result['number'].append((density, [site] * 2, 1))
            if site in region:
                result['charge'].append((density, [site] * 2, 1))
        result['spin'].append(('cd', [site] * 2, 0.5))
        result['spin'].append(('CD', [site] * 2, -0.5))
    for index in range(len(case.get('phonons', []))):
        result['phonon'].append(('EF', [case['n_sites'] + index] * 2, 1))
    for ops, sites, value in electronic_terms(case, 'after'):
        delta = sum((1 if op in 'cC' else -1) for op, site in zip(ops, sites) if site in region)
        if not delta:
            continue
        net = sum(1 if op in 'cC' else -1 for op in ops)
        result['source' if net else 'current'].append((ops, sites, -1j * delta * value))
    result['energy'] = hamiltonian_terms(case, 'after')
    return result


def choose_order(case):
    if case.get('phonons'):
        order = []
        for site in range(case['n_sites']):
            order.append(site)
            order.extend(case['n_sites'] + index for index, mode in enumerate(case['phonons']) if mode['site'] == site)
        return order
    return list(range(case['n_sites']))


def local_operators(levels=None):
    if levels is not None:
        return {'': np.eye(levels), 'E': np.diag(np.sqrt(np.arange(1, levels)), -1), 'F': np.diag(np.sqrt(np.arange(1, levels)), 1)}
    create_up = np.zeros((4, 4))
    create_up[1, 0] = create_up[3, 2] = 1
    create_down = np.zeros((4, 4))
    create_down[2, 0], create_down[3, 1] = 1, -1
    return {'': np.eye(4), 'c': create_up, 'd': create_up.T, 'C': create_down, 'D': create_down.T}
