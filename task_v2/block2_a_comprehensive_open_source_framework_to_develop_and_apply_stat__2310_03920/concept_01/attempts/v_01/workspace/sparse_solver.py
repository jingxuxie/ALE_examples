import itertools
import math
import time

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh, expm_multiply


def popcount(values):
    counts = np.zeros(values.shape, dtype=np.int16)
    remaining = values.copy()
    while np.any(remaining):
        counts += (remaining & 1).astype(np.int16)
        remaining >>= 1
    return counts


def basis_states(case):
    sites, sector = case['n_sites'], case['sector']
    def fixed_bits(modes, number):
        return [sum(1 << mode for mode in occupied)
                for occupied in itertools.combinations(modes, number)]
    if sector['kind'] == 'number_sz':
        up = (sector['value'] + sector['twosz']) // 2
        down = sector['value'] - up
        values = [first | second for first in fixed_bits(range(0, 2 * sites, 2), up)
                  for second in fixed_bits(range(1, 2 * sites, 2), down)]
    elif sector['kind'] == 'number':
        values = fixed_bits(range(2 * sites), sector['value'])
    else:
        values = np.arange(1 << (2 * sites), dtype=np.int64)
        values = values[popcount(values) % 2 == sector['value']]
    return np.sort(np.asarray(values, dtype=np.int64))


def fermion_product(states, operators):
    target = states.copy()
    amplitudes = np.ones(len(states))
    for mode, creation in reversed(operators):
        occupied = (target >> mode) & 1
        amplitudes *= (occupied == (0 if creation else 1))
        amplitudes *= 1 - 2 * (popcount(target & ((1 << mode) - 1)) % 2)
        target ^= 1 << mode
    valid = amplitudes != 0
    columns = np.flatnonzero(valid)
    rows = np.searchsorted(states, target[valid])
    in_sector = rows < len(states)
    in_sector[in_sector] &= states[rows[in_sector]] == target[valid][in_sector]
    if not np.all(in_sector):
        raise ValueError('Hamiltonian term leaves the specified sector')
    return sparse.coo_matrix((amplitudes[valid], (rows, columns)),
                             shape=(len(states), len(states))).tocsr()


def build(case):
    states = basis_states(case)
    sites = case['n_sites']
    occupation = np.array([((states >> (2 * site)) & 1) + ((states >> (2 * site + 1)) & 1)
                           for site in range(sites)])
    spin = sum((((states >> (2 * site)) & 1) - ((states >> (2 * site + 1)) & 1)) / 2
               for site in range(sites))
    doubles = np.array([((states >> (2 * site)) & 1) * ((states >> (2 * site + 1)) & 1)
                        for site in range(sites)])
    region = set(case['region'])
    electron_ops = []
    for edge in case.get('edges', []):
        left, right = edge['sites']
        for first in range(2):
            for second in range(2):
                if any(abs(complex(*edge[stage][first][second])) > 0 for stage in ('before', 'after')):
                    operator = fermion_product(states, [(2 * left + first, True), (2 * right + second, False)])
                    electron_ops.append((operator, {stage: complex(*edge[stage][first][second])
                                                   for stage in ('before', 'after')},
                                         int(left in region) - int(right in region), 'current'))
    for pair in case.get('pairing', []):
        left, right = pair['sites']
        first, second = pair['spins']
        operator = fermion_product(states, [(2 * left + first, True), (2 * right + second, True)])
        electron_ops.append((operator, {stage: complex(*pair[stage]) for stage in ('before', 'after')},
                             int(left in region) + int(right in region), 'source'))
    modes = case.get('phonons', [])
    oscillator_dimension = math.prod(mode['levels'] for mode in modes)
    oscillator_indices = np.arange(oscillator_dimension)
    oscillator_number = np.zeros(oscillator_dimension)
    oscillator_energy = np.zeros(oscillator_dimension)
    oscillator_ops = []
    for index, mode in enumerate(modes):
        stride = math.prod(other['levels'] for other in modes[index + 1:])
        quanta = oscillator_indices // stride % mode['levels']
        oscillator_number += quanta
        oscillator_energy += mode['omega'] * quanta
        valid = quanta > 0
        annihilation = sparse.coo_matrix((np.sqrt(quanta[valid]),
                                         (oscillator_indices[valid] - stride, oscillator_indices[valid])),
                                        shape=(oscillator_dimension, oscillator_dimension)).tocsr()
        oscillator_ops.append(annihilation + annihilation.T)
    oscillator_identity = sparse.identity(oscillator_dimension, format='csr')
    electron_identity = sparse.identity(len(states), format='csr')
    matrices = {}
    for stage in ('before', 'after'):
        diagonal = np.asarray(case['onsite'][stage], dtype=float) @ occupation + np.asarray(case['interaction'], dtype=float) @ doubles
        for site, field in enumerate(case.get('zeeman', [0] * sites)):
            diagonal += field * (((states >> (2 * site)) & 1) - ((states >> (2 * site + 1)) & 1)) / 2
        for edge in case.get('density_edges', []):
            left, right = edge['sites']
            diagonal += edge['strength'] * occupation[left] * occupation[right]
        hamiltonian = sparse.diags(diagonal, format='csr', dtype=complex)
        for operator, amplitudes, delta, observable in electron_ops:
            hamiltonian += amplitudes[stage] * operator + amplitudes[stage].conjugate() * operator.getH()
        matrices[stage] = sparse.kron(hamiltonian, oscillator_identity, format='csr')
        matrices[stage] += sparse.kron(electron_identity, sparse.diags(oscillator_energy), format='csr')
        for mode, displacement in zip(modes, oscillator_ops):
            matrices[stage] += mode['coupling'][stage] * sparse.kron(
                sparse.diags(occupation[mode['site']] - mode['offset']), displacement, format='csr')
        if np.max(np.abs(matrices[stage].data.imag), initial=0.0) == 0:
            matrices[stage] = matrices[stage].real.copy()
    for name in ('current', 'source'):
        matrix = sparse.csr_matrix((len(states), len(states)), dtype=complex)
        for operator, amplitudes, delta, observable in electron_ops:
            if observable == name:
                coefficient = -1j * delta * amplitudes['after']
                matrix += coefficient * operator + coefficient.conjugate() * operator.getH()
        matrices[name] = sparse.kron(matrix, oscillator_identity, format='csr')
    diagonals = dict(charge=np.repeat(occupation[list(region)].sum(axis=0), oscillator_dimension),
                     number=np.repeat(occupation.sum(axis=0), oscillator_dimension),
                     spin=np.repeat(spin, oscillator_dimension),
                     phonon=np.tile(oscillator_number, len(states)))
    return matrices, diagonals


