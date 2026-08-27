import numpy as np
from scipy.linalg import eigh, lu_factor, lu_solve
from scipy.optimize import minimize_scalar
from numpy.polynomial.legendre import leggauss
from .model import matrices, extend
from .reservoirs import fermi, surface


def bound_occupation(energies, chemical_potential, temperature):
    weights = fermi(energies, chemical_potential, temperature)
    if temperature == 0:
        tolerance = 32 * np.finfo(float).eps * np.maximum(1., np.maximum(abs(energies), abs(chemical_potential)))
        weights = np.where(abs(energies - chemical_potential) <= tolerance, 0., weights)
    return weights


def band_edges(cell, hop):
    momenta = np.linspace(-np.pi, np.pi, 513)

    def bands(momentum):
        return np.linalg.eigvalsh(cell + np.exp(-1j * momentum) * hop +
                                 np.exp(1j * momentum) * hop.conj().T)

    values = np.asarray([bands(momentum) for momentum in momenta])
    edges, intervals = [], []
    for band in range(len(cell)):
        if np.ptp(values[:, band]) < 1e-10:
            edges.append(float(np.mean(values[:, band])))
            continue
        first_edge = len(edges)
        edges.extend([float(values[0, band]), float(values[-1, band])])
        for index in range(1, len(momenta) - 1):
            previous = values[index, band] - values[index - 1, band]
            following = values[index + 1, band] - values[index, band]
            if previous * following <= 0:
                sign = 1 if previous <= 0 else -1
                result = minimize_scalar(lambda momentum: sign * bands(momentum)[band],
                                         bounds=(momenta[index - 1], momenta[index + 1]),
                                         method='bounded', options={'xatol': 1e-13})
                edges.append(float(sign * result.fun))
        previous = values[0, band] - values[-2, band]
        following = values[1, band] - values[0, band]
        if previous * following <= 0:
            sign = 1 if previous <= 0 else -1
            spacing = momenta[1] - momenta[0]
            result = minimize_scalar(lambda momentum: sign * bands(momentum)[band],
                                     bounds=(momenta[0] - spacing, momenta[0] + spacing),
                                     method='bounded', options={'xatol': 1e-13})
            edges.append(float(sign * result.fun))
        intervals.append((min(edges[first_edge:]), max(edges[first_edge:])))
    return edges, intervals


def surface_function(cell, hop, eta=1e-10):
    scalar = np.trace(hop) / len(hop)
    if np.max(abs(hop - scalar * np.eye(len(hop)))) < 1e-13 and abs(scalar) > 1e-14:
        eigenvalues, vectors = eigh(cell)

        def evaluate(energy):
            shifted = energy - eigenvalues
            root = np.sqrt((shifted * shifted - 4 * abs(scalar) ** 2).astype(complex))
            root = np.where((shifted < 0) & (abs(shifted) >= 2 * abs(scalar)), -root, root)
            diagonal = 2 / (shifted + root)
            return (vectors * diagonal) @ vectors.conj().T

        return evaluate
    return lambda energy: surface(energy, cell, hop, eta=eta)


def localized_states(case, hamiltonian, active, interfaces, ends, config):
    dense = hamiltonian.toarray()
    if np.max(abs(dense.imag)) < 1e-14:
        dense = dense.real
    energies, vectors = eigh(dense, check_finite=False, overwrite_a=True)
    tail = []
    for interface, end in zip(interfaces, ends):
        width = len(interface)
        count = (int(end[-1]) + 1 - int(interface[0])) // width
        start = int(interface[0]) + int(0.75 * count) * width
        tail.extend(range(start, int(end[-1]) + 1))
    tail = np.asarray(tail, dtype=int)
    retained_energies, retained_vectors, leakages, candidates = [], [], [], []
    start = 0
    while start < len(energies):
        stop = start + 1
        while stop < len(energies) and abs(energies[stop] - energies[start]) < 2e-10:
            stop += 1
        block = vectors[:, start:stop]
        for column in range(block.shape[1]):
            if np.sum(abs(block[active, column]) ** 2) > 1e-8:
                candidates.append((float(energies[start + column]), block[active, column].copy()))
        if stop - start > 1:
            if len(tail):
                leakage, rotation = eigh(block[tail].conj().T @ block[tail], check_finite=False)
                block = block @ rotation[:, leakage < config['bound_tail_tolerance']]
            if block.shape[1]:
                local_weight, rotation = eigh(block[active].conj().T @ block[active], check_finite=False)
                block = block @ rotation[:, local_weight > 1e-12]
        if block.shape[1]:
            leakage = np.sum(abs(block[tail]) ** 2, axis=0) if len(tail) else np.zeros(block.shape[1])
            local_weight = np.sum(abs(block[active]) ** 2, axis=0)
            selected = (leakage < config['bound_tail_tolerance']) & (local_weight > 1e-12)
            for column in np.flatnonzero(selected):
                retained_energies.append(float(np.mean(energies[start:stop])))
                retained_vectors.append(block[active, column])
                leakages.append(float(leakage[column]))
        start = stop
    bound_vectors = np.asarray(retained_vectors, dtype=complex).T if retained_vectors else np.zeros((len(active), 0), complex)
    return np.asarray(retained_energies), bound_vectors, leakages, candidates


