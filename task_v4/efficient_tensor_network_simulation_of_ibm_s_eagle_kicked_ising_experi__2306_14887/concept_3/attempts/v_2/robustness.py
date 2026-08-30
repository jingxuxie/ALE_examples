import itertools
import json
import os
import time
import numpy as np
from optimize import ROOT, Ensemble, encode, load, optimize, save, training_scenarios
from scipy.special import logsumexp

BOUNDS = np.array([.025, .025, .015] + [.005] * 12 + [.01] * 12)
GROUPS = np.array([0,0,1,0,1,1,0,1,0,1,1,0])

def decode(values, name='generated'):
    return {'name': name, 'gain_a': float(values[0]), 'gain_b': float(values[1]),
            'zz_common': float(values[2]), 'zz_local': values[3:15].tolist(),
            'z_drift_radians_per_layer': values[15:27].tolist()}

def unique(scenarios):
    entries = {}
    for scenario in scenarios:
        values = np.array(encode(scenario))
        nonzero = np.flatnonzero(values[15:])
        if len(nonzero) and values[15 + nonzero[0]] < 0:
            values[15:] *= -1
        key = tuple(np.round(values, 12))
        if key not in entries:
            entries[key] = decode(values, scenario.get('name', 'generated'))
    return list(entries.values())

def make_pool(seed=946123):
    generator = np.random.default_rng(seed)
    scenarios = list(training_scenarios())
    uniform = np.ones(12)
    alternating = (-1.) ** np.arange(12)
    half = np.array([1.] * 6 + [-1.] * 6)
    group = 1. - 2 * GROUPS
    fields = [np.zeros(12), uniform, alternating, half, group]
    fields.extend(np.roll(half, offset) for offset in [1,2,3])
    fields.extend(np.eye(12)[site] for site in [0,3,6,9])
    for gain_a, gain_b, common in itertools.product([-1,1], repeat=3):
        for field_index, field in enumerate(fields):
            values = np.zeros(27)
            values[:3] = [gain_a*.025, gain_b*.025, common*.015]
            values[3:15] = common*.005
            values[15:] = .01*field
            scenarios.append(decode(values, f'corner_{gain_a}_{gain_b}_{common}_field_{field_index}'))
        for residual_index, residual in enumerate([alternating, -alternating, group, -group, half, -half]):
            for field_index, field in enumerate(fields[:5]):
                values = np.zeros(27)
                values[:3] = [gain_a*.025, gain_b*.025, common*.015]
                values[3:15] = .005*residual
                values[15:] = .01*field
                scenarios.append(decode(values, f'local_{gain_a}_{gain_b}_{common}_{residual_index}_{field_index}'))
    for index in range(256):
        values = generator.choice([-1.,1.], 27) * BOUNDS
        if index < 128:
            values[3:] *= generator.uniform(0,1,24)
        if index < 64:
            values[:3] *= generator.uniform(0,1,3)
        scenarios.append(decode(values, f'disorder_{index}'))
    return unique(scenarios)

def adversaries(angles, starts=24, iterations=14, seed=1948, initial=None):
    generator = np.random.default_rng(seed)
    values = generator.choice([-1.,1.], (starts, 27)) * BOUNDS
    if initial:
        values = np.vstack((values,np.array([encode(scenario) for scenario in initial])))
    best_scores = np.ones(len(values))
    best_values = values.copy()
    for iteration in range(iterations):
        scenarios = [decode(value) for value in values]
        scores, gradients = Ensemble(scenarios).evaluate_errors(angles)
        improved = scores < best_scores
        best_scores[improved] = scores[improved]
        best_values[improved] = values[improved]
        updated = -np.sign(gradients) * BOUNDS
        if np.array_equal(updated, values):
            break
        values = updated
    print('adversaries', iteration + 1, 'min', best_scores.min(), flush=True)
    order = np.argsort(best_scores)
    return unique([decode(best_values[index], f'adversary_{seed}_{index}') for index in order])

def validate_errors(angles):
    values = np.random.default_rng(749).uniform(-.8,.8,27) * BOUNDS
    scores, gradients = Ensemble([decode(values)]).evaluate_errors(angles)
    for index in [0,1,2,3,11,15,22,26]:
        shifted = values.copy()
        shifted[index] += 1e-6
        positive = Ensemble([decode(shifted)]).evaluate(angles, False)[0]
        shifted[index] -= 2e-6
        negative = Ensemble([decode(shifted)]).evaluate(angles, False)[0]
        print('error gradient', index, abs((positive-negative)/2e-6-gradients[0,index]), flush=True)

def gauge_search(angles, scenarios, rounds=3, temperature=.002):
    ensemble = Ensemble(scenarios)
    current = angles.copy()
    scores = ensemble.evaluate(current, False)
    objective = temperature * logsumexp(-scores / temperature)
    for round_index in range(rounds):
        changed = False
        for layer in np.random.default_rng(round_index+31).permutation(24):
            candidate = current.copy().reshape(24,2)
            candidate[layer] = (candidate[layer] + 2*np.pi) % (2*np.pi) - np.pi
            candidate = candidate.ravel()
            scores = ensemble.evaluate(candidate, False)
            candidate_objective = temperature * logsumexp(-scores / temperature)
            if candidate_objective < objective - 1e-9:
                current = candidate
                objective = candidate_objective
                changed = True
                print('gauge', round_index, layer, 'min', scores.min(), flush=True)
        if not changed:
            break
    return current

def main():
    angles = load(ROOT / os.environ.get('WARM_START', 'pulses.json'))
    if not (ROOT / 'public_warm_start.json').exists():
        save(angles, 'public_warm_start.json')
    validate_errors(angles)
    pool = make_pool()
    core = unique(training_scenarios() + [scenario for scenario in pool
                  if scenario['name'].startswith('corner_') and scenario['name'].endswith(('_field_0', '_field_1'))])
    best = -np.inf
    for epoch in range(int(os.environ.get('EPOCHS', 12))):
        pool = unique(pool + adversaries(angles, starts=24, seed=epoch+9914))
        ensemble = Ensemble(pool)
        scores = ensemble.evaluate(angles, False)
        worst = np.argsort(scores)
        print('EPOCH', epoch, 'pool', len(pool), 'min', scores.min(), 'mean', scores.mean(), 'worst', pool[worst[0]]['name'], flush=True)
        (ROOT / 'stress_scenarios.json').write_text(json.dumps({'scenarios': pool}))
        if (ROOT / 'robust_best.json').exists():
            best = float(ensemble.evaluate(load(ROOT / 'robust_best.json'), False).min())
        if scores.min() > best:
            best = float(scores.min())
            save(angles, 'robust_best.json')
            save(angles)
        training = unique(core + [pool[index] for index in worst[:32]])
        print('training', len(training), 'best', best, flush=True)
        if epoch % 3 == 0:
            angles = gauge_search(angles, training)
        angles = optimize(angles, training, iterations=240 if epoch < 6 else 160,
                          temperature=.004 if epoch < 3 else .001,
                          filename=f'epoch_{epoch:02d}.json')
        full_scores = ensemble.evaluate(angles, False)
        print('AFTER', epoch, 'min', full_scores.min(), 'mean', full_scores.mean(), flush=True)
        if full_scores.min() > best:
            best = float(full_scores.min())
            save(angles, 'robust_best.json')
            save(angles)
        elif full_scores.min() < best - .005:
            angles = load(ROOT / 'robust_best.json')
    save(load(ROOT / 'robust_best.json'))

if __name__ == '__main__':
    main()
