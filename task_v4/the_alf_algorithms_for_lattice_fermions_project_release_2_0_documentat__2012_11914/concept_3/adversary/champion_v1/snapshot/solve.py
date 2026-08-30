import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import sys
import time
from pathlib import Path
import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import least_squares, nnls
from models import spectrum, MODELS, OMEGA


class Objective:
    def __init__(self, design, target, model, prior=.8):
        self.design = design
        self.target = target
        self.model = model
        self.prior = prior
        self.previous = None

    def calculate(self, parameters):
        if self.previous is None or not np.array_equal(parameters, self.previous):
            self.mass, derivative = spectrum(parameters, self.model)
            self.residual = np.concatenate((self.design @ self.mass - self.target, self.prior * (parameters - .5)))
            self.jacobian = np.vstack((self.design @ derivative, self.prior * np.eye(len(parameters))))
            self.previous = parameters.copy()

    def fun(self, parameters):
        self.calculate(parameters)
        return self.residual

    def jac(self, parameters):
        self.calculate(parameters)
        return self.jacobian


def kernel(beta, tau, edges):
    nodes, weights = np.polynomial.legendre.leggauss(6)
    omega = (edges[:-1] + edges[1:])[:, None] / 2 + np.diff(edges)[:, None] * nodes / 2
    exponent = -tau[:, None, None] * omega[None, :, :] - np.logaddexp(0, -beta * omega)[None, :, :]
    return np.exp(exponent) @ (weights / 2)


def nonparametric(design, target, regularization=10):
    centers = np.linspace(-6.5, 6.5, 97)
    basis = np.exp(-.5 * ((OMEGA[:, None] - centers) / .23)**2)
    basis /= basis.sum(axis=0)
    matrix = design @ basis
    augmented = np.vstack((matrix, regularization * np.eye(len(centers)), np.full((1, len(centers)), 1e4)))
    values = np.r_[target, np.zeros(len(centers)), 1e4]
    coefficients = nnls(augmented, values, maxiter=1500)[0]
    mass = basis @ coefficients
    mass /= mass.sum()
    error = design @ mass - target
    return mass, error @ error


def solve(input_path, output_path):
    started = time.monotonic()
    data = dict(np.load(input_path, allow_pickle=False))
    pool = dict(np.load(Path(__file__).with_name('pool.npz'), allow_pickle=False))
    count = len(data['beta'])
    masses = np.empty((count, 256))
    quantiles = np.empty((count, 3))
    records = []
    prior = float(os.environ.get('PRIOR', '.8'))
    starts = int(os.environ.get('STARTS', '2'))
    for row, beta in enumerate(data['beta']):
        response = kernel(beta, data['tau'][row], data['omega_edges'])
        chol = np.linalg.cholesky(data['covariance'][row])
        design = solve_triangular(chol, response, lower=True)
        target = solve_triangular(chol, data['correlation'][row], lower=True)
        left, singular, right = np.linalg.svd(design, full_matrices=False)
        rank = 24
        projected = singular[:rank, None] * right[:rank]
        observations = left[:, :rank].T @ target
        allmass, allchi, allscore, allparameters, allstd = [], [], [], [], []
        for model, (family, sign) in enumerate(MODELS):
            differences = projected @ pool['m' + str(model)].T - observations[:, None]
            distances = (differences**2).sum(axis=0)
            indices = np.argsort(distances)[:starts]
            objective = Objective(projected, observations, model, prior)
            best = None
            for index in indices:
                initial = pool['p' + str(model)][index]
                fit = least_squares(objective.fun, initial, jac=objective.jac, bounds=(np.zeros(len(initial)), np.ones(len(initial))), max_nfev=90, ftol=2e-5, xtol=2e-5, gtol=2e-5)
                if best is None or fit.cost < best.cost:
                    best = fit
            objective.calculate(best.x)
            mass = objective.mass.copy()
            residual = projected @ mass - observations
            chi = residual @ residual
            jacobian = objective.jacobian[:rank]
            hessian = jacobian.T @ jacobian + 12 * np.eye(len(best.x))
            covariance = np.linalg.inv(hessian)
            derivative = spectrum(best.x, model)[1]
            lowjac = derivative[120:136].sum(axis=0)
            lowstd = np.sqrt(lowjac @ covariance @ lowjac)
            score = chi + np.linalg.slogdet(np.eye(len(best.x)) + jacobian.T @ jacobian / 12)[1]
            allmass.append(mass)
            allchi.append(chi)
            allscore.append(score)
            allparameters.append(best.x)
            allstd.append(lowstd)
        mass, chi = nonparametric(projected, observations)
        allmass.append(mass)
        allchi.append(chi)
        allscore.append(chi + 65)
        allstd.append(.012)
        scores = np.array(allscore)
        weights = np.exp(-.5 * (scores - scores.min()))
        weights /= weights.sum()
        masses[row] = weights @ np.array(allmass)
        low = masses[row, 120:136].sum()
        spread = np.sqrt(np.sum(weights * (np.array(allstd)**2 + (np.array(allmass)[:, 120:136].sum(axis=1) - low)**2)))
        quantiles[row] = np.clip(low + np.array([-1.2816, 0, 1.2816]) * spread, 0, 1)
        records.append((allmass, allchi, allscore, allstd))
        if os.environ.get('DEBUG') and row % 16 == 0:
            print(row, round(time.monotonic() - started, 2), np.round(allchi, 1), flush=True)
    np.savez_compressed(output_path, sample_id=data['sample_id'], spectral_mass=masses, low_mass_quantiles=quantiles)
    if os.environ.get('DEBUG'):
        np.savez_compressed(str(output_path) + '.debug.npz', mass=np.array([record[0] for record in records]), chi=np.array([record[1] for record in records]), score=np.array([record[2] for record in records]), std=np.array([record[3] for record in records]))
        print('runtime', time.monotonic() - started, flush=True)


if __name__ == '__main__':
    solve(sys.argv[1], sys.argv[2])
