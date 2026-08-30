"""Deterministic, covariance-whitened, regularized nonnegative least squares."""

import argparse
import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import nnls


def solve(input_path, output_path):
    with np.load(input_path, allow_pickle=False) as archive:
        inputs = {name: archive[name] for name in archive.files}
    edges = inputs["omega_edges"]
    omega = (edges[:-1] + edges[1:]) / 2.0
    centers = np.linspace(-7.75, 7.75, 81)
    basis = np.exp(-0.5 * ((omega[:, None] - centers[None, :]) / 0.28) ** 2)
    basis /= basis.sum(axis=0, keepdims=True)
    nodes, weights = np.polynomial.legendre.leggauss(6)
    frequencies = omega[:, None] + np.diff(edges)[:, None] / 2.0 * nodes
    regularizer = 20.0 * np.eye(len(centers))
    norm_row = np.full((1, len(centers)), 1e4)
    mass = np.empty((len(inputs["sample_id"]), len(omega)))
    for row, beta in enumerate(inputs["beta"]):
        exponent = -inputs["tau"][row, :, None, None] * frequencies[None, :, :]
        exponent -= np.logaddexp(0.0, -beta * frequencies)[None, :, :]
        response = np.exp(exponent) @ (weights / 2.0)
        chol = np.linalg.cholesky(inputs["covariance"][row])
        design = solve_triangular(chol, response @ basis, lower=True)
        target = solve_triangular(chol, inputs["correlation"][row], lower=True)
        augmented = np.vstack((design, regularizer, norm_row))
        values = np.concatenate((target, np.zeros(len(centers)), [1e4]))
        coefficients, _ = nnls(augmented, values, maxiter=2000)
        mass[row] = basis @ coefficients
        mass[row] /= mass[row].sum()
    overlap = np.maximum(0.0, np.minimum(edges[1:], 0.5) - np.maximum(edges[:-1], -0.5)) / np.diff(edges)
    low_mass = mass @ overlap
    quantiles = np.clip(low_mass[:, None] + np.array([-0.035, 0.0, 0.035]), 0.0, 1.0)
    np.savez_compressed(output_path, sample_id=inputs["sample_id"], spectral_mass=mass, low_mass_quantiles=quantiles)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    arguments = parser.parse_args()
    solve(arguments.input, arguments.output)