def repair_shallow_bound_states(local_hamiltonian, leads, surfaces, offsets, edges,
                                candidates, energies, vectors, deficit):
    dimension = len(local_hamiltonian)

    def self_energy(energy):
        sigma = np.zeros((dimension, dimension), complex)
        for index, (cell, hop, contact) in enumerate(leads):
            begin, end = offsets[index:index + 2]
            sigma[begin:end, begin:end] = hop.conj().T @ surfaces[index](energy) @ hop
        return sigma

    candidate_list = list(candidates)
    for edge in edges:
        for sign in [-1, 1]:
            energy = edge + sign * 1e-7 * max(1., abs(edge))
            sigma = self_energy(energy)
            values, states = eigh(local_hamiltonian + (sigma + sigma.conj().T) / 2,
                                  check_finite=False)
            for index in np.flatnonzero(abs(values - energy) < .3):
                candidate_list.append((energy, states[:, index]))
    added_energies, added_vectors, residuals = [], [], []

    def propagating_weight(sigma, vector):
        gamma_values, gamma_vectors = eigh(1j * (sigma - sigma.conj().T), check_finite=False)
        selected = gamma_values > max(1e-6, np.max(gamma_values) * 1e-9)
        return float(np.sum(gamma_values[selected] * abs(gamma_vectors[:, selected].conj().T @ vector) ** 2))

    for energy, local_state in candidate_list:
        vector = local_state / np.linalg.norm(local_state)
        if np.real(np.vdot(vector, deficit @ vector)) < 1e-7:
            continue
        sigma = self_energy(energy)
        gamma = 1j * (sigma - sigma.conj().T)
        if propagating_weight(sigma, vector) > 1e-18:
            continue
        converged = False
        for iteration in range(40):
            sigma = self_energy(energy)
            effective = local_hamiltonian + (sigma + sigma.conj().T) / 2
            values, states = eigh(effective, check_finite=False)
            index = int(np.argmax(abs(states.conj().T @ vector)))
            vector = states[:, index]
            distance = min([abs(energy - edge) for edge in edges] + [1.])
            spacing = min(1e-5 * max(1., abs(energy)), max(1e-9, distance * .001))
            derivative = (self_energy(energy + spacing) - self_energy(energy - spacing)) / (2 * spacing)
            metric = np.eye(dimension) - (derivative + derivative.conj().T) / 2
            normalization = float(np.real(np.vdot(vector, metric @ vector)))
            residual = values[index] - energy
            if normalization <= 0 or not np.isfinite(normalization):
                break
            gamma = 1j * (sigma - sigma.conj().T)
            broadening = float(np.real(np.vdot(vector, gamma @ vector))) / normalization
            if abs(residual) < 2e-11 and broadening < 2e-8 and propagating_weight(sigma, vector) < 1e-18:
                converged = True
                break
            correction = residual / normalization
            if abs(correction) > .25:
                break
            energy += correction
        if not converged:
            continue
        for old_energy, old_vector in zip(list(energies) + added_energies,
                                           list(vectors.T) + added_vectors):
            if abs(energy - old_energy) < 2e-7:
                vector = vector - old_vector * np.vdot(old_vector, metric @ vector)
        normalization = float(np.real(np.vdot(vector, metric @ vector)))
        if normalization < 1e-7:
            continue
        vector = vector / np.sqrt(normalization)
        if np.linalg.norm(vector) < 1e-7:
            continue
        added_energies.append(float(energy))
        added_vectors.append(vector)
        residuals.append(float(abs(residual)))
        deficit -= np.outer(vector, vector.conj())
    added = np.asarray(added_vectors, dtype=complex).T if added_vectors else np.zeros((dimension, 0), complex)
    return np.asarray(added_energies), added, residuals


