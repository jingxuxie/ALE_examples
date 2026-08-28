"""Calibration and complete secular dynamics for the six-qubit simulator."""

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import json
import sys

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares
from scipy import sparse
from scipy.sparse.linalg import expm_multiply


DIMENSION = 64


def spectrum(bath, frequency):
    frequency = np.asarray(frequency, dtype=float)
    if bath["beta"] == 0:
        return np.full_like(frequency, bath["amplitude"])
    return (
        bath["amplitude"]
        * (frequency**2 + bath["cutoff"] ** 2) ** (-0.5 * bath["beta"])
        + bath["floor"]
    )


def fit_bath(rows):
    count = len(rows)
    width = max(len(row["omega"]) for row in rows)
    frequencies = np.zeros((count, width))
    weights = np.zeros((count, width))
    for index, row in enumerate(rows):
        frequencies[index, : len(row["omega"])] = row["omega"]
        weights[index, : len(row["weight"])] = row["weight"]
    modes = np.array([row["mode"] for row in rows], dtype=float)
    values = np.array([row["value"] for row in rows], dtype=float)
    sigmas = np.array([row["sigma"] for row in rows], dtype=float)
    inverse_sigma = 1.0 / sigmas

    def white_residual(parameters):
        amplitude, eta = parameters
        return (amplitude * (1.0 + modes * eta) - values) * inverse_sigma

    def white_jacobian(parameters):
        amplitude, eta = parameters
        return np.column_stack((1.0 + modes * eta, amplitude * modes)) * inverse_sigma[:, None]

    single_values = values[modes == 0]
    amplitude_start = float(np.clip(np.median(single_values if len(single_values) else values), 1.01e-5, 0.119))
    white_fit = least_squares(
        white_residual,
        [amplitude_start, 0.3],
        jac=white_jacobian,
        bounds=([1e-5, 0.0], [0.12, 1.0]),
        x_scale=[0.03, 1.0],
        ftol=1e-13,
        xtol=1e-13,
        gtol=1e-11,
        max_nfev=500,
    )
    best_objective = float(white_fit.fun @ white_fit.fun + 2 * np.log(count))
    best_bath = {
        "beta": 0,
        "amplitude": float(white_fit.x[0]),
        "cutoff": 1.0,
        "floor": 0.0,
        "eta": float(white_fit.x[1]),
    }
    eta_start = float(np.clip(white_fit.x[1], 1e-6, 1.0 - 1e-6))

    for beta in (1, 2):
        def residual(parameters):
            amplitude, cutoff, floor, eta = parameters
            band = np.sum(weights * (frequencies**2 + cutoff**2) ** (-beta / 2), axis=1)
            return ((1.0 + modes * eta) * (amplitude * band + floor) - values) * inverse_sigma

        def jacobian(parameters):
            amplitude, cutoff, floor, eta = parameters
            denominator = frequencies**2 + cutoff**2
            band = np.sum(weights * denominator ** (-beta / 2), axis=1)
            derivative = -beta * cutoff * np.sum(weights * denominator ** (-beta / 2 - 1), axis=1)
            pair_factor = 1.0 + modes * eta
            return np.column_stack(
                (pair_factor * band, pair_factor * amplitude * derivative,
                 pair_factor, modes * (amplitude * band + floor))
            ) * inverse_sigma[:, None]

        for cutoff_start in (0.1201, 0.22, 0.45, 0.8, 1.1999):
            band = np.sum(weights * (frequencies**2 + cutoff_start**2) ** (-beta / 2), axis=1)
            design = np.column_stack((band, np.ones(count))) * (1.0 + modes * eta_start)[:, None]
            linear_start = np.linalg.lstsq(design * inverse_sigma[:, None], values * inverse_sigma, rcond=None)[0]
            start = [float(np.clip(linear_start[0], 1.01e-5, 0.1199)), cutoff_start,
                     float(np.clip(linear_start[1], 1e-8, 0.01999)), eta_start]
            fit = least_squares(
                residual,
                start,
                jac=jacobian,
                bounds=([1e-5, 0.12, 0.0, 0.0], [0.12, 1.2, 0.02, 1.0]),
                x_scale=[0.03, 0.5, 0.01, 1.0],
                ftol=1e-12,
                xtol=1e-12,
                gtol=1e-10,
                max_nfev=600,
            )
            objective = float(fit.fun @ fit.fun + 4 * np.log(count))
            if objective < best_objective - 1e-8:
                best_objective = objective
                best_bath = dict(zip(("amplitude", "cutoff", "floor", "eta"), map(float, fit.x)))
                best_bath["beta"] = beta
    return best_bath


def state_vector(specification):
    state = np.zeros(DIMENSION, dtype=complex)
    state[np.asarray(specification["indices"], dtype=int)] = (
        np.asarray(specification["real"]) + 1j * np.asarray(specification["imag"])
    )
    return state


