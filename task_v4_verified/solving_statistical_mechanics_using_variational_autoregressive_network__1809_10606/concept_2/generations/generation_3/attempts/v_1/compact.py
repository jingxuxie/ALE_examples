import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from scipy.optimize import minimize

from exact import STATES, FEATURES, EDGES, LIMIT, LOWER, evaluate
from sectors import best_sector


torch.set_num_threads(1)
torch.set_default_dtype(torch.float64)


class Compact:
    def __init__(self, witness, free_count=4):
        self.witness = dict(witness)
        self.frozen_count = 16 - free_count
        frozen_count = self.frozen_count
        self.free_count = free_count
        self.order = witness['order']
        inverse = np.argsort(self.order)
        frozen = np.ones((1 << (frozen_count - 1), frozen_count))
        frozen[:, 1:] = 2 * ((np.arange(len(frozen))[:, None] >> np.arange(frozen_count - 1)) & 1) - 1
        energy = np.zeros(len(frozen))
        fields = np.zeros((len(frozen), free_count))
        configurations = 2 * ((np.arange(1 << free_count)[:, None] >> np.arange(free_count)) & 1) - 1
        energy_free = np.zeros(len(configurations))
        for coupling, (first, second) in zip(witness['bonds'], EDGES):
            first, second = sorted([inverse[first], inverse[second]])
            if second < frozen_count:
                energy -= coupling * frozen[:, first] * frozen[:, second]
            elif first < frozen_count:
                fields[:, second - frozen_count] += coupling * frozen[:, first]
            else:
                energy_free -= coupling * configurations[:, first - frozen_count] * configurations[:, second - frozen_count]
        self.frozen = torch.tensor(frozen)
        self.energy = torch.tensor(energy)
        self.fields = torch.tensor(fields)
        self.energy_free = torch.tensor(energy_free)
        self.lower = np.tril_indices(frozen_count, -1)
        self.active = np.r_[np.flatnonzero(LOWER[0] < frozen_count),
                            np.flatnonzero((LOWER[0] >= frozen_count) & (LOWER[1] < frozen_count))]
        self.count = len(self.active)
        self.active_rows = LOWER[0][self.active]
        self.active_columns = LOWER[1][self.active]
        all_energy = -FEATURES @ witness['bonds']
        spectrum, labels = np.unique(all_energy, return_inverse=True)
        distance = (STATES != witness['pattern']).sum(axis=1)
        sector = np.minimum(distance, 16 - distance) <= witness['radius']
        self.spectrum = torch.tensor(spectrum)
        self.multiplicity = torch.tensor(np.bincount(labels).astype(float))
        self.sector_multiplicity = torch.tensor(np.bincount(labels, weights=sector).astype(float))
        frozen_distance = (frozen != np.asarray(witness['pattern'])[self.order[:frozen_count]]).sum(axis=1)
        configurations = 2 * ((np.arange(1 << free_count)[:, None] >> np.arange(free_count)) & 1) - 1
        free_distance = (configurations != np.asarray(witness['pattern'])[self.order[frozen_count:]]).sum(axis=1)
        distance = frozen_distance[:, None] + free_distance[None, :]
        self.sector = torch.tensor((np.minimum(distance, 16 - distance) <= witness['radius']).astype(float))
        self.configurations = torch.tensor(configurations, dtype=torch.float64)
        self.last = None

    def unpack(self, parameters):
        weights = np.zeros((16, 16))
        weights[self.active_rows, self.active_columns] = parameters[:self.count]
        lengths = np.abs(weights).sum(axis=1)
        weights *= np.minimum(1, (LIMIT - 2e-12) / np.maximum(lengths, 1e-100))[:, None]
        return dict(self.witness, weights=weights.tolist(), beta=float(parameters[-1]))

    def pack(self, witness):
        return np.r_[np.array(witness['weights'])[self.active_rows, self.active_columns], witness['beta']]

    def calculate(self, values):
        if self.last is not None and np.array_equal(self.last, values):
            return self.result
        self.last = values.copy()
        parameters = torch.tensor(values, requires_grad=True)
        weights = torch.zeros((16, 16))
        weights[self.active_rows, self.active_columns] = parameters[:self.count]
        beta = parameters[-1]
        frozen_count = self.frozen_count
        logits_frozen = self.frozen @ weights[:frozen_count, :frozen_count].T
        logq_frozen = -torch.nn.functional.softplus(-self.frozen * logits_frozen).sum(dim=1)
        probq = 2 * torch.exp(logq_frozen)
        logits_free = self.frozen @ weights[frozen_count:, :frozen_count].T
        means = torch.tanh(logits_free / 2)
        variances = 1 - means ** 2
        coefficient = logits_free / 2 - beta * self.fields
        logcosh = torch.nn.functional.softplus(logits_free) - logits_free / 2
        mean_reward = beta * self.energy + logq_frozen + (coefficient * means - logcosh).sum(dim=1)
        centered = mean_reward - probq @ mean_reward
        reward_variance = probq @ (centered ** 2 + (coefficient ** 2 * variances).sum(dim=1))
        entropy = -probq @ logq_frozen + probq @ (logcosh - logits_free * means / 2).sum(dim=1)
        logz = torch.logsumexp(-beta * self.spectrum + torch.log(self.multiplicity), dim=0)
        target = self.multiplicity * torch.exp(-beta * self.spectrum - logz)
        target_sector = (self.sector_multiplicity * torch.exp(-beta * self.spectrum - logz)).sum()
        reverse_kl = probq @ mean_reward + logz
        energyq = probq @ (self.energy - (self.fields * means).sum(dim=1))
        energyp = target @ self.spectrum
        energy_error = beta * (energyq - energyp)
        residual = (self.frozen + 1) / 2 - torch.sigmoid(logits_frozen)
        grad_frozen = ((probq * centered)[:, None] * residual).T @ self.frozen
        conditional_gradient = probq[:, None] * coefficient * variances / 2
        grad_free = conditional_gradient.T @ self.frozen
        grad_free_free = conditional_gradient.T @ means
        gradient = torch.cat([grad_frozen[self.lower], grad_free.reshape(-1),
                              grad_free_free[np.tril_indices(self.free_count, -1)]])
        free_probability = torch.prod((1 + means[:, None, :] * self.configurations[None, :, :]) / 2, dim=2)
        proposal_sector = probq @ (free_probability * self.sector).sum(dim=1)
        ratios = torch.cat([torch.stack([reward_variance / .05, 3 / entropy, .4 / reverse_kl,
                           torch.sqrt(energy_error ** 2 + 1e-14) / .32,
                           .35 / target_sector, proposal_sector / .001]),
                            torch.sqrt(gradient ** 2 + 1e-18) / .003])
        objective = torch.logsumexp(10 * ratios, dim=0) / 10
        objective.backward()
        self.result = float(objective.detach()), parameters.grad.detach().numpy()
        return self.result


