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


def initial_experiments():
    random = np.random.default_rng(83471)
    preparations = [21, 7, 25, 42, 11, 38, 28, 49]
    durations = [0.65, 1.1, 1.45, 1.7, 2.0, 2.2, 2.5, 2.7]
    return [experiment(preparation, duration, random.uniform(-1.6, 1.6, 6))
            for preparation, duration in zip(preparations, durations)]


def information(predictions, gradients):
    return np.einsum("eoi,eoj->eij", gradients / np.sqrt(predictions[:, :, None]),
                     gradients / np.sqrt(predictions[:, :, None]), optimize=True)


def choose_experiment(normalized, experiments, random, max_time=6.0):
    predictions, gradients = Model(experiments).evaluate(normalized)
    current = information(predictions, gradients).sum(axis=0) + np.eye(20) * 0.002
    candidates = []
    for index in range(160):
        preparation = STATES[index % 20]
        duration = random.uniform(2.5, max_time) if max_time > 2.5 else max_time
        if index < 20:
            duration = random.uniform(0, 1.0)
        elif index < 40:
            duration = random.uniform(1, 3)
        phases = random.uniform(-np.pi, np.pi, 6)
        if index % 8 == 0:
            phases *= 0
        candidates.append(experiment(preparation, duration, phases))
    candidate_p, candidate_j = Model(candidates).evaluate(normalized)
    candidate_information = information(candidate_p, candidate_j)
    covariances = np.linalg.inv(current[None, :, :] + candidate_information)
    scores = np.trace(covariances, axis1=1, axis2=2)
    return candidates[int(np.argmin(scores))]


def run_controller(query, config, diagnostic=False):
    began = time.process_time()
    random = np.random.default_rng(51923)
    experiments = []
    counts = []
    for setting in initial_experiments()[:config["query_budget"]]:
        experiments.append(setting)
        counts.append(query(setting))
    starts = [np.full(20, 0.5)]
    for field_level in (0.2, 0.8):
        initial = np.full(20, 0.5)
        initial[6:11] = field_level
        starts.append(initial)
    best = None
    for initial in starts:
        result = fit_data(experiments, counts, initial)
        if diagnostic:
            print("initial", result[1], result[2], time.process_time() - began, file=sys.stderr, flush=True)
        if best is None or result[1] < best[1]:
            best = result
    if best[1] > 650:
        for attempt in range(48):
            initial = best[0].copy()
            initial[:14] = random.uniform(0.05, 0.95, 14)
            if attempt % 3 == 0:
                initial = fit_data(experiments[:6], counts[:6], initial, max_nfev=75)[0]
            result = fit_data(experiments, counts, initial)
            if diagnostic:
                print("restart", attempt, result[1], time.process_time() - began, file=sys.stderr, flush=True)
            if result[1] < best[1]:
                best = result
            if best[1] <= 650 or time.process_time() - began > 35:
                break
    normalized = best[0]
    while len(experiments) < config["query_budget"]:
        setting = choose_experiment(normalized, experiments, random)
        experiments.append(setting)
        counts.append(query(setting))
        normalized, cost, evaluations = fit_data(experiments, counts, normalized, max_nfev=55)
        if cost > max(650, 75 * len(experiments)) and time.process_time() - began < 65:
            for attempt in range(24):
                initial = normalized.copy()
                initial[:14] = random.uniform(0.05, 0.95, 14)
                initial = fit_data(experiments[:6], counts[:6], initial, max_nfev=75)[0]
                initial = fit_data(experiments[:8], counts[:8], initial, max_nfev=75)[0]
                candidate, candidate_cost, candidate_evaluations = fit_data(experiments, counts, initial)
                if candidate_cost < cost:
                    normalized, cost, evaluations = candidate, candidate_cost, candidate_evaluations
                if cost <= max(650, 75 * len(experiments)) or time.process_time() - began > 75:
                    break
        if diagnostic:
            print("step", len(experiments), "time", round(setting["time"], 2), "cost", round(cost, 2),
                  "eval", evaluations, "cpu", round(time.process_time() - began, 2), file=sys.stderr, flush=True)
    return LOWER + SCALE * normalized


def main():
    start = json.loads(sys.stdin.readline())

    def query(setting):
        print(json.dumps(setting), flush=True)
        response = json.loads(sys.stdin.readline())
        return response["counts"]

    parameters = run_controller(query, start["config"])
    print(json.dumps({"type": "answer", "parameters": parameters.tolist()}), flush=True)


if __name__ == "__main__":
    main()
