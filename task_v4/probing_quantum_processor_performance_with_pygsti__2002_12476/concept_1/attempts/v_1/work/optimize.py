import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from fast_features import ROOT, CANDIDATES
from physics import FAMILIES, design_cost, risks, score_risks, validate_batches


CONTRACT = json.loads((ROOT / 'input/contract.json').read_text())
COSTS = np.array([64 * (20 + len(item['germ']) * item['repetitions']) for item in CANDIDATES])
BASELINE = np.array(json.loads((ROOT / 'baseline/design.json').read_text())['batches'])


def sparse_risks(features, batches):
    selected = np.flatnonzero(batches > 0)
    return risks(features[:, selected], batches[selected])


class Problem:
    def __init__(self, data, family_power=1, tail=0, boost=1):
        self.features = data['features'] * 8
        self.families = data['families']
        self.baseline_risks = sparse_risks(data['features'], BASELINE)
        self.weights = np.zeros(len(self.features))
        stress_weights = data['stress_weights'] if 'stress_weights' in data else np.zeros(len(self.features))
        ordinary = stress_weights == 0
        for family in FAMILIES:
            mask = (self.families == family) & ordinary
            self.weights[mask] = 1 / (6 * mask.sum() * self.baseline_risks[mask].mean() ** family_power)
        self.weights /= np.dot(self.weights, self.baseline_risks)
        self.tail = tail
        self.scenario_weights = np.zeros(len(self.features))
        for family in FAMILIES:
            mask = (self.families == family) & ordinary
            self.scenario_weights[mask] = 1 / (6 * mask.sum())
            if family in ('mixed', 'anisotropic'):
                self.weights[mask] *= boost
        self.scenario_weights += stress_weights

    def aggregate(self, risk, gradient=False):
        expanded = risk.ndim == 2
        baseline = self.baseline_risks[:, None] if expanded else self.baseline_risks
        weights = self.weights[:, None] if expanded else self.weights
        scenario_weights = self.scenario_weights[:, None] if expanded else self.scenario_weights
        excess = np.maximum(risk / baseline - 0.55, 0)
        value = np.sum(weights * risk + self.tail * scenario_weights * excess ** 2, axis=0)
        if gradient:
            return value, weights + 2 * self.tail * scenario_weights * excess / baseline
        return value

    def evaluate(self, batches, selected=None, gradient=False):
        features = self.features if selected is None else self.features[:, selected]
        information = features.transpose(0, 2, 1) @ (batches[None, :, None] * features)
        covariance = np.linalg.inv(information + np.eye(14) * 1e-10)
        risk = np.trace(covariance[:, :12, :12], axis1=1, axis2=2)
        objective, risk_derivative = self.aggregate(risk, True)
        if not gradient:
            return objective
        transformed = features @ covariance[:, :, :12]
        derivative = -np.einsum('sci,sci,s->c', transformed, transformed, risk_derivative)
        return objective, derivative

    def optimize(self, selected, initial=None, maxiter=180):
        selected = np.array(selected, dtype=int)
        budget = 1600000 - 12000 * min(len(selected), 24)
        costs = COSTS[selected]
        cap = 48 * costs / budget
        if initial is None:
            fractions = capped_normalize(np.ones(len(selected)), cap)
        else:
            fractions = capped_normalize(np.maximum(initial * costs / budget, 1e-7), cap)
        def objective(fractions):
            value, derivative = self.evaluate(fractions * budget / costs, selected, True)
            return value, derivative * budget / costs
        result = minimize(objective, fractions, jac=True, method='SLSQP',
                          bounds=list(zip(np.zeros(len(selected)), cap)),
                          constraints={'type': 'eq', 'fun': lambda fractions: fractions.sum() - 1,
                                       'jac': lambda fractions: np.ones(len(fractions))},
                          options={'ftol': 1e-10, 'maxiter': maxiter})
        batches = result.x * budget / costs
        return batches, result.fun

    def continuous(self, iterations=400, seed=0):
        budget = 1600000 - 12000 * 24
        cap = 48 * COSTS / budget
        generator = np.random.default_rng(seed)
        fractions = capped_normalize(generator.uniform(0.5, 1.5, len(COSTS)), cap)
        for iteration in range(iterations):
            objective, derivative = self.evaluate(fractions * budget / COSTS, gradient=True)
            benefit = np.maximum(-derivative * budget / COSTS, 1e-20)
            fractions = capped_normalize(fractions * np.sqrt(benefit), cap)
            if iteration % 100 == 0:
                print('continuous', iteration, objective, flush=True)
        return fractions * budget / COSTS

    def prune(self, batches):
        selected = np.flatnonzero(batches > 0)
        for target in [100, 70, 50, 40, 35, 30, 28, 26, 24]:
            if len(selected) <= target:
                continue
            keep = np.argsort(batches[selected] * COSTS[selected])[-target:]
            selected = selected[keep]
            values, objective = self.optimize(selected, batches[selected])
            batches = np.zeros(len(COSTS))
            batches[selected] = values
            print('prune', target, objective, 'minimum', values.min(), flush=True)
        return batches

    def remove_losses(self, selected, values):
        features = self.features[:, selected]
        information = features.transpose(0, 2, 1) @ (values[None, :, None] * features)
        covariance = np.linalg.inv(information + np.eye(14) * 1e-10)
        transformed = features @ covariance
        leverage = np.einsum('sci,sci->sc', features, transformed)
        benefit = np.sum(transformed[:, :, :12] ** 2, axis=2)
        risk = np.trace(covariance[:, :12, :12], axis1=1, axis2=2)
        changes = benefit * values[None, :] / np.maximum(1 - values[None, :] * leverage, 1e-12)
        losses = self.aggregate(risk[:, None] + changes) - self.aggregate(risk)
        return losses

    def prune_exact(self, batches, target=24):
        selected = np.flatnonzero(batches > 1e-6)
        values, objective = self.optimize(selected, batches[selected])
        active = values > 1e-5
        if active.sum() >= target:
            selected, values = selected[active], values[active]
        while len(selected) > target:
            losses = self.remove_losses(selected, values)
            removed = int(np.argmin(losses))
            selected = np.delete(selected, removed)
            values = np.delete(values, removed)
            values, objective = self.optimize(selected, values)
            if len(selected) % 5 == 0 or len(selected) == target:
                print('exact prune', len(selected), objective, flush=True)
        batches = np.zeros(len(COSTS))
        batches[selected] = values
        return batches

    def augment(self, batches, iterations=10, count=8):
        objective = self.evaluate(batches)
        for iteration in range(iterations):
            _, gradient = self.evaluate(batches, gradient=True)
            benefit = -gradient / COSTS
            benefit[batches > 1e-6] = -np.inf
            added = np.argsort(benefit)[-count:]
            trial = batches.copy()
            trial[added] = 0.1
            trial = self.prune_exact(trial)
            trial_objective = self.evaluate(trial)
            print('augment', iteration, objective, trial_objective, flush=True)
            if trial_objective >= objective - 1e-8:
                break
            batches, objective = trial, trial_objective
        return batches

    def exchange(self, batches, iterations=60):
        selected = np.flatnonzero(batches > 1e-6)
        values, objective = self.optimize(selected, batches[selected])
        batches = np.zeros(len(COSTS))
        batches[selected] = values
        for iteration in range(iterations):
            features = self.features[:, selected]
            information = features.transpose(0, 2, 1) @ (values[None, :, None] * features)
            covariance = np.linalg.inv(information + np.eye(14) * 1e-10)
            choices = []
            for position, removed in enumerate(selected):
                removed_feature = features[:, position]
                transformed = np.einsum('si,sij->sj', removed_feature, covariance)
                leverage = np.einsum('si,si->s', removed_feature, transformed)
                denominator = np.maximum(1 - values[position] * leverage, 1e-12)
                without = covariance + (values[position] / denominator)[:, None, None] * transformed[:, :, None] * transformed[:, None, :]
                without_risk = np.trace(without[:, :12, :12], axis1=1, axis2=2)
                full_transformed = self.features @ without
                benefits = np.sum(full_transformed[:, :, :12] ** 2, axis=2)
                full_leverage = np.einsum('sci,sci->sc', full_transformed, self.features)
                new_batches = np.minimum(values[position] * COSTS[removed] / COSTS, 48)
                reduction = benefits * new_batches[None, :] / (1 + full_leverage * new_batches[None, :])
                swap_risk = self.aggregate(without_risk[:, None] - reduction)
                swap_risk[selected] = np.inf
                added = int(np.argmin(swap_risk))
                choices.append((swap_risk[added], position, added, new_batches[added]))
            choices.sort()
            accepted = False
            for predicted, position, added, allocation in choices[:5]:
                if predicted > objective * 1.01:
                    break
                trial = selected.copy()
                trial[position] = added
                initial = values.copy()
                initial[position] = allocation
                trial_values, trial_objective = self.optimize(trial, initial)
                if trial_objective < objective - 1e-7:
                    print('swap', iteration, 'old', selected[position], 'new', added,
                          'objective', trial_objective, flush=True)
                    selected, values, objective = trial, trial_values, trial_objective
                    accepted = True
                    break
            if not accepted:
                print('exchange converged', iteration, objective, flush=True)
                break
        batches = np.zeros(len(COSTS))
        batches[selected] = values
        return batches

    def integer(self, batches):
        result = np.floor(batches + 1e-7).astype(int)
        selected = np.flatnonzero(batches > 1e-6)
        result[selected] = np.maximum(result[selected], 1)
        while True:
            remaining = 1600000 - design_cost(result, CANDIDATES, CONTRACT)
            legal = selected[(COSTS[selected] <= remaining) & (result[selected] < 48)]
            if len(legal) == 0:
                break
            trial_objectives = []
            for candidate in legal:
                trial = result.copy()
                trial[candidate] += 1
                trial_objectives.append(self.evaluate(trial[selected], selected))
            best = legal[np.argmin(trial_objectives)]
            result[best] += 1
        for iteration in range(100):
            objective = self.evaluate(result[selected], selected)
            best_objective = objective
            best = None
            remaining = 1600000 - design_cost(result, CANDIDATES, CONTRACT)
            for removed in selected:
                if result[removed] <= 1:
                    continue
                for added in selected:
                    amount = min((remaining + COSTS[removed]) // COSTS[added], 48 - result[added])
                    if added == removed or amount < 1:
                        continue
                    trial = result.copy()
                    trial[removed] -= 1
                    trial[added] += amount
                    trial_objective = self.evaluate(trial[selected], selected)
                    if trial_objective < best_objective - 1e-10:
                        best_objective, best = trial_objective, trial
            if best is None:
                break
            result = best
        return result


def capped_normalize(values, cap):
    result = values / values.sum()
    for _ in range(100):
        oversized = result > cap
        if not oversized.any():
            break
        result[oversized] = cap[oversized]
        available = ~oversized
        result[available] *= (1 - result[oversized].sum()) / result[available].sum()
    return result


def report(batches, label):
    validate_batches(batches.tolist(), CANDIDATES, CONTRACT)
    print(label, 'cost', design_cost(batches, CANDIDATES, CONTRACT), 'support', np.count_nonzero(batches), flush=True)
    for filename in [ROOT / 'input/development.npz', Path('training.npz'), Path('validation.npz')]:
        data = np.load(filename)
        score, families = score_risks(sparse_risks(data['features'], batches), sparse_risks(data['features'], BASELINE), data['families'])
        print(str(filename), score, families, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--start')
    parser.add_argument('--output', default='design.json')
    parser.add_argument('--iterations', type=int, default=400)
    parser.add_argument('--exchange', type=int, default=60)
    parser.add_argument('--power', type=float, default=1)
    parser.add_argument('--data', default='training.npz')
    parser.add_argument('--exact', action='store_true')
    parser.add_argument('--augment', type=int, default=0)
    parser.add_argument('--tail', type=float, default=0)
    parser.add_argument('--boost', type=float, default=1)
    args = parser.parse_args()
    problem = Problem(np.load(args.data), args.power, args.tail, args.boost)
    if args.start:
        if args.start.endswith('.npy'):
            batches = np.load(args.start)
        else:
            batches = np.array(json.loads(Path(args.start).read_text())['batches'], dtype=float)
    else:
        continuous = problem.continuous(args.iterations, args.seed)
        np.save(args.output.replace('.json', '_relaxed.npy'), continuous)
        if args.exact:
            selected = np.argsort(continuous * COSTS)[-100:]
            batches = np.zeros(len(COSTS))
            batches[selected] = continuous[selected]
            batches = problem.prune_exact(batches)
        else:
            batches = problem.prune(continuous)
    batches = problem.exchange(batches, args.exchange)
    if args.augment:
        batches = problem.augment(batches, args.augment)
        batches = problem.exchange(batches, args.exchange)
    np.save(args.output.replace('.json', '_continuous.npy'), batches)
    integer = problem.integer(batches)
    Path(args.output).write_text(json.dumps({'batches': integer.tolist()}) + '\n')
    report(integer, args.output)


if __name__ == '__main__':
    main()