def simulate(case, settings, output):
    started = time.perf_counter()
    matrices, diagonals = build(case)
    initial, final = matrices['before'], matrices['after']
    dimension = initial.shape[0]
    rng = np.random.default_rng(settings['seed'])
    if np.max(np.abs(initial.data), initial=0.0) == 0:
        initial_energy = 0.0
        state = rng.normal(size=dimension)
    elif dimension <= 4:
        energies, vectors = np.linalg.eigh(initial.toarray())
        initial_energy, state = energies[0], vectors[:, 0]
    else:
        guess = rng.normal(size=dimension)
        if np.iscomplexobj(initial.data):
            guess = guess + 1j * rng.normal(size=dimension)
        energies, vectors = eigsh(initial, k=1, which='SA', tol=settings['eig_tol'],
                                 v0=guess,
                                 maxiter=20000, ncv=min(dimension, 40))
        initial_energy, state = energies[0], vectors[:, 0]
    state /= np.linalg.norm(state)
    residual = float(np.linalg.norm(initial @ state - initial_energy * state))
    preparation_seconds = time.perf_counter() - started
    rows = []
    previous = 0.0
    for instant in case['times']:
        if instant < previous:
            raise ValueError('Sampling times must be nondecreasing and nonnegative')
        if instant > previous:
            generator = -1j * (instant - previous) * final
            state = expm_multiply(generator, state, traceA=generator.diagonal().sum())
        norm = float(np.vdot(state, state).real)
        row = dict(time=instant, norm=norm)
        probabilities = np.abs(state) ** 2 / norm
        row.update({name: float(probabilities @ diagonal) for name, diagonal in diagonals.items()})
        for name, operator in [('energy', final), ('current', matrices['current']), ('source', matrices['source'])]:
            row[name] = float(np.vdot(state, operator @ state).real / norm)
        rows.append(row)
        previous = instant
    charge = sparse.diags(diagonals['charge'])
    continuity = 1j * (final @ charge - charge @ final) - matrices['current'] - matrices['source']
    return float(initial_energy.real), rows, dict(
        initial_residual=residual, preparation_seconds=preparation_seconds,
        hamiltonian_nnz=int(final.nnz), hermiticity_max=float(abs(final - final.getH()).max()),
        continuity_operator_max=float(abs(continuity).max()))
