import json
import math
import os
import sys
import time
from contextlib import nullcontext

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import numpy as np
from scipy import linalg, sparse
from scipy.optimize import least_squares
from scipy.sparse.linalg import expm_multiply

try:
    from threadpoolctl import threadpool_limits
except ImportError:
    threadpool_limits = None


def local_operators(spin):
    link_dim = int(round(2 * spin + 1))
    flux_values = np.arange(link_dim, dtype=float) - spin
    raising = np.zeros((link_dim, link_dim))
    for index in range(link_dim - 1):
        raising[index + 1, index] = np.sqrt(
            spin * (spin + 1) - flux_values[index] * (flux_values[index] + 1)
        )
    lower = np.array([[0.0, 1.0], [0.0, 0.0]])
    return {
        "identity": np.eye(2 * link_dim),
        "number": np.kron(np.diag([0.0, 1.0]), np.eye(link_dim)),
        "flux": np.kron(np.eye(2), np.diag(flux_values)),
        "lower": np.kron(lower, np.eye(link_dim)),
        "assisted": np.kron(lower, raising),
        "flip": np.kron(np.eye(2), raising + raising.T)
        / np.sqrt(spin * (spin + 1)),
    }


def local_terms(settings, parameters):
    length = settings["length"]
    spin = settings["spin"]
    pair_error, link_error, mass_shift = parameters
    operators = local_operators(spin)
    identity = operators["identity"]
    number = operators["number"]
    flux = operators["flux"]
    sites = []
    bonds = []
    profile = settings.get("profile", [0.0] * length)
    coefficients = settings.get("coefficients", [1.0] * length)
    for site in range(length):
        term = (settings["mass"] + profile[site] + mass_shift) * number
        term = term + settings["electric"] * (flux @ flux) / 2
        term = term + link_error * operators["flip"]
        if site == 0:
            generator = flux + number - spin * identity
            protection = (
                generator @ generator
                if settings["protection"] == "full"
                else coefficients[site] * generator
            )
            term = term + settings["V"] * protection
        sites.append(term)
    hopping = -settings["J"] / np.sqrt(spin * (spin + 1)) * np.kron(
        operators["assisted"], operators["lower"]
    )
    hopping = hopping + pair_error * np.kron(operators["lower"], operators["lower"])
    hopping = hopping + hopping.T
    for site in range(length - 1):
        generator = (-1) ** (site + 1) * (
            np.kron(flux, identity) + np.kron(identity, flux + number)
        )
        protection = (
            generator @ generator
            if settings["protection"] == "full"
            else coefficients[site + 1] * generator
        )
        term = hopping + settings["V"] * protection
        term = term + np.kron(identity, sites[site + 1])
        if site == 0:
            term = term + np.kron(sites[0], identity)
        bonds.append(term)
    return sites, bonds, operators


