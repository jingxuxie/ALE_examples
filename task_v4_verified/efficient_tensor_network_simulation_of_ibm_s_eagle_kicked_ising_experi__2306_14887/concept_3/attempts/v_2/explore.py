import os
import json
import time
import numpy as np
from scipy.special import logsumexp
from optimize import ROOT, Ensemble, load, save, optimize, training_scenarios
from robustness import make_pool, unique, adversaries

def anneal(angles, scenarios, steps=3500, seed=119):
    generator = np.random.default_rng(seed)
    ensemble = Ensemble(scenarios)
    current = angles.copy()
    scores = ensemble.evaluate(current, False)
    temperature = .001
    value = temperature * logsumexp(-scores/temperature)
    best_value = value
    best = current.copy()
    best_minimum = float(scores.min())
    started = time.time()
    for step in range(steps):
        cycle = step % 700
        thermal = .007 * (.00015/.007) ** (cycle/699)
        if cycle == 0 and step:
            current = best.copy()
            value = best_value
        candidate = current.copy().reshape(24,2)
        count = generator.choice([1,2,3,5], p=[.65,.25,.08,.02])
        layers = generator.choice(24, count, replace=False)
        candidate[layers] = (candidate[layers] + 2*np.pi) % (2*np.pi) - np.pi
        candidate = candidate.ravel()
        scores = ensemble.evaluate(candidate, False)
        trial_value = temperature * logsumexp(-scores/temperature)
        if trial_value < value or generator.random() < np.exp(min(0., (value-trial_value)/thermal)):
            current = candidate
            value = trial_value
        if trial_value < best_value:
            best = candidate.copy()
            best_value = trial_value
            best_minimum = float(scores.min())
            save(best, 'gauge_candidate.json')
            print('gauge best', step, best_minimum, 'seconds', time.time()-started, flush=True)
        if step % 500 == 0:
            print('anneal', step, 'best', best_minimum, 'seconds', time.time()-started, flush=True)
    return best

def main():
    pool = make_pool()
    if (ROOT / 'stress_scenarios.json').exists():
        pool = unique(pool + json.loads((ROOT / 'stress_scenarios.json').read_text())['scenarios'])
    angles = load(ROOT / os.environ.get('WARM_START', 'robust_best.json'))
    core = [scenario for scenario in pool if scenario['name'].startswith('corner_') and
            scenario['name'].endswith(tuple(f'_field_{field}' for field in range(5)))]
    core += [training_scenarios()[0]]
    generator = np.random.default_rng(57814)
    for epoch in range(int(os.environ.get('EXPLORE_EPOCHS', 8))):
        pool = unique(pool + adversaries(angles, starts=32, seed=epoch+26713))
        ensemble = Ensemble(pool)
        incumbent = load(ROOT / 'robust_best.json')
        incumbent_scores = ensemble.evaluate(incumbent, False)
        scores = ensemble.evaluate(angles, False)
        if scores.min() < incumbent_scores.min() - .003:
            angles = incumbent
            scores = incumbent_scores
        worst = np.argsort(scores)
        training = unique(core + [pool[index] for index in worst[:20]])
        print('EXPLORE', epoch, 'pool', len(pool), 'train', len(training), 'min', scores.min(), 'incumbent', incumbent_scores.min(), flush=True)
        angles = anneal(angles, training, steps=int(os.environ.get('ANNEAL_STEPS', 2800)), seed=epoch+33991)
        if epoch % 3 == 2:
            angles = np.clip(angles + generator.normal(0,.12,48), -np.pi, np.pi)
        scores = ensemble.evaluate(angles, False)
        training = unique(core + [pool[index] for index in np.argsort(scores)[:28]])
        angles = optimize(angles, training, iterations=650, temperature=.0005, filename=f'explore_{epoch:02d}.json')
        scores = ensemble.evaluate(angles, False)
        print('EXPLORE AFTER', epoch, scores.min(), scores.mean(), flush=True)
        if scores.min() > incumbent_scores.min():
            save(angles, 'robust_best.json')
            save(angles)
        (ROOT / 'stress_scenarios.json').write_text(json.dumps({'scenarios': pool}))
        if scores.min() > .957:
            break

if __name__ == '__main__':
    main()