def optimize(witness, iterations=200):
    model = Compact(witness)
    original = model.pack(witness)
    count = model.count
    split = np.r_[np.maximum(original[:count], 0), np.maximum(-original[:count], 0), original[-1]]
    row_jac = np.zeros((15, 2 * count + 1))
    row_jac[model.active_rows - 1, np.arange(count)] = -1
    row_jac[model.active_rows - 1, np.arange(count) + count] = -1

    def objective(parameters):
        merged = np.r_[parameters[:count] - parameters[count:2 * count], parameters[-1]]
        value, derivative = model.calculate(merged)
        return value, np.r_[derivative[:count], -derivative[:count], derivative[-1]]

    result = minimize(objective, split, jac=True, method='SLSQP',
                      bounds=[(0, LIMIT)] * (2 * count) + [(1, 3)],
                      constraints={'type': 'ineq', 'fun': lambda parameters: LIMIT - 3e-12 + row_jac @ parameters,
                                   'jac': lambda parameters: row_jac},
                      options={'maxiter': iterations, 'ftol': 1e-9})
    return model.unpack(np.r_[result.x[:count] - result.x[count:2 * count], result.x[-1]])


def search(source, count, seed, prefix):
    random = np.random.default_rng(seed)
    original = json.loads(Path(source).read_text())
    best = original
    best_score = evaluate(best)['core_score']
    start = time.time()
    for trial in range(count):
        witness = dict(best if trial % 4 else original)
        weights = np.array(witness['weights'])
        order = witness['order']
        if trial:
            if trial % 3 != 0:
                for row in random.choice(np.arange(12, 16), random.integers(1, 4), replace=False):
                    neighbors = []
                    for first, second in EDGES:
                        if first == order[row]:
                            neighbors.append(order.index(second))
                        elif second == order[row]:
                            neighbors.append(order.index(first))
                    random.shuffle(neighbors)
                    weights[row] = 0
                    fraction_positive, fraction_negative = random.uniform(.05, .95, 2)
                    weights[row, neighbors] = (LIMIT - 1e-10) / 2 * np.array([
                        fraction_positive, 1 - fraction_positive, -fraction_negative, fraction_negative - 1])
            else:
                for row in random.choice(np.arange(2, 12), random.integers(2, 7), replace=False):
                    parents = random.choice(row, min(3, row), replace=False)
                    distribution = random.dirichlet(np.ones(len(parents)))
                    weights[row] = 0
                    weights[row, parents] = (LIMIT - 1e-10) * distribution
        weights[12:, 12:] = 0
        witness['weights'] = weights.tolist()
        witness = optimize(witness, 220)
        witness, _, _ = best_sector(witness, strict=False)
        report = evaluate(witness)
        print(trial, round(time.time() - start, 1), report, flush=True)
        Path(f'{prefix}_{trial}.json').write_text(json.dumps(witness))
        if report['core_score'] > best_score:
            best, best_score = witness, report['core_score']
            Path(prefix + '_best.json').write_text(json.dumps(best))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--count', type=int, default=30)
    parser.add_argument('--seed', type=int, default=210)
    parser.add_argument('--prefix', default='compact')
    arguments = parser.parse_args()
    search(arguments.source, arguments.count, arguments.seed, arguments.prefix)
