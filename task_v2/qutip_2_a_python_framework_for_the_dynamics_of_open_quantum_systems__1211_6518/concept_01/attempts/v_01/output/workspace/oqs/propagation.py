import numpy as np
from scipy.linalg import eigh
from scipy.sparse import csr_matrix

from .baths import spectrum
from .integration import integrate
from .io import coefficient


def local_operators(case):
    if case['physics'] == 'lindblad':
        return list(case['c_ops']), case['c_coeffs']
    energy_scale = max(float(np.ptp(np.linalg.eigvalsh(case['H0']))), 1e-6)
    operators = [np.sqrt(float(spectrum(bath, energy_scale))) * operator
                 for bath, operator in zip(case['baths'], case['a_ops'])]
    return operators, [{'kind': 'constant'} for operator in operators]


class MatrixAction:
    def __init__(self, matrix, sparse_allowed):
        threshold = 2e-13 * max(1.0, np.max(np.abs(matrix)))
        filtered = np.where(np.abs(matrix) > threshold, matrix, 0)
        self.sparse = sparse_allowed and np.count_nonzero(filtered) < 0.2 * matrix.size
        self.matrix = csr_matrix(filtered) if self.sparse else matrix
        self.transpose = self.matrix.T.tocsr() if self.sparse else matrix.T

    def left(self, density):
        return self.matrix @ density

    def right(self, density):
        if self.sparse:
            return (self.transpose @ density.T).T
        return density @ self.matrix


def propagate_lindblad(case, initial, options):
    dimension = len(case['H0'])
    jumps, specifications = local_operators(case)
    hamiltonians = [case['H0'], *case['h_ops']]
    basis = None
    if dimension >= 12 and initial.ndim == 2:
        energies, proposed = eigh(case['H0'])
        candidates = [np.diag(energies).astype(complex)] + [proposed.conj().T @ operator @ proposed
                                                         for operator in hamiltonians[1:] + jumps]
        original = hamiltonians + jumps
        occupancy = lambda matrices: sum(np.count_nonzero(np.abs(matrix) > 2e-12 * max(1, np.max(np.abs(matrix))))
                                         for matrix in matrices)
        if occupancy(candidates) < 0.8 * occupancy(original):
            basis = proposed
            hamiltonians = candidates[:len(hamiltonians)]
            jumps = candidates[len(hamiltonians):]
            initial = basis.conj().T @ initial @ basis
    sparse_allowed = dimension >= 8 and initial.ndim == 2 and not options.get('dense_operators', False)
    h_actions = [MatrixAction(operator, sparse_allowed) for operator in hamiltonians]
    jump_actions = [(MatrixAction(jump, sparse_allowed), MatrixAction(jump.conj().T, sparse_allowed),
                     MatrixAction(jump.conj().T @ jump, sparse_allowed)) for jump in jumps]
    shape = initial.shape

    def derivative(time, vector):
        density = vector.reshape(shape)
        result = -1j * (h_actions[0].left(density) - h_actions[0].right(density))
        for action, specification in zip(h_actions[1:], case['h_coeffs']):
            result += -1j * coefficient(specification, time) * (action.left(density) - action.right(density))
        for (jump, adjoint, gram), specification in zip(jump_actions, specifications):
            amplitude = abs(coefficient(specification, time))
            scale = amplitude if options.get('legacy_amplitudes', False) else amplitude ** 2
            result += scale * (adjoint.right(jump.left(density))
                               - 0.5 * (gram.left(density) + gram.right(density)))
        return result.ravel()

    integration_options = dict(options)
    if options.get('frobenius_atol', False):
        integration_options['atol'] = options['atol'] / dimension
    states = integrate(case, derivative, initial, case['times'], integration_options)
    if basis is not None:
        states = basis @ states @ basis.conj().T
    return states


def propagate_local_periodic(case, initial, options):
    dimension = len(case['H0'])
    delays = case['times'] - case['times'][0]
    cycles = np.floor(delays / case['period']).astype(np.int64)
    residuals = delays - cycles * case['period']
    requested = np.unique(np.append(residuals, case['period']))
    periodic_case = dict(case, times=case['times'][0] + requested)
    basis = np.eye(dimension ** 2, dtype=complex).reshape(dimension ** 2, dimension, dimension)
    trajectories = propagate_lindblad(periodic_case, basis, options)
    maps = trajectories.reshape(len(requested), dimension ** 2, dimension ** 2).transpose(0, 2, 1)
    initial_vectors = initial.reshape(-1, dimension ** 2).T
    powers = {int(cycle): np.linalg.matrix_power(maps[-1], int(cycle)) for cycle in np.unique(cycles)}
    return np.asarray([(maps[np.searchsorted(requested, residual)] @ powers[int(cycle)] @ initial_vectors)
                       .T.reshape(initial.shape) for residual, cycle in zip(residuals, cycles)])


def propagate(case, initial, options):
    if options.get('engine') == 'local' and case['physics'] == 'floquet':
        return propagate_local_periodic(case, initial, options)
    if options.get('engine') == 'local' or case['physics'] == 'lindblad':
        return propagate_lindblad(case, initial, options)
    if case['physics'] == 'redfield':
        from .spectral import propagate_redfield
        return propagate_redfield(case, initial, options)
    if case['physics'] == 'floquet':
        from .floquet import propagate_floquet
        return propagate_floquet(case, initial, options)
    raise ValueError('Unsupported physics: ' + case['physics'])
