import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import functools
import json
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.sparse.linalg import LinearOperator, eigsh


TARGETS = ("odd_gap", "even_gap", "odd_spacing")


@functools.lru_cache(maxsize=4)
def operators(fock, frequency):
    indices = np.arange(fock + 4)
    coordinate = np.diag(np.sqrt(indices[1:] / (2 * frequency)), 1)
    coordinate += coordinate.T
    square = coordinate @ coordinate
    fourth = square @ square
    kinetic = np.diag(frequency * (indices + 0.5)) - frequency ** 2 * square / 2
    return tuple(matrix[:fock, :fock] for matrix in (coordinate, square, fourth, kinetic))


def local_basis(mass, quartic, count, fock, frequency):
    coordinate, square, fourth, kinetic = operators(fock, frequency)
    matrix = kinetic + mass * square / 2 + quartic * fourth / 4
    levels = np.empty(count)
    vectors = np.zeros((fock, count))
    for parity in (0, 1):
        values, states = eigh(matrix[parity::2, parity::2], subset_by_index=(0, count // 2 - 1), check_finite=False)
        levels[parity::2] = values
        vectors[parity::2, parity::2] = states
    position = vectors.T @ coordinate @ vectors
    return levels, position


def axis_product(operator, vector, axis):
    return np.moveaxis(np.tensordot(operator, vector, axes=(1, axis)), 0, axis)


def solve(case, count=16, fock=80, frequency=2.0, tolerance=1e-12):
    sites = case["sites"]
    scale = (case["lambda"] / 6.0) ** (1.0 / 3.0)
    masses = np.array(case.get("mu2_by_site", [case["mu2"]] * sites)) / scale ** 2
    quartics = np.array(case.get("lambda_by_site", [case["lambda"]] * sites)) / (6 * scale ** 3)
    couplings = np.array(case.get("kappa_by_bond", [case["kappa"]] * (sites - 1))) / scale ** 2
    diagonal = np.zeros((count,) * sites)
    positions = []
    for site in range(sites):
        degree_term = (couplings[site - 1] if site > 0 else 0.0) + (couplings[site] if site < sites - 1 else 0.0)
        levels, position = local_basis(masses[site] + degree_term, quartics[site], count, fock, frequency)
        shape = [1] * sites
        shape[site] = count
        diagonal += (levels - levels[0]).reshape(shape)
        positions.append(position)
    integers = np.arange(count ** sites, dtype=np.int64)
    parity = np.zeros_like(integers)
    work = integers.copy()
    for site in range(sites):
        parity += work % count
        work //= count
    sectors = []
    state_residuals = []
    for sector in (0, 1):
        indices = integers[parity % 2 == sector]

        def multiply(vector):
            full = np.zeros(count ** sites)
            full[indices] = vector
            tensor = full.reshape((count,) * sites)
            output = diagonal * tensor
            for bond, coupling in enumerate(couplings):
                transformed = axis_product(positions[bond], tensor, bond)
                transformed = axis_product(positions[bond + 1], transformed, bond + 1)
                output -= coupling * transformed
            return output.ravel()[indices]

        operator = LinearOperator((len(indices), len(indices)), matvec=multiply, dtype=float)
        initial = np.sin(np.arange(len(indices)) + 0.123)
        values, vectors = eigsh(operator, k=2, which="SA", tol=tolerance, ncv=24, v0=initial, maxiter=10000)
        order = np.argsort(values)
        values, vectors = values[order], vectors[:, order]
        rayleigh = []
        residuals = []
        for state in range(2):
            product = multiply(vectors[:, state])
            energy = np.sum(product.astype(np.longdouble) * vectors[:, state].astype(np.longdouble))
            rayleigh.append(energy)
            residuals.append(float(np.linalg.norm(product - float(energy) * vectors[:, state])))
        sectors.append(rayleigh)
        state_residuals.append(residuals)
    even, odd = sectors
    gaps = scale * np.array([odd[0] - even[0], even[1] - even[0], odd[1] - odd[0]], dtype=float)
    return {"id": case["id"], "targets": dict(zip(TARGETS, gaps.tolist()))}, {
        "count": count, "fock": fock, "frequency": frequency,
        "dimension": count ** sites // 2, "residuals_dimensionless": state_residuals,
        "shifted_sector_energies_dimensionless": [[float(value) for value in levels] for levels in sectors]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--train", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    configuration_path = Path(__file__).with_name("control.json")
    configuration = json.loads(configuration_path.read_text()) if configuration_path.exists() else {}
    cases = json.loads(Path(arguments.input).read_text())["cases"]
    predictions = []
    diagnostics = []
    for case in cases:
        prediction, diagnostic = solve(case, **configuration)
        predictions.append(prediction)
        diagnostics.append(dict(diagnostic, id=case["id"]))
    output = Path(arguments.output)
    output.write_text(json.dumps({"schema_version": 1, "predictions": predictions}, allow_nan=False))
    output.with_name("diagnostics.json").write_text(json.dumps(diagnostics, allow_nan=False))


if __name__ == "__main__":
    main()
