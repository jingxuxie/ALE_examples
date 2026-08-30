import os
import time

START_TIME = time.monotonic()
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import cholesky, solve, solve_triangular
from scipy.optimize import minimize
from scipy.special import expit, logsumexp


class TimeLimit(Exception):
    pass


def configurations(count):
    indices = np.arange(1 << count, dtype=np.uint32)
    return 2.0 * ((indices[:, None] >> np.arange(count)) & 1) - 1.0


class Basis:
    def __init__(self, count, deadline=float("inf")):
        self.count = count
        self.deadline = deadline
        self.spins = configurations(count)
        self.design = [np.ascontiguousarray(np.column_stack((np.ones(1 << position), self.spins[:1 << position, :position])))
                       for position in range(count)]


def marginals(probability, count):
    result = [probability]
    for position in range(count):
        result.append(result[-1].reshape(2, -1).sum(axis=0))
    return result[::-1]


def fit_logistic(design, positive, negative, initial, deadline=float("inf")):
    mass = positive + negative
    keep = mass > 1e-14
    design = np.ascontiguousarray(design[keep])
    positive = positive[keep]
    mass = mass[keep]
    total = mass.sum()
    positive = positive / total
    mass = mass / total
    parameters = initial.copy()
    regularization = 1e-9
    for iteration in range(25):
        if time.monotonic() > deadline:
            break
        logits = design @ parameters
        predicted = expit(logits)
        gradient = design.T @ (mass * predicted - positive) + regularization * parameters
        if np.max(np.abs(gradient)) < 2e-9:
            break
        curvature = mass * predicted * (1 - predicted)
        hessian = design.T @ (curvature[:, None] * design)
        hessian.flat[::len(parameters) + 1] += regularization
        update = solve(hessian, gradient, assume_a="pos", check_finite=False)
        objective = mass @ np.logaddexp(0, logits) - positive @ logits + 0.5 * regularization * (parameters @ parameters)
        directional = gradient @ update
        step = min(1.0, 5.0 / max(5.0, np.abs(update).sum()))
        accepted = False
        for search in range(15):
            trial = parameters - step * update
            trial_logits = design @ trial
            trial_objective = mass @ np.logaddexp(0, trial_logits) - positive @ trial_logits + 0.5 * regularization * (trial @ trial)
            if trial_objective <= objective - 0.01 * step * directional:
                accepted = True
                break
            step *= 0.5
        if not accepted:
            break
        parameters = trial
    return parameters


def weak_order(couplings, free):
    graph = np.abs(couplings).copy()
    remaining = list(free)
    result = []
    while remaining:
        strengths = np.tanh(graph[np.ix_(remaining, remaining)])
        site = remaining[int(np.argmin(np.sum(strengths ** 2, axis=1)))]
        remaining.remove(site)
        result.append(site)
        neighbors = np.tanh(graph[remaining, site])
        induced = np.outer(neighbors, neighbors)
        np.fill_diagonal(induced, 0)
        graph[np.ix_(remaining, remaining)] = np.minimum(4, graph[np.ix_(remaining, remaining)] + induced)
    return result[::-1]


def graph_order(adjacency, strengths, pivots):
    count = len(adjacency)
    adjacency = list(adjacency)
    remaining = [site for site in range(count) if site not in pivots]
    mask = sum(1 << site for site in remaining)
    result = []
    cost = 0
    while remaining:
        site = min(remaining, key=lambda site: ((adjacency[site] & mask).bit_count(), strengths[site]))
        neighbors = adjacency[site] & mask
        degree = neighbors.bit_count()
        cost += max(0, 3 ** max(0, degree - 2) - 1)
        remaining.remove(site)
        mask ^= 1 << site
        for other in remaining:
            if neighbors & (1 << other):
                adjacency[other] |= neighbors & ~(1 << other)
        result.append(site)
    return cost, result[::-1]


def structural_cutsets(couplings, count, deadline):
    size = len(couplings)
    adjacency = [sum(1 << other for other in range(size) if abs(couplings[site, other]) > 1e-10)
                 for site in range(size)]
    strengths = np.abs(couplings).sum(axis=1).tolist()
    candidates = []
    for pivots in itertools.combinations(range(size), count):
        if time.monotonic() > deadline:
            break
        cost, order = graph_order(adjacency, strengths, pivots)
        candidates.append((cost, pivots))
    candidates.sort()
    chosen = []
    for cost, pivots in candidates:
        if all(len(set(pivots) & set(previous)) < max(1, count - 1) for previous in chosen):
            chosen.append(pivots)
        if len(chosen) == 2:
            break
    return chosen


