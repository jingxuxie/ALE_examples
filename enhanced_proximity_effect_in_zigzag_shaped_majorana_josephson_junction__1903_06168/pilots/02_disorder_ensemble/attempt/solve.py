#!/usr/bin/env python3
"""Calibrated spatial disorder and sparse, Bloch-minimized BdG spectra."""

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import argparse
import json
import math
from pathlib import Path
import sys
import time
import warnings

sys.dont_write_bytecode = True

import numpy as np
import scipy.constants as constants
import scipy.linalg as dense_linalg
import scipy.optimize as optimize
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg


HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE.parent / "participant" / "workspace"
if not (MODEL_PATH / "clean_model.py").is_file():
    MODEL_PATH = HERE / "workspace"
sys.path.insert(0, str(MODEL_PATH))
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="MUMPS is not available.*")
    from clean_model import make_system, parameters
    from random_field import field


def disorder_strength(mfp_nm):
    """Return the uniform half-width U in meV, using the specified SI DOS."""
    mean_free_path = float(mfp_nm) * 1e-9
    if math.isinf(mean_free_path):
        return 0.0
    if not math.isfinite(mean_free_path) or mean_free_path <= 0:
        raise ValueError("mfp_nm must be positive")
    energy_unit = constants.eV * 1e-3
    mass = 0.023 * constants.m_e
    fermi_velocity = math.sqrt(2 * 10 * energy_unit / mass)
    site_density = (10e-9) ** 2 * mass / (math.pi * constants.hbar ** 2)
    variance = constants.hbar * fermi_velocity / (
        2 * math.pi * site_density * mean_free_path
    )
    return math.sqrt(3 * variance) / energy_unit