def build_model(model, initial):
    basis = np.arange(DIMENSION)
    masks = 1 << np.arange(5, -1, -1)
    bits = ((basis[None, :] & masks[:, None]) != 0).astype(float)
    spin_z = 1.0 - 2.0 * bits
    density = bits[::2]
    link_z = spin_z[1::2]
    gauss = np.array([spin_z[2 * site] * link_z[(site - 1) % 3] * link_z[site] for site in range(3)])
    target = gauss[:, int(initial["indices"][0])]
    violations = (1.0 - target[:, None] * gauss) / 2.0
    ideal = np.diag(-np.asarray(model["electric"]) @ link_z + np.asarray(model["mass"]) @ density).astype(complex)
    error = np.zeros((DIMENSION, DIMENSION), dtype=complex)
    for site in range(3):
        next_site = (site + 1) % 3
        sources = basis[(bits[2 * site] == 0) & (bits[2 * next_site] == 1)]
        matter_destinations = sources ^ masks[2 * site] ^ masks[2 * next_site]
        destinations = matter_destinations ^ masks[2 * site + 1]
        hopping = model["hopping"][site] * np.exp(1j * model["phase"][site])
        ideal[destinations, sources] += hopping
        ideal[sources, destinations] += np.conj(hopping)
        error[matter_destinations, sources] += model["error_hop"][site]
        error[sources, matter_destinations] += model["error_hop"][site]
        error[basis ^ masks[2 * site + 1], basis] += model["error_link"][site]
    observables = np.concatenate((violations.mean(axis=0)[None, :], link_z.mean(axis=0)[None, :], density))
    return ideal, error, violations, density, observables, masks


def cluster_sorted(values, tolerance):
    order = np.argsort(values, kind="stable")
    sorted_values = values[order]
    clusters = []
    start = 0
    while start < len(values):
        stop = int(np.searchsorted(sorted_values, sorted_values[start] + tolerance, side="right"))
        clusters.append((float(np.mean(sorted_values[start:stop])), order[start:stop]))
        start = stop
    return clusters


class SecularSystem:
    def __init__(self, hamiltonian, masks, model):
        self.energies, self.unitary = eigh(hamiltonian, driver="evd", check_finite=False)
        clustered_energies = self.energies.copy()
        for mean, indices in cluster_sorted(self.energies, 1e-9):
            clustered_energies[indices] = mean
        gaps = (clustered_energies[None, :] - clustered_energies[:, None]).ravel()
        self.groups = cluster_sorted(gaps, 1e-8)
        basis = np.arange(DIMENSION)
        self.local = np.array([
            self.unitary.conj().T @ self.unitary[basis ^ mask, :] for mask in masks
        ])
        self.weights = np.array([model[species + "_weight"] for species in ("matter", "link")])
        self.signs = np.array([model[species + "_sign"] for species in ("matter", "link")])

    def dissipator(self, bath):
        eta = bath["eta"]
        channels = []
        for species in range(2):
            operators = self.local[species::2] * np.sqrt(self.weights[species])[:, None, None]
            if eta < 1.0:
                channels.extend(np.sqrt(1.0 - eta) * operators)
            if eta > 0.0:
                channels.append(np.sqrt(eta) * np.sum(self.signs[species, :, None, None] * operators, axis=0))
        channels = np.asarray(channels).reshape(-1, DIMENSION**2)
        active = np.max(np.abs(channels), axis=0) > 1e-13
        output_rows = []
        input_columns = []
        coefficients = []
        activity_operators = np.zeros((3, DIMENSION, DIMENSION), dtype=complex)
        rates = spectrum(bath, [frequency for frequency, indices in self.groups])
        for (frequency, indices), rate in zip(self.groups, rates):
            indices = indices[active[indices]]
            if not len(indices):
                continue
            destinations = indices // DIMENSION
            sources = indices % DIMENSION
            amplitudes = channels[:, indices]
            gram = rate * (amplitudes.T @ amplitudes.conj())
            row_indices = (destinations[:, None] * DIMENSION + destinations[None, :]).ravel()
            column_indices = (sources[:, None] * DIMENSION + sources[None, :]).ravel()
            output_rows.append(row_indices)
            input_columns.append(column_indices)
            coefficients.append(gram.ravel())
            diagonal_pairs = destinations[:, None] == destinations[None, :]
            first, second = np.nonzero(diagonal_pairs)
            activity_bin = 0 if abs(frequency) <= 1e-8 else (1 if abs(frequency) < 2.0 else 2)
            np.add.at(activity_operators[activity_bin], (sources[second], sources[first]), gram[first, second])
        gain = sparse.coo_matrix(
            (np.concatenate(coefficients), (np.concatenate(output_rows), np.concatenate(input_columns))),
            shape=(DIMENSION**2, DIMENSION**2),
        ).tocsr()
        gain.eliminate_zeros()
        loss = activity_operators.sum(axis=0)
        loss = (loss + loss.conj().T) * 0.5
        loss[np.abs(loss) < 1e-15] = 0.0
        identity = sparse.eye(DIMENSION, format="csr")
        dissipator = gain - 0.5 * (
            sparse.kron(sparse.csr_matrix(loss), identity, format="csr")
            + sparse.kron(identity, sparse.csr_matrix(loss.T), format="csr")
        )
        return dissipator, activity_operators

    def audit(self, bath, states):
        dissipator, activities = self.dissipator(bath)
        results = []
        for specification in states:
            state = self.unitary.conj().T @ state_vector(specification)
            rho = np.outer(state, state.conj())
            response = (dissipator @ rho.ravel()).reshape(DIMENSION, DIMENSION)
            response = self.unitary @ response @ self.unitary.conj().T
            activity = np.einsum("i,kij,j->k", state.conj(), activities, state).real
            results.append({"real": response.real.tolist(), "imag": response.imag.tolist(),
                            "activity": np.maximum(activity, 0.0).tolist()})
        return results

    def predict(self, bath, initial, ideal_states, observables, times):
        dissipator, activities = self.dissipator(bath)
        coherent = -1j * (self.energies[:, None] - self.energies[None, :]).ravel()
        generator = dissipator + sparse.diags(coherent, format="csr")
        state = self.unitary.conj().T @ initial
        rho = np.outer(state, state.conj()).ravel()
        trajectory = expm_multiply(
            generator, rho, start=0.0, stop=float(times[-1]), num=len(times),
            endpoint=True,
        ).reshape(len(times), DIMENSION, DIMENSION)
        transformed_observables = np.array([
            self.unitary.conj().T @ (diagonal[:, None] * self.unitary) for diagonal in observables
        ])
        expectations = np.einsum("tij,oji->to", trajectory, transformed_observables).real
        ideal_energy_states = ideal_states @ self.unitary.conj()
        fidelity = np.einsum("ti,tij,tj->t", ideal_energy_states.conj(), trajectory, ideal_energy_states).real
        return {"gauge": expectations[:, 0].tolist(), "fidelity": fidelity.tolist(),
                "electric": expectations[:, 1].tolist(), "density": expectations[:, 2:].tolist()}


