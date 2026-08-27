import numpy as np
from scipy.linalg import eigh
from scipy.sparse import eye
from scipy.sparse.linalg import splu
from scipy.optimize import brentq
from .model import matrices, extend
from .reservoirs import fermi, surface, band_samples


class SpectralProblem:
    def __init__(self, case, tolerance):
        self.case = case
        self.central, self.leads = matrices(case)
        self.identity = np.eye(len(self.central))
        self.tolerance = tolerance
        self.cache = {}
        self.ranges = []
        self.diagonal = []
        self.edges = []
        for cell, hop, contact in self.leads:
            momenta, bands = band_samples(cell, hop, 513)
            ranges = [(float(np.min(bands[:, band])), float(np.max(bands[:, band]))) for band in range(len(cell))]
            self.ranges.append(ranges)
            self.edges.extend(value for interval in ranges for value in interval)
            coefficient = np.trace(hop) / len(hop)
            if np.max(abs(hop - coefficient * np.eye(len(hop)))) < 1e-12:
                values, vectors = eigh(cell)
                self.diagonal.append((values, vectors, abs(coefficient)))
            else:
                self.diagonal.append(None)

    def lead_surface(self, energy, index):
        simple = self.diagonal[index]
        if simple is None:
            cell, hop, contact = self.leads[index]
            return surface(energy, cell, hop, eta=1e-10)
        values, vectors, hopping = simple
        shifted = energy + 1e-10j - values
        root = np.sqrt(shifted ** 2 - 4 * hopping ** 2)
        root = np.where(root.imag < 0, -root, root)
        roots = (shifted - root) / (2 * hopping ** 2)
        return (vectors * roots) @ vectors.conj().T

    def propagating(self, energy, index):
        return any(lower < energy < upper for lower, upper in self.ranges[index])

    def evaluate(self, energy):
        key = float(energy)
        if key in self.cache:
            return self.cache[key]
        sigmas = []
        gammas = []
        greens = []
        for index, (cell, hop, contact) in enumerate(self.leads):
            green = self.lead_surface(energy, index)
            greens.append(green)
            sigma = contact @ green @ contact.conj().T
            sigmas.append(sigma)
            gamma = 1j * (sigma - sigma.conj().T)
            if not self.propagating(energy, index):
                gamma *= 0
            spec = self.case['leads'][index]
            gammas.append(gamma * fermi(energy, spec['mu'], spec['temperature']))
        resolvent = np.linalg.inv((energy + 1e-10j) * self.identity - self.central - sum(sigmas))
        spectral = resolvent @ sum(gammas) @ resolvent.conj().T / (2 * np.pi)
        result = spectral, greens
        self.cache[key] = result
        return result

    def quadrature(self, tmax, order=12):
        lower, upper = min(self.edges), max(self.edges)
        endpoints = [lower, upper] + self.edges
        for spec in self.case['leads']:
            endpoints.extend([spec['mu'] + multiple * spec['temperature'] for multiple in [-12, -4, 0, 4, 12]])
        endpoints.extend(np.linalg.eigvalsh(self.central).tolist())
        endpoints = sorted(set(float(value) for value in endpoints if lower <= value <= upper))
        nodes_small, weights_small = np.polynomial.legendre.leggauss(order)
        nodes_large, weights_large = np.polynomial.legendre.leggauss(2 * order)
        nodes = []
        weights = []
        def refine(begin, end, left_angle, right_angle, depth):
            integrals = []
            for rule_nodes, rule_weights in [(nodes_small, weights_small), (nodes_large, weights_large)]:
                angles = (left_angle + right_angle) / 2 + rule_nodes * (right_angle - left_angle) / 2
                energies = begin + (end - begin) * (1 - np.cos(angles)) / 2
                measures = rule_weights * (right_angle - left_angle) / 2 * (end - begin) * np.sin(angles) / 2
                values = [self.evaluate(float(energy))[0] for energy in energies]
                integrals.append(np.einsum('a,aij->ij', measures, values))
            discrepancy = np.max(abs(integrals[1] - integrals[0]))
            threshold = self.tolerance * ((end - begin) * (right_angle - left_angle) / (upper - lower) + np.max(abs(integrals[1])))
            if discrepancy > threshold and depth < 12:
                midpoint = (left_angle + right_angle) / 2
                refine(begin, end, left_angle, midpoint, depth + 1)
                refine(begin, end, midpoint, right_angle, depth + 1)
            else:
                nodes.extend(energies.tolist())
                weights.extend(measures.tolist())
        for begin, end in zip(endpoints[:-1], endpoints[1:]):
            if end - begin < 1e-9:
                continue
            count = max(1, int(np.ceil((end - begin) * tmax / 12)))
            angles = np.linspace(0, np.pi, count + 1)
            for left_angle, right_angle in zip(angles[:-1], angles[1:]):
                refine(begin, end, left_angle, right_angle, 0)
        return np.asarray(nodes), np.asarray(weights)


