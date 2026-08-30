import itertools

import numpy as np
from scipy.optimize import least_squares

from experiment import MASKS, ORDERS, SUBSETS, transform


EDGES = np.array(list(itertools.combinations(range(8), 2)))


class Resolvent:
    def __init__(self, energy, orbitals, observed, alpha=0.3):
        self.observed = np.asarray(observed)
        self.energy = energy
        self.gaps = orbitals[3:] + 0.22
        self.alpha = alpha
        self.activity = -energy[MASKS[1]] * (1 - alpha * energy[MASKS[1]] / self.gaps)
        self.scale = np.sqrt(self.activity[:, None] * self.activity[None, :])
        self.occupations = ((self.observed[:, None] >> np.arange(8)[None, :]) & 1).astype(float)
        self.outer = self.occupations[:, :, None] * self.occupations[:, None, :]
        self.mobius = np.eye(len(observed))
        for row, mask in enumerate(observed):
            if ORDERS[mask] <= 3:
                self.mobius[row] = SUBSETS[mask, observed] * (-1.) ** (ORDERS[mask] - ORDERS[observed])
            else:
                for column, subset in enumerate(observed):
                    if ORDERS[subset] <= 3 and SUBSETS[mask, subset]:
                        self.mobius[row, column] = -sum((-1.) ** (ORDERS[child] - ORDERS[subset]) for child in observed if ORDERS[child] <= 3 and SUBSETS[mask, child] and SUBSETS[child, subset])
        self.weights = 1 / np.array([0.02, 0.002, 0.0002, 0.00004, 0.00004, 0.00004])[ORDERS[observed] - 1]
        self.target = self.mobius @ energy[observed]
        self.ridge = np.r_[np.full(28, 0.005), np.full(28, 0.001)]
        self.cache_parameters = None

    def matrices(self, parameters):
        hopping = np.zeros((8, 8))
        hopping[EDGES[:, 0], EDGES[:, 1]] = parameters[:28]
        hopping += hopping.T
        gram = np.diag(self.activity)
        gram[EDGES[:, 0], EDGES[:, 1]] = parameters[28:] * self.scale[EDGES[:, 0], EDGES[:, 1]]
        gram += np.triu(gram, 1).T
        return hopping, gram

    def evaluate(self, parameters, gradient=False):
        if self.cache_parameters is None or not np.array_equal(parameters, self.cache_parameters):
            hopping, gram = self.matrices(parameters)
            matrix = np.eye(8)[None, :, :] + self.outer * hopping[None, :, :]
            matrix[:, np.arange(8), np.arange(8)] -= self.alpha * self.energy[self.observed, None] * self.occupations / self.gaps[None, :]
            inverse = np.linalg.inv(matrix)
            active_gram = gram[None, :, :] * self.outer
            values = -np.einsum('bij,bji->b', inverse, active_gram)
            hopping_gradient = 2 * (inverse @ active_gram @ inverse)[:, EDGES[:, 0], EDGES[:, 1]] * self.outer[:, EDGES[:, 0], EDGES[:, 1]]
            gram_gradient = -2 * inverse[:, EDGES[:, 0], EDGES[:, 1]] * self.scale[EDGES[:, 0], EDGES[:, 1]][None, :] * self.outer[:, EDGES[:, 0], EDGES[:, 1]]
            jacobian = np.concatenate((hopping_gradient, gram_gradient), axis=1)
            residual = (self.mobius @ values - self.target) * self.weights
            jacobian = (self.mobius @ jacobian) * self.weights[:, None]
            eigenvalues, eigenvectors = np.linalg.eigh(np.eye(8) + hopping)
            guard = max(0, 0.3 - eigenvalues[0]) * 10
            guard_gradient = np.zeros(56)
            if guard:
                guard_gradient[:28] = -20 * eigenvectors[EDGES[:, 0], 0] * eigenvectors[EDGES[:, 1], 0]
            self.cache_parameters = parameters.copy()
            self.cache_residual = np.r_[residual, parameters * self.ridge, guard]
            self.cache_jacobian = np.r_[jacobian, np.diag(self.ridge), guard_gradient[None, :]]
        return self.cache_jacobian if gradient else self.cache_residual

    def fit(self, seed=0, iterations=300):
        generator = np.random.default_rng(seed)
        terms = transform(self.energy)
        if seed == 0:
            correlations = np.ones(28) * 0.7
        else:
            vectors = generator.normal(size=(8, 3))
            vectors /= np.linalg.norm(vectors, axis=1)[:, None]
            correlations = (vectors @ vectors.T)[EDGES[:, 0], EDGES[:, 1]]
        pair_values = terms[(1 << EDGES[:, 0]) | (1 << EDGES[:, 1])]
        hopping = np.clip(pair_values / (2 * self.scale[EDGES[:, 0], EDGES[:, 1]] * correlations), -0.25, 0.25)
        parameters = np.r_[hopping, correlations]
        return least_squares(self.evaluate, parameters, jac=lambda values: self.evaluate(values, True), method='lm', max_nfev=iterations, ftol=1e-7, x_scale='jac')

    def predict(self, parameters, masks):
        hopping, gram = self.matrices(parameters)
        occupations = ((np.asarray(masks)[:, None] >> np.arange(8)[None, :]) & 1).astype(float)
        outer = occupations[:, :, None] * occupations[:, None, :]
        energy = -occupations @ self.activity
        for iteration in range(12):
            matrix = np.eye(8)[None, :, :] + outer * hopping[None, :, :]
            matrix[:, np.arange(8), np.arange(8)] -= self.alpha * energy[:, None] * occupations / self.gaps[None, :]
            inverse = np.linalg.inv(matrix)
            energy = -np.einsum('bij,bji->b', inverse, gram[None, :, :] * outer)
        return energy