def choose_pivots(spins, probability, count, first=None):
    selected = []
    cells = np.zeros(len(spins), dtype=np.int32)
    first_scores = None
    for depth in range(count):
        scores = np.zeros(spins.shape[1])
        for value in range(1 << depth):
            keep = cells == value
            local = probability[keep]
            mass = local.sum()
            if mass < 1e-200:
                continue
            local = local / mass
            local_spins = spins[keep]
            mean = local @ local_spins
            covariance = local_spins.T @ (local[:, None] * local_spins) - np.outer(mean, mean)
            variance = np.maximum(np.diag(covariance), 1e-8)
            scores += mass * np.sum(covariance ** 2, axis=0) / variance
        scores[selected] = -1
        if depth == 0:
            first_scores = scores.copy()
        pivot = int(first) if depth == 0 and first is not None else int(np.argmax(scores))
        selected.append(pivot)
        cells += (spins[:, pivot] > 0).astype(np.int32) << depth
    return selected, first_scores


class Cell:
    def __init__(self, log_target, couplings, fields, fixed, basis):
        self.fixed = fixed
        self.free = [site for site in range(len(fields)) if site not in fixed]
        self.basis = basis
        self.count = len(self.free)
        selection = [slice(None)] * len(fields)
        for site, value in fixed.items():
            selection[len(fields) - 1 - site] = int(value > 0)
        local = log_target.reshape((2,) * len(fields))[tuple(selection)].reshape(-1)
        self.log_mass = float(logsumexp(local))
        self.log_target = local - self.log_mass
        self.probability = np.exp(self.log_target)
        self.couplings = couplings
        self.fields = fields.copy()
        for site, value in fixed.items():
            self.fields += couplings[:, site] * value
        self.best = None

    def ordered_target(self, order):
        axes = [self.count - 1 - self.free.index(site) for site in order[::-1]]
        return self.log_target.reshape((2,) * self.count).transpose(axes).reshape(-1)

    def covariance_order(self):
        spins = self.basis.spins
        mean = self.probability @ spins
        covariance = spins.T @ (self.probability[:, None] * spins) - np.outer(mean, mean)
        remaining = list(range(self.count))
        result = []
        while remaining:
            variance = np.maximum(np.diag(covariance), 1e-8)
            score = np.sum(covariance ** 2, axis=0) / variance
            site = max(remaining, key=lambda site: score[site])
            result.append(self.free[site])
            remaining.remove(site)
            covariance -= np.outer(covariance[:, site], covariance[site]) / variance[site]
        return result

    def fit(self, order):
        log_target = self.ordered_target(order)
        marginal = marginals(np.exp(log_target), self.count)
        parameters = []
        for position, site in enumerate(order):
            initial = np.concatenate(([2 * self.fields[site]], 2 * self.couplings[site, order[:position]]))
            if position < self.count - 1:
                target = marginal[position + 1].reshape(2, -1)
                initial = fit_logistic(self.basis.design[position], target[1], target[0], initial, self.basis.deadline)
            norm = np.abs(initial).sum()
            parameters.append(initial * min(1, 59 / max(1, norm)))
        candidate = Candidate(self, list(order), parameters, log_target)
        self.consider(candidate)
        return candidate

    def consider(self, candidate):
        if self.best is None or candidate.score < self.best.score:
            self.best = candidate


class Candidate:
    def __init__(self, cell, order, parameters, log_target):
        self.cell = cell
        self.order = order
        self.parameters = parameters
        self.log_target = log_target
        self.log_joint = self.joint(parameters)
        difference = self.log_joint - log_target
        self.reverse = float(np.exp(self.log_joint) @ difference)
        self.forward = float(-np.exp(log_target) @ difference)
        self.log_chi = float(logsumexp(2 * log_target - self.log_joint))
        self.score = self.reverse + 0.002 * np.expm1(min(50, self.log_chi))

    def joint(self, parameters):
        joint = np.zeros(1)
        for design, parameter in zip(self.cell.basis.design, parameters):
            logits = design @ parameter
            joint = np.concatenate((joint - np.logaddexp(0, logits), joint - np.logaddexp(0, -logits)))
        return joint