def scalar_bound_states(case, hamiltonian, interfaces, ends):
    central, leads = matrices(case)
    if not leads or not all(len(cell) == 1 for cell, hop, contact in leads):
        return None
    lower = min(float(cell[0, 0].real - 2 * abs(hop[0, 0])) for cell, hop, contact in leads)
    upper = max(float(cell[0, 0].real + 2 * abs(hop[0, 0])) for cell, hop, contact in leads)
    margin = float(np.linalg.norm(central, np.inf) + sum(np.linalg.norm(contact, np.inf) for cell, hop, contact in leads) + abs(lower) + abs(upper) + 8)
    identity = np.eye(len(central))
    def embedded(energy):
        effective = central.copy()
        derivative = np.zeros_like(central)
        surfaces = []
        for cell, hop, contact in leads:
            displacement = energy - cell[0, 0].real
            hopping = abs(hop[0, 0])
            root = np.sign(displacement) * np.sqrt(displacement ** 2 - 4 * hopping ** 2)
            green = (displacement - root) / (2 * hopping ** 2)
            slope = (1 - displacement / root) / (2 * hopping ** 2)
            effective += (contact @ contact.conj().T) * green
            derivative += (contact @ contact.conj().T) * slope
            surfaces.append(green)
        return energy * identity - effective, derivative, surfaces
    roots = []
    for begin, end in [(lower - margin, lower - 1e-12), (upper + 1e-12, upper + margin)]:
        initial_values = np.linalg.eigvalsh(embedded(begin)[0])
        final_values = np.linalg.eigvalsh(embedded(end)[0])
        for branch in range(len(central)):
            if initial_values[branch] * final_values[branch] < 0:
                def residual(energy):
                    return np.linalg.eigvalsh(embedded(energy)[0])[branch]
                root = brentq(residual, begin, end, xtol=2e-14)
                if not any(abs(root - previous) < 1e-9 for previous in roots):
                    roots.append(root)
    energies = []
    states = []
    for energy in sorted(roots):
        matrix, derivative, surfaces = embedded(energy)
        values, vectors = eigh(matrix)
        nullspace = vectors[:, abs(values) < 1e-9]
        metric = nullspace.conj().T @ (identity - derivative) @ nullspace
        values, basis = eigh(metric)
        normalized = nullspace @ (basis / np.sqrt(values)) @ basis.conj().T
        full = np.zeros((hamiltonian.shape[0], normalized.shape[1]), dtype=complex)
        full[:len(central)] = normalized
        for (cell, hop, contact), green, first, last in zip(leads, surfaces, interfaces, ends):
            count = int(last[-1] - first[0] + 1)
            first_cell = green * (contact.conj().T @ normalized)
            full[int(first[0]):int(last[-1]) + 1] = (green * hop[0, 0]) ** np.arange(count)[:, None] * first_cell
        states.append(full)
        energies.extend([energy] * normalized.shape[1])
    vectors = np.hstack(states) if states else np.empty((hamiltonian.shape[0], 0), dtype=complex)
    return np.asarray(energies), vectors, lower, upper


