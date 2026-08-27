import itertools
import math
import time

import numpy as np
from scipy import sparse
from scipy.linalg import expm, expm_frechet
from scipy.special import roots_hermitenorm
from scipy.sparse.linalg import expm_multiply

from .physics import ideal_channel, liouvillian


def prepare(case, arrays):
    law = case['noise']
    sigma = np.asarray(law['sigma'], dtype=float)
    mixing = np.asarray(law['mixing'], dtype=float)
    dimension = arrays['H'].shape[-1]
    operators = np.einsum('sa,am,aij->smij', arrays['sensitivity'],
                          mixing * sigma, arrays['operators'])
    operators -= (np.trace(operators, axis1=-2, axis2=-1)[..., None, None]
                  * np.eye(dimension) / dimension)
    rates = np.asarray(law.get('rates', np.zeros(len(sigma))), dtype=float)
    if law['kind'] in ('static', 'white'):
        rates = np.zeros(len(sigma))
    if law['kind'] == 'telegraph':
        rates = 2 * rates
    if np.any(rates < 0) or np.any(sigma < 0):
        raise ValueError('Noise rates and standard deviations must be nonnegative.')
    if law['kind'] != 'telegraph':
        compressed = []
        compressed_rates = []
        for rate in np.unique(rates):
            group = operators[:, rates == rate]
            flattened = group.transpose(1, 0, 2, 3).reshape(group.shape[1], -1)
            gram = (flattened.conj() @ flattened.T).real
            values, vectors = np.linalg.eigh(gram)
            keep = values > max(1e-28, values.max(initial=0) * 1e-13)
            rotated = np.einsum('smij,mk->skij', group, vectors[:, keep])
            compressed.append(rotated)
            compressed_rates.extend([rate] * int(keep.sum()))
        operators = np.concatenate(compressed, axis=1)
        rates = np.asarray(compressed_rates)
    else:
        keep = np.max(np.abs(operators), axis=(0, 2, 3)) > 1e-15
        operators = operators[:, keep]
        rates = rates[keep]
    return operators, rates


def response(arrays, operators, rates, reset=False, split=1):
    dimension = arrays['H'].shape[-1] ** 2
    count = len(rates)
    state = np.zeros(((count + 2) * dimension, dimension), dtype=complex)
    state[:dimension] = np.eye(dimension)
    identity = sparse.eye(dimension, format='csr')
    boundaries = set(arrays['blocks'][1:-1]) if reset else set()
    for segment, (duration, control, noise) in enumerate(zip(arrays['dt'], arrays['H'], operators)):
        if segment in boundaries:
            state[dimension:-dimension] = 0
        control_generator = sparse.csr_matrix(liouvillian(control))
        blocks = [[None for column in range(count + 2)] for row in range(count + 2)]
        blocks[0][0] = control_generator
        blocks[-1][-1] = control_generator
        for latent, (operator, rate) in enumerate(zip(noise, rates)):
            noise_generator = sparse.csr_matrix(liouvillian(operator))
            blocks[latent + 1][latent + 1] = control_generator - rate * identity
            blocks[latent + 1][0] = noise_generator
            blocks[-1][latent + 1] = noise_generator
        generator = sparse.bmat(blocks, format='csr') * (duration / split)
        for subdivision in range(split):
            state = expm_multiply(generator, state, traceA=generator.diagonal().sum())
    return state[:dimension].conj().T @ state[-dimension:]


def envelope_bound(arrays, operators, rates, reset=False):
    eigenvalues = np.linalg.eigvalsh(operators)
    amplitude = eigenvalues[..., -1] - eigenvalues[..., 0]
    memory = np.zeros(len(rates))
    bound = 0.0
    boundaries = set(arrays['blocks'][1:-1]) if reset else set()
    for segment, (duration, strength) in enumerate(zip(arrays['dt'], amplitude)):
        if segment in boundaries:
            memory[:] = 0
        scaled = rates * duration
        integral = np.empty_like(rates)
        triangular = np.empty_like(rates)
        small = np.abs(scaled) < 1e-4
        integral[small] = duration * (1 - scaled[small] / 2 + scaled[small] ** 2 / 6
                                     - scaled[small] ** 3 / 24)
        triangular[small] = duration ** 2 * (0.5 - scaled[small] / 6
                                             + scaled[small] ** 2 / 24
                                             - scaled[small] ** 3 / 120)
        integral[~small] = -np.expm1(-scaled[~small]) / rates[~small]
        triangular[~small] = (duration - integral[~small]) / rates[~small]
        bound += np.sum(strength * memory * integral + strength ** 2 * triangular)
        memory = np.exp(-scaled) * memory + strength * integral
    return float(bound)


