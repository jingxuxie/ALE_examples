import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from scipy.optimize import minimize

from compact import Compact
from exact import STATES, LOWER, LIMIT, evaluate
from sectors import best_sector


class Block(Compact):
    def __init__(self, witness, free_count=5):
        super().__init__(witness, free_count)
        self.active = np.arange(120)
        self.count = 120
        self.active_rows, self.active_columns = LOWER
        self.full_energy = self.energy[:, None] - self.fields @ self.configurations.T + self.energy_free[None, :]

    def calculate(self, values):
        if self.last is not None and np.array_equal(self.last, values):
            return self.result
        self.last = values.copy()
        parameters = torch.tensor(values, requires_grad=True)
        weights = torch.zeros((16, 16))
        weights[LOWER] = parameters[:120]
        beta = parameters[-1]
        frozen_count = self.frozen_count
        logits_frozen = self.frozen @ weights[:frozen_count, :frozen_count].T
        logq_frozen = -torch.nn.functional.softplus(-self.frozen * logits_frozen).sum(dim=1)
        probq = 2 * torch.exp(logq_frozen)
        logits = ((self.frozen @ weights[frozen_count:, :frozen_count].T)[:, None, :]
                  + (self.configurations @ weights[frozen_count:, frozen_count:].T)[None, :, :])
        logq_free = -torch.nn.functional.softplus(-self.configurations[None, :, :] * logits).sum(dim=2)
        conditional = torch.exp(logq_free)
        logq = logq_frozen[:, None] + logq_free
        joint = probq[:, None] * conditional
        reward = beta * self.full_energy + logq
        mean_reward = torch.sum(joint * reward)
        centered = reward - mean_reward
        variance = torch.sum(joint * centered ** 2)
        entropy = -torch.sum(joint * logq)
        logz = torch.logsumexp(-beta * self.spectrum + torch.log(self.multiplicity), dim=0)
        target = self.multiplicity * torch.exp(-beta * self.spectrum - logz)
        target_sector = (self.sector_multiplicity * torch.exp(-beta * self.spectrum - logz)).sum()
        reverse_kl = mean_reward + logz
        energy_error = beta * (torch.sum(joint * self.full_energy) - target @ self.spectrum)
        residual = (self.frozen + 1) / 2 - torch.sigmoid(logits_frozen)
        centered_frozen = torch.sum(conditional * centered, dim=1)
        grad_frozen = ((probq * centered_frozen)[:, None] * residual).T @ self.frozen
        weighted_scores = (joint * centered)[:, :, None] * ((self.configurations[None, :, :] + 1) / 2 - torch.sigmoid(logits))
        grad_free = torch.sum(weighted_scores, dim=1).T @ self.frozen
        grad_free_free = torch.sum(weighted_scores, dim=0).T @ self.configurations
        gradient = torch.cat([grad_frozen[self.lower], grad_free.reshape(-1),
                              grad_free_free[np.tril_indices(self.free_count, -1)]])
        proposal_sector = torch.sum(joint * self.sector)
        ratios = torch.cat([torch.stack([variance / .05, 3 / entropy, .4 / reverse_kl,
                           torch.sqrt(energy_error ** 2 + 1e-14) / .32,
                           .35 / target_sector, proposal_sector / .001]),
                            torch.sqrt(gradient ** 2 + 1e-18) / .003])
        objective = torch.logsumexp(15 * ratios, dim=0) / 15
        objective.backward()
        self.result = float(objective.detach()), parameters.grad.detach().numpy()
        return self.result


def optimize(witness, iterations=180):
    model = Block(witness)
    original = model.pack(witness)
    split = np.r_[np.maximum(original[:120], 0), np.maximum(-original[:120], 0), original[-1]]
    row_jac = np.zeros((15, 241))
    row_jac[LOWER[0] - 1, np.arange(120)] = -1
    row_jac[LOWER[0] - 1, np.arange(120) + 120] = -1

    def objective(parameters):
        merged = np.r_[parameters[:120] - parameters[120:240], parameters[-1]]
        value, derivative = model.calculate(merged)
        return value, np.r_[derivative[:120], -derivative[:120], derivative[-1]]

    result = minimize(objective, split, jac=True, method='SLSQP',
                      bounds=[(0, LIMIT)] * 240 + [(1, 3)],
                      constraints={'type': 'ineq', 'fun': lambda parameters: LIMIT - 3e-12 + row_jac @ parameters,
                                   'jac': lambda parameters: row_jac},
                      options={'maxiter': iterations, 'ftol': 1e-9})
    return model.unpack(np.r_[result.x[:120] - result.x[120:240], result.x[-1]])


def search(source, count, seed, prefix):
    random = np.random.default_rng(seed)
    original = json.loads(Path(source).read_text())
    best = original
    best_score = evaluate(best)['core_score']
    start = time.time()
    for trial in range(count):
        witness = dict(best if trial % 4 else original)
        weights = np.array(witness['weights'])
        report, (energy, proposal, target, logq, gradient) = evaluate(witness, True)
        mode = STATES[np.argmax(proposal), witness['order']]
        weights *= mode[:, None] * mode[None, :]
        if trial:
            if trial % 3 != 0:
                for row in random.choice(np.arange(2, 12), random.integers(2, 7), replace=False):
                    parents = random.choice(row, min(3, row), replace=False)
                    distribution = random.dirichlet(np.ones(len(parents)))
                    weights[row] = 0
                    weights[row, parents] = (LIMIT - 1e-10) * distribution
            else:
                for row in random.choice(np.arange(6, 16), random.integers(2, 7), replace=False):
                    weights[row, :row] += random.normal(0, .45, row)
                    weights[row] *= (LIMIT - 1e-10) / np.maximum(np.abs(weights[row]).sum(), LIMIT)
        weights *= mode[:, None] * mode[None, :]
        witness['weights'] = weights.tolist()
        witness = optimize(witness, 200)
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
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--seed', type=int, default=905)
    parser.add_argument('--prefix', default='block')
    arguments = parser.parse_args()
    search(arguments.source, arguments.count, arguments.seed, arguments.prefix)
