import os
import time

STARTED = time.monotonic()
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logsumexp


def configurations(count):
    return 2.0 * ((np.arange(1 << count, dtype=np.uint32)[:, None] >> np.arange(count)) & 1) - 1


def blocks_of(couplings):
    count = len(couplings)
    values = np.sort(np.abs(couplings[np.triu_indices(count, 1)]))
    positive = values[values > 1e-8]
    if not len(positive):
        return [[site] for site in range(count)]
    ratios = positive[1:] / positive[:-1]
    eligible = np.where(positive[1:] > positive[-1] * 0.15)[0]
    if len(eligible):
        split = eligible[np.argmax(ratios[eligible])]
        threshold = np.sqrt(positive[split] * positive[split + 1])
    else:
        threshold = positive[-1] * 0.3
    remaining = set(range(count))
    blocks = []
    while remaining:
        block = [min(remaining)]
        remaining.remove(block[0])
        for site in block:
            neighbors = [other for other in sorted(remaining) if abs(couplings[site, other]) > threshold]
            block.extend(neighbors)
            remaining.difference_update(neighbors)
        blocks.append(block)
    return sorted(blocks, key=lambda block: (-len(block), block))


def fit_single(spins, probability, order):
    count = spins.shape[1]
    weights = np.zeros((count, count))
    biases = np.zeros(count)
    for position, site in enumerate(order):
        design = np.column_stack((np.ones(len(spins)), spins[:, order[:position]]))
        target = (spins[:, site] + 1) * 0.5
        parameter = np.zeros(position + 1)
        for iteration in range(35):
            logits = design @ parameter
            predicted = expit(logits)
            gradient = design.T @ (probability * (predicted - target)) + 1e-9 * parameter
            if np.max(np.abs(gradient)) < 1e-10:
                break
            curvature = probability * predicted * (1 - predicted)
            hessian = design.T @ (curvature[:, None] * design) + np.eye(position + 1) * 1e-9
            update = np.linalg.solve(hessian, gradient)
            step = min(1.0, 4.0 / max(4.0, np.max(np.abs(update))))
            parameter -= step * update
        biases[site] = parameter[0]
        weights[site, order[:position]] = parameter[1:]
    return biases, weights


class LocalMixture:
    def __init__(self, couplings, fields, orders, initial=None, diversity=0.0):
        self.count = len(fields)
        self.spins = configurations(self.count)
        self.target = 0.5 * np.sum((self.spins @ couplings) * self.spins, axis=1) + self.spins @ fields
        self.target -= logsumexp(self.target)
        self.probability = np.exp(self.target)
        self.orders = np.asarray(orders)
        self.components = len(orders)
        self.diversity = diversity
        self.rows = np.concatenate([np.full(position + 1, site) for position, site in enumerate(orders[0])])
        self.columns = []
        self.row_indices = []
        for order in orders:
            self.row_indices.append(np.concatenate([np.full(position + 1, site) for position, site in enumerate(order)]))
            self.columns.append(np.concatenate([np.r_[self.count, order[:position]] for position in range(self.count)]))
        self.row_indices = np.asarray(self.row_indices)
        self.columns = np.asarray(self.columns, dtype=int)
        self.design = np.column_stack((self.spins, np.ones(len(self.spins))))
        if initial is None:
            matrices = []
            for order in orders:
                bias, weight = fit_single(self.spins, self.probability, order)
                matrices.append(np.column_stack((weight, bias)))
            matrices = np.asarray(matrices)
            self.initial = matrices[np.arange(self.components)[:, None], self.row_indices, self.columns].ravel()
        else:
            self.initial = initial

    def unpack(self, parameter):
        matrices = np.zeros((self.components, self.count, self.count + 1))
        matrices[np.arange(self.components)[:, None], self.row_indices, self.columns] = parameter.reshape(self.components, -1)
        return matrices

    def objective(self, parameter):
        matrices = self.unpack(parameter)
        logits = np.matmul(self.design, matrices.transpose(0, 2, 1))
        component_logs = -np.logaddexp(0, -self.spins * logits).sum(axis=2)
        mixture_log = logsumexp(component_logs, axis=0) - np.log(self.components)
        probability = np.exp(mixture_log)
        difference = mixture_log - self.target
        reverse = probability @ difference
        forward = -self.probability @ difference
        responsibilities = np.exp(component_logs - logsumexp(component_logs, axis=0))
        chi_terms = np.exp(np.minimum(100, 2 * self.target - mixture_log))
        component_probability = np.exp(component_logs) / self.components
        diversity_terms = component_probability * (component_logs - mixture_log)
        multiplier = responsibilities * (probability * (difference + 1) - 0.01 * self.probability - 0.003 * chi_terms)
        multiplier += self.diversity * diversity_terms
        residual = multiplier[:, :, None] * ((self.spins + 1) * 0.5 - expit(logits))
        gradient = np.matmul(residual.transpose(0, 2, 1), self.design)
        excess = np.maximum(0, np.abs(matrices).sum(axis=2) - 58)
        gradient += 0.02 * excess[:, :, None] * np.sign(matrices)
        selected = gradient[np.arange(self.components)[:, None], self.row_indices, self.columns].ravel()
        return reverse + 0.01 * forward + 0.003 * (chi_terms.sum() - 1) + self.diversity * diversity_terms.sum() + 0.01 * np.sum(excess ** 2) + 1e-9 * (parameter @ parameter), selected + 2e-9 * parameter

    def fit(self, iterations=1000):
        fitted = minimize(self.objective, self.initial, jac=True, method="L-BFGS-B",
                          options={"maxiter": iterations, "ftol": 1e-13, "gtol": 2e-8, "maxcor": 30})
        self.parameter = fitted.x
        self.score = self.objective(fitted.x)[0]
        self.matrices = self.unpack(fitted.x)
        norms = np.abs(self.matrices).sum(axis=2)
        self.matrices *= np.minimum(1, 59.5 / np.maximum(1, norms))[:, :, None]
        return self


