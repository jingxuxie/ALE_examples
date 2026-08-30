import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import sys
import time

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares


LOWER = np.array([0.55] * 6 + [-0.5] * 5 + [0.3, 0.05, 0.05] + [0.002] * 6)
UPPER = np.array([1.45] * 6 + [0.5] * 5 + [1.7, 0.5, 0.5] + [0.05] * 6)
WIDTH = UPPER - LOWER
STATES = np.array([mask for mask in range(64) if mask.bit_count() == 3])
OCC = ((STATES[:, None] >> np.arange(6)) & 1).astype(float)
SPIN = OCC - 0.5
INDEX = {int(mask): index for index, mask in enumerate(STATES)}
BITS = (np.arange(64)[:, None] >> np.arange(6)) & 1
DIFFERENCES = BITS[:, None, :] != OCC[None, :, :]
EXCHANGE = np.zeros((8, 20, 20))
ISING = np.zeros((8, 20))
for offset in (1, 2):
    for site in range(6):
        neighbor = (site + offset) % 6
        bond = site if offset == 1 else 6 + site % 2
        ISING[bond] += SPIN[:, site] * SPIN[:, neighbor]
        for index, mask in enumerate(STATES):
            if ((mask >> site) & 1) != ((mask >> neighbor) & 1):
                EXCHANGE[bond, INDEX[int(mask) ^ (1 << site) ^ (1 << neighbor)], index] += 0.5
DIAGONAL = np.diag_indices(20)
FIELD = SPIN[:, :5] - SPIN[:, 5:6]


class Model:
    def __init__(self, experiments):
        self.times = np.array([experiment["time"] for experiment in experiments])
        self.indices = np.array([INDEX[experiment["preparation"]] for experiment in experiments])
        self.kicks = np.exp(-1j * (np.array([experiment["phases"] for experiment in experiments]) @ OCC.T))

    def evaluate(self, normalized, derivatives=True):
        parameters = LOWER + WIDTH * normalized
        couplings = np.r_[parameters[:6], parameters[12:14]]
        hamiltonian = np.einsum("b,bij->ij", couplings, EXCHANGE)
        hamiltonian[DIAGONAL] += parameters[11] * (couplings @ ISING) + FIELD @ parameters[6:11]
        energies, vectors = eigh(hamiltonian, check_finite=False, driver="evr")
        half = self.times / 2
        propagators = np.exp(-1j * half[:, None] * energies)
        initial = vectors[self.indices]
        middle = (propagators * initial) @ vectors.T
        kicked = middle * self.kicks
        middle_eigen = kicked @ vectors
        final = (propagators * middle_eigen) @ vectors.T
        populations = np.abs(final) ** 2
        detector = np.prod(np.where(DIFFERENCES, parameters[14:20], 1 - parameters[14:20]), axis=2)
        predictions = populations @ detector.T
        predictions = np.maximum(predictions, 1e-15)
        if not derivatives:
            return predictions
        directions = np.zeros((14, 20, 20))
        directions[:6] = EXCHANGE[:6]
        directions[:6, DIAGONAL[0], DIAGONAL[1]] += parameters[11] * ISING[:6]
        directions[6:11, DIAGONAL[0], DIAGONAL[1]] = FIELD.T
        directions[11, DIAGONAL[0], DIAGONAL[1]] = couplings @ ISING
        directions[12:14] = EXCHANGE[6:8]
        directions[12:14, DIAGONAL[0], DIAGONAL[1]] += parameters[11] * ISING[6:8]
        directions *= WIDTH[:14, None, None]
        transformed = vectors.T @ directions @ vectors
        difference = energies[:, None] - energies[None, :]
        average = (energies[:, None] + energies[None, :]) / 2
        divided = -1j * half[:, None, None] * np.exp(-1j * half[:, None, None] * average)
        divided *= np.sinc(half[:, None, None] * difference / (2 * np.pi))
        frechet = divided[:, None, :, :] * transformed[None, :, :, :]
        first = (frechet @ initial[:, None, :, None])[..., 0] @ vectors.T
        first = (first * self.kicks[:, None, :]) @ vectors
        second = (frechet @ middle_eigen[:, None, :, None])[..., 0]
        final_gradient = (first * propagators[:, None, :] + second) @ vectors.T
        population_gradient = 2 * np.real(final[:, None, :].conj() * final_gradient)
        gradient = np.empty((len(self.times), 64, 20))
        gradient[:, :, :14] = (population_gradient @ detector.T).transpose(0, 2, 1)
        detector_gradient = detector[:, :, None] * np.where(DIFFERENCES, 1 / parameters[14:20], -1 / (1 - parameters[14:20]))
        gradient[:, :, 14:] = np.einsum("es,osd->eod", populations, detector_gradient) * WIDTH[14:]
        return predictions, gradient


