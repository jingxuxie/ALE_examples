import json
import sys

import numpy as np
from scipy import linalg, optimize, sparse
from scipy.sparse.csgraph import connected_components


DIMENSION = 64


def spectrum(frequency, bath):
    frequency = np.asarray(frequency)
    if bath["beta"] == 0:
        return np.full_like(frequency, bath["amplitude"], dtype=float)
    return (
        bath["amplitude"]
        * (frequency**2 + bath["cutoff"] ** 2) ** (-0.5 * bath["beta"])
        + bath["floor"]
    )


def fit_bath(rows):
    count = len(rows)
    width = max(len(row["omega"]) for row in rows)
    frequencies = np.zeros((count, width))
    weights = np.zeros_like(frequencies)
    for index, row in enumerate(rows):
        frequencies[index, : len(row["omega"])] = row["omega"]
        weights[index, : len(row["weight"])] = row["weight"]
    modes = np.array([row["mode"] for row in rows], dtype=float)
    values = np.array([row["value"] for row in rows])
    inverse_sigma = 1.0 / np.array([row["sigma"] for row in rows])
    lower_amplitude, upper_amplitude = 1e-5, 0.12
    best_objective = np.inf
    best_bath = None

    for beta in (0, 1, 2):
        if beta == 0:
            def residual(parameters):
                amplitude, eta = parameters
                return ((1.0 + modes * eta) * amplitude - values) * inverse_sigma

            def jacobian(parameters):
                amplitude, eta = parameters
                return np.column_stack(
                    ((1.0 + modes * eta) * inverse_sigma,
                     modes * amplitude * inverse_sigma)
                )

            seed = np.clip(np.median(values), lower_amplitude, upper_amplitude)
            result = optimize.least_squares(
                residual, [seed, 0.4], jac=jacobian,
                bounds=([lower_amplitude, 0.0], [upper_amplitude, 1.0]),
                x_scale="jac", ftol=1e-12, xtol=1e-12, gtol=1e-12,
                max_nfev=500,
            )
            objective = float(np.dot(result.fun, result.fun)) + 2 * np.log(count)
            bath = {
                "beta": 0, "amplitude": float(result.x[0]), "cutoff": 1.0,
                "floor": 0.0, "eta": float(result.x[1]),
            }
        else:
            def residual(parameters):
                amplitude, cutoff, floor, eta = parameters
                band = np.sum(
                    weights * (frequencies**2 + cutoff**2) ** (-0.5 * beta), axis=1
                )
                rate = (1.0 + modes * eta) * (amplitude * band + floor)
                return (rate - values) * inverse_sigma

            def jacobian(parameters):
                amplitude, cutoff, floor, eta = parameters
                squared = frequencies**2 + cutoff**2
                kernel = squared ** (-0.5 * beta)
                band = np.sum(weights * kernel, axis=1)
                derivative = np.sum(weights * kernel / squared, axis=1) * (-beta * cutoff)
                factor = (1.0 + modes * eta) * inverse_sigma
                return np.column_stack(
                    (factor * band, factor * amplitude * derivative, factor,
                     modes * (amplitude * band + floor) * inverse_sigma)
                )

            winner = None
            for cutoff in (0.14, 0.4, 0.8, 1.18):
                for eta in (0.05, 0.55, 0.95):
                    band = np.sum(
                        weights * (frequencies**2 + cutoff**2) ** (-0.5 * beta), axis=1
                    )
                    factor = (1.0 + modes * eta) * inverse_sigma
                    design = np.column_stack((factor * band, factor))
                    linear = optimize.lsq_linear(
                        design, values * inverse_sigma,
                        bounds=([lower_amplitude, 0.0], [upper_amplitude, 0.02]),
                        tol=1e-12, max_iter=100,
                    )
                    seed = [linear.x[0], cutoff, linear.x[1], eta]
                    result = optimize.least_squares(
                        residual, seed, jac=jacobian,
                        bounds=([lower_amplitude, 0.12, 0.0, 0.0],
                                [upper_amplitude, 1.2, 0.02, 1.0]),
                        x_scale="jac", ftol=1e-12, xtol=1e-12, gtol=1e-12,
                        max_nfev=500,
                    )
                    if winner is None or np.dot(result.fun, result.fun) < np.dot(winner.fun, winner.fun):
                        winner = result
            objective = float(np.dot(winner.fun, winner.fun)) + 4 * np.log(count)
            bath = dict(zip(("amplitude", "cutoff", "floor", "eta"), map(float, winner.x)))
            bath["beta"] = beta
        if objective < best_objective - 1e-8:
            best_objective = objective
            best_bath = bath
    return best_bath


