import argparse
import json
import time
from pathlib import Path

import numpy as np

from optimize import Problem, COSTS, FAMILIES, CANDIDATES, report


def search(problem, initial, relaxed, iterations, seed, output, lock_idle=False):
    generator = np.random.default_rng(seed)
    selected = np.flatnonzero(initial > 1e-6)
    locked = [index for index in selected if lock_idle and set(CANDIDATES[index]['germ']) == {'I'} and
              len(CANDIDATES[index]['germ']) * CANDIDATES[index]['repetitions'] > 1]
    values, objective = problem.optimize(selected, initial[selected])
    best_value = objective
    best_selected, best_values = selected.copy(), values.copy()
    pool_base = np.argsort(relaxed * COSTS)[-150:]
    started = time.time()
    pool = pool_base
    for iteration in range(iterations):
        features = problem.features[:, selected]
        information = features.transpose(0, 2, 1) @ (values[None, :, None] * features)
        covariance = np.linalg.inv(information + np.eye(14) * 1e-10)
        risk = np.trace(covariance[:, :12, :12], axis1=1, axis2=2)
        transformed = features @ covariance
        leverage = np.sum(features * transformed, axis=2)
        factors = values[None, :] / np.maximum(1 - values[None, :] * leverage, 1e-12)
        without_risk = risk[:, None] + factors * np.sum(transformed[:, :, :12] ** 2, axis=2)
        if iteration % 10 == 0:
            batches = np.zeros(len(COSTS))
            batches[selected] = values
            _, gradient = problem.evaluate(batches, gradient=True)
            pool = np.unique(np.concatenate([pool_base, np.argsort(-gradient / COSTS)[-50:]]))
        outside = np.setdiff1d(pool, selected)
        choices = []
        for added in outside:
            added_feature = problem.features[:, added]
            added_transformed = np.einsum('si,sij->sj', added_feature, covariance)
            overlap = np.einsum('sci,si->sc', transformed, added_feature)
            adjusted = added_transformed[:, None, :12] + (factors * overlap)[:, :, None] * transformed[:, :, :12]
            added_leverage = np.sum(added_feature * added_transformed, axis=1)[:, None] + factors * overlap ** 2
            amount = np.minimum(values * COSTS[selected] / COSTS[added], 48)
            swap_risks = without_risk - amount[None, :] * np.sum(adjusted ** 2, axis=2) / (1 + amount[None, :] * added_leverage)
            swap_values = problem.aggregate(swap_risks)
            swap_values[np.isin(selected, locked)] = np.inf
            for position in np.argsort(swap_values)[:2]:
                choices.append((swap_values[position], int(position), int(added), amount[position]))
        choices.sort()
        temperature = 0.004 * (0.08 ** ((iteration % 100) / 99))
        subset = choices[:40]
        probabilities = np.exp(-(np.array([choice[0] for choice in subset]) - subset[0][0]) / temperature)
        probabilities /= probabilities.sum()
        chosen = subset[int(generator.choice(len(subset), p=probabilities))]
        predicted, position, added, amount = chosen
        trial_selected = selected.copy()
        trial_values = values.copy()
        trial_selected[position] = added
        trial_values[position] = amount
        trial_values, trial_objective = problem.optimize(trial_selected, trial_values, maxiter=100)
        difference = trial_objective - objective
        if difference < 0 or generator.random() < np.exp(-difference / temperature):
            selected, values, objective = trial_selected, trial_values, trial_objective
        if objective < best_value - 1e-8:
            best_value = objective
            best_selected, best_values = selected.copy(), values.copy()
            batches = np.zeros(len(COSTS))
            batches[selected] = values
            np.save(output.replace('.json', '_continuous.npy'), batches)
            print('best', iteration, best_value, 'seconds', time.time() - started, flush=True)
        if iteration % 25 == 0:
            print('progress', iteration, objective, best_value, flush=True)
        if iteration % 100 == 99:
            selected, values, objective = best_selected.copy(), best_values.copy(), best_value
    batches = np.zeros(len(COSTS))
    batches[best_selected] = best_values
    if not lock_idle:
        batches = problem.exchange(batches)
    batches = problem.integer(batches)
    Path(output).write_text(json.dumps({'batches': batches.tolist()}) + '\n')
    report(batches, output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='design_initial.json')
    parser.add_argument('--output', default='design_search.json')
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--iterations', type=int, default=500)
    parser.add_argument('--tail', type=float, default=0)
    parser.add_argument('--boost', type=float, default=1)
    parser.add_argument('--large', action='store_true')
    parser.add_argument('--data', default='training_large.npz')
    parser.add_argument('--lock-idle', action='store_true')
    args = parser.parse_args()
    data = np.load(args.data)
    if not args.large:
        selected_scenarios = np.concatenate([np.flatnonzero(data['families'] == family)[:count]
                                             for family, count in zip(FAMILIES, [15, 20, 20, 65, 15, 80])])
        data = {key: data[key][selected_scenarios] for key in data.files}
    problem = Problem(data, tail=args.tail, boost=args.boost)
    initial = np.array(json.loads(Path(args.start).read_text())['batches'], dtype=float)
    relaxed = np.load('design_exact_relaxed.npy')
    search(problem, initial, relaxed, args.iterations, args.seed, args.output, args.lock_idle)


if __name__ == '__main__':
    main()
