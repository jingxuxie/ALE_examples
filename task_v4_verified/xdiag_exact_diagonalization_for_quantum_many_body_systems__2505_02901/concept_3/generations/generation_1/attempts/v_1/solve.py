import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import sys
import time

import numpy as np
from scipy.optimize import least_squares, minimize


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


def information(predictions, gradients):
    return np.einsum("eoi,eoj->eij", gradients / np.sqrt(predictions[:, :, None]),
                     gradients / np.sqrt(predictions[:, :, None]), optimize=True)



FIRST_SETTINGS = [
    experiment(14, 1.8, [1.7002112143880446, -2.116297196150549, 1.0363505253702625, 0.3250873448580345, -2.3190923655027778, 1.0128542381262022]),
    experiment(50, 1.8, [0.13584329719902977, -1.5387883138261493, 1.051422876010074, 0.7866737914949864, -1.9134405286891962, -2.787855242071247]),
]

def global_start(random, attempt):
    initial = random.uniform(.02, .98, 20)
    initial[14:] = .5
    if attempt % 4 == 0:
        level = (.08, .24, .4, .6, .76, .92)[(attempt // 4) % 6]
        initial[6:11] = np.clip(level + random.normal(0, .055, 5), .001, .999)
    if attempt % 5 == 0:
        initial[:6] = random.uniform(.03, .35, 6)
    return initial

def distinct_results(results, gap=24):
    ordered = sorted(results, key=lambda result: result[1])
    selected = []
    for result in ordered:
        if result[1] > ordered[0][1] + gap:
            break
        if not any(np.linalg.norm(result[0] - previous[0]) < .04 for previous in selected):
            selected.append(result)
    return selected[:5]

class Design:
    def __init__(self, experiments, results, random):
        self.modes = distinct_results(results, gap=20)
        self.samples = [result[0] for result in self.modes]
        weights = np.exp(-.5*np.array([result[1] - self.modes[0][1] for result in self.modes]))
        self.mode_weights = weights / weights.sum()
        self.weights = self.mode_weights.tolist()
        best_information = information(*Model(experiments).evaluate(self.samples[0])).sum(axis=0)
        covariance = np.linalg.inv(12288 * best_information + np.eye(20)*.01)
        direction = random.multivariate_normal(np.zeros(20), covariance) * .65
        self.samples.extend([np.clip(self.samples[0] + direction, .00001, .99999), np.clip(self.samples[0] - direction, .00001, .99999)])
        self.weights[0] *= .5
        self.weights.extend([self.mode_weights[0]*.25]*2)
        self.current = [information(*Model(experiments).evaluate(sample)).sum(axis=0) for sample in self.samples]

    def score(self, candidates):
        scores = np.zeros(len(candidates))
        predictions = []
        model = Model(candidates)
        for sample, current, weight in zip(self.samples, self.current, self.weights):
            probability, gradient = model.evaluate(sample)
            candidate_information = information(probability, gradient)
            covariance = np.linalg.inv(current[None] + candidate_information + np.eye(20)*1e-8)
            scores += weight * np.trace(covariance, axis1=1, axis2=2) / 12288 / 20
            predictions.append(probability)
        for left in range(len(self.modes)):
            for right in range(left):
                affinity = np.minimum(np.sqrt(predictions[left]*predictions[right]).sum(axis=1), 1.0)
                difference = np.mean((self.samples[left] - self.samples[right])**2)
                scores += np.sqrt(self.mode_weights[left]*self.mode_weights[right]) * difference * affinity**12288
        return scores

def select_final(experiments, results, random, refine=True):
    objective = Design(experiments, results, random)
    candidates = []
    for index in range(640):
        duration = random.uniform(2.0, 6.0)
        phases = random.uniform(-np.pi, np.pi, 6)
        if index % 5 == 0:
            phases[:] = 0
        elif index % 5 == 1:
            phases *= .3
        if index < 40:
            duration = random.uniform(0, 2)
        candidates.append(experiment(STATES[index % 20], duration, phases))
    scores = np.concatenate([objective.score(candidates[start:start+40]) for start in range(0, len(candidates), 40)])
    order = np.argsort(scores)
    chosen = candidates[order[0]]
    best_score = scores[order[0]]
    if refine:
        used = set()
        for index in order:
            setting = candidates[index]
            preparation = setting['preparation']
            if preparation in used:
                continue
            used.add(preparation)
            phases = np.array(setting['phases'])
            phases = (phases - phases[5] + np.pi) % (2*np.pi) - np.pi
            initial = np.r_[setting['time'], phases[:5]]
            def function(values):
                candidate = experiment(preparation, values[0], np.r_[values[1:], 0])
                return np.log(objective.score([candidate])[0])
            fit = minimize(function, initial, method='L-BFGS-B', bounds=[(0, 6)]+[(-3*np.pi, 3*np.pi)]*5,
                           options={'maxiter':25, 'ftol':1e-6, 'maxls':12})
            if np.exp(fit.fun) < best_score:
                best_score = np.exp(fit.fun)
                chosen = experiment(preparation, fit.x[0], (np.r_[fit.x[1:], 0] + np.pi) % (2*np.pi) - np.pi)
            if len(used) >= 3:
                break
    return chosen, best_score, len(objective.modes)

def run_robust(query, config, diagnostic=False):
    began = time.process_time()
    wall_began = time.monotonic()
    random = np.random.default_rng(381531)
    experiments = list(FIRST_SETTINGS)
    counts = [query(setting) for setting in experiments]
    results = []
    for attempt in range(96):
        initial = global_start(random, attempt) if attempt else np.full(20, .5)
        initial[14:] = .5
        if attempt % 4 == 3:
            previous = min(results, key=lambda result: result[1])[0]
            initial = np.clip(previous + random.normal(0, .18, 20), .0001, .9999)
            initial[14:] = previous[14:]
        results.append(fit_data(experiments, counts, initial, max_nfev=160))
        if time.process_time()-began > 30 or time.monotonic()-wall_began > 50:
            break
    results.sort(key=lambda result: result[1])
    setting, design_score, modes = select_final(experiments, results, random, refine=not os.environ.get('NO_REFINE'))
    experiments.append(setting)
    counts.append(query(setting))
    final = fit_data(experiments, counts, results[0][0], max_nfev=200)
    starts = [result[0] for result in distinct_results(results, gap=100)]
    starts += [np.clip(results[0][0]+random.normal(0,.08,20), .0001, .9999) for index in range(12)]
    starts += [global_start(random, index) for index in range(40)]
    for initial in starts:
        initial[14:] = final[0][14:]
        result = fit_data(experiments, counts, initial, max_nfev=180)
        if result[1] < final[1]:
            final = result
        if time.process_time()-began > 90 or time.monotonic()-wall_began > 145:
            break
    attempt = 0
    while final[1] > 260 and time.process_time()-began < 85 and time.monotonic()-wall_began < 140:
        initial = global_start(random, attempt)
        initial[14:] = final[0][14:]
        if attempt % 3 == 0:
            initial = fit_data(experiments[:2], counts[:2], initial, max_nfev=160)[0]
        elif attempt % 3 == 1:
            initial = np.clip(final[0] + random.normal(0, .25, 20), .0001, .9999)
        result = fit_data(experiments, counts, initial, max_nfev=220)
        if result[1] < final[1]:
            final = result
        attempt += 1
    if diagnostic:
        print('robust', round(results[0][1], 2), round(final[1], 2), 'modes', modes, 'crb', round(np.sqrt(design_score), 5), 'cpu', round(time.process_time()-began, 2), json.dumps(setting), file=sys.stderr, flush=True)
    return LOWER + SCALE * final[0]

def main():
    start = json.loads(sys.stdin.readline())

    def query(setting):
        print(json.dumps(setting), flush=True)
        response = json.loads(sys.stdin.readline())
        return response["counts"]

    parameters = run_robust(query, start["config"])
    parameters = np.clip(parameters, LOWER, UPPER)
    print(json.dumps({"type": "answer", "parameters": parameters.tolist()}), flush=True)


if __name__ == "__main__":
    main()