def state_vector(specification):
    vector = np.zeros(DIMENSION, dtype=complex)
    vector[np.asarray(specification["indices"], dtype=int)] = (
        np.asarray(specification["real"]) + 1j * np.asarray(specification["imag"])
    )
    return vector


def build_system(case):
    model = case["model"]
    indices = np.arange(DIMENSION)
    masks = 1 << np.arange(5, -1, -1)
    occupation = ((indices[None, :] & masks[:, None]) != 0).astype(float)
    pauli_z = 1.0 - 2.0 * occupation
    ideal = np.zeros((DIMENSION, DIMENSION), dtype=complex)
    error = np.zeros_like(ideal)
    constraints = np.empty((3, DIMENSION))
    reference_index = case["initial"]["indices"][0]
    for site in range(3):
        next_site = (site + 1) % 3
        previous_site = (site - 1) % 3
        matter = 2 * site
        link = matter + 1
        next_matter = 2 * next_site
        sources = indices[(occupation[matter] == 0) & (occupation[next_matter] == 1)]
        bare_destinations = sources ^ masks[matter] ^ masks[next_matter]
        destinations = bare_destinations ^ masks[link]
        hopping = model["hopping"][site] * np.exp(1j * model["phase"][site])
        ideal[destinations, sources] += hopping
        ideal[sources, destinations] += hopping.conjugate()
        error[bare_destinations, sources] += model["error_hop"][site]
        error[sources, bare_destinations] += model["error_hop"][site]
        error[indices ^ masks[link], indices] += model["error_link"][site]
        ideal[indices, indices] += (
            -model["electric"][site] * pauli_z[link]
            + model["mass"][site] * occupation[matter]
        )
        generator = pauli_z[matter] * pauli_z[2 * previous_site + 1] * pauli_z[link]
        constraints[site] = (1.0 - generator[reference_index] * generator) / 2.0
    observables = np.vstack(
        (np.mean(constraints, axis=0), np.mean(pauli_z[1::2], axis=0), occupation[::2])
    )
    return ideal, error, constraints, occupation[::2], observables, masks


def cluster_sorted(values, tolerance):
    start = 0
    while start < len(values):
        stop = int(np.searchsorted(values, values[start] + tolerance, side="right"))
        yield start, stop
        start = stop


