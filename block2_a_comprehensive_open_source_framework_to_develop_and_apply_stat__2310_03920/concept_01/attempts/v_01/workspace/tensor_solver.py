import math
import json
import time

import numpy as np
from pyblock2.driver.core import DMRGDriver, SymmetryTypes


def choose_layout(case, optimize):
    sites = case['n_sites']
    proposed = case.get('layout', list(range(sites + len(case.get('phonons', [])))))
    if not optimize:
        return list(proposed)
    electrons = [site for site in proposed if site < sites]
    links = [(record['sites'][0], record['sites'][1])
             for name in ('edges', 'pairing', 'density_edges') for record in case.get(name, [])]
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import reverse_cuthill_mckee
    graph = coo_matrix((np.ones(2 * len(links)),
                        ([left for left, right in links] + [right for left, right in links],
                         [right for left, right in links] + [left for left, right in links])),
                       shape=(sites, sites)).tocsr()
    bandwidth_order = reverse_cuthill_mckee(graph, symmetric_mode=True).tolist()
    def cost(order):
        positions = {site: index for index, site in enumerate(order)}
        spans = [abs(positions[left] - positions[right]) for left, right in links]
        return sum(spans) + 0.2 * sum(span ** 2 for span in spans)
    best = min([electrons, list(range(sites)), bandwidth_order], key=cost)
    best_cost = cost(best)
    rng = np.random.default_rng(718)
    for iteration in range(300):
        trial = list(best)
        left, right = rng.choice(sites, 2, replace=False) if sites > 1 else (0, 0)
        trial[left], trial[right] = trial[right], trial[left]
        trial_cost = cost(trial)
        if trial_cost < best_cost:
            best, best_cost = trial, trial_cost
    result = []
    for site in best:
        result.append(site)
        result.extend(sites + index for index, mode in enumerate(case.get('phonons', [])) if mode['site'] == site)
    return result


def initialize(case, settings, output):
    sector = case['sector']
    redundant_number = sector['kind'] == 'number' and settings.get('number_as_sz', False)
    specialized = (sector['kind'] == 'number_sz' and not settings.get('general_symmetry', False)) or redundant_number
    symmetry_type = SymmetryTypes.SZ if specialized else SymmetryTypes.SAny
    driver = DMRGDriver(scratch=str(output / 'scratch'), symm_type=symmetry_type | SymmetryTypes.CPX,
                        n_threads=2, n_mkl_threads=1, stack_mem=256 << 20)
    driver.bw.b.Random.rand_seed(settings['seed'])
    if redundant_number:
        quantum = lambda bits: driver.bw.SX(bits.bit_count(), bits.bit_count(), 0)
        target = driver.bw.SX(sector['value'], sector['value'], 0)
    elif specialized:
        quantum = lambda bits: driver.bw.SX(bits.bit_count(), (bits & 1) - ((bits >> 1) & 1), 0)
        target = driver.bw.SX(sector['value'], sector['twosz'], 0)
    elif sector['kind'] == 'number_sz':
        driver.set_symmetry_groups('U1Fermi', 'U1')
        quantum = lambda bits: driver.bw.SX(bits.bit_count(), (bits & 1) - ((bits >> 1) & 1))
        target = driver.bw.SX(sector['value'], sector['twosz'])
    elif sector['kind'] == 'number':
        driver.set_symmetry_groups('U1Fermi')
        quantum = lambda bits: driver.bw.SX(bits.bit_count())
        target = driver.bw.SX(sector['value'])
    else:
        driver.set_symmetry_groups('Z2Fermi')
        quantum = lambda bits: driver.bw.SX(bits.bit_count() % 2)
        target = driver.bw.SX(sector['value'])
    layout = settings.get('layout_override') or choose_layout(case, settings['optimize_layout'])
    settings['tensor_layout'] = layout
    settings['symmetry_implementation'] = 'specialized SZ' if specialized else 'general Abelian'
    if redundant_number:
        settings['symmetry_implementation'] = 'specialized SZ with redundant (N,N), not physical Sz'
    zero = quantum(0)
    driver.initialize_system(n_sites=len(layout), vacuum=zero, target=target, hamil_init=False)
    groups = {}
    for bits in range(4):
        groups.setdefault(quantum(bits), []).append(bits)
    ordered_groups = sorted(groups.items())
    bits_order = [bits for label, values in ordered_groups for bits in values]
    electronic_basis = [(label, len(values)) for label, values in ordered_groups]
    electronic_ops = {'': np.eye(4)}
    for spin, name in enumerate('cC'):
        creation = np.zeros((4, 4))
        for column, bits in enumerate(bits_order):
            if not bits & (1 << spin):
                row = bits_order.index(bits | (1 << spin))
                creation[row, column] = (-1) ** ((bits & ((1 << spin) - 1)).bit_count())
        electronic_ops[name] = creation
        electronic_ops['dD'[spin]] = creation.T
    electronic_ops['n'] = np.diag([bits.bit_count() for bits in bits_order])
    electronic_ops['s'] = np.diag([((bits & 1) - ((bits >> 1) & 1)) / 2 for bits in bits_order])
    electronic_ops['w'] = np.diag([int(bits == 3) for bits in bits_order])
    bases, operators = [], []
    for physical in layout:
        if physical < case['n_sites']:
            bases.append(electronic_basis)
            operators.append(electronic_ops)
        else:
            mode = case['phonons'][physical - case['n_sites']]
            levels = mode['levels']
            annihilation = np.diag(np.sqrt(np.arange(1, levels)), 1)
            bases.append([(zero, levels)])
            operators.append({'': np.eye(levels), 'p': np.diag(np.arange(levels)),
                              'x': annihilation + annihilation.T})
    driver.ghamil = driver.get_custom_hamiltonian(bases, operators, orb_dependent_ops='')
    return driver, {physical: index for index, physical in enumerate(layout)}


