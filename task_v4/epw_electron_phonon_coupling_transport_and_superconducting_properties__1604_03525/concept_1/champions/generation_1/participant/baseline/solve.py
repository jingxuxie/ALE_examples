import argparse
import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import nnls
from threadpoolctl import threadpool_limits


def predict(inputs):
    omega = inputs['omega_mev']
    widths = inputs['domega_mev']
    centers = np.geomspace(1.0, 115.0, 64)
    spreads = 1.3 + 0.045 * centers
    basis = np.exp(-0.5 * ((omega[:, None] - centers[None, :]) / spreads[None, :]) ** 2)
    basis *= (omega[:, None] ** 2 / (omega[:, None] ** 2 + 4))
    basis /= np.sum(basis * (2 * widths / omega)[:, None], axis=0)
    mass_basis = (2 * widths / omega)[:, None] * basis
    prediction = []
    for row in range(len(inputs['interaction'])):
        slots = np.flatnonzero(inputs['mask'][row])
        nu = inputs['nu_mev'][row, slots]
        kernel = omega[None, :] ** 2 / (omega[None, :] ** 2 + nu[:, None] ** 2)
        standard = inputs['noise_std'][row, slots]
        rho = inputs['noise_rho'][row]
        length = inputs['noise_length'][row]
        correlation = (1 - rho) * np.eye(len(slots)) + rho * np.exp(-np.abs(slots[:, None] - slots[None, :]) / length)
        covariance = standard[:, None] * correlation * standard[None, :]
        root = np.linalg.cholesky(covariance)
        matrix = solve_triangular(root, kernel @ mass_basis, lower=True)
        target = solve_triangular(root, inputs['interaction'][row, slots], lower=True)
        matrix = np.vstack([matrix, 15 * np.eye(len(centers))])
        target = np.concatenate([target, np.zeros(len(centers))])
        coefficients, _ = nnls(matrix, target, maxiter=2000)
        prediction.append(basis @ coefficients)
    return np.array(prediction)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as archive:
        inputs = dict(archive)
    with threadpool_limits(limits=1):
        alpha2f = predict(inputs)
    np.savez_compressed(args.output, alpha2f=alpha2f)


if __name__ == '__main__':
    main()
