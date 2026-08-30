import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/probing_quantum_processor_performance_with_pygsti__2002_12476/concept_1/participant')
sys.path.insert(0, str(ROOT / 'workspace'))
from physics import fisher_features, sample_parameters, FAMILIES

CANDIDATES = json.loads((ROOT / 'input/candidates.json').read_text())
DATA = np.load(ROOT / 'input/development.npz')
COSTS = DATA['costs'].astype(float)
BASELINE = np.array(json.loads((ROOT / 'baseline/design.json').read_text())['batches'])
BUDGET = 1600000 - 24 * 12000


def profile(features, support, batches, return_cov=False):
    rows = features[:, support]
    vectors = rows * np.sqrt(64 * batches)[None, :, None]
    information = vectors.transpose(0, 2, 1) @ vectors + np.eye(14) * 1e-10
    covariance = np.linalg.inv(information)
    transformed = vectors @ covariance
    leverage = transformed @ vectors.transpose(0, 2, 1)
    target = transformed[:, :, :12] @ transformed[:, :, :12].transpose(0, 2, 1)
    intact = np.trace(covariance[:, :12, :12], axis1=1, axis2=2)
    first, second = np.triu_indices(len(support), 1)
    diagonal_h = np.diagonal(leverage, axis1=1, axis2=2)
    diagonal_g = np.diagonal(target, axis1=1, axis2=2)
    first_h = 1 - diagonal_h[:, first]
    second_h = 1 - diagonal_h[:, second]
    cross_h = leverage[:, first, second]
    determinant = first_h * second_h - cross_h ** 2
    increment = (second_h * diagonal_g[:, first] + first_h * diagonal_g[:, second] +
                 2 * cross_h * target[:, first, second]) / np.maximum(determinant, 1e-15)
    risks = intact[:, None] + increment
    if return_cov:
        return intact, risks, covariance, rows, first, second
    return intact, risks.max(axis=1)


class Objective:
    def __init__(self, features, weights=None, intact_weight=1.0, temperature=0.25):
        self.features = features
        self.weights = np.ones(len(features)) / len(features) if weights is None else weights
        self.intact_weight = intact_weight
        self.temperature = temperature

    def value(self, support, batches):
        intact, loss = profile(self.features, support, batches)
        loss_value, unused = self.loss_value_weights(loss)
        return loss_value + self.intact_weight * self.weights @ intact

    def loss_value_weights(self, loss):
        return self.weights @ loss, self.weights

    def fun(self, batches, support):
        intact, risks, covariance, rows, first, second = profile(self.features, support, batches, True)
        top_count = min(8, risks.shape[1])
        top_indices = np.argpartition(risks, -top_count, axis=1)[:, -top_count:]
        top_risks = np.take_along_axis(risks, top_indices, axis=1)
        temperature = self.temperature
        maximum = top_risks.max(axis=1)
        pair_weights = np.exp((top_risks - maximum[:, None]) / temperature)
        soft_loss = maximum + temperature * np.log(pair_weights.sum(axis=1))
        pair_weights /= pair_weights.sum(axis=1)[:, None]
        selected_first = first[top_indices]
        selected_second = second[top_indices]
        information = rows.transpose(0, 2, 1) @ (rows * (64 * batches)[None, :, None]) + np.eye(14) * 1e-10
        scenario_indices = np.arange(len(rows))[:, None]
        first_rows = rows[scenario_indices, selected_first]
        second_rows = rows[scenario_indices, selected_second]
        loss_information = information[:, None] - 64 * batches[selected_first, None, None] * first_rows[:, :, :, None] * first_rows[:, :, None, :]
        loss_information -= 64 * batches[selected_second, None, None] * second_rows[:, :, :, None] * second_rows[:, :, None, :]
        loss_covariance = np.linalg.inv(loss_information)
        projected = np.einsum('sci,skij->skcj', rows, loss_covariance[:, :, :, :12], optimize=True)
        pair_grad = -64 * np.sum(projected ** 2, axis=-1)
        pair_grad[scenario_indices, np.arange(top_count)[None, :], selected_first] = 0
        pair_grad[scenario_indices, np.arange(top_count)[None, :], selected_second] = 0
        intact_projected = rows @ covariance[:, :, :12]
        intact_grad = -64 * np.sum(intact_projected ** 2, axis=-1)
        loss_value, loss_weights = self.loss_value_weights(soft_loss)
        gradient = np.einsum('s,sk,skc->c', loss_weights, pair_weights, pair_grad, optimize=True)
        gradient += self.intact_weight * self.weights @ intact_grad
        value = loss_value + self.intact_weight * self.weights @ intact
        return value, gradient

    def allocate(self, support, initial=None, maxiter=80):
        costs = COSTS[support]
        if initial is None:
            initial = np.minimum(48, BUDGET / len(support) / costs)
        else:
            initial = np.clip(initial, 0.1, 48)
            if costs @ initial > BUDGET:
                initial *= BUDGET / (costs @ initial)
        result = minimize(lambda batches: self.fun(batches, support), initial, jac=True, method='SLSQP',
                          bounds=[(0.5, 48)] * len(support),
                          constraints={'type': 'ineq', 'fun': lambda batches: (BUDGET - costs @ batches) / 10000,
                                       'jac': lambda batches: -costs / 10000},
                          options={'maxiter': maxiter, 'ftol': 2e-6})
        return result.x, self.value(support, result.x)


