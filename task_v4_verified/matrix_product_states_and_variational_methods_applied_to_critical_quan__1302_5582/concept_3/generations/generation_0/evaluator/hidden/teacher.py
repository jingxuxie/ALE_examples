import math
import time

import numpy as np
from scipy import linalg, sparse
from scipy.sparse.linalg import eigsh


TARGETS = ("odd_gap", "even_gap", "odd_spacing")
CUTOFFS = (20, 28, 36, 44, 52, 60)


def projected_operators(cutoff, omega):
    padded = cutoff + 4
    lowering = np.diag(np.sqrt(np.arange(1, padded, dtype=float)), 1)
    coordinate = (lowering + lowering.T) / np.sqrt(2.0 * omega)
    square = coordinate @ coordinate
    fourth = square @ square
    momentum = 1j * np.sqrt(omega / 2.0) * (lowering.T - lowering)
    momentum_square = (momentum @ momentum).real
    return tuple(sparse.csr_matrix(operator[:cutoff, :cutoff]) for operator in
                 (coordinate, square, fourth, momentum_square))


def tensor_product(operators):
    result = operators[0]
    for operator in operators[1:]:
        result = sparse.kron(result, operator, format="csr")
    return result


def hamiltonian(sites, cutoff, mass, coupling, omega):
    coordinate, square, fourth, momentum_square = projected_operators(cutoff, omega)
    identity = sparse.eye(cutoff, format="csr")
    potential_minimum = -min(mass, 0.0) ** 2 / 4.0
    result = sparse.csr_matrix((cutoff ** sites, cutoff ** sites))
    for site in range(sites):
        degree = int(site > 0) + int(site < sites - 1)
        local = (0.5 * momentum_square + 0.5 * (mass + degree * coupling) * square
                 + 0.25 * fourth - potential_minimum * identity)
        factors = [identity] * sites
        factors[site] = local
        result += tensor_product(factors)
    for site in range(sites - 1):
        factors = [identity] * sites
        factors[site] = coordinate
        factors[site + 1] = coordinate
        result -= coupling * tensor_product(factors)
    result.eliminate_zeros()
    return result, sites * potential_minimum


def basis_indices(sites, cutoff):
    indices = np.arange(cutoff ** sites, dtype=np.int64)
    occupations = np.array(np.unravel_index(indices, (cutoff,) * sites)).T
    parity = np.sum(occupations, axis=1) % 2
    return occupations, parity


def spectrum(sites, cutoff, mass, coupling, omega, boundary=False):
    started = time.monotonic()
    matrix, energy_origin = hamiltonian(sites, cutoff, mass, coupling, omega)
    occupations, parity = basis_indices(sites, cutoff)
    energies = []
    residuals = []
    boundary_weights = []
    extended_energies = []
    orthogonality = []
    for sector in (0, 1):
        indices = np.flatnonzero(parity == sector)
        block = matrix[indices][:, indices].tocsr()
        if len(indices) <= 300:
            values, vectors = linalg.eigh(block.toarray(), subset_by_index=(0, 1))
        else:
            start = np.sin(np.arange(1, len(indices) + 1, dtype=float) * 1.23456789)
            values, vectors = eigsh(block, k=2, which="SA", tol=2e-13,
                                    ncv=32, maxiter=30000, v0=start)
            order = np.argsort(values)
            values, vectors = values[order], vectors[:, order]
        extended_block = block.astype(np.longdouble)
        extended_vectors = vectors.astype(np.longdouble)
        products = extended_block @ extended_vectors
        rayleigh = np.sum(extended_vectors * products, axis=0) / np.sum(extended_vectors ** 2, axis=0)
        state_residuals = np.sqrt(np.sum((products - extended_vectors * rayleigh) ** 2, axis=0))
        energies.append([float(value) for value in rayleigh])
        extended_energies.append(rayleigh)
        residuals.append([float(value) for value in state_residuals])
        orthogonality.append(float(np.max(np.abs(vectors.T @ vectors - np.eye(2)))))
        if boundary:
            fraction = np.mean(occupations[indices] >= cutoff - 2, axis=1)
            boundary_weights.append([float(np.dot(fraction, vectors[:, state] ** 2))
                                     for state in range(2)])
    even, odd = extended_energies
    gaps = np.array([odd[0] - even[0], even[1] - even[0], odd[1] - odd[0]], dtype=float)
    state_errors = np.array(residuals)
    error_sums = np.array([state_errors[1, 0] + state_errors[0, 0],
                          state_errors[0, 1] + state_errors[0, 0],
                          state_errors[1, 1] + state_errors[1, 0]])
    roundoff = 64.0 * np.finfo(float).eps * max(1.0, np.max(np.abs(energies)))
    result = {
        "cutoff": cutoff,
        "omega_dimensionless": omega,
        "energy_origin_dimensionless": energy_origin,
        "shifted_energies_dimensionless": energies,
        "gaps_dimensionless": gaps.tolist(),
        "state_residuals_dimensionless": residuals,
        "residual_roundoff_gap_ratio": ((error_sums + roundoff) / np.maximum(np.abs(gaps), 1e-300)).tolist(),
        "orthogonality_max": max(orthogonality),
        "sector_dimension": cutoff ** sites // 2,
        "seconds": time.monotonic() - started
    }
    if boundary:
        result["boundary_weights"] = boundary_weights
    return result


