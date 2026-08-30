import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import sys
import time

import numpy as np
from scipy.optimize import least_squares


LOWER = np.array([0.55] * 6 + [-0.5] * 5 + [0.3, 0.05, 0.05] + [0.002] * 6)
UPPER = np.array([1.45] * 6 + [0.5] * 5 + [1.7, 0.5, 0.5] + [0.05] * 6)
SCALE = UPPER - LOWER
STATES = np.array([mask for mask in range(64) if mask.bit_count() == 3])
INDEX = {int(mask): index for index, mask in enumerate(STATES)}
OCC = ((STATES[:, None] >> np.arange(6)) & 1).astype(float)
SPIN = OCC - 0.5
DIAG = np.arange(20)
EXCHANGE = np.zeros((8, 20, 20))
ISING = np.zeros((8, 20))
for offset in (1, 2):
    for site in range(6):
        other = (site + offset) % 6
        bond = site if offset == 1 else 6 + site % 2
        ISING[bond] += SPIN[:, site] * SPIN[:, other]
        for state_index, mask in enumerate(STATES):
            if ((mask >> site) & 1) != ((mask >> other) & 1):
                EXCHANGE[bond, INDEX[int(mask) ^ (1 << site) ^ (1 << other)], state_index] += 0.5
DIFFER = (((np.arange(64)[:, None, None] >> np.arange(6)) & 1) != OCC[None, :, :])


class Model:
    def __init__(self, experiments):
        self.times = np.array([experiment["time"] for experiment in experiments])
        self.preps = np.array([INDEX[experiment["preparation"]] for experiment in experiments])
        phases = np.array([experiment["phases"] for experiment in experiments])
        self.kicks = np.exp(-1j * (phases @ OCC.T))

    def evaluate(self, normalized, jacobian=True):
        parameters = LOWER + SCALE * normalized
        couplings = parameters[np.r_[0:6, 12:14]]
        matrix = np.einsum("b,bij->ij", couplings, EXCHANGE)
        diagonal = couplings @ ISING
        matrix[DIAG, DIAG] += parameters[11] * diagonal + (SPIN[:, :5] - SPIN[:, 5, None]) @ parameters[6:11]
        energies, vectors = np.linalg.eigh(matrix)
        half = np.exp(-0.5j * self.times[:, None] * energies)
        initial = vectors[self.preps]
        first = (half * initial) @ vectors.T
        middle = (self.kicks * first) @ vectors
        final = (half * middle) @ vectors.T
        populations = np.abs(final) ** 2
        errors = parameters[14:20]
        detector = np.prod(np.where(DIFFER, errors, 1.0 - errors), axis=2)
        predictions = np.maximum(populations @ detector.T, 1e-300)
        if not jacobian:
            return predictions
        derivative = np.zeros((14, 20, 20))
        for parameter, bond in enumerate(range(6)):
            derivative[parameter] = EXCHANGE[bond]
            derivative[parameter, DIAG, DIAG] += parameters[11] * ISING[bond]
        for site in range(5):
            derivative[6 + site, DIAG, DIAG] = SPIN[:, site] - SPIN[:, 5]
        derivative[11, DIAG, DIAG] = diagonal
        for bond in range(2):
            derivative[12 + bond] = EXCHANGE[6 + bond]
            derivative[12 + bond, DIAG, DIAG] += parameters[11] * ISING[6 + bond]
        derivative *= SCALE[:14, None, None]
        rotated = vectors.T @ derivative @ vectors
        duration = self.times[:, None, None] * 0.5
        differences = energies[:, None] - energies[None, :]
        means = (energies[:, None] + energies[None, :]) * 0.5
        frechet = (-1j * duration) * np.exp(-1j * duration * means) * np.sinc(duration * differences / (2 * np.pi))
        first_derivative = np.einsum("eij,aij,ej->eai", frechet, rotated, initial, optimize=True)
        final_derivative = np.einsum("eij,aij,ej->eai", frechet, rotated, middle, optimize=True)
        final_derivative += half[:, None, :] * (((first_derivative @ vectors.T) * self.kicks[:, None, :]) @ vectors)
        final_derivative = final_derivative @ vectors.T
        population_derivative = 2 * (final[:, None, :].conj() * final_derivative).real
        gradients = np.empty((len(self.times), 64, 20))
        gradients[:, :, :14] = (population_derivative @ detector.T).transpose(0, 2, 1)
        detector_derivative = detector[:, :, None] * np.where(DIFFER, 1 / errors, -1 / (1 - errors)) * SCALE[14:20]
        gradients[:, :, 14:20] = np.einsum("es,osa->eoa", populations, detector_derivative, optimize=True)
        return predictions, gradients


class Likelihood:
    def __init__(self, experiments, counts):
        self.model = Model(experiments)
        self.counts = np.array(counts, dtype=float)
        self.shots = self.counts.sum(axis=1)[:, None]
        self.last = None

    def calculate(self, normalized):
        if self.last is not None and np.array_equal(self.last, normalized):
            return
        predictions, gradients = self.model.evaluate(normalized)
        expected = predictions * self.shots
        nonzero = self.counts > 0
        ratio = np.zeros_like(expected)
        ratio[nonzero] = (expected[nonzero] - self.counts[nonzero]) / self.counts[nonzero]
        ratio = np.maximum(ratio, -1 + 1e-15)
        core = ratio - np.log1p(ratio)
        small = np.abs(ratio) < 1e-4
        core[small] = ratio[small] ** 2 * (0.5 - ratio[small] / 3 + ratio[small] ** 2 / 4)
        deviance = np.where(nonzero, 2 * self.counts * core, 2 * expected)
        residual = np.sign(expected - self.counts) * np.sqrt(np.maximum(deviance, 0))
        factor = np.empty_like(expected)
        regular = np.abs(residual) > 1e-7
        factor[regular] = (1 - self.counts[regular] / expected[regular]) / residual[regular]
        factor[~regular] = 1 / np.sqrt(np.maximum(expected[~regular], 1e-30))
        self.residual = residual.ravel()
        self.jacobian = (gradients * (factor * self.shots)[:, :, None]).reshape(-1, 20)
        self.last = normalized.copy()

    def fun(self, normalized):
        self.calculate(normalized)
        return self.residual

    def jac(self, normalized):
        self.calculate(normalized)
        return self.jacobian


def fit_data(experiments, counts, initial, max_nfev=90):
    likelihood = Likelihood(experiments, counts)
    fit = least_squares(likelihood.fun, np.clip(initial, 1e-7, 1 - 1e-7), jac=likelihood.jac,
                        bounds=(np.zeros(20), np.ones(20)), max_nfev=max_nfev,
                        ftol=2e-7, xtol=2e-7, gtol=2e-5)
    return fit.x, 2 * fit.cost, fit.nfev


def experiment(preparation, duration, phases):
    return {"type": "query", "preparation": int(preparation), "time": float(duration),
            "phases": np.asarray(phases, dtype=float).tolist()}