def static_quadrature(arrays, operators, order, reset=False, deadline=None):
    latent_count = operators.shape[1]
    dimension = arrays['H'].shape[-1]
    nodes, weights = roots_hermitenorm(order)
    weights /= np.sqrt(2 * np.pi)
    indices = np.asarray(list(itertools.product(range(order), repeat=latent_count)))
    points = nodes[indices]
    probabilities = np.prod(weights[indices], axis=1)
    boundaries = arrays['blocks'] if reset else [0, len(arrays['dt'])]
    channel = np.eye(dimension ** 2, dtype=complex)
    for begin, end in zip(boundaries[:-1], boundaries[1:]):
        block_channel = np.zeros_like(channel)
        for start in range(0, len(points), 2048):
            sample = points[start:start + 2048]
            propagators = np.broadcast_to(np.eye(dimension),
                                          (len(sample), dimension, dimension)).astype(complex).copy()
            for duration, control, noise in zip(arrays['dt'][begin:end], arrays['H'][begin:end],
                                                operators[begin:end]):
                if deadline is not None and time.perf_counter() > deadline:
                    raise TimeoutError('Static quadrature reached its wall-time budget.')
                hamiltonians = control + np.einsum('bm,mij->bij', sample, noise)
                eigenvalues, eigenvectors = np.linalg.eigh(hamiltonians)
                increments = (eigenvectors * np.exp(-1j * duration * eigenvalues)[:, None, :]
                              ) @ eigenvectors.conj().transpose(0, 2, 1)
                propagators = increments @ propagators
            block_channel += np.einsum('b,bik,bjl->ijkl', probabilities[start:start + 2048],
                                       propagators.conj(), propagators).reshape(channel.shape)
        channel = block_channel @ channel
    return channel, len(points)


def multi_indices(count, degree):
    def compositions(total, length):
        if length == 1:
            yield (total,)
        else:
            for first in range(total + 1):
                for remaining in compositions(total - first, length - 1):
                    yield (first,) + remaining
    return [item for total in range(degree + 1) for item in compositions(total, count)]


def bath_matrices(rates, degree, telegraph=False):
    count = len(rates)
    if telegraph:
        maximum = count if degree is None else min(degree, count)
        indices = [tuple(int(latent in active) for latent in range(count))
                   for tier in range(maximum + 1)
                   for active in itertools.combinations(range(count), tier)]
    else:
        indices = multi_indices(count, degree)
    lookup = {index: position for position, index in enumerate(indices)}
    coupling = []
    for latent in range(count):
        rows, columns, entries = [], [], []
        for row, index in enumerate(indices):
            neighbor = list(index)
            neighbor[latent] += 1
            column = lookup.get(tuple(neighbor))
            if column is not None:
                rows.extend([row, column])
                columns.extend([column, row])
                entries.extend([np.sqrt(neighbor[latent])] * 2)
        coupling.append(sparse.csr_matrix((entries, (rows, columns)),
                                          shape=(len(indices), len(indices))))
    damping = np.asarray(indices) @ rates
    return coupling, damping


def hierarchy(arrays, operators, rates, degree, reset=False, telegraph=False, split=1,
              deadline=None):
    dimension = arrays['H'].shape[-1] ** 2
    coupling, damping = bath_matrices(rates, degree, telegraph)
    count = len(damping)
    state = np.zeros(((count + 1) * dimension, dimension), dtype=complex)
    state[-dimension:] = np.eye(dimension)
    coupling = [sparse.vstack([sparse.hstack([bath, bath[:, :1]]),
                               sparse.csr_matrix((1, count + 1))], format='csr')
                for bath in coupling]
    bath_identity = sparse.eye(count + 1, format='csr')
    decay = sparse.kron(sparse.diags(-np.append(damping, 0)), sparse.eye(dimension), format='csr')
    boundaries = set(arrays['blocks'][1:-1]) if reset else set()
    for segment, (duration, control, noise) in enumerate(zip(arrays['dt'], arrays['H'], operators)):
        if deadline is not None and time.perf_counter() > deadline:
            raise TimeoutError('Stochastic Liouville propagation reached its wall-time budget.')
        if segment in boundaries:
            state[dimension:-dimension] = 0
        generator = sparse.kron(bath_identity, sparse.csr_matrix(liouvillian(control)),
                                format='csr') + decay
        for bath, operator in zip(coupling, noise):
            generator += sparse.kron(bath, sparse.csr_matrix(liouvillian(operator)), format='csr')
        generator *= duration / split
        for subdivision in range(split):
            state = expm_multiply(generator, state, traceA=generator.diagonal().sum())
    return ideal_channel(arrays) + state[:dimension], count