def log_difference(first, second):
    first_gaps = np.asarray(first["gaps_dimensionless"])
    second_gaps = np.asarray(second["gaps_dimensionless"])
    if np.any(first_gaps <= 0) or np.any(second_gaps <= 0):
        return [1e100] * 3
    return np.abs(np.log(first_gaps / second_gaps)).tolist()


def certify(parameters):
    sites = parameters["sites"]
    mass = parameters["r"]
    coupling = parameters["j"]
    reference_omega = math.sqrt(max(0.0, mass) + 2.0 * coupling + 2.0)
    history = []
    for cutoff in CUTOFFS:
        current = spectrum(sites, cutoff, mass, coupling, reference_omega)
        history.append(current)
        if len(history) < 3:
            continue
        changes = [log_difference(history[-3], history[-2]),
                   log_difference(history[-2], history[-1])]
        if np.min(current["gaps_dimensionless"]) < 1e-6:
            return None, {"reason": "gap_below_resolvable_domain", "history": history}
        if max(np.max(change) for change in changes) > 2e-5:
            continue
        if max(current["residual_roundoff_gap_ratio"]) > 2e-6:
            continue
        if np.max(current["state_residuals_dimensionless"]) > 1e-10:
            continue
        independent = spectrum(sites, cutoff, mass, coupling, reference_omega * 1.17)
        basis_change = log_difference(current, independent)
        if max(basis_change) > 2e-5:
            continue
        if max(independent["residual_roundoff_gap_ratio"]) > 2e-6:
            continue
        if np.max(independent["state_residuals_dimensionless"]) > 1e-10:
            continue
        scale = parameters["scale"]
        targets = {target: float(scale * value) for target, value in
                   zip(TARGETS, current["gaps_dimensionless"])}
        certificate = {
            "accepted": True,
            "parameters_private": parameters,
            "history": history,
            "independent_basis": independent,
            "last_two_cutoff_log_changes": changes,
            "independent_basis_log_change": basis_change,
            "numerical_log_uncertainty_proxy": np.maximum.reduce([
                np.array(changes[0]), np.array(changes[1]), np.array(basis_change),
                np.array(current["residual_roundoff_gap_ratio"]),
                np.array(independent["residual_roundoff_gap_ratio"])]).tolist(),
            "uncertainty_is_rigorous_tail_bound": False,
            "label_cutoff": cutoff,
            "label_basis_omega_dimensionless": reference_omega,
            "label_rule": "computed final reference-basis Ritz gaps, no extrapolation"
        }
        return targets, certificate
    return None, {"reason": "cutoff_or_residual_not_certified", "history": history}


def public_case(case_id, family, parameters):
    sites, mass, coupling, scale, omega = (parameters[key] for key in
                                          ("sites", "r", "j", "scale", "omega"))
    records = []
    for multiplier in (1.0, 1.4):
        for cutoff in (4, 6, 8):
            result = spectrum(sites, cutoff, mass, coupling, omega * multiplier, boundary=True)
            records.append({
                "cutoff": cutoff,
                "omega": omega * multiplier * scale,
                "energy_origin": result["energy_origin_dimensionless"] * scale,
                "even_energies": (np.asarray(result["shifted_energies_dimensionless"][0]) * scale).tolist(),
                "odd_energies": (np.asarray(result["shifted_energies_dimensionless"][1]) * scale).tolist(),
                "signed_gaps": dict(zip(TARGETS, (np.asarray(result["gaps_dimensionless"]) * scale).tolist())),
                "boundary_weights": result["boundary_weights"],
                "state_residuals": (np.asarray(result["state_residuals_dimensionless"]) * scale).tolist()
            })
    return {
        "id": case_id,
        "family": family,
        "sites": sites,
        "mu2": mass * scale ** 2,
        "lambda": 6.0 * scale ** 3,
        "kappa": coupling * scale ** 2,
        "boundary": "open",
        "spectra": records
    }