class SecularSystem:
    def __init__(self, hamiltonian, masks):
        self.energies, self.vectors = linalg.eigh(hamiltonian, check_finite=False)
        grouped = self.energies.copy()
        for start, stop in cluster_sorted(grouped.copy(), 1e-9):
            grouped[start:stop] = np.mean(grouped[start:stop])
        gaps = (grouped[None, :] - grouped[:, None]).ravel()
        order = np.argsort(gaps, kind="stable")
        sorted_gaps = gaps[order]
        self.groups = [
            (float(np.mean(sorted_gaps[start:stop])), order[start:stop])
            for start, stop in cluster_sorted(sorted_gaps, 1e-8)
        ]
        self.local = np.array([
            self.vectors.conj().T @ self.vectors[np.arange(DIMENSION) ^ mask, :]
            for mask in masks
        ])

    def dissipator(self, model, bath):
        eta = bath["eta"]
        channels = []
        for offset, species in ((0, "matter"), (1, "link")):
            weighted = np.sqrt(np.asarray(model[species + "_weight"]))[:, None, None] * self.local[offset::2]
            channels.extend(np.sqrt(1.0 - eta) * weighted)
            channels.append(
                np.sqrt(eta) * np.sum(
                    np.asarray(model[species + "_sign"])[:, None, None] * weighted, axis=0
                )
            )
        channels = np.asarray(channels).reshape(8, -1)
        active = np.max(np.abs(channels), axis=0) > 2e-14
        row_parts, column_parts, data_parts = [], [], []
        activity_operators = np.zeros((3, DIMENSION, DIMENSION), dtype=complex)
        rates = spectrum(np.array([group[0] for group in self.groups]), bath)
        for (frequency, full_pairs), rate in zip(self.groups, rates):
            pairs = full_pairs[active[full_pairs]]
            if not len(pairs):
                continue
            destinations = pairs // DIMENSION
            sources = pairs % DIMENSION
            elements = channels[:, pairs]
            gram = rate * (elements.T @ elements.conj())
            rows = (destinations[:, None] * DIMENSION + destinations[None, :]).ravel()
            columns = (sources[:, None] * DIMENSION + sources[None, :]).ravel()
            data = gram.ravel()
            keep = np.abs(data) > 1e-24
            row_parts.append(rows[keep])
            column_parts.append(columns[keep])
            data_parts.append(data[keep])
            equal_destinations = destinations[:, None] == destinations[None, :]
            first, second = np.nonzero(equal_destinations)
            activity_bin = 0 if abs(frequency) <= 1e-8 else (1 if abs(frequency) < 2.0 else 2)
            np.add.at(
                activity_operators[activity_bin], (sources[first], sources[second]),
                gram[first, second].conj(),
            )
        shape = (DIMENSION**2, DIMENSION**2)
        if data_parts:
            gain = sparse.coo_matrix(
                (np.concatenate(data_parts),
                 (np.concatenate(row_parts), np.concatenate(column_parts))), shape=shape
            ).tocsr()
        else:
            gain = sparse.csr_matrix(shape, dtype=complex)
        loss = sparse.csr_matrix(np.sum(activity_operators, axis=0))
        identity = sparse.eye(DIMENSION, format="csr")
        dissipator = gain - 0.5 * (
            sparse.kron(loss, identity, format="csr")
            + sparse.kron(identity, loss.T, format="csr")
        )
        dissipator = dissipator.tocsr()
        dissipator.eliminate_zeros()
        return dissipator, activity_operators

    def audit(self, model, bath, states):
        dissipator, activities = self.dissipator(model, bath)
        result = []
        for specification in states:
            vector = self.vectors.conj().T @ state_vector(specification)
            density = np.outer(vector, vector.conj())
            derivative = (dissipator @ density.ravel()).reshape(DIMENSION, DIMENSION)
            derivative = self.vectors @ derivative @ self.vectors.conj().T
            activity = np.real(np.einsum("aij,ji->a", activities, density))
            result.append({
                "real": derivative.real.tolist(), "imag": derivative.imag.tolist(),
                "activity": np.maximum(activity, 0.0).tolist(),
            })
        return result

    def evolve(self, dissipator, initial, times):
        vector = self.vectors.conj().T @ initial
        initial_density = np.outer(vector, vector.conj()).ravel()
        frequencies = (self.energies[:, None] - self.energies[None, :]).ravel()
        _, labels = connected_components(abs(dissipator), directed=False)
        sizes = np.bincount(labels)
        singleton = sizes[labels] == 1
        evolved = np.zeros((len(times), DIMENSION**2), dtype=complex)
        diagonal = dissipator.diagonal() - 1j * frequencies
        evolved[:, singleton] = (
            np.exp(times[:, None] * diagonal[None, singleton]) * initial_density[None, singleton]
        )
        for label in np.flatnonzero(sizes > 1):
            indices = np.flatnonzero(labels == label)
            start = initial_density[indices]
            if np.linalg.norm(start) < 1e-16:
                continue
            block = dissipator[indices][:, indices].toarray()
            block_frequencies = frequencies[indices]
            mean_frequency = np.mean(block_frequencies)
            hermitian_error = np.max(np.abs(block - block.conj().T))
            hermitian_tolerance = 1e-12 * np.max(np.abs(block)) + 1e-25
            if np.ptp(block_frequencies) < 1e-11 and hermitian_error <= hermitian_tolerance:
                eigenvalues, eigenvectors = linalg.eigh(
                    0.5 * (block + block.conj().T), check_finite=False
                )
                coefficients = eigenvectors.conj().T @ start
                evolved[:, indices] = (
                    np.exp(times[:, None] * (eigenvalues[None, :] - 1j * mean_frequency))
                    * coefficients[None, :]
                ) @ eigenvectors.T
            else:
                block[np.diag_indices_from(block)] -= 1j * (block_frequencies - mean_frequency)
                eigenvalues, eigenvectors = linalg.eig(block, check_finite=False)
                coefficients = linalg.solve(eigenvectors, start, check_finite=False)
                evolved[:, indices] = (
                    np.exp(times[:, None] * (eigenvalues[None, :] - 1j * mean_frequency))
                    * coefficients[None, :]
                ) @ eigenvectors.T
        evolved[0] = initial_density
        return evolved.reshape(len(times), DIMENSION, DIMENSION)


