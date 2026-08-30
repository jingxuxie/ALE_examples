import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import time

import numpy as np
from scipy import linalg, sparse
from scipy.sparse.linalg import eigsh

from benchlib import CONCEPT
from direct_control import solve

sys.path.insert(0, str(CONCEPT / "evaluator/hidden"))
import teacher


def native_spectrum(case, cutoff, omega):
    started = time.monotonic()
    sites = case["sites"]
    scale = (case["lambda"] / 6) ** (1 / 3)
    masses = np.array(case.get("mu2_by_site", [case["mu2"]] * sites)) / scale ** 2
    quartics = np.array(case.get("lambda_by_site", [case["lambda"]] * sites)) / (6 * scale ** 3)
    bonds = np.array(case.get("kappa_by_bond", [case["kappa"]] * (sites - 1))) / scale ** 2
    coordinate, square, fourth, momentum_square = teacher.projected_operators(cutoff, omega)
    identity = sparse.eye(cutoff, format="csr")
    origins = -np.minimum(masses, 0) ** 2 / (4 * quartics)
    matrix = sparse.csr_matrix((cutoff ** sites, cutoff ** sites))
    for site in range(sites):
        degree = (bonds[site - 1] if site > 0 else 0) + (bonds[site] if site < sites - 1 else 0)
        local = momentum_square / 2 + (masses[site] + degree) * square / 2 + quartics[site] * fourth / 4 - origins[site] * identity
        factors = [identity] * sites
        factors[site] = local
        matrix += teacher.tensor_product(factors)
    for bond, coupling in enumerate(bonds):
        factors = [identity] * sites
        factors[bond], factors[bond + 1] = coordinate, coordinate
        matrix -= coupling * teacher.tensor_product(factors)
    matrix.eliminate_zeros()
    occupations, parity = teacher.basis_indices(sites, cutoff)
    energies, residuals, boundaries = [], [], []
    for sector in (0, 1):
        indices = np.flatnonzero(parity == sector)
        block = matrix[indices][:, indices].tocsr()
        if len(indices) <= 300:
            values, vectors = linalg.eigh(block.toarray(), subset_by_index=(0, 1))
        else:
            initial = np.sin(np.arange(len(indices)) + 0.234)
            values, vectors = eigsh(block, k=2, which="SA", tol=2e-13, ncv=32, v0=initial, maxiter=20000)
            order = np.argsort(values)
            vectors = vectors[:, order]
        extended = vectors.astype(np.longdouble)
        products = block.astype(np.longdouble) @ extended
        rayleigh = np.sum(extended * products, axis=0) / np.sum(extended ** 2, axis=0)
        energies.append(rayleigh)
        residuals.append(np.sqrt(np.sum((products - extended * rayleigh) ** 2, axis=0)).astype(float).tolist())
        fraction = np.mean(occupations[indices] >= cutoff - 2, axis=1)
        boundaries.append([float(fraction @ vectors[:, state] ** 2) for state in range(2)])
    even, odd = energies
    gaps = scale * np.array([odd[0] - even[0], even[1] - even[0], odd[1] - odd[0]], dtype=float)
    return {"cutoff": cutoff, "omega": omega * scale, "energy_origin": float(np.sum(origins) * scale),
            "even_energies": (np.array(even, dtype=float) * scale).tolist(),
            "odd_energies": (np.array(odd, dtype=float) * scale).tolist(),
            "signed_gaps": dict(zip(teacher.TARGETS, gaps.tolist())),
            "state_residuals": (np.array(residuals) * scale).tolist(), "boundary_weights": boundaries,
            "seconds": time.monotonic() - started}


def gap_array(record):
    return np.array([record["prediction"]["targets"][target] for target in teacher.TARGETS])


def solve_reference(case, count, fock=80, frequency=2.0):
    started = time.monotonic()
    prediction, diagnostic = solve(case, count=count, fock=fock, frequency=frequency, tolerance=2e-13)
    scale = (case["lambda"] / 6) ** (1 / 3)
    gaps = np.array([prediction["targets"][target] for target in teacher.TARGETS]) / scale
    residuals = np.array(diagnostic["residuals_dimensionless"])
    sums = np.array([residuals[0, 0] + residuals[1, 0], residuals[0].sum(), residuals[1].sum()])
    rounding = 64 * np.finfo(float).eps * max(1.0, np.max(np.abs(diagnostic["shifted_sector_energies_dimensionless"])))
    return {"prediction": prediction, "diagnostic": diagnostic, "seconds": time.monotonic() - started,
            "residual_roundoff_gap_ratio": ((sums + rounding) / np.maximum(np.abs(gaps), 1e-300)).tolist()}


def certify(case):
    history = []
    counts = (6, 8, 10, 12) if case["sites"] == 6 else (6, 8, 10, 12, 14, 16)
    scale = (case["lambda"] / 6) ** (1 / 3)
    for count in counts:
        current = solve_reference(case, count)
        history.append(current)
        if len(history) < 3:
            continue
        if min(gap_array(current)) / scale < 1e-6:
            return {"accepted": False, "reason": "gap_floor", "history": history}
        changes = [np.abs(np.log(gap_array(history[-3]) / gap_array(history[-2]))),
                   np.abs(np.log(gap_array(history[-2]) / gap_array(history[-1])))]
        if np.max(changes) > 2e-5 or max(current["residual_roundoff_gap_ratio"]) > 2e-6:
            continue
        independent = solve_reference(case, count, fock=96, frequency=2.34)
        discrepancy = np.abs(np.log(gap_array(independent) / gap_array(current)))
        if max(discrepancy) > 2e-5 or max(independent["residual_roundoff_gap_ratio"]) > 2e-6:
            continue
        if max(np.max(current["diagnostic"]["residuals_dimensionless"]),
               np.max(independent["diagnostic"]["residuals_dimensionless"])) > 1e-10:
            continue
        return {"accepted": True, "history": history, "independent_basis": independent,
                "last_two_cutoff_log_changes": [change.tolist() for change in changes],
                "basis_log_change": discrepancy.tolist(), "label": current["prediction"],
                "truth_extrapolated": False, "rigorous_full_hilbert_residual_bound": False,
                "residual_scope": "compressed finite Hamiltonian; cutoff and basis comparisons additionally probe omitted states"}
    return {"accepted": False, "reason": "reference_cutoff_not_certified", "history": history}


def generate_case(case):
    certificate = certify(case)
    if certificate["accepted"]:
        case["spectra"] = [native_spectrum(case, cutoff, omega) for omega in (0.7, 0.98) for cutoff in (4, 6)]
        for spectrum in case["spectra"]:
            spectrum.pop("seconds")
    return {"case": case, "certificate": certificate}
