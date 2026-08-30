"""Frozen floating continuum screen; an ACCEPT is not a PSD certificate."""

import os

for thread_variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[thread_variable] = "1"

import argparse
import itertools
import json
import warnings

import numpy as np
from numpy.polynomial import chebyshev as cheb
from scipy.optimize import minimize_scalar


VERSION = "collective-chebyshev-screen-v2"
NEGATIVE_TOLERANCE = 5e-11
PROFILES = {
    "uniform_lobatto": (257, 193, 127, 0.0),
    "shifted_lobatto": (263, 199, 131, 0.21132486540518713),
    "incommensurate": (269, 211, 137, 0.3819660112501051),
}


class NumericalFailure(ValueError):
    pass


def evaluate_matrices(coefficients, points):
    points = np.atleast_1d(np.asarray(points, dtype=np.float64))
    coordinates = (2.0 * points - 1.0)[:, None, None]
    following = np.zeros((len(points), 4, 4), dtype=np.float64)
    after_following = following.copy()
    for matrix in coefficients[:0:-1]:
        current = matrix + 2.0 * coordinates * following - after_following
        after_following, following = following, current
    values = coefficients[0] + coordinates * following - after_following
    if not np.isfinite(values).all():
        raise NumericalFailure("nonfinite matrix evaluation")
    return values


def _root_projections(polynomial):
    polynomial = np.asarray(polynomial, dtype=np.float64)
    if not np.isfinite(polynomial).all():
        raise NumericalFailure("nonfinite polynomial")
    nonzero = np.flatnonzero(polynomial != 0.0)
    if len(nonzero) == 0 or nonzero[-1] == 0:
        return np.empty(0)
    polynomial = polynomial[: nonzero[-1] + 1]
    roots = cheb.chebroots(polynomial / np.max(np.abs(polynomial)))
    if not np.isfinite(roots).all():
        raise NumericalFailure("nonfinite companion roots")
    real_parts = roots.real
    eligible = real_parts[(real_parts >= -1.0 - 1e-10) & (real_parts <= 1.0 + 1e-10)]
    return np.clip((eligible + 1.0) / 2.0, 0.0, 1.0)


def determinant_candidates(coefficients):
    collected = []
    for size in range(1, 5):
        for subset in itertools.combinations(range(4), size):
            determinant = np.zeros(size * (len(coefficients) - 1) + 1)
            for permutation in itertools.permutations(range(size)):
                inversions = sum(
                    permutation[left] > permutation[right]
                    for left in range(size)
                    for right in range(left + 1, size)
                )
                product = np.array([1.0])
                for row, column in enumerate(permutation):
                    product = cheb.chebmul(product, coefficients[:, subset[row], subset[column]])
                determinant[: len(product)] += (-1.0 if inversions % 2 else 1.0) * product
            collected.extend(_root_projections(cheb.chebder(determinant)))
            collected.extend(_root_projections(determinant))
    candidates = np.asarray(collected)
    if len(candidates):
        candidates = np.clip(
            np.concatenate((candidates, candidates - 2e-7, candidates + 2e-7)),
            0.0,
            1.0,
        )
    return np.unique(candidates)


def _mesh(profile):
    uniform_count, cosine_count, irrational_count, phase = PROFILES[profile]
    uniform = (np.arange(uniform_count) + phase) / (uniform_count - 1)
    cosine = (1.0 - np.cos(np.pi * np.arange(cosine_count) / (cosine_count - 1))) / 2.0
    irrational = np.mod((np.arange(irrational_count) + 1) * np.sqrt(2.0) + phase, 1.0)
    return np.unique(np.clip(np.concatenate(([0.0, 1.0], uniform, cosine, irrational)), 0.0, 1.0))


