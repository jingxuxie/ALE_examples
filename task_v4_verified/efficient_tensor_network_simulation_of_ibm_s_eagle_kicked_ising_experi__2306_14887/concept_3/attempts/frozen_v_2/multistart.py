import os
import json
import time
import numpy as np
from scipy.optimize import minimize
from optimize import ROOT, Ensemble, load, save, optimize, training_scenarios
from robustness import make_pool, unique, adversaries, gauge_search

def main():
    generator = np.random.default_rng(int(os.environ.get('SEARCH_SEED', 90416)))
    nominal = Ensemble([training_scenarios()[0]])
    pool = make_pool()
    if (ROOT / 'stress_scenarios.json').exists():
        pool = unique(pool + json.loads((ROOT / 'stress_scenarios.json').read_text())['scenarios'])
    core = [scenario for scenario in pool if scenario['name'].startswith('corner_') and
            scenario['name'].endswith(tuple(f'_field_{field}' for field in range(5)))]
    core += [training_scenarios()[0]]
    core_ensemble = Ensemble(core)
    archive_path = ROOT/os.environ.get('CANDIDATES_FILE','nominal_candidates.npz')
    center = load(ROOT/os.environ['CENTER_FILE']).reshape(24,2).mean(axis=1) if os.environ.get('CENTER_FILE') else None
    candidates = []
    if os.environ.get('SKIP_NOMINAL'):
        archive = np.load(archive_path)
        candidates = [(float(score),angles.copy(),index) for index,(score,angles) in enumerate(zip(archive['scores'],archive['angles']))]
    started = time.time()
    def nominal_objective(controls):
        angles = np.repeat(controls[:,None],2,axis=1).ravel()
        scores, gradients = nominal.evaluate(angles)
        return -scores[0], -gradients[0].reshape(24,2).sum(axis=1)
    for trial in range(0 if os.environ.get('SKIP_NOMINAL') else int(os.environ.get('NOMINAL_TRIALS', 100))):
        initial = generator.uniform(-np.pi/2,np.pi/2,24) if center is None else center + generator.normal(0,[.15,.3,.6,1.][trial%4],24)
        result = minimize(nominal_objective, initial, jac=True, method='L-BFGS-B',
                          options={'maxiter': 500, 'ftol': 1e-12, 'gtol': 1e-7, 'maxcor': 20})
        if -result.fun < .9999:
            print('nominal failed', trial, -result.fun, flush=True)
            continue
        controls = (result.x + np.pi/2) % np.pi - np.pi/2
        if center is not None:
            alternate = controls - np.where(controls >= 0,np.pi,-np.pi)
            controls = np.where(abs(controls-center) < abs(alternate-center),controls,alternate)
        angles = np.repeat(controls[:,None],2,axis=1).ravel()
        angles = gauge_search(angles, core, rounds=1, temperature=.002)
        scores = core_ensemble.evaluate(angles, False)
        candidates.append((float(scores.min()), angles.copy(), trial))
        print('NOMINAL', trial, 'min', scores.min(), 'best', max(item[0] for item in candidates), 'seconds',time.time()-started, flush=True)
        if trial % 10 == 0:
            np.savez(archive_path, angles=np.array([item[1] for item in candidates]), scores=np.array([item[0] for item in candidates]))
    candidates.sort(key=lambda item: item[0], reverse=True)
    np.savez(archive_path, angles=np.array([item[1] for item in candidates]), scores=np.array([item[0] for item in candidates]))
    if center is not None:
        selected = []
        for candidate in candidates:
            controls = candidate[1].reshape(24,2).mean(axis=1)
            if all(np.linalg.norm((controls-other[1].reshape(24,2).mean(axis=1)+np.pi/2)%np.pi-np.pi/2) > 1.0 for other in selected):
                selected.append(candidate)
        candidates = selected
    for rank, (initial_score, angles, trial) in enumerate(candidates[:int(os.environ.get('REFINE_TRIALS', 10))]):
        save(angles, f'nominal_rank_{rank:02d}.json')
        print('REFINE', rank, 'trial', trial, flush=True)
        for epoch in range(3):
            pool = unique(pool + adversaries(angles, starts=24, seed=37151+rank*10+epoch))
            ensemble = Ensemble(pool)
            scores = ensemble.evaluate(angles, False)
            training = unique(core + [pool[index] for index in np.argsort(scores)[:28]])
            if epoch == 1:
                angles = gauge_search(angles, training, rounds=2, temperature=.001)
            angles = optimize(angles, training, iterations=650 if epoch == 0 else 320,
                              temperature=.001 if epoch == 0 else .0003,
                              filename=f'restart_{rank:02d}_{epoch}.json')
            scores = ensemble.evaluate(angles, False)
            incumbent = load(ROOT/'robust_best.json')
            incumbent_min = float(ensemble.evaluate(incumbent, False).min())
            print('REFINED', rank, epoch, 'min', scores.min(), 'incumbent', incumbent_min, flush=True)
            if scores.min() > incumbent_min:
                save(angles, 'robust_best.json')
                save(angles)
            (ROOT/'stress_scenarios.json').write_text(json.dumps({'scenarios':pool}))
            if scores.min() > .956:
                return

if __name__ == '__main__':
    main()