class ExactModel:
    def __init__(self, settings, pairs):
        self.settings = settings
        self.pairs = pairs
        length = settings["length"]
        spin = settings["spin"]
        link_dim = int(round(2 * spin + 1))
        local_dim = 2 * link_dim
        dimension = local_dim ** length
        all_indices = np.arange(dimension, dtype=np.int64)
        powers = local_dim ** np.arange(length - 1, -1, -1, dtype=np.int64)
        all_digits = (all_indices[:, None] // powers[None, :]) % local_dim
        keep = np.sum(all_digits // link_dim, axis=1) % 2 == 0
        indices = all_indices[keep]
        digits = all_digits[keep]
        numbers = (digits // link_dim).astype(float)
        flux = (digits % link_dim).astype(float) - spin
        inverse = np.full(dimension, -1, dtype=np.int64)
        inverse[indices] = np.arange(len(indices))
        generators = flux + numbers
        generators[:, 0] -= spin
        generators[:, 1:] += flux[:, :-1]
        self.numbers = numbers
        self.violation = generators ** 2
        self.pair_numbers = np.array(
            [numbers[:, left] * numbers[:, right] for left, right in pairs]
        ).reshape(len(pairs), len(indices)).T
        profile = np.asarray(settings.get("profile", [0.0] * length))
        diagonal = numbers @ (settings["mass"] + profile)
        diagonal += settings["electric"] / 2 * np.sum(flux ** 2, axis=1)
        if settings["protection"] == "full":
            diagonal += settings["V"] * self.violation.sum(axis=1)
        else:
            coefficients = np.asarray(settings["coefficients"])
            diagonal += settings["V"] * (generators @ (coefficients * (-1.0) ** np.arange(length)))
        count = len(indices)
        fixed = sparse.diags(diagonal, format="csr")
        mass = sparse.diags(numbers.sum(axis=1), format="csr")
        rows = {"link": [], "pair": [], "hop": []}
        columns = {"link": [], "pair": [], "hop": []}
        values = {"link": [], "pair": [], "hop": []}
        scale = np.sqrt(spin * (spin + 1))
        for site in range(length):
            allowed = flux[:, site] < spin
            source = np.flatnonzero(allowed)
            target = inverse[indices[source] + powers[site]]
            amplitude = np.sqrt(
                spin * (spin + 1) - flux[source, site] * (flux[source, site] + 1)
            ) / scale
            rows["link"].extend([source, target])
            columns["link"].extend([target, source])
            values["link"].extend([amplitude, amplitude])
            if site == length - 1:
                continue
            source = np.flatnonzero((numbers[:, site] == 1) & (numbers[:, site + 1] == 1))
            target = inverse[indices[source] - link_dim * (powers[site] + powers[site + 1])]
            amplitude = np.ones(len(source))
            rows["pair"].extend([source, target])
            columns["pair"].extend([target, source])
            values["pair"].extend([amplitude, amplitude])
            source = source[flux[source, site] < spin]
            target = inverse[
                indices[source] - link_dim * (powers[site] + powers[site + 1]) + powers[site]
            ]
            amplitude = -settings["J"] * np.sqrt(
                spin * (spin + 1) - flux[source, site] * (flux[source, site] + 1)
            ) / scale
            rows["hop"].extend([source, target])
            columns["hop"].extend([target, source])
            values["hop"].extend([amplitude, amplitude])
        matrices = {}
        for name in rows:
            if rows[name]:
                matrices[name] = sparse.coo_matrix(
                    (np.concatenate(values[name]), (np.concatenate(rows[name]), np.concatenate(columns[name]))),
                    shape=(count, count),
                ).tocsr()
            else:
                matrices[name] = sparse.csr_matrix((count, count))
        self.parts = [fixed + matrices["hop"], matrices["pair"], matrices["link"], mass]
        self.dense = count <= 900
        if self.dense:
            self.parts = [part.toarray() for part in self.parts]
        initial_index = sum((link_dim - 1 if site % 2 == 0 else 0) * powers[site] for site in range(length))
        self.initial = np.zeros(count)
        self.initial[inverse[initial_index]] = 1.0

    def simulate(self, parameters, times):
        hamiltonian = self.parts[0].copy()
        for parameter, part in zip(parameters, self.parts[1:]):
            hamiltonian = hamiltonian + parameter * part
        times = np.asarray(times, dtype=float)
        if self.dense:
            energies, vectors = linalg.eigh(hamiltonian, check_finite=False, driver="evd")
            states = (np.exp(-1j * np.outer(times, energies)) * (vectors.T @ self.initial)) @ vectors.T
        else:
            states = []
            state = self.initial.astype(complex)
            previous = 0.0
            for target in times:
                interval = target - previous
                if interval:
                    state = expm_multiply(-1j * interval * hamiltonian, state)
                states.append(state.copy())
                previous = target
            states = np.asarray(states)
        probabilities = abs(states) ** 2
        density = probabilities @ self.numbers
        violation = probabilities @ self.violation
        correlation = probabilities @ self.pair_numbers
        for index, (left, right) in enumerate(self.pairs):
            correlation[:, index] -= density[:, left] * density[:, right]
        return density, violation, correlation


def fit_parameters(calibrations):
    models = [ExactModel(record["settings"], record["pairs"]) for record in calibrations]
    blocks = ("density", "violation", "correlation")

    def residual(parameters):
        residuals = []
        for model, record in zip(models, calibrations):
            prediction = model.simulate(parameters, record["times"])
            sigma = max(float(record.get("noise_sigma", 2e-6)), 1e-12)
            for name, values in zip(blocks, prediction):
                observed = np.asarray(record["observed"][name]).reshape(values.shape)
                residuals.append(((values - observed) / sigma).ravel())
        return np.concatenate(residuals)

    bounds = ([0.025, 0.025, -0.25], [0.30, 0.30, 0.25])
    result = least_squares(
        residual, [0.13, 0.13, 0.0], bounds=bounds,
        xtol=2e-11, ftol=2e-11, gtol=2e-7, max_nfev=100,
        diff_step=2e-5,
    )
    if np.mean(result.fun ** 2) > 9.0:
        for initial in ([0.08, 0.23, -0.17], [0.23, 0.08, 0.17], [0.2, 0.2, -0.2]):
            candidate = least_squares(
                residual, initial, bounds=bounds, xtol=2e-11,
                ftol=2e-11, gtol=2e-7, max_nfev=100, diff_step=2e-5,
            )
            if candidate.cost < result.cost:
                result = candidate
            if np.mean(result.fun ** 2) <= 9.0:
                break
    return result.x


class MatrixProductEvolution:
    def __init__(self, settings, parameters, max_bond=128, cutoff=1e-11):
        self.settings = settings
        self.length = settings["length"]
        self.max_bond = max_bond
        self.cutoff = cutoff
        self.discarded = 0.0
        self.gate_cache = {}
        self.random = np.random.default_rng(71937)
        self.randomized = os.environ.get("SOLVER_RANDOMIZED", "1") != "0"
        sites, bonds, self.operators = local_terms(settings, parameters)
        self.local_dim = len(self.operators["identity"])
        self.local_parity = np.repeat([0, 1], self.local_dim // 2)
        self.bond_eigen = [linalg.eigh(term, check_finite=False) for term in bonds]
        self.site_eigen = linalg.eigh(sites[0], check_finite=False)
        self.tensors = []
        self.charges = [np.zeros(1, dtype=np.int8) for _ in range(self.length + 1)]
        for site in range(self.length):
            tensor = np.zeros((1, self.local_dim, 1), dtype=complex)
            tensor[0, self.local_dim // 2 - 1 if site % 2 == 0 else 0, 0] = 1.0
            self.tensors.append(tensor)
        physical_charge = (self.local_parity[:, None] + self.local_parity[None, :]) % 2
        self.gate_sectors = [np.flatnonzero(physical_charge.ravel() == charge) for charge in (0, 1)]

    def gates(self, interval):
        key = round(float(interval), 14)
        if key not in self.gate_cache:
            gates = []
            for energies, vectors in self.bond_eigen:
                gate = (vectors * np.exp(-1j * interval * energies)) @ vectors.T
                gates.append([np.ascontiguousarray(gate[np.ix_(sector, sector)]) for sector in self.gate_sectors])
            if len(self.gate_cache) > 40:
                self.gate_cache.clear()
            self.gate_cache[key] = gates
        return self.gate_cache[key]

    def decompose(self, block, force_full=False):
        sample_rank = self.max_bond // 2 + 36
        use_random = self.randomized and not force_full and min(block.shape) >= 192 and sample_rank < 0.65 * min(block.shape)
        if use_random:
            random_vectors = self.random.normal(size=(block.shape[1], sample_rank))
            random_vectors = random_vectors + 1j * self.random.normal(size=random_vectors.shape)
            basis = linalg.qr(block @ random_vectors, mode="economic", check_finite=False)[0]
            adjoint = block.conj().T
            for iteration in range(2):
                alternate = linalg.qr(adjoint @ basis, mode="economic", check_finite=False)[0]
                basis = linalg.qr(block @ alternate, mode="economic", check_finite=False)[0]
            left_vectors, singular, right_vectors = linalg.svd(
                basis.conj().T @ block, full_matrices=False, check_finite=False,
                overwrite_a=True, lapack_driver="gesdd",
            )
            left_vectors = basis @ left_vectors
        else:
            left_vectors, singular, right_vectors = linalg.svd(
                block, full_matrices=False, check_finite=False, overwrite_a=True,
                lapack_driver="gesdd",
            )
        return left_vectors, singular, right_vectors, use_random

    def apply_bond(self, site, gate, direction):
        left_tensor = self.tensors[site]
        right_tensor = self.tensors[site + 1]
        left_dim, local_dim, middle_dim = left_tensor.shape
        right_dim = right_tensor.shape[2]
        row_charge = (self.charges[site][:, None] + self.local_parity[None, :]).ravel() % 2
        column_charge = (self.local_parity[:, None] + self.charges[site + 2][None, :]).ravel() % 2
        row_sectors = [np.flatnonzero(row_charge == charge) for charge in (0, 1)]
        column_sectors = [np.flatnonzero(column_charge == charge) for charge in (0, 1)]
        if middle_dim >= 32:
            theta = np.zeros((left_dim * local_dim, local_dim * right_dim), dtype=complex)
            left_matrix = left_tensor.reshape(left_dim * local_dim, middle_dim)
            right_matrix = right_tensor.reshape(middle_dim, local_dim * right_dim)
            for charge in (0, 1):
                middle = np.flatnonzero(self.charges[site + 1] == charge)
                rows, columns = row_sectors[charge], column_sectors[charge]
                theta[np.ix_(rows, columns)] = left_matrix[np.ix_(rows, middle)] @ right_matrix[np.ix_(middle, columns)]
        else:
            theta = left_tensor.reshape(left_dim * local_dim, middle_dim) @ right_tensor.reshape(middle_dim, local_dim * right_dim)
        physical = theta.reshape(left_dim, local_dim * local_dim, right_dim).transpose(1, 0, 2).reshape(local_dim * local_dim, -1)
        evolved = np.zeros_like(physical)
        boundary_charge = (self.charges[site][:, None] + self.charges[site + 2][None, :]).ravel() % 2
        for charge, (sector, sector_gate) in enumerate(zip(self.gate_sectors, gate)):
            boundary = np.flatnonzero(boundary_charge == charge)
            evolved[np.ix_(sector, boundary)] = sector_gate @ physical[np.ix_(sector, boundary)]
        theta = evolved.reshape(local_dim, local_dim, left_dim, right_dim).transpose(2, 0, 1, 3).reshape(left_dim * local_dim, local_dim * right_dim)
        decompositions = []
        approximate = []
        for charge in (0, 1):
            rows, columns = row_sectors[charge], column_sectors[charge]
            block = theta[np.ix_(rows, columns)]
            if min(block.shape) == 0:
                decompositions.append((rows, columns, None, np.empty(0), None))
                approximate.append(False)
                continue
            left_vectors, singular, right_vectors, randomized = self.decompose(block)
            decompositions.append((rows, columns, left_vectors, singular, right_vectors))
            approximate.append(randomized)
        all_singular = np.concatenate([part[3] for part in decompositions])
        descending = np.sort(all_singular)[::-1]
        provisional_threshold = descending[min(self.max_bond, len(descending)) - 1]
        for charge in (0, 1):
            part = decompositions[charge]
            if approximate[charge] and part[3][-8] >= provisional_threshold:
                rows, columns = part[:2]
                left_vectors, singular, right_vectors, randomized = self.decompose(theta[np.ix_(rows, columns)], force_full=True)
                decompositions[charge] = (rows, columns, left_vectors, singular, right_vectors)
        all_singular = np.concatenate([part[3] for part in decompositions])
        descending = np.sort(all_singular)[::-1]
        total_norm = float(np.vdot(theta, theta).real)
        missing_norm = max(0.0, total_norm - float(np.sum(descending ** 2)))
        tails = np.cumsum(descending[::-1] ** 2)[::-1] + missing_norm
        keep = int(np.searchsorted(-tails, -self.cutoff))
        keep = max(1, min(keep, self.max_bond, len(descending)))
        threshold = descending[keep - 1]
        ranks = [int(np.count_nonzero(part[3] >= threshold)) for part in decompositions]
        while sum(ranks) > keep:
            sector = min((charge for charge in (0, 1) if ranks[charge]), key=lambda charge: decompositions[charge][3][ranks[charge] - 1])
            ranks[sector] -= 1
        kept_norm = sum(float(np.sum(part[3][:rank] ** 2)) for part, rank in zip(decompositions, ranks))
        self.discarded += max(0.0, total_norm - kept_norm)
        normalization = math.sqrt(kept_norm)
        new_left = np.zeros((left_dim * local_dim, keep), dtype=complex)
        new_right = np.zeros((keep, local_dim * right_dim), dtype=complex)
        new_charges = np.empty(keep, dtype=np.int8)
        offset = 0
        for charge, (part, rank) in enumerate(zip(decompositions, ranks)):
            if not rank:
                continue
            rows, columns, left_vectors, singular, right_vectors = part
            positions = np.arange(offset, offset + rank)
            scaled = singular[:rank] / normalization
            if direction == "right":
                new_left[np.ix_(rows, positions)] = left_vectors[:, :rank]
                new_right[np.ix_(positions, columns)] = scaled[:, None] * right_vectors[:rank]
            else:
                new_left[np.ix_(rows, positions)] = left_vectors[:, :rank] * scaled
                new_right[np.ix_(positions, columns)] = right_vectors[:rank]
            new_charges[positions] = charge
            offset += rank
        self.tensors[site] = new_left.reshape(left_dim, local_dim, keep)
        self.tensors[site + 1] = new_right.reshape(keep, local_dim, right_dim)
        self.charges[site + 1] = new_charges

    def second_order_step(self, interval):
        if self.length == 1:
            energies, vectors = self.site_eigen
            gate = (vectors * np.exp(-1j * interval * energies)) @ vectors.T
            self.tensors[0] = (gate @ self.tensors[0].reshape(self.local_dim)).reshape(1, self.local_dim, 1)
            return
        half_gates = self.gates(interval / 2)
        full_gates = self.gates(interval)
        for site in range(self.length - 2):
            self.apply_bond(site, half_gates[site], "right")
        self.apply_bond(self.length - 2, full_gates[-1], "left")
        for site in range(self.length - 3, -1, -1):
            self.apply_bond(site, half_gates[site], "left")

    def step(self, interval, order=4):
        if order == 2:
            self.second_order_step(interval)
        elif order == 4:
            first = 1.0 / (2.0 - 2.0 ** (1.0 / 3.0))
            self.second_order_step(first * interval)
            self.second_order_step((1.0 - 2.0 * first) * interval)
            self.second_order_step(first * interval)
        else:
            first = 1.0 / (4.0 - 4.0 ** (1.0 / 3.0))
            for coefficient in (first, first, 1.0 - 4.0 * first, first, first):
                self.second_order_step(coefficient * interval)

    @staticmethod
    def transfer(environment, tensor, weights=None):
        left_dim, local_dim, right_dim = tensor.shape
        temporary = (environment @ tensor.reshape(left_dim, local_dim * right_dim)).reshape(left_dim, local_dim, right_dim)
        if weights is not None:
            temporary = temporary * weights[None, :, None]
        return tensor.reshape(left_dim * local_dim, right_dim).conj().T @ temporary.reshape(left_dim * local_dim, right_dim)

    def measure(self, pairs):
        number = np.diag(self.operators["number"])
        flux = np.diag(self.operators["flux"])
        charge = number + flux
        density = np.empty(self.length)
        violation = np.empty(self.length)
        flux_squared = np.empty(self.length)
        left_environments = [np.ones((1, 1), dtype=complex)]
        preceding_flux = None
        for site, tensor in enumerate(self.tensors):
            environment = left_environments[-1]
            left_dim, local_dim, right_dim = tensor.shape
            temporary = (environment @ tensor.reshape(left_dim, -1)).reshape(tensor.shape)
            physical_probability = np.einsum("apr,apr->p", tensor.conj(), temporary).real
            density[site] = physical_probability @ number
            flux_squared[site] = physical_probability @ (flux ** 2)
            if site == 0:
                violation[site] = physical_probability @ ((charge - self.settings["spin"]) ** 2)
            else:
                mixed_tensor = (preceding_flux @ tensor.reshape(left_dim, -1)).reshape(tensor.shape)
                mixed = np.einsum("apr,apr,p->", tensor.conj(), mixed_tensor, charge).real
                violation[site] = flux_squared[site - 1] + physical_probability @ (charge ** 2) + 2 * mixed
            adjoint = tensor.reshape(left_dim * local_dim, right_dim).conj().T
            preceding_flux = adjoint @ (temporary * flux[None, :, None]).reshape(left_dim * local_dim, right_dim)
            left_environments.append(adjoint @ temporary.reshape(left_dim * local_dim, right_dim))
        norm = float(left_environments[-1][0, 0].real)
        density /= norm
        violation /= norm
        correlation = np.empty(len(pairs))
        grouped = {}
        for index, (left, right) in enumerate(pairs):
            left, right = min(left, right), max(left, right)
            if left == right:
                correlation[index] = density[left] * (1 - density[left])
            else:
                grouped.setdefault(left, {}).setdefault(right, []).append(index)
        for left, endpoints in grouped.items():
            environment = self.transfer(left_environments[left], self.tensors[left], number)
            for right in range(left + 1, max(endpoints) + 1):
                tensor = self.tensors[right]
                left_dim, local_dim, right_dim = tensor.shape
                temporary = (environment @ tensor.reshape(left_dim, -1)).reshape(tensor.shape)
                if right in endpoints:
                    joint = np.einsum("apr,apr,p->", tensor.conj(), temporary, number).real / norm
                    value = joint - density[left] * density[right]
                    for index in endpoints[right]:
                        correlation[index] = value
                environment = tensor.reshape(left_dim * local_dim, right_dim).conj().T @ temporary.reshape(left_dim * local_dim, right_dim)
        return density, np.maximum(violation, 0.0), correlation


def simulate_chain(settings, parameters, times, pairs, start_time=None):
    length = settings["length"]
    local_dim = int(round(2 * settings["spin"] + 1)) * 2
    if local_dim ** length <= 20000:
        return ExactModel(settings, pairs).simulate(parameters, times)
    start_time = time.monotonic() if start_time is None else start_time
    max_bond = int(os.environ.get("SOLVER_MAX_BOND", 384 if local_dim == 4 else 256))
    cutoff = float(os.environ.get("SOLVER_CUTOFF", 1e-12))
    order = int(os.environ.get("SOLVER_ORDER", 5))
    potential = abs(settings["V"])
    if settings["protection"] == "linear":
        coefficients = np.asarray(settings["coefficients"], dtype=float)
        coefficient_scale = max(1.0, np.max(np.abs(coefficients)))
        if length > 1:
            coefficient_scale = max(coefficient_scale, np.max(np.abs(np.diff(coefficients))))
        potential *= coefficient_scale / 2
    mass_values = settings["mass"] + parameters[2] + np.asarray(settings.get("profile", [0.0] * length))
    local_scale = max(1.0, abs(settings["J"]), 0.5 * np.max(np.abs(mass_values)), 0.5 * abs(settings["electric"]) * settings["spin"])
    base_step = 0.24 if order == 5 else 0.12 if order == 4 else 0.025
    timestep = float(os.environ.get("SOLVER_DT", base_step / (local_scale + 0.16 * potential)))
    budget = float(os.environ.get("SOLVER_TIME_BUDGET", 3300.0))
    evolution = MatrixProductEvolution(settings, parameters, max_bond, cutoff)
    results = [[], [], []]
    current = 0.0
    step_rates = []
    intervals = np.diff(np.concatenate(([0.0], np.asarray(times, dtype=float))))
    step_counts = [max(1, int(math.ceil(interval / timestep - 1e-12))) if interval > 1e-14 else 0 for interval in intervals]
    remaining_steps = sum(step_counts)
    for target, steps in zip(times, step_counts):
        interval = float(target) - current
        step_size = interval / max(1, steps)
        for step_index in range(steps):
            before = time.monotonic()
            evolution.step(step_size, order)
            current += step_size
            duration = time.monotonic() - before
            remaining_steps -= 1
            step_rates.append(duration)
            if len(step_rates) > 3:
                step_rates.pop(0)
            remaining = float(times[-1]) - current
            available = budget - (time.monotonic() - start_time)
            projected = max(step_rates) * remaining_steps
            actual_bond = max(tensor.shape[-1] for tensor in evolution.tensors)
            if len(step_rates) >= 2 and projected > 0.85 * available and evolution.max_bond > 16:
                factor = max(0.60, min(0.95, (max(available, 1.0) * 0.7 / max(projected, 1.0)) ** (1.0 / 3.0)))
                evolution.max_bond = max(16, int(min(evolution.max_bond, actual_bond) * factor))
                step_rates.clear()
            elif len(step_rates) == 3 and projected < 0.5 * available and actual_bond >= 0.95 * evolution.max_bond and evolution.max_bond < max_bond and remaining > 1.0:
                evolution.max_bond = min(max_bond, int(1.1 * evolution.max_bond) + 2)
                step_rates.clear()
        current = float(target)
        values = evolution.measure(pairs)
        for destination, value in zip(results, values):
            destination.append(value)
    return tuple(np.asarray(block) for block in results)


def solve(case):
    start = time.monotonic()
    context = threadpool_limits(limits=1) if threadpool_limits is not None else nullcontext()
    with context:
        parameters = fit_parameters(case["calibration"])
        density, violation, correlation = simulate_chain(
            case["experiment"], parameters, case["times"], case["pairs"], start
        )
    return {
        "parameters": parameters.tolist(),
        "density": density.tolist(),
        "violation": violation.tolist(),
        "correlation": correlation.tolist(),
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as stream:
            case = json.load(stream)
    else:
        case = json.load(sys.stdin)
    json.dump(solve(case), sys.stdout, allow_nan=False)
    sys.stdout.write("\n")