class Objective:
    def __init__(self, experiments, counts):
        self.model = Model(experiments)
        self.data = np.asarray(counts) / np.asarray(counts).sum(axis=1)[:, None]
        self.last = None

    def compute(self, normalized):
        if self.last is not None and np.array_equal(normalized, self.last):
            return
        self.last = normalized.copy()
        probability, derivative = self.model.evaluate(normalized)
        ratio = self.data / probability
        delta = probability - self.data
        divergence = delta.copy()
        nonzero = self.data > 0
        divergence[nonzero] += self.data[nonzero] * np.log(ratio[nonzero])
        root = np.sqrt(np.maximum(2 * divergence, 1e-25))
        self.residual = (np.sign(delta) * root).ravel()
        weight = np.abs(1 - ratio) / root
        close = np.abs(delta) < 1e-6 * probability
        weight[close] = 1 / np.sqrt(probability[close])
        self.jacobian = (weight[:, :, None] * derivative).reshape(-1, 20)

    def fun(self, normalized):
        self.compute(normalized)
        return self.residual

    def jac(self, normalized):
        self.compute(normalized)
        return self.jacobian


def fit_parameters(experiments, counts, starts, max_nfev=90):
    objective = Objective(experiments, counts)
    best = None
    for start in starts:
        fitted = least_squares(objective.fun, np.clip(start, 1e-7, 1 - 1e-7), jac=objective.jac,
                               bounds=(0, 1), max_nfev=max_nfev, ftol=2e-7, xtol=2e-7, gtol=1e-7)
        if best is None or fitted.cost < best.cost:
            best = fitted
    return best.x, best.cost


def experiment(preparation, duration, phases):
    return {"type": "query", "preparation": int(preparation), "time": float(duration), "phases": np.asarray(phases).tolist()}


def initial_experiments():
    random = np.random.default_rng(18717)
    result = [experiment(21, 0, np.zeros(6))]
    for preparation, duration in zip([7, 21, 25, 42, 13, 38, 11, 52], [1.25, 1.4, 1.65, 1.8, 2.1, 2.3, 2.6, 2.7]):
        result.append(experiment(preparation, duration, random.uniform(-1.6, 1.6, 6)))
    return result


def select_experiment(normalized, experiments, random, shots=2048):
    probability, gradient = Model(experiments).evaluate(normalized)
    information = shots * np.einsum("eoi,eoj,eo->ij", gradient, gradient, 1 / probability)
    candidates = [experiment(21, 0, np.zeros(6))]
    for index in range(160):
        duration = random.uniform(2, 6)
        phases = random.uniform(-np.pi, np.pi, 6)
        if index % 4 == 0:
            phases = np.zeros(6)
        candidates.append(experiment(random.choice(STATES), duration, phases))
    probability, gradient = Model(candidates).evaluate(normalized)
    gains = shots * np.einsum("eoi,eoj,eo->eij", gradient, gradient, 1 / probability)
    inverses = np.linalg.inv(information[None] + gains + 1e-5 * np.eye(20))
    risks = np.trace(inverses, axis1=1, axis2=2)
    return candidates[np.argmin(risks)]


def run_controller(query, config, diagnostics=False):
    begin = time.process_time()
    random = np.random.default_rng(71183)
    experiments = []
    counts = []
    normalized = np.full(20, 0.5)
    for request in initial_experiments()[:config["query_budget"]]:
        counts.append(query(request))
        experiments.append(request)
    zero_counts = np.asarray(counts[0])
    errors = zero_counts @ (BITS != OCC[INDEX[21]]) / zero_counts.sum()
    normalized[14:] = np.clip((errors - LOWER[14:]) / WIDTH[14:], 0.01, 0.99)
    starts = [normalized.copy()]
    for field_level in (0.2, 0.8):
        start = normalized.copy()
        start[6:11] = field_level
        starts.append(start)
    for index in range(3):
        start = normalized.copy()
        start[:14] = random.uniform(0.1, 0.9, 14)
        starts.append(start)
    normalized, cost = fit_parameters(experiments, counts, starts)
    if diagnostics:
        print("initial", cost, "cpu", time.process_time() - begin, file=sys.stderr, flush=True)
    while len(experiments) < config["query_budget"]:
        request = select_experiment(normalized, experiments, random, config["shots"])
        counts.append(query(request))
        experiments.append(request)
        normalized, cost = fit_parameters(experiments, counts, [normalized], max_nfev=45)
        if diagnostics:
            print("step", len(experiments), "t", request["time"], "cost", cost, "cpu", time.process_time() - begin, file=sys.stderr, flush=True)
    return LOWER + WIDTH * normalized


def main():
    start = json.loads(sys.stdin.readline())

    def query(request):
        print(json.dumps(request), flush=True)
        return json.loads(sys.stdin.readline())["counts"]

    parameters = run_controller(query, start["config"])
    print(json.dumps({"type": "answer", "parameters": parameters.tolist()}), flush=True)


if __name__ == "__main__":
    main()
