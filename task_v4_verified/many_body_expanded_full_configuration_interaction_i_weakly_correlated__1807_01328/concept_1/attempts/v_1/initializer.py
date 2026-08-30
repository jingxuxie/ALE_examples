import itertools

import numpy as np
from scipy.optimize import least_squares

from experiment import MASKS, transform
from physical import PAIR_INDEX, SITE_PAIRS


EDGES = np.array(list(itertools.combinations(range(8), 2)))
LOOKUP = np.zeros((8, 8), dtype=int)
LOOKUP[EDGES[:, 0], EDGES[:, 1]] = np.arange(28)
LOOKUP += LOOKUP.T
TRIANGLES = np.array(list(itertools.combinations(range(8), 3)))
TRI_EDGES = np.stack([LOOKUP[TRIANGLES[:, left], TRIANGLES[:, right]] for left, right in [(0, 1), (0, 2), (1, 2)]], axis=1)
TRI_MASKS = np.sum(1 << TRIANGLES, axis=1)


class Initializer:
    def __init__(self, energy, orbitals):
        self.energy = energy
        self.orbitals = orbitals
        self.activity = -energy[MASKS[1]]
        self.pairs = transform(energy)[(1 << EDGES[:, 0]) | (1 << EDGES[:, 1])]
        self.pair_activity = self.activity[EDGES].sum(axis=1)
        self.triple_activity = self.activity[TRIANGLES]
        self.scale = np.maximum(self.triple_activity.sum(axis=1) * 0.003, 1e-7)

    def values(self, parameters, signs=None):
        squares = np.exp(2 * parameters)
        products = 0.5 * (self.pairs * (1 - squares) + self.pair_activity * squares)
        triangle_squares = squares[TRI_EDGES]
        cycle = np.sqrt(np.prod(triangle_squares, axis=1))
        determinant_base = 1 - triangle_squares.sum(axis=1)
        numerator_base = np.sum(self.triple_activity * (1 - triangle_squares[:, ::-1]), axis=1) - 2 * products[TRI_EDGES].sum(axis=1)
        coefficient = 2 * cycle * np.sum(products[TRI_EDGES] / triangle_squares, axis=1)
        if signs is not None:
            selected_signs = np.prod(signs[TRI_EDGES], axis=1)
            values = -(numerator_base + selected_signs * coefficient) / (determinant_base + 2 * selected_signs * cycle)
        else:
            positive = -(numerator_base + coefficient) / (determinant_base + 2 * cycle)
            negative = -(numerator_base - coefficient) / (determinant_base - 2 * cycle)
            selected_signs = np.where(np.abs(positive - self.energy[TRI_MASKS]) < np.abs(negative - self.energy[TRI_MASKS]), 1, -1)
            values = np.where(selected_signs == 1, positive, negative)
        gram_magnitudes = np.abs(products) / np.sqrt(squares * np.prod(self.activity[EDGES], axis=1))
        return values, selected_signs, gram_magnitudes

    def residual(self, parameters, signs=None):
        values, _, gram_magnitudes = self.values(parameters, signs)
        return np.r_[(values - self.energy[TRI_MASKS]) / self.scale,
                     np.maximum(gram_magnitudes - 1.05, 0) * 0.3,
                     np.exp(parameters) * 0.02]

    def fit(self, seed=0):
        generator = np.random.default_rng(seed)
        initial = np.log(np.clip(np.sqrt(np.abs(self.pairs) / self.pair_activity) * 0.65, 0.02, 0.25))
        if seed:
            initial += generator.normal(0, 0.4, 28)
        result = least_squares(self.residual, initial, bounds=(-6, -0.5), max_nfev=100, ftol=1e-5)
        _, triangle_signs, _ = self.values(result.x)
        triple_lookup = {tuple(triangle): sign for triangle, sign in zip(TRIANGLES, triangle_signs)}
        best = None
        for anchor in range(8):
            signs = np.ones(28)
            for index, (left, right) in enumerate(EDGES):
                if left != anchor and right != anchor:
                    signs[index] = triple_lookup[tuple(sorted((anchor, left, right)))]
            score = np.linalg.norm(self.residual(result.x, signs))
            if best is None or score < best[0]:
                best = score, signs
        signs = best[1]
        parameters = result.x
        for iteration in range(3):
            result = least_squares(lambda values: self.residual(values, signs), parameters, bounds=(-6, -0.5), max_nfev=70, ftol=1e-5)
            parameters = result.x
            score = np.linalg.norm(result.fun)
            for index in range(28):
                signs[index] *= -1
                new_score = np.linalg.norm(self.residual(parameters, signs))
                if new_score < score:
                    score = new_score
                else:
                    signs[index] *= -1
        hopping = np.exp(parameters) * signs
        squares = hopping ** 2
        gram_values = 0.5 * (self.pairs * (1 - squares) + self.pair_activity * squares) / hopping
        gram = np.diag(self.activity)
        gram[EDGES[:, 0], EDGES[:, 1]] = gram_values
        gram += np.triu(gram, 1).T
        eigenvalues, eigenvectors = np.linalg.eigh(gram)
        amplitudes = eigenvectors[:, -3:] * np.sqrt(np.maximum(eigenvalues[-3:], 1e-10))[None, :]
        amplitudes *= np.sqrt(self.activity / np.sum(amplitudes ** 2, axis=1))[:, None]
        matrix = np.zeros((11, 11))
        gaps = self.orbitals[3:] + 0.22
        matrix[:3, 3:] = amplitudes.T * np.sqrt(gaps)[None, :]
        matrix[EDGES[:, 0] + 3, EDGES[:, 1] + 3] = hopping * np.sqrt(gaps[EDGES[:, 0]] * gaps[EDGES[:, 1]])
        output = np.zeros(110)
        output[:55] = matrix[SITE_PAIRS[:, 0], SITE_PAIRS[:, 1]]
        return output, score