def action_key(action):
    return float(action["strength"]), tuple(map(float, action["coefficients"]))


def solve(case: dict) -> dict:
    bath = fit_bath(case["calibration"])
    ideal, error, constraints, occupation, observables, masks = build_system(case)
    model = case["model"]
    indices = np.arange(DIMENSION)
    systems = {}

    def get_system(action):
        key = action_key(action)
        if key not in systems:
            strength, coefficients = key
            coefficients = np.asarray(coefficients)
            hamiltonian = ideal + model["lambda"] * error
            hamiltonian[indices, indices] += strength * (coefficients @ constraints)
            hamiltonian[indices, indices] += (
                model["kappa"] * strength**2
                * ((np.asarray(model["crosstalk"]) * coefficients**2) @ occupation)
            )
            systems[key] = SecularSystem(hamiltonian, masks)
        return systems[key]

    audit_specification = case["audit"]
    audit = get_system(audit_specification["action"]).audit(
        model, audit_specification["bath"], audit_specification["states"]
    )
    times = np.asarray(case["times"], dtype=float)
    initial = state_vector(case["initial"])
    ideal_energies, ideal_vectors = linalg.eigh(ideal, check_finite=False)
    ideal_states = (
        np.exp(-1j * times[:, None] * ideal_energies[None, :])
        * (ideal_vectors.conj().T @ initial)[None, :]
    ) @ ideal_vectors.T
    predictions = {}
    best_risk = np.inf
    selected = None
    cached_predictions = {}
    for action in case["actions"]:
        cost = action["strength"]**2 * np.dot(action["coefficients"], action["coefficients"])
        if cost > case["budget"] + 1e-10:
            continue
        key = action_key(action)
        if key in cached_predictions:
            prediction, risk = cached_predictions[key]
        else:
            system = get_system(action)
            dissipator, _ = system.dissipator(model, bath)
            densities = system.evolve(dissipator, initial, times)
            transformed_observables = np.array([
                system.vectors.conj().T @ (observable[:, None] * system.vectors)
                for observable in observables
            ])
            expected = np.real(np.einsum("tij,aji->ta", densities, transformed_observables))
            ideal_in_basis = ideal_states @ system.vectors.conj()
            fidelities = np.real(np.einsum(
                "ti,tij,tj->t", ideal_in_basis.conj(), densities, ideal_in_basis
            ))
            prediction = {
                "gauge": expected[:, 0].tolist(), "fidelity": fidelities.tolist(),
                "electric": expected[:, 1].tolist(), "density": expected[:, 2:].tolist(),
            }
            risk = float(np.trapz(0.45 * expected[:, 0] + 0.55 * (1.0 - fidelities), times) / times[-1])
            cached_predictions[key] = prediction, risk
        predictions[action["id"]] = prediction
        if risk < best_risk - 1e-10:
            best_risk = risk
            selected = action["id"]
    return {"bath": bath, "audit": audit, "predictions": predictions, "selected_action": selected}


if __name__ == "__main__":
    json.dump(solve(json.load(sys.stdin)), sys.stdout, allow_nan=False)
    sys.stdout.write("\n")