class Refinement:
    def __init__(self, candidate, deadline, chi_weight=0.002):
        self.candidate = candidate
        self.cell = candidate.cell
        self.count = self.cell.count
        self.design = self.cell.basis.design
        self.initial = candidate.parameters
        self.log_target = candidate.log_target
        self.target = np.exp(self.log_target)
        self.deadline = deadline
        self.chi_weight = chi_weight
        self.alpha = 0.03
        marginal = marginals(self.target, self.count)
        self.transforms = []
        for position in range(self.count - 1):
            predicted = expit(self.design[position] @ self.initial[position])
            curvature = marginal[position] * predicted * (1 - predicted)
            hessian = self.design[position].T @ (curvature[:, None] * self.design[position])
            hessian.flat[::position + 2] += 1e-6
            factor = cholesky(hessian, lower=True, check_finite=False)
            transform = solve_triangular(factor.T, np.eye(position + 1), lower=False, check_finite=False)
            self.transforms.append(transform)
        self.size = self.count * (self.count - 1) // 2
        self.best_objective = np.inf
        self.best_parameters = self.initial

    def unpack(self, vector):
        parameters = []
        start = 0
        for position, transform in enumerate(self.transforms):
            parameters.append(self.initial[position] + transform @ vector[start:start + position + 1])
            start += position + 1
        parameters.append(self.initial[-1])
        return parameters

    def evaluate(self, vector):
        if time.monotonic() > self.deadline:
            raise TimeLimit()
        parameters = self.unpack(vector)
        joint = np.zeros(1)
        probabilities = []
        for design, parameter in zip(self.design, parameters):
            logits = design @ parameter
            probabilities.append(expit(logits))
            joint = np.concatenate((joint - np.logaddexp(0, logits), joint - np.logaddexp(0, -logits)))
        difference = joint - self.log_target
        probability = np.exp(joint)
        reverse = float(probability @ difference)
        forward = float(-self.target @ difference)
        log_tilt = 2 * self.log_target - joint
        log_chi = float(logsumexp(log_tilt))
        chi = np.exp(min(50, log_chi))
        tilt = np.exp(log_tilt - log_chi) * chi
        residual = probability * (difference - reverse) - self.alpha * self.target - self.chi_weight * tilt
        objective = reverse + self.alpha * forward + self.chi_weight * (chi * (1 + max(0, log_chi - 50)) - 1)
        gradient = [None] * (self.count - 1)
        valid = True
        for position in range(self.count - 1, -1, -1):
            children = residual.reshape(2, -1)
            parent = children.sum(axis=0)
            if position < self.count - 1:
                logit_gradient = children[1] - parent * probabilities[position]
                raw_gradient = self.design[position].T @ logit_gradient
                norm = np.abs(parameters[position]).sum()
                excess = max(0, norm - 58.5)
                if excess:
                    objective += excess ** 2
                    raw_gradient += 2 * excess * np.sign(parameters[position])
                valid = valid and norm <= 59
                gradient[position] = self.transforms[position].T @ raw_gradient
            residual = parent
        if valid and np.isfinite(objective) and objective < self.best_objective:
            self.best_objective = objective
            self.best_parameters = [parameter.copy() for parameter in parameters]
        return objective, np.concatenate(gradient)

    def fit(self, iterations=45):
        if not self.size:
            return self.candidate
        try:
            minimize(self.evaluate, np.zeros(self.size), method="L-BFGS-B", jac=True,
                     options={"maxiter": iterations, "ftol": 2e-11, "gtol": 2e-7, "maxls": 15, "maxcor": 12})
        except TimeLimit:
            pass
        return Candidate(self.cell, self.candidate.order, self.best_parameters, self.log_target)


def partition(log_target, couplings, fields, pivots, basis):
    cells = []
    free = [site for site in range(len(fields)) if site not in pivots]
    order = weak_order(couplings, free)
    for component in range(1 << len(pivots)):
        fixed = {site: 2 * ((component >> position) & 1) - 1 for position, site in enumerate(pivots)}
        cell = Cell(log_target, couplings, fields, fixed, basis)
        cell.fit(order)
        cells.append(cell)
    return cells


def summary(cells):
    log_mass = np.array([cell.log_mass for cell in cells])
    log_mass -= logsumexp(log_mass)
    mixing = np.exp(log_mass)
    reverse = float(mixing @ np.array([cell.best.reverse for cell in cells]))
    log_chi = float(logsumexp(log_mass + np.array([cell.best.log_chi for cell in cells])))
    score = reverse + 0.002 * np.expm1(min(50, log_chi))
    return score, reverse, np.exp(-log_chi)