def fit_block(couplings, fields, rng, components=2, trials=4, diversity=0.0):
    count = len(fields)
    best = None
    for trial in range(trials):
        orders = [rng.permutation(count).tolist() for unused in range(components)]
        local = LocalMixture(couplings, fields, orders, diversity=diversity)
        local.initial += rng.normal(0, 0.15, local.initial.shape)
        local.fit(1200)
        if best is None or local.score < best.score:
            best = local
        if best.score < 2e-7 or time.monotonic() - STARTED > 70:
            break
    return best


def solve_instance(instance):
    count = int(instance["n"])
    couplings = np.asarray(instance["couplings"], dtype=float)
    fields = np.asarray(instance["fields"], dtype=float)
    blocks = blocks_of(couplings)
    rng = np.random.default_rng(715923)
    if max(map(len, blocks)) > 9:
        blocks = [list(range(count))]
        if count > 12:
            spins = configurations(count)
            target = 0.5 * np.sum((spins @ couplings) * spins, axis=1) + spins @ fields
            probability = np.exp(target - logsumexp(target))
            orders = [rng.permutation(count).tolist() for unused in range(8)]
            fitted = [fit_single(spins, probability, order) for order in orders]
            return {"mixing": [0.125] * 8, "biases": [item[0].tolist() for item in fitted],
                    "weights": [item[1].tolist() for item in fitted], "orders": orders}
    means = np.zeros(count)
    for iteration in range(4):
        for block in blocks:
            local_couplings = couplings[np.ix_(block, block)]
            effective = fields[block] + couplings[block] @ means - local_couplings @ means[block]
            spins = configurations(len(block))
            target = 0.5 * np.sum((spins @ local_couplings) * spins, axis=1) + spins @ effective
            means[block] = np.exp(target - logsumexp(target)) @ spins
    fitted = []
    for block in blocks:
        local_couplings = couplings[np.ix_(block, block)]
        effective = fields[block] + couplings[block] @ means - local_couplings @ means[block]
        local = fit_block(local_couplings, effective, rng, diversity=0.025 if len(blocks) > 3 else 0)
        fitted.append(local)
        print("block", len(block), "local_objective", local.score, "elapsed", time.monotonic() - STARTED, file=sys.stderr, flush=True)
    codes = [1, 2, 4, 7, 3, 5, 6]
    weights = np.zeros((8, count, count))
    biases = np.zeros((8, count))
    orders = []
    for component in range(8):
        order = []
        for index, (block, local) in enumerate(zip(blocks, fitted)):
            label = (component & codes[index % len(codes)]).bit_count() % 2
            matrix = local.matrices[label]
            weights[component][np.ix_(block, block)] = matrix[:, :len(block)]
            biases[component, block] = matrix[:, -1]
            order.extend(np.asarray(block)[local.orders[label]].tolist())
        orders.append(order)
    return {"mixing": [0.125] * 8, "weights": weights.tolist(), "biases": biases.tolist(), "orders": orders}


def main():
    instance = json.loads(Path(sys.argv[1]).read_text())
    model = solve_instance(instance)
    Path(sys.argv[2]).write_text(json.dumps(model, separators=(",", ":"), allow_nan=False))


if __name__ == "__main__":
    main()