def _screen_profile(coefficients, profile, polynomial_points):
    evaluations = 0
    best_value = float("inf")
    best_point = 0.0
    phase = "independent_meshes"
    optimizations = 0

    def sample(points):
        nonlocal evaluations, best_value, best_point
        points = np.atleast_1d(points)
        values = np.linalg.eigvalsh(evaluate_matrices(coefficients, points))
        if not np.isfinite(values).all():
            raise NumericalFailure("nonfinite eigensystem")
        evaluations += len(points)
        lowest = int(np.argmin(values[:, 0]))
        if values[lowest, 0] < best_value:
            best_value = float(values[lowest, 0])
            best_point = float(points[lowest])
        return values

    def report():
        return {
            "profile": profile,
            "accepted": bool(best_value >= -NEGATIVE_TOLERANCE),
            "minimum_seen": best_value,
            "argmin_seen": best_point,
            "evaluations": evaluations,
            "local_optimizations": optimizations,
            "last_stage": phase,
            "determinant_candidates": len(polynomial_points),
        }

    points = _mesh(profile)
    values = sample(points)
    if best_value < -NEGATIVE_TOLERANCE:
        return report()

    phase = "principal_minor_roots_and_stationary_points"
    if len(polynomial_points):
        sample(polynomial_points)
        if best_value < -NEGATIVE_TOLERANCE:
            return report()
        points = np.unique(np.concatenate((points, polynomial_points)))
        values = sample(points)

    phase = "adaptive_low_eigenvalue_intervals"
    derivative = cheb.chebder(coefficients, axis=0) * 2.0
    for refinement in range(3):
        widths = np.diff(points)
        midpoints = (points[:-1] + points[1:]) / 2.0
        slopes = np.linalg.norm(evaluate_matrices(derivative, midpoints), axis=(1, 2))
        endpoint_floor = np.minimum(values[:-1, 0], values[1:, 0])
        gaps = np.minimum(values[:-1, 1] - values[:-1, 0], values[1:, 1] - values[1:, 0])
        risk = endpoint_floor / (widths * (slopes + 1e-12) + 1e-14)
        risk += 0.05 * gaps / (np.max(gaps) + 1e-14)
        selected = np.argsort(risk, kind="stable")[:24]
        sample(midpoints[selected])
        if best_value < -NEGATIVE_TOLERANCE:
            return report()
        points = np.unique(np.concatenate((points, midpoints[selected])))
        values = sample(points)

    phase = "bounded_eigenvalue_minimization"
    minima = np.flatnonzero(
        (values[1:-1, 0] <= values[:-2, 0])
        & (values[1:-1, 0] <= values[2:, 0])
        & (np.maximum(values[:-2, 0], values[2:, 0]) - values[1:-1, 0] > 1e-13)
    ) + 1
    ordered_minima = minima[np.argsort(values[minima, 0], kind="stable")][:64]
    for location in ordered_minima:
        result = minimize_scalar(
            lambda point: float(sample([point])[0, 0]),
            bounds=(points[location - 1], points[location + 1]),
            method="bounded",
            options={"xatol": 2e-13, "maxiter": 90},
        )
        optimizations += 1
        if not result.success or not np.isfinite(result.fun):
            raise NumericalFailure("local optimizer did not converge")
        sample([result.x])
        if best_value < -NEGATIVE_TOLERANCE:
            return report()

    phase = "frozen_rayleigh_stationary_points"
    low_indices = list(np.argsort(values[:, 0], kind="stable")[:6])
    gap_indices = list(np.argsort(values[:, 1] - values[:, 0], kind="stable")[:2])
    for location in low_indices + gap_indices:
        eigenvalues, eigenvectors = np.linalg.eigh(evaluate_matrices(coefficients, [points[location]])[0])
        if not np.isfinite(eigenvalues).all() or not np.isfinite(eigenvectors).all():
            raise NumericalFailure("nonfinite Rayleigh direction")
        direction_count = 2 if location in gap_indices else 1
        for direction_index in range(direction_count):
            direction = eigenvectors[:, direction_index]
            scalar = np.einsum("i,kij,j->k", direction, coefficients, direction)
            candidates = _root_projections(cheb.chebder(scalar))
            if len(candidates):
                sample(candidates)
                if best_value < -NEGATIVE_TOLERANCE:
                    return report()
    return report()


def screen_all(coefficients):
    coefficients = np.asarray(coefficients, dtype=np.float64)
    if coefficients.ndim != 3 or coefficients.shape[1:] != (4, 4) or not 3 <= len(coefficients) <= 25:
        raise ValueError("expected degree 2..24, four-by-four matrices")
    if not np.isfinite(coefficients).all() or not np.array_equal(coefficients, coefficients.transpose(0, 2, 1)):
        raise ValueError("expected finite symmetric matrices")
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        try:
            polynomial_points = determinant_candidates(coefficients)
        except (ValueError, FloatingPointError, RuntimeWarning, np.linalg.LinAlgError) as error:
            return [
                {"profile": profile, "accepted": False, "failure": type(error).__name__}
                for profile in PROFILES
            ]
        reports = []
        for profile in PROFILES:
            try:
                reports.append(_screen_profile(coefficients, profile, polynomial_points))
            except (ValueError, FloatingPointError, RuntimeWarning, np.linalg.LinAlgError) as error:
                reports.append({"profile": profile, "accepted": False, "failure": type(error).__name__})
        return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("witness")
    arguments = parser.parse_args()
    with open(arguments.witness, encoding="utf-8") as stream:
        witness = json.load(stream)
    coefficients = np.asarray(witness["coefficients"], dtype=np.float64) / witness["denominator"]
    reports = screen_all(coefficients)
    print(json.dumps({"guard_version": VERSION, "accepted": all(item["accepted"] for item in reports), "profiles": reports}, allow_nan=False))


if __name__ == "__main__":
    main()
