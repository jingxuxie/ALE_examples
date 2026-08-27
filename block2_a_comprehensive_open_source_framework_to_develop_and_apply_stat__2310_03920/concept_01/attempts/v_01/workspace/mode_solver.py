import numpy as np
from pyblock2.driver.core import DMRGDriver, SymmetryTypes

from tensor_solver import choose_layout


def initialize_modes(case, settings, output):
    sector = case['sector']
    sites = case['n_sites']
    specialized = sector['kind'] == 'number' and not case.get('phonons')
    symmetry = SymmetryTypes.SGF if specialized else SymmetryTypes.SAny
    driver = DMRGDriver(scratch=str(output / 'scratch'), symm_type=symmetry | SymmetryTypes.CPX,
                        n_threads=2, n_mkl_threads=1, stack_mem=256 << 20)
    driver.bw.b.Random.rand_seed(settings['seed'])
    spatial = choose_layout(case, settings['optimize_layout'])
    layout = []
    for physical in spatial:
        layout.extend([2 * physical, 2 * physical + 1] if physical < sites else [sites + physical])
    layout = settings.get('mode_layout_override') or layout
    settings['tensor_layout'] = layout
    settings['symmetry_implementation'] = 'specialized SGF modes' if specialized else 'general Abelian modes'
    settings['local_electronic_dimension'] = 2
    if specialized:
        driver.initialize_system(n_sites=len(layout), n_elec=sector['value'])
        return driver, {physical: index for index, physical in enumerate(layout)}
    if sector['kind'] == 'number_sz':
        driver.set_symmetry_groups('U1Fermi', 'U1')
        zero = driver.bw.SX(0, 0)
        target = driver.bw.SX(sector['value'], sector['twosz'])
        quantum = lambda mode: driver.bw.SX(1, 1 if mode % 2 == 0 else -1)
    elif sector['kind'] == 'number':
        driver.set_symmetry_groups('U1Fermi')
        zero = driver.bw.SX(0)
        target = driver.bw.SX(sector['value'])
        quantum = lambda mode: driver.bw.SX(1)
    else:
        driver.set_symmetry_groups('Z2Fermi')
        zero = driver.bw.SX(0)
        target = driver.bw.SX(sector['value'])
        quantum = lambda mode: driver.bw.SX(1)
    driver.initialize_system(n_sites=len(layout), vacuum=zero, target=target, hamil_init=False)
    bases, operators = [], []
    for physical in layout:
        if physical < 2 * sites:
            bases.append([(zero, 1), (quantum(physical), 1)])
            operators.append({'': np.eye(2), 'C': np.array([[0, 0], [1, 0]]),
                              'D': np.array([[0, 1], [0, 0]])})
        else:
            levels = case['phonons'][physical - 2 * sites]['levels']
            annihilation = np.diag(np.sqrt(np.arange(1, levels)), 1)
            bases.append([(zero, levels)])
            operators.append({'': np.eye(levels), 'p': np.diag(np.arange(levels)),
                              'x': annihilation + annihilation.T})
    driver.ghamil = driver.get_custom_hamiltonian(bases, operators, orb_dependent_ops='')
    return driver, {physical: index for index, physical in enumerate(layout)}


def make_mode_mpo(driver, case, positions, stage=None, probe=None):
    builder = driver.expr_builder()
    count = 0
    def add(expression, indices, coefficient):
        nonlocal count
        if abs(coefficient) > 1e-16:
            builder.add_term(expression, [positions[mode] for mode in indices], complex(coefficient))
            count += 1
    sites = case['n_sites']
    region = set(case['region'])
    if probe in ('charge', 'number', 'spin', 'phonon'):
        if probe == 'phonon':
            for index in range(len(case.get('phonons', []))):
                add('p', [2 * sites + index], 1)
        else:
            for site in (case['region'] if probe == 'charge' else range(sites)):
                for spin in range(2):
                    mode = 2 * site + spin
                    add('CD', [mode, mode], (0.5 if spin == 0 else -0.5) if probe == 'spin' else 1)
    else:
        if probe is None:
            for site in range(sites):
                for spin in range(2):
                    mode = 2 * site + spin
                    add('CD', [mode, mode], case['onsite'][stage][site]
                        + case.get('zeeman', [0] * sites)[site] * (0.5 if spin == 0 else -0.5))
                add('CDCD', [2 * site, 2 * site, 2 * site + 1, 2 * site + 1], case['interaction'][site])
            for edge in case.get('density_edges', []):
                for first in range(2):
                    for second in range(2):
                        left, right = 2 * edge['sites'][0] + first, 2 * edge['sites'][1] + second
                        add('CDCD', [left, left, right, right], edge['strength'])
            for index, oscillator in enumerate(case.get('phonons', [])):
                boson = 2 * sites + index
                add('p', [boson], oscillator['omega'])
                for spin in range(2):
                    mode = 2 * oscillator['site'] + spin
                    add('CDx', [mode, mode, boson], oscillator['coupling'][stage])
                add('x', [boson], -oscillator['offset'] * oscillator['coupling'][stage])
        if probe in (None, 'current'):
            for edge in case.get('edges', []):
                left, right = edge['sites']
                for first in range(2):
                    for second in range(2):
                        coefficient = complex(*edge[stage][first][second])
                        if probe == 'current':
                            coefficient *= -1j * (int(left in region) - int(right in region))
                        add('CD', [2 * left + first, 2 * right + second], coefficient)
                        add('CD', [2 * right + second, 2 * left + first], coefficient.conjugate())
        if probe in (None, 'source'):
            for pair in case.get('pairing', []):
                left, right = pair['sites']
                first, second = pair['spins']
                coefficient = complex(*pair[stage])
                if probe == 'source':
                    coefficient *= -1j * (int(left in region) + int(right in region))
                add('CC', [2 * left + first, 2 * right + second], coefficient)
                add('DD', [2 * right + second, 2 * left + first], coefficient.conjugate())
    if count == 0:
        return None
    return driver.get_mpo(builder.finalize(adjust_order=True, fermionic_ops='CD'), iprint=0)
