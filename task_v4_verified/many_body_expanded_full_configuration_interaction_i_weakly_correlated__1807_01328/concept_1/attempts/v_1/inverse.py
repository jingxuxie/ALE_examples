import itertools
import time

import numpy as np
from scipy.optimize import least_squares

from experiment import MASKS, ORDERS, SUBSETS, report, transform


PAIRS = np.array(list(itertools.combinations(range(8), 2)))
ROOTS = np.arange(8)


class Inverse:
    def __init__(self, terms, rank=3, observed=None):
        self.terms = terms
        self.rank = rank
        self.scale = np.sqrt(np.maximum(-terms[MASKS[1]], 1e-12))
        self.observed = np.concatenate((MASKS[2], MASKS[3])) if observed is None else np.array(observed)
        needed = np.flatnonzero(np.any(SUBSETS[self.observed], axis=0) & (ORDERS >= 2))
        self.needed = needed
        self.occupations = ((needed[:, None] >> ROOTS[None, :]) & 1).astype(float)
        self.outer = self.occupations[:, :, None] * self.occupations[:, None, :]
        self.mobius = SUBSETS[self.observed][:, needed] * (-1.0) ** (ORDERS[self.observed, None] - ORDERS[needed][None, :])
        self.offset = np.sum(SUBSETS[self.observed][:, MASKS[1]] * terms[MASKS[1]][None, :] * (-1.0) ** (ORDERS[self.observed, None] - 1), axis=1)
        self.weights = 1 / np.maximum(np.sum(SUBSETS[self.observed][:, MASKS[1]] * (-terms[MASKS[1]])[None, :], axis=1), 0.003)

    def evaluate(self, parameters, jacobian=False, masks=None):
        vectors = parameters[28:].reshape(8, self.rank)
        norms = np.linalg.norm(vectors, axis=1)
        vectors = vectors / norms[:, None]
        amplitudes = self.scale[:, None] * vectors
        gram = amplitudes @ amplitudes.T
        hopping = np.zeros((8, 8))
        hopping[PAIRS[:, 0], PAIRS[:, 1]] = parameters[:28]
        hopping += hopping.T
        if masks is None:
            outer = self.outer
            occupations = self.occupations
        else:
            occupations = ((np.asarray(masks)[:, None] >> ROOTS[None, :]) & 1).astype(float)
            outer = occupations[:, :, None] * occupations[:, None, :]
        inverse = np.linalg.inv(np.eye(8)[None, :, :] + hopping[None, :, :] * outer)
        active_gram = gram[None, :, :] * outer
        energy = -np.einsum('bij,bji->b', inverse, active_gram)
        if masks is not None:
            return energy
        predicted = self.mobius @ energy + self.offset
        residual = (predicted - self.terms[self.observed]) * self.weights
        if not jacobian:
            return residual
        hopping_gradient = 2 * (inverse @ active_gram @ inverse)[:, PAIRS[:, 0], PAIRS[:, 1]] * outer[:, PAIRS[:, 0], PAIRS[:, 1]]
        vector_gradient = -2 * (inverse @ (amplitudes[None, :, :] * occupations[:, :, None])) * (self.scale[None, :, None] * occupations[:, :, None])
        vector_gradient = (vector_gradient - np.sum(vector_gradient * vectors[None, :, :], axis=2)[:, :, None] * vectors[None, :, :]) / norms[None, :, None]
        gradient = np.concatenate((hopping_gradient, vector_gradient.reshape(len(energy), -1)), axis=1)
        return (self.mobius @ gradient) * self.weights[:, None]

    def fit(self, seed=0, iterations=100):
        generator = np.random.default_rng(seed)
        parameters = np.concatenate((generator.normal(0, 0.08, 28), generator.normal(size=8 * self.rank)))
        result = least_squares(self.evaluate, parameters, jac=lambda params: self.evaluate(params, True), max_nfev=iterations, method='lm', ftol=1e-8)
        return result


def main():
    data = np.load('train.npz')
    energies, families = data['energies'][-1800:], data['families'][-1800:]
    terms = transform(energies)
    selected = np.arange(18)
    started = time.time()
    for index in selected:
        problem = Inverse(terms[index])
        best = None
        for seed in range(3):
            result = problem.fit(seed=seed, iterations=120)
            predicted = transform(problem.evaluate(result.x, masks=np.arange(256)))
            error = (predicted[ORDERS >= 4] - terms[index, ORDERS >= 4]).sum()
            record = (np.linalg.norm(result.fun), error, result.nfev)
            if best is None or record[0] < best[0]:
                best = record
        print(index, families[index], best, time.time() - started, flush=True)


if __name__ == '__main__':
    main()