def artifact(cells, count):
    log_mass = np.array([cell.log_mass for cell in cells])
    mixing = np.maximum(np.exp(log_mass - logsumexp(log_mass)), 1e-300)
    mixing /= mixing.sum()
    model = {"mixing": mixing.tolist(), "weights": [], "biases": [], "orders": []}
    for cell in cells:
        weights = np.zeros((count, count))
        biases = np.zeros(count)
        for site, value in cell.fixed.items():
            biases[site] = 55 * value
        for position, site in enumerate(cell.best.order):
            parameters = cell.best.parameters[position]
            biases[site] = parameters[0]
            weights[site, cell.best.order[:position]] = parameters[1:]
        norms = np.abs(biases) + np.abs(weights).sum(axis=1)
        scaling = np.minimum(1, 59 / np.maximum(1, norms))
        model["weights"].append((weights * scaling[:, None]).tolist())
        model["biases"].append((biases * scaling).tolist())
        model["orders"].append(list(cell.fixed) + cell.best.order)
    return model


def solve_instance(instance, seconds=100):
    started = time.monotonic()
    deadline = started + seconds
    count = int(instance["n"])
    couplings = np.asarray(instance["couplings"], dtype=np.float64)
    fields = np.asarray(instance["fields"], dtype=np.float64)
    spins = configurations(count)
    log_target = 0.5 * np.sum((spins @ couplings) * spins, axis=1) + spins @ fields
    log_target -= logsumexp(log_target)
    probability = np.exp(log_target)
    pivot_count = min(3, max(0, count - 1))
    pivots, first_scores = choose_pivots(spins, probability, pivot_count)
    basis = Basis(count - pivot_count, deadline - 2)
    fit_started = time.monotonic()
    best = partition(log_target, couplings, fields, pivots, basis)
    partition_time = time.monotonic() - fit_started
    best_score = summary(best)[0]
    alternatives = []
    if best_score > 2e-5 and time.monotonic() + 3 * partition_time + 20 < deadline:
        if np.count_nonzero(couplings) <= 6 * count:
            alternatives = structural_cutsets(couplings, pivot_count, min(deadline - 25, time.monotonic() + 4))
        elif best_score > 0.001:
            first_scores[pivots] = -1
            other, unused = choose_pivots(spins, probability, pivot_count, int(np.argmax(first_scores)))
            alternatives.append(other)
    del spins, probability
    tried = {tuple(sorted(pivots))}
    for alternate in alternatives:
        if tuple(sorted(alternate)) in tried or time.monotonic() + 2 * partition_time + 20 > deadline:
            continue
        tried.add(tuple(sorted(alternate)))
        fit_started = time.monotonic()
        candidate = partition(log_target, couplings, fields, alternate, basis)
        partition_time = max(partition_time, time.monotonic() - fit_started)
        score = summary(candidate)[0]
        if score < best_score:
            best, best_score = candidate, score
    rng = np.random.default_rng(742091)
    for trial in range(4):
        if time.monotonic() + max(10, 2 * partition_time) > deadline:
            break
        for cell in best:
            if time.monotonic() + 10 > deadline:
                break
            order = cell.covariance_order() if trial == 0 else rng.permutation(cell.free).tolist()
            cell.fit(order)
        if summary(best)[1] < 2e-5:
            break
    for cell in sorted(best, key=lambda cell: -np.exp(cell.log_mass) * cell.best.score):
        if time.monotonic() + 1 > deadline:
            break
        refined = Refinement(cell.best, deadline - 0.5).fit()
        cell.consider(refined)
    if summary(best)[2] < 0.6:
        for cell in best:
            original = cell.best
            for scale in (0.99, 0.97, 0.94, 0.9, 0.85):
                if time.monotonic() + 0.5 > deadline:
                    break
                parameters = [parameter * scale for parameter in original.parameters]
                cell.consider(Candidate(cell, original.order, parameters, original.log_target))
    return artifact(best, count)


def main():
    instance = json.loads(Path(sys.argv[1]).read_text())
    model = solve_instance(instance, max(5, 105 - (time.monotonic() - START_TIME)))
    destination = Path(sys.argv[2])
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(json.dumps(model, separators=(",", ":"), allow_nan=False))
    os.replace(temporary, destination)


if __name__ == "__main__":
    main()