def white_channel(arrays, operators, split=1):
    dimension = arrays['H'].shape[-1] ** 2
    channel = np.eye(dimension, dtype=complex)
    ideal = channel.copy()
    quadratic = np.zeros_like(channel)
    for duration, control, noise in zip(arrays['dt'], arrays['H'], operators):
        control_generator = liouvillian(control)
        dissipator = np.zeros_like(control_generator)
        for operator in noise:
            generator = liouvillian(operator)
            dissipator += generator @ generator / 2
        step = duration / split
        ideal_increment, quadratic_increment = expm_frechet(control_generator * step,
                                                           dissipator * step)
        increment = expm((control_generator + dissipator) * step)
        for subdivision in range(split):
            channel = increment @ channel
            quadratic = ideal_increment @ quadratic + quadratic_increment @ ideal
            ideal = ideal_increment @ ideal
    return channel, ideal.conj().T @ quadratic


def predict(case, arrays, mode='selected'):
    if mode == 'baseline':
        from .baseline import predict as baseline_predict
        return baseline_predict(case, arrays, mode)
    started = time.perf_counter()
    deadline = started + 85
    kind = case['noise']['kind']
    if kind not in ('static', 'ou', 'broadband', 'telegraph', 'white'):
        raise ValueError(f'Unsupported physical noise law: {kind}')
    operators, rates = prepare(case, arrays)
    reset = mode == 'no_memory'
    refined = mode == 'refined'
    split = 2 if refined else 1
    diagnostics = dict(noise_law=kind, latent_count=len(rates), memory_reset=reset,
                       segments=len(arrays['dt']), dimension=arrays['H'].shape[-1],
                       exponential_substeps=split, convergence=[])
    ideal = ideal_channel(arrays)
    if len(rates) == 0:
        diagnostics['method'] = 'no_effective_noise'
        return ideal, np.zeros_like(ideal), diagnostics
    if kind == 'white':
        channel, quadratic = white_channel(arrays, operators, split)
        diagnostics['method'] = 'exact_stratonovich_lindblad'
        return channel, quadratic, diagnostics
    quadratic = response(arrays, operators, rates, reset, split)
    telegraph = kind == 'telegraph'
    if telegraph and 2 ** len(rates) <= 256 and 2 ** len(rates) * ideal.size < 1e6:
        try:
            channel, count = hierarchy(arrays, operators, rates, None, reset, True, split, deadline)
            diagnostics.update(method='exact_telegraph_stochastic_liouville', bath_states=count)
            return channel, quadratic, diagnostics
        except TimeoutError:
            diagnostics['resource_warning'] = 'Exact bath exceeded the 85-second solver budget.'
    bound = envelope_bound(arrays, operators, rates, reset)
    norm = np.linalg.norm(quadratic)
    if bound < 1:
        remainder = np.expm1(bound) - bound
        absolute_bound = arrays['H'].shape[-1] * remainder
        weak_bound = 2 * absolute_bound / max(norm - absolute_bound, 1e-15)
    else:
        weak_bound = float('inf')
    diagnostics.update(gaussian_dyson_bound=bound,
                       weak_relative_error_bound=weak_bound if np.isfinite(weak_bound) else None)
    if not refined and weak_bound < 2e-4:
        diagnostics.update(method='bounded_second_cumulant',
                           approximation='Phi0 exp(k2); ordered coherent response retained')
        return ideal @ expm(quadratic), quadratic, diagnostics
    if bound < 0.03:
        tail = bound ** 3 / 6
        term = tail
        for order in range(4, 14):
            term *= bound / order
            tail += term
        omitted_bound = arrays['H'].shape[-1] * tail / max(
            norm - arrays['H'].shape[-1] * (np.expm1(bound) - bound), 1e-15)
        fourth_states = (1 + len(rates) + math.comb(len(rates), 2) if telegraph else
                         math.comb(len(rates) + 2, 2))
        if (omitted_bound < (2e-9 if refined else 2e-6) and fourth_states <= 3000
                and fourth_states * ideal.size <= 6e6):
            try:
                channel, count = hierarchy(arrays, operators, rates, 2, reset, telegraph, 1, deadline)
            except TimeoutError:
                diagnostics.update(method='budget_limited_second_cumulant', converged=False,
                                   resource_warning='Fourth-order refinement exceeded solver budget.')
                return ideal @ expm(quadratic), quadratic, diagnostics
            diagnostics.update(method=('bounded_fourth_order_walsh' if telegraph else
                                       'bounded_fourth_order_hermite'), hierarchy_degree=2,
                               bath_states=count, converged=True,
                               hierarchy_exponential_substeps=1,
                               hierarchy_relative_truncation_bound=omitted_bound,
                               convergence_basis='Gaussian Dyson tail, exact through fourth order')
            return channel, quadratic, diagnostics
    tolerance = 2e-8 if refined else 2e-6
    diagnostics['convergence_tolerance'] = tolerance
    previous = None
    converged = False
    channel = ideal @ expm(quadratic)
    if kind == 'static' and len(rates) <= 3:
        orders = [14, 20, 28, 38, 50] if refined else [10, 14, 20, 28, 38]
        completed_order = None
        count = 0
        for order in orders:
            if order ** len(rates) > 70000:
                break
            try:
                candidate, candidate_count = static_quadrature(arrays, operators, order, reset, deadline)
            except TimeoutError:
                diagnostics['resource_warning'] = 'Quadrature stopped at the 85-second solver budget.'
                break
            channel, count = candidate, candidate_count
            completed_order = order
            residual = (None if previous is None else float(np.linalg.norm(channel - previous)
                        / max(np.linalg.norm(channel - ideal), 1e-10)))
            diagnostics['convergence'].append(dict(order=order, nodes=count, relative_change=residual))
            if residual is not None and residual < tolerance:
                converged = True
                break
            previous = channel
            if time.perf_counter() - started > 55:
                break
        diagnostics.update(method='stationary_gaussian_quadrature', quadrature_order=completed_order,
                           quadrature_nodes=count, converged=converged)
    else:
        degrees = ([2, 3, 4, 6, 8, 12, 16, 20] if bound < 0.03 else
                   ([3, 4, 5, 6, 8, 10, 12, 16] if len(rates) >= 4 else
                    ([10, 14, 18, 24, 30] if refined else [8, 12, 16, 22, 28])))
        completed_degree = None
        count = 0
        for degree in degrees:
            bath_count = (sum(math.comb(len(rates), tier) for tier in range(min(degree, len(rates)) + 1))
                          if telegraph else math.comb(len(rates) + degree, degree))
            if bath_count > 3000 or bath_count * ideal.shape[0] ** 2 > 6e6:
                break
            try:
                candidate, candidate_count = hierarchy(arrays, operators, rates, degree,
                                                       reset, telegraph, split, deadline)
            except TimeoutError:
                diagnostics['resource_warning'] = 'Hierarchy stopped at the 85-second solver budget.'
                break
            channel, count = candidate, candidate_count
            completed_degree = degree
            residual = (None if previous is None else float(np.linalg.norm(channel - previous)
                        / max(np.linalg.norm(channel - ideal), 1e-10)))
            diagnostics['convergence'].append(dict(degree=degree, bath_states=count,
                                                   relative_change=residual))
            if residual is not None and residual < tolerance:
                converged = True
                break
            if telegraph and degree >= len(rates):
                converged = True
                break
            previous = channel
            if time.perf_counter() - started > 55:
                break
        minimum_states = (1 + len(rates) + math.comb(len(rates), 2) if telegraph else
                          math.comb(len(rates) + 2, 2))
        if (completed_degree is None and time.perf_counter() < deadline
                and minimum_states <= 3000 and minimum_states * ideal.size <= 6e6):
            try:
                channel, count = hierarchy(arrays, operators, rates, 2, reset, telegraph, split, deadline)
                completed_degree = 2
            except TimeoutError:
                diagnostics['resource_warning'] = 'Initial hierarchy exceeded solver budget; cumulant fallback.'
        diagnostics.update(method=('telegraph_walsh_stochastic_liouville' if telegraph else
                                   'gaussian_hermite_stochastic_liouville'), hierarchy_degree=completed_degree,
                           bath_states=count, converged=converged)
    if not converged:
        diagnostics['accuracy_warning'] = 'Finite-noise channel did not meet the convergence target; k2 is separate.'
        if count == 0:
            diagnostics['method'] = 'budget_limited_second_cumulant'
    return channel, quadratic, diagnostics