def make_mpo(driver, case, positions, stage=None, probe=None):
    builder = driver.expr_builder()
    count = 0
    def add(expression, indices, coefficient):
        nonlocal count
        if abs(coefficient) > 1e-16:
            builder.add_term(expression, [positions[site] for site in indices], complex(coefficient))
            count += 1
    sites = case['n_sites']
    region = set(case['region'])
    if probe in ('charge', 'number', 'spin', 'phonon'):
        if probe == 'phonon':
            for index in range(len(case.get('phonons', []))):
                add('p', [sites + index], 1)
        else:
            for site in (case['region'] if probe == 'charge' else range(sites)):
                add('s' if probe == 'spin' else 'n', [site], 1)
    else:
        if probe is None:
            for site in range(sites):
                add('n', [site], case['onsite'][stage][site])
                add('w', [site], case['interaction'][site])
                add('s', [site], case.get('zeeman', [0] * sites)[site])
            for edge in case.get('density_edges', []):
                add('nn', edge['sites'], edge['strength'])
            for index, mode in enumerate(case.get('phonons', [])):
                oscillator = sites + index
                add('p', [oscillator], mode['omega'])
                add('nx', [mode['site'], oscillator], mode['coupling'][stage])
                add('x', [oscillator], -mode['offset'] * mode['coupling'][stage])
        if probe in (None, 'current'):
            for edge in case.get('edges', []):
                left, right = edge['sites']
                for first in range(2):
                    for second in range(2):
                        coefficient = complex(*edge[stage][first][second])
                        if probe == 'current':
                            coefficient *= -1j * (int(left in region) - int(right in region))
                        add('cC'[first] + 'dD'[second], [left, right], coefficient)
                        add('cC'[second] + 'dD'[first], [right, left], coefficient.conjugate())
        if probe in (None, 'source'):
            for pair in case.get('pairing', []):
                left, right = pair['sites']
                first, second = pair['spins']
                coefficient = complex(*pair[stage])
                if probe == 'source':
                    coefficient *= -1j * (int(left in region) + int(right in region))
                add('cC'[first] + 'cC'[second], [left, right], coefficient)
                add('dD'[second] + 'dD'[first], [right, left], coefficient.conjugate())
    if count == 0:
        return None
    return driver.get_mpo(builder.finalize(adjust_order=True, fermionic_ops='cdCD'), iprint=0)