class TailObjective(Objective):
    def __init__(self, features, weights, intact_weight, temperature, baseline_loss, power):
        super().__init__(features, weights, 100 * intact_weight, temperature)
        self.baseline_loss = baseline_loss
        self.power = power

    def loss_value_weights(self, loss):
        relative = loss / self.baseline_loss
        value = 100 * self.weights @ (relative ** self.power + 0.005 * loss)
        derivative = 100 * self.weights * (self.power * relative ** (self.power - 1) / self.baseline_loss + 0.005)
        return value, derivative


def generate_one(arguments):
    seed, family = arguments
    parameters = sample_parameters(np.random.default_rng(seed), family)
    return fisher_features(parameters, CANDIDATES), parameters, family


def generate(count, seed, filename):
    from concurrent.futures import ProcessPoolExecutor
    arguments = [(seed + index, family) for index, family in enumerate(np.repeat(FAMILIES, count))]
    with ProcessPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(generate_one, arguments))
    np.savez_compressed(filename, features=np.array([entry[0] for entry in results]),
                        parameters=np.array([entry[1] for entry in results]), families=np.array([entry[2] for entry in results]))
    print('generated', filename, len(results), flush=True)


def report(features, families, support, batches):
    base_intact, base_loss = profile(features, np.flatnonzero(BASELINE), BASELINE[BASELINE > 0])
    intact, loss = profile(features, support, batches)
    print('mean', intact.mean(), loss.mean(), 'ratios', intact.mean() / base_intact.mean(), loss.mean() / base_loss.mean(), flush=True)
    for family in FAMILIES:
        selected = families == family
        print(family, 'intact', intact[selected].mean(), 'loss', loss[selected].mean(),
              'base_loss', base_loss[selected].mean(), 'reduction', 1 - loss[selected].mean() / base_loss[selected].mean(), flush=True)


def save(support, batches, filename='design.json'):
    result = np.zeros(len(CANDIDATES), dtype=int)
    result[support] = batches.astype(int)
    Path(filename).write_text(json.dumps({'batches': result.tolist()}) + '\n')


def integerize(objective, support, batches):
    rounded = np.maximum(1, np.floor(batches)).astype(int)
    while COSTS[support] @ rounded > BUDGET:
        best = None
        for position in np.flatnonzero(rounded > 1):
            trial = rounded.copy()
            trial[position] -= 1
            score = objective.value(support, trial)
            if best is None or score < best[0]:
                best = score, trial
        rounded = best[1]
    while True:
        remaining = BUDGET - COSTS[support] @ rounded
        allowed = np.flatnonzero((rounded < 48) & (COSTS[support] <= remaining))
        if not len(allowed):
            break
        current_score = objective.value(support, rounded)
        best = None
        for position in allowed:
            trial = rounded.copy()
            trial[position] += 1
            score = objective.value(support, trial)
            improvement = (current_score - score) / COSTS[support[position]]
            if best is None or improvement > best[0]:
                best = improvement, trial
        rounded = best[1]
    return rounded


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--generate', type=int)
    parser.add_argument('--seed', type=int, default=724193)
    parser.add_argument('--file', default='training.npz')
    args = parser.parse_args()
    if args.generate:
        generate(args.generate, args.seed, args.file)
    else:
        support = np.flatnonzero(BASELINE)
        objective = Objective(DATA['features'], intact_weight=1.0)
        print('baseline', objective.value(support, BASELINE[support]), flush=True)
        start = time.time()
        batches, value = objective.allocate(support, BASELINE[support])
        print('allocated', time.time()-start, value, batches, flush=True)
        rounded = integerize(objective, support, batches)
        save(support, rounded, 'initial.json')
        report(DATA['features'], DATA['families'], support, rounded)