def prepare(case, hamiltonian, interfaces, ends, config):
    dimension = hamiltonian.shape[0]
    central_size = len(case['hamiltonian']['real'])
    bound_hamiltonian = hamiltonian
    bound_ends = ends
    restriction = np.arange(dimension)
    if ends:
        physical_cells = int((ends[0][-1] - interfaces[0][0] + 1) / len(ends[0]))
        stationary_cells = max(physical_cells, config.get('stationary_cells', 128))
        if any(np.linalg.matrix_rank(hop) < len(hop) for cell, hop, contact in matrices(case)[1]):
            stationary_cells = max(stationary_cells, config.get('singular_stationary_cells', 256))
        if stationary_cells > physical_cells:
            bound_hamiltonian, bound_interfaces, bound_ends = extend(case, stationary_cells)
            restriction = np.concatenate([np.arange(central_size)] + [np.arange(first[0], first[0] + physical_cells * len(first)) for first in bound_interfaces])
    energies, vectors = eigh(bound_hamiltonian.toarray(), check_finite=False)
    if not ends:
        weights = fermi(energies, case['bound_mu'], case['bound_temperature'])
        occupied = weights > 1e-13
        return energies[occupied], vectors[:, occupied] * np.sqrt(weights[occupied]), {'bound_states': len(energies), 'continuum_states': 0}
    end_indices = np.concatenate(bound_ends)
    end_weight = np.sum(abs(vectors[end_indices]) ** 2, axis=0)
    central_weight = np.sum(abs(vectors[:central_size]) ** 2, axis=0)
    bound = (end_weight < 2e-13) & (central_weight > 1e-5)
    scalar_states = scalar_bound_states(case, hamiltonian, interfaces, ends)
    if scalar_states is not None:
        scalar_energies, scalar_vectors, scalar_lower, scalar_upper = scalar_states
        bound &= (energies > scalar_lower) & (energies < scalar_upper)
    bound_weights = fermi(energies, case['bound_mu'], case['bound_temperature'])
    occupied = bound & (bound_weights > 1e-13)
    if not config.get('include_bound', True):
        occupied[:] = False
    wavefunctions = [vectors[restriction][:, occupied] * np.sqrt(bound_weights[occupied])]
    mode_energies = list(energies[occupied])
    extra_count = 0
    extra_occupied_count = 0
    if scalar_states is not None:
        extra_count = len(scalar_energies)
        scalar_weights = fermi(scalar_energies, case['bound_mu'], case['bound_temperature'])
        scalar_selected = (scalar_weights > 1e-13) & config.get('include_bound', True)
        wavefunctions.append(scalar_vectors[:, scalar_selected] * np.sqrt(scalar_weights[scalar_selected]))
        mode_energies.extend(scalar_energies[scalar_selected].tolist())
        extra_occupied_count = int(np.sum(scalar_selected))
    problem = SpectralProblem(case, config['quadrature_tolerance'])
    nodes, weights = problem.quadrature(max(case['times']), config['order'])
    identity = eye(dimension, dtype=complex, format='csc')
    for energy, weight in zip(nodes, weights):
        effective = ((energy + 1e-10j) * identity - hamiltonian).tolil()
        injection = []
        for index, ((cell, hop, contact), ending) in enumerate(zip(problem.leads, ends)):
            green = problem.lead_surface(energy, index)
            sigma = hop.conj().T @ green @ hop
            effective[np.ix_(ending, ending)] -= sigma
            spec = case['leads'][index]
            occupation = fermi(energy, spec['mu'], spec['temperature'])
            if occupation < 1e-13 or not problem.propagating(energy, index):
                continue
            gamma = 1j * (sigma - sigma.conj().T)
            values, basis = eigh(gamma, check_finite=False)
            selected = values > 1e-7
            sources = np.zeros((dimension, int(np.sum(selected))), dtype=complex)
            sources[ending] = basis[:, selected] * np.sqrt(values[selected] * occupation * weight / (2 * np.pi))
            injection.append(sources)
        if injection:
            rhs = np.hstack(injection)
            solved = splu(effective.tocsc()).solve(rhs)
            wavefunctions.append(solved)
            mode_energies.extend([float(energy)] * rhs.shape[1])
    state = np.ascontiguousarray(np.hstack(wavefunctions))
    return np.asarray(mode_energies), state, {'bound_states': int(np.sum(bound)) + extra_count, 'occupied_bound_states': int(np.sum(occupied)) + extra_occupied_count, 'continuum_states': state.shape[1] - int(np.sum(occupied)) - extra_occupied_count, 'quadrature_nodes': len(nodes), 'analytic_bound_energies': scalar_energies.tolist() if scalar_states is not None else []}