def simulate(case, settings, output):
    started = time.perf_counter()
    initializer, constructor = initialize, make_mpo
    if settings.get('spin_orbitals', False):
        from mode_solver import initialize_modes, make_mode_mpo
        initializer, constructor = initialize_modes, make_mode_mpo
    driver, positions = initializer(case, settings, output)
    initial = constructor(driver, case, positions, stage='before')
    zero_initial = initial is None
    if zero_initial:
        initial = driver.get_identity_mpo()
    bond = settings['bond']
    state = driver.get_random_mps(tag='GS', bond_dim=settings.get('initial_bond', min(32, bond)), nroots=1, dot=2)
    schedule = settings.get('bond_schedule', [min(32, bond)] * 2 + [min(64, bond)] * 2 + [bond])
    initial_energy = driver.dmrg(initial, state, n_sweeps=settings['sweeps'], bond_dims=schedule,
                                 noises=[1e-5, 1e-6, 1e-7, 1e-8, 0],
                                 thrds=[1e-10, 1e-12, settings.get('davidson_tol', 1e-15)],
                                 tol=settings['energy_tol'], cutoff=settings['cutoff'], iprint=0)
    bonds, discarded, energies = driver.get_dmrg_results()
    identity = driver.get_identity_mpo()
    initial_norm = float(driver.expectation(state, identity, state).real)
    initial_energy = 0.0 if zero_initial else float(driver.expectation(state, initial, state).real / initial_norm)
    initial_variance = None
    if settings.get('measure_variance', False):
        initial_variance = float(driver.expectation(state, initial, state, stacked_mpo=initial).real / initial_norm - initial_energy ** 2)
    preparation_seconds = time.perf_counter() - started
    print(json.dumps(dict(phase='prepared', seconds=preparation_seconds, energy=initial_energy)), flush=True)
    final = constructor(driver, case, positions, stage='after')
    probes = {name: constructor(driver, case, positions, stage='after', probe=name)
              for name in ('charge', 'number', 'spin', 'phonon', 'current', 'source')}
    probes['energy'] = final
    rows, td_discarded = [], []
    previous = 0.0
    for index, instant in enumerate(case['times']):
        if instant < previous:
            raise ValueError('Sampling times must be nondecreasing and nonnegative')
        if instant > previous and final is not None:
            boundaries = [previous, instant]
            switch = settings.get('one_site_after')
            if switch is not None and previous < switch < instant:
                boundaries.insert(1, switch)
            for segment, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
                if switch is not None and start >= switch - 1e-12:
                    state, forward = driver.adjust_mps(state, dot=1)
                count = math.ceil((end - start) / settings['step'] - 1e-12)
                state = driver.td_dmrg(final, state, target_t=1j * (end - start), n_steps=count,
                                       te_type='tdvp', hermitian=True, normalize_mps=False,
                                       final_mps_tag='TD' + str(index % 2) + str(segment), bond_dims=[bond],
                                       cutoff=settings['cutoff'], krylov_conv_thrd=settings.get('krylov_tol', 1e-18),
                                       krylov_subspace_size=30, iprint=0)
                td_discarded.extend(float(value) for value in driver._te.dws)
        norm = float(driver.expectation(state, identity, state).real)
        row = dict(time=instant, norm=norm)
        for name, operator in probes.items():
            row[name] = float(driver.expectation(state, operator, state).real / norm) if operator is not None else 0.0
        rows.append(row)
        print(json.dumps(dict(phase='sample', time=instant, seconds=time.perf_counter() - started)), flush=True)
        previous = instant
    diagnostics = dict(preparation_seconds=preparation_seconds,
                       zero_initial_hamiltonian=zero_initial,
                       initial_variance=initial_variance,
                       dmrg_energies=np.real(energies).ravel().tolist(),
                       dmrg_discarded_weights=np.asarray(discarded).tolist(),
                       tdvp_max_discarded_weight=max(td_discarded, default=0))
    driver.finalize()
    return float(np.real(initial_energy)), rows, diagnostics