def nested_dissection(positions):
    """Order grid separators last, including the periodic cell seam."""
    def partition(indices):
        if len(indices) <= 24:
            return indices
        coordinates = positions[indices]
        axis = int(np.argmax(np.ptp(coordinates, axis=0)))
        values = coordinates[:, axis]
        unique = np.unique(values)
        separator = unique[len(unique) // 2]
        return np.concatenate((
            partition(indices[values < separator]),
            partition(indices[values > separator]),
            indices[values == separator],
        ))

    seam = positions[:, 0] == positions[:, 0].min()
    site_order = np.concatenate((partition(np.flatnonzero(~seam)), np.flatnonzero(seam)))
    return (4 * site_order[:, None] + np.arange(4)).ravel()


class JunctionSpectrum:
    def __init__(self, case, verbose=False):
        self.started = time.monotonic()
        self.verbose = verbose
        self.strength = disorder_strength(case["mfp_nm"])
        self.system = make_system(case["amplitude_nm"])
        self.params = parameters(case["field_T"], case["phase_rad"])
        positions = np.asarray([site.pos for site in self.system.sites])
        potential = field(self.strength, case["salt"])
        disorder = np.asarray([potential(*site.pos) for site in self.system.sites])
        matrix = self.system.hamiltonian_submatrix(
            params=dict(self.params, k_x=0.0), sparse=True
        ).tocsc()
        matrix += sparse.diags(
            (disorder[:, None] * np.array([1, -1, 1, -1])).ravel(), format="csc"
        )
        matrix.eliminate_zeros()
        self.permutation = nested_dissection(positions)
        self.matrix = matrix[self.permutation, :][:, self.permutation].tocsc()
        self.matrix.sort_indices()
        self.cell_steps = 390
        reordered_x = np.repeat(positions[:, 0], 4)[self.permutation]
        entries = self.matrix.tocoo()
        displacement = reordered_x[entries.col] - reordered_x[entries.row]
        displacement = (displacement + 1950) % 3900 - 1950
        horizontal = displacement != 0
        self.horizontal = sparse.csc_matrix(
            (entries.data[horizontal], (entries.row[horizontal], entries.col[horizontal])),
            shape=self.matrix.shape,
        )
        self.current = sparse.csc_matrix(
            (1j * np.sign(displacement[horizontal]) * entries.data[horizontal],
             (entries.row[horizontal], entries.col[horizontal])),
            shape=self.matrix.shape,
        )
        self.samples = []
        self.rng = np.random.default_rng(78123)
        self.log("built", self.matrix.shape[0], "orbitals; U =", self.strength)

    def log(self, *message):
        if self.verbose:
            print(f"[{time.monotonic() - self.started:.2f}s]", *message,
                  file=sys.stderr, flush=True)

    def coefficients(self, phase):
        angle = phase / self.cell_steps
        return -2 * math.sin(angle / 2) ** 2, math.sin(angle)

    def hamiltonian(self, phase):
        cosine, sine = self.coefficients(phase)
        if phase == 0:
            return self.matrix
        return (self.matrix + cosine * self.horizontal + sine * self.current).tocsc()

    def evaluate(self, phase, count=12):
        phase = float(phase)
        for sample in self.samples:
            if abs(phase - sample["phase"]) < 2e-7:
                return sample
        started = time.monotonic()
        matrix = self.hamiltonian(phase)
        shift = 0.0
        try:
            factor = sparse_linalg.splu(
                matrix, permc_spec="NATURAL", diag_pivot_thresh=0.01,
                options={"SymmetricMode": True},
            )
        except RuntimeError:
            shift = 1e-8
            factor = sparse_linalg.splu(
                matrix - shift * sparse.eye(matrix.shape[0], format="csc"),
                permc_spec="NATURAL", diag_pivot_thresh=0.1,
                options={"SymmetricMode": True},
            )
        inverse = sparse_linalg.LinearOperator(
            matrix.shape, matvec=factor.solve, dtype=matrix.dtype
        )
        initial = self.rng.standard_normal(matrix.shape[0]).astype(complex)
        energies, vectors = sparse_linalg.eigsh(
            matrix, k=count, sigma=shift, OPinv=inverse,
            v0=initial, tol=2e-9, ncv=max(32, 2 * count + 8), maxiter=800,
        )
        residual = float(np.max(np.linalg.norm(matrix @ vectors - vectors * energies, axis=0)))
        if residual > 2e-7:
            def refined_solve(rhs):
                solution = factor.solve(rhs)
                correction = rhs - matrix @ solution + shift * solution
                return solution + factor.solve(correction)
            inverse = sparse_linalg.LinearOperator(
                matrix.shape, matvec=refined_solve, dtype=matrix.dtype
            )
            energies, vectors = sparse_linalg.eigsh(
                matrix, k=count, sigma=shift, OPinv=inverse, v0=initial,
                tol=2e-10, ncv=max(40, 2 * count + 8), maxiter=1200,
            )
            residual = float(np.max(np.linalg.norm(matrix @ vectors - vectors * energies, axis=0)))
            if residual > 2e-6:
                raise ArithmeticError(f"Unconverged eigenpairs: residual {residual}")
        sample = dict(phase=phase, gap=float(np.min(np.abs(energies))),
                      energies=energies, vectors=vectors,
                      seconds=time.monotonic() - started, residual=residual)
        self.samples.append(sample)
        self.log("phase", f"{phase:.9f}", "gap", f"{sample['gap']:.10g}",
                 "residual", f"{residual:.2g}", "seconds", f"{sample['seconds']:.2f}")
        return sample

    def reduced_spectrum(self):
        """Project H(k)^2, not just H(k), to avoid indefinite Ritz pollution."""
        vectors = np.asfortranarray(np.concatenate(
            [sample["vectors"] for sample in self.samples], axis=1
        ))
        basis, singular_values, right = dense_linalg.svd(
            vectors, full_matrices=False, overwrite_a=True, check_finite=False,
            lapack_driver="gesdd",
        )
        del vectors, right
        basis = np.ascontiguousarray(basis[:, singular_values > 2e-9 * singular_values[0]])
        images = [operator @ basis for operator in
                  (self.matrix, self.horizontal, self.current)]
        del basis
        products = []
        for first in range(3):
            for second in range(first, 3):
                product = images[first].conj().T @ images[second]
                if first != second:
                    product += product.conj().T
                else:
                    product = (product + product.conj().T) * 0.5
                products.append(product)
        del images
        base, cross_horizontal, cross_current, horizontal_squared, cross_both, current_squared = products
        self.log("reduced dimension", base.shape[0])

        def gap(phase):
            cosine, sine = self.coefficients(float(phase))
            projected = (base + cosine * cross_horizontal + sine * cross_current
                         + cosine ** 2 * horizontal_squared + cosine * sine * cross_both
                         + sine ** 2 * current_squared)
            lowest = dense_linalg.eigh(
                projected, eigvals_only=True, subset_by_index=(0, 0),
                check_finite=False, overwrite_a=True,
            )[0]
            return math.sqrt(max(0.0, float(lowest)))
        return gap

    def candidates(self, gap):
        phases = np.linspace(0, np.pi, 129)
        values = np.asarray([gap(phase) for phase in phases])
        candidates = [(float(values[0]), 0.0), (float(values[-1]), float(np.pi))]
        for index in range(1, len(phases) - 1):
            if values[index] <= min(values[index - 1], values[index + 1]):
                result = optimize.minimize_scalar(
                    gap, bounds=(phases[index - 1], phases[index + 1]),
                    method="bounded", options={"xatol": 2e-6, "maxiter": 40},
                )
                candidates.append((float(result.fun), float(result.x)))
        return sorted(candidates)

    def minimum_gap(self):
        for phase in np.linspace(0, np.pi, 5):
            self.evaluate(phase)
        best = min(sample["gap"] for sample in self.samples)
        for iteration in range(4):
            projected_gap = self.reduced_spectrum()
            candidates = self.candidates(projected_gap)
            self.log("projected minima", candidates)
            added = 0
            for prediction, phase in candidates:
                if prediction > best + max(0.002, 0.05 * best):
                    continue
                separation = min(abs(phase - sample["phase"]) for sample in self.samples)
                if separation < 2e-4:
                    continue
                elapsed = time.monotonic() - self.started
                typical = max(sample["seconds"] for sample in self.samples)
                if elapsed + 2.5 * typical > 510:
                    break
                sample = self.evaluate(phase)
                added += 1
                best = min(best, sample["gap"])
                if added >= 3:
                    break
            if not added:
                break
            if best < 2e-6:
                break
            if abs(candidates[0][0] - best) < 1e-5:
                break
        self.log("minimum", best, "from", len(self.samples), "full sparse spectra")
        return best


def solve_case(case, verbose=False):
    spectrum = JunctionSpectrum(case, verbose=verbose)
    gap = spectrum.minimum_gap()
    return {"id": case["id"], "strength_meV": spectrum.strength, "gap_meV": gap}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true")
    arguments = parser.parse_args()
    with arguments.input.open() as handle:
        request = json.load(handle)
    results = [solve_case(case, verbose=arguments.verbose) for case in request["cases"]]
    with arguments.output.open("w") as handle:
        json.dump({"results": results}, handle, allow_nan=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