def prepare_scattering(case, hamiltonian, interfaces, ends, config):
    central, leads = matrices(case)
    size = len(central)
    active = np.concatenate([np.arange(size)] + interfaces)
    local_hamiltonian = hamiltonian[active][:, active].toarray()
    local_size = len(active)
    offsets = np.cumsum([size] + [len(cell) for cell, hop, contact in leads])
    bound_hamiltonian, bound_interfaces, bound_ends = extend(case, config['bound_cells'])
    bound_active = np.concatenate([np.arange(size)] + bound_interfaces)
    bound_energies, bound_vectors, leakages, candidates = localized_states(
        case, bound_hamiltonian, bound_active, bound_interfaces, bound_ends, config)
    bound_weights = bound_occupation(bound_energies, case['bound_mu'], case['bound_temperature'])
    if config['preparation'] == 'averaged_occupations' and leads:
        average_mu = float(np.mean([lead['mu'] for lead in case['leads']]))
        average_temperature = max(lead['temperature'] for lead in case['leads'])
        bound_weights = bound_occupation(bound_energies, average_mu, average_temperature)
    all_energies, all_states = [], []
    total_covariance = bound_vectors @ bound_vectors.conj().T
    bound_selected = bound_weights > 1e-14
    if np.any(bound_selected):
        all_energies.extend(bound_energies[bound_selected].tolist())
        all_states.extend((bound_vectors[:, bound_selected] * np.sqrt(bound_weights[bound_selected])).T)
    surfaces = [surface_function(cell, hop) for cell, hop, contact in leads]
    broad_surfaces = [surface_function(cell, hop, eta=1e-9) for cell, hop, contact in leads]
    generic_surfaces = [np.max(abs(hop - np.trace(hop) / len(hop) * np.eye(len(hop)))) >= 1e-13
                        for cell, hop, contact in leads]
    boundaries, lead_intervals = [], []
    for cell, hop, contact in leads:
        edges, intervals = band_edges(cell, hop)
        boundaries.extend(edges)
        lead_intervals.append(intervals)
    evaluations = 0
    maximum_depth = 0
    accepted_intervals = 0
    estimated_error = 0.

    def sample(energy):
        nonlocal evaluations
        evaluations += 1
        open_leads = [any(low < energy < high for low, high in intervals) for intervals in lead_intervals]
        if not any(open_leads):
            return np.zeros((local_size, 0), complex), np.zeros(0), np.zeros((3, local_size, local_size), complex)
        operator = (energy + 1e-14j) * np.eye(local_size) - local_hamiltonian
        incoming = []
        occupations = []
        for index, (cell, hop, contact) in enumerate(leads):
            sigma = hop.conj().T @ surfaces[index](energy) @ hop
            if not np.all(np.isfinite(sigma)):
                raise FloatingPointError('nonfinite retarded surface at energy ' + str(energy))
            begin, end = offsets[index:index + 2]
            operator[begin:end, begin:end] -= sigma
            if not open_leads[index]:
                continue
            gamma = 1j * (sigma - sigma.conj().T)
            weights, vectors = eigh(gamma, check_finite=False)
            selected = weights > max(2e-8, np.max(weights) * 1e-9)
            if generic_surfaces[index] and np.any(selected):
                broad_sigma = hop.conj().T @ broad_surfaces[index](energy) @ hop
                broad_gamma = 1j * (broad_sigma - broad_sigma.conj().T)
                broad_weights = np.real(np.sum(vectors.conj() * (broad_gamma @ vectors), axis=0))
                selected &= (weights > .4 * broad_weights) & (weights < 2 * broad_weights)
                weights = np.maximum(0., (10 * weights - broad_weights) / 9)
            if not np.any(selected):
                continue
            source = np.zeros((local_size, int(np.sum(selected))), complex)
            source[begin:end] = vectors[:, selected] * np.sqrt(weights[selected] / (2 * np.pi))
            incoming.append(source)
            spec = case['leads'][index]
            if config['preparation'] == 'averaged_occupations':
                occupation = fermi(energy, average_mu, average_temperature)
            else:
                occupation = fermi(energy, spec['mu'], spec['temperature'])
            occupations.extend([float(occupation)] * source.shape[1])
        if not incoming:
            modes = np.zeros((local_size, 0), complex)
        else:
            modes = lu_solve(lu_factor(operator, check_finite=False),
                             np.concatenate(incoming, axis=1), check_finite=False)
        occupations = np.asarray(occupations)
        covariance = modes @ modes.conj().T
        occupied = (modes * occupations) @ modes.conj().T
        features = np.stack([covariance, occupied, covariance * np.exp(-1j * energy * case['times'][-1])])
        return modes, occupations, features

    rules = {order: leggauss(order) for order in (8, 16)}

    def integrate(low, high, left, right, tolerance, depth):
        nonlocal total_covariance, maximum_depth, accepted_intervals, estimated_error
        maximum_depth = max(maximum_depth, depth)
        estimates = []
        fine_samples = []
        for order in (8, 16):
            nodes, weights = rules[order]
            angles = (left + right) / 2 + (right - left) / 2 * nodes
            energies = low + (high - low) * np.sin(angles) ** 2
            coefficients = (right - left) / 2 * weights * (high - low) * np.sin(2 * angles)
            estimate = np.zeros((3, local_size, local_size), complex)
            for energy, coefficient in zip(energies, coefficients):
                modes, occupations, features = sample(energy)
                estimate += coefficient * features
                if order == config['quadrature_output_order']:
                    fine_samples.append((energy, coefficient, modes, occupations))
            estimates.append(estimate)
        error = float(np.max(abs(estimates[1] - estimates[0])))
        if error > tolerance and depth < config['quadrature_max_depth']:
            middle = (left + right) / 2
            integrate(low, high, left, middle, tolerance / 2, depth + 1)
            integrate(low, high, middle, right, tolerance / 2, depth + 1)
            return
        accepted_intervals += 1
        estimated_error += error
        total_covariance += estimates[0 if config['quadrature_output_order'] == 8 else 1][0]
        for energy, coefficient, modes, occupations in fine_samples:
            selected = occupations > 1e-14
            if np.any(selected):
                weighted = modes[:, selected] * np.sqrt(coefficient * occupations[selected])
                all_energies.extend([float(energy)] * weighted.shape[1])
                all_states.extend(weighted.T)

    if boundaries:
        lower, upper = min(boundaries), max(boundaries)
        for energy, vector in candidates:
            if lower < energy < upper and np.sum(abs(vector) ** 2) > .4 and np.all(abs(bound_energies - energy) > 1e-7):
                boundaries.append(energy)
        for spec in case['leads']:
            for shift in [-8, -2, 0, 2, 8]:
                energy = spec['mu'] + shift * spec['temperature']
                if lower < energy < upper:
                    boundaries.append(energy)
        boundaries = sorted(boundaries)
        unique = [boundaries[0]]
        for energy in boundaries[1:]:
            if energy - unique[-1] > 2e-9:
                unique.append(energy)
        for low, high in zip(unique[:-1], unique[1:]):
            tolerance = config['quadrature_tolerance'] * (high - low) / max(upper - lower, 1e-12)
            integrate(low, high, 0, np.pi / 2, tolerance, 0)
    shallow_energies, shallow_residuals = [], []
    deficit = np.eye(local_size) - total_covariance
    if leads and np.max(abs(deficit)) > 3e-6:
        extra_energies, extra_vectors, shallow_residuals = repair_shallow_bound_states(
            local_hamiltonian, leads, surfaces, offsets, boundaries, candidates,
            bound_energies, bound_vectors, deficit.copy())
        shallow_energies = extra_energies.tolist()
        extra_weights = bound_occupation(extra_energies, case['bound_mu'], case['bound_temperature'])
        if config['preparation'] == 'averaged_occupations':
            extra_weights = bound_occupation(extra_energies, average_mu, average_temperature)
        total_covariance += extra_vectors @ extra_vectors.conj().T
        for energy, vector, weight in zip(extra_energies, extra_vectors.T, extra_weights):
            if weight > 1e-14:
                all_energies.append(float(energy))
                all_states.append(vector * np.sqrt(weight))
        bound_energies = np.concatenate([bound_energies, extra_energies])
        bound_weights = np.concatenate([bound_weights, extra_weights])
    initial = np.asarray(all_states, dtype=complex).T if all_states else np.zeros((local_size, 0), complex)
    metadata = dict(initialization='lead_resolved_scattering_plus_localized_spectrum',
                    initial_states=len(all_energies), quadrature_evaluations=evaluations,
                    quadrature_intervals=accepted_intervals, quadrature_max_depth=maximum_depth,
                    quadrature_error_estimate=estimated_error,
                    spectral_sum_rule_error=float(np.max(abs(total_covariance - np.eye(local_size)))),
                    bound_energies=bound_energies.tolist(), bound_occupations=bound_weights.tolist(),
                    bound_tail_weights=leakages, active_dimension=local_size,
                    nonlinear_bound_energies=shallow_energies, nonlinear_bound_residuals=shallow_residuals)
    metadata['accuracy_warning'] = metadata['spectral_sum_rule_error'] > 1e-5 or maximum_depth >= config['quadrature_max_depth']
    return np.asarray(all_energies), initial, active, metadata