def solve(case: dict) -> dict:
    bath = fit_bath(case["calibration"])
    model = case["model"]
    ideal, error, violations, density, observables, masks = build_model(model, case["initial"])
    cache = {}

    def system_for(action):
        strength = float(action["strength"])
        coefficients = np.asarray(action["coefficients"], dtype=float)
        key = (strength, tuple(coefficients))
        if key not in cache:
            detuning = model["kappa"] * strength**2 * (np.asarray(model["crosstalk"]) * coefficients**2) @ density
            protection = strength * coefficients @ violations
            hamiltonian = ideal + model["lambda"] * error + np.diag(protection + detuning)
            cache[key] = SecularSystem(hamiltonian, masks, model)
        return cache[key]

    audit = case["audit"]
    audit_results = system_for(audit["action"]).audit(audit["bath"], audit["states"])
    times = np.asarray(case["times"], dtype=float)
    initial = state_vector(case["initial"])
    ideal_energies, ideal_unitary = eigh(ideal, driver="evd", check_finite=False)
    ideal_states = (
        np.exp(-1j * times[:, None] * ideal_energies) * (ideal_unitary.conj().T @ initial)[None, :]
    ) @ ideal_unitary.T
    predictions = {}
    selected_action = None
    best_risk = float("inf")
    for action in case["actions"]:
        cost = action["strength"] ** 2 * float(np.sum(np.asarray(action["coefficients"], dtype=float) ** 2))
        if cost > case["budget"] + 1e-10:
            continue
        prediction = system_for(action).predict(bath, initial, ideal_states, observables, times)
        predictions[action["id"]] = prediction
        loss = 0.45 * np.asarray(prediction["gauge"]) + 0.55 * (1.0 - np.asarray(prediction["fidelity"]))
        risk = float(np.sum(np.diff(times) * (loss[1:] + loss[:-1]) * 0.5) / times[-1])
        if risk < best_risk - 1e-10:
            best_risk = risk
            selected_action = action["id"]
    return {"bath": bath, "audit": audit_results, "predictions": predictions, "selected_action": selected_action}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as input_file:
            case_input = json.load(input_file)
    else:
        case_input = json.load(sys.stdin)
    json.dump(solve(case_input), sys.stdout, allow_nan=False)
    sys.stdout.write("\n")
