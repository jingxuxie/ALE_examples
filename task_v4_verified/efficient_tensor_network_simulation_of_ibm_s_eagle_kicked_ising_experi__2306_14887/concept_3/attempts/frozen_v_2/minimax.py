import os
import json
import time
import numpy as np
from scipy.optimize import minimize
from optimize import ROOT, Ensemble, load, save, training_scenarios
from robustness import make_pool, unique, adversaries

def fit(angles, scenarios, filename, iterations=500):
    ensemble = Ensemble(scenarios)
    previous = None
    cache = None
    best = -np.inf
    evaluations = 0
    started = time.time()
    def evaluate(controls):
        nonlocal previous, cache, best, evaluations
        if previous is None or not np.array_equal(controls,previous):
            cache = ensemble.evaluate(controls)
            previous = controls.copy()
            evaluations += 1
            if cache[0].min() > best:
                best = float(cache[0].min())
                save(controls,filename)
            if evaluations % 20 == 0 or evaluations == 1:
                print('minimax',evaluations,'min',cache[0].min(),'best',best,'seconds',time.time()-started,flush=True)
        return cache
    initial_scores = evaluate(angles)[0]
    initial = np.r_[angles, initial_scores.min()-.00001]
    objective_gradient = np.r_[np.zeros(48),-1.]
    def constraints(values):
        return evaluate(values[:48])[0] - values[-1]
    def constraint_jacobian(values):
        return np.column_stack((evaluate(values[:48])[1], -np.ones(len(scenarios))))
    result = minimize(lambda values: -values[-1], initial, jac=lambda values: objective_gradient,
                      method='SLSQP', bounds=[(-np.pi,np.pi)]*48+[(0,1)],
                      constraints={'type':'ineq','fun':constraints,'jac':constraint_jacobian},
                      options={'maxiter':iterations,'ftol':1e-11,'disp':True})
    print('minimax result',result.message,'nit',result.nit,flush=True)
    return load(ROOT/filename)

def main():
    pool = make_pool()
    if (ROOT/'stress_scenarios.json').exists():
        pool = unique(pool + json.loads((ROOT/'stress_scenarios.json').read_text())['scenarios'])
    angles = load(ROOT/os.environ.get('WARM_START','robust_best.json'))
    core = [scenario for scenario in pool if scenario['name'].startswith('corner_') and
            scenario['name'].endswith(tuple(f'_field_{field}' for field in range(5)))]
    core += [training_scenarios()[0]]
    for epoch in range(int(os.environ.get('MINIMAX_EPOCHS',5))):
        pool = unique(pool+adversaries(angles,starts=40,seed=597914+epoch))
        ensemble = Ensemble(pool)
        scores = ensemble.evaluate(angles,False)
        training = unique(core+[pool[index] for index in np.argsort(scores)[:80]])
        print('MINIMAX EPOCH',epoch,'pool',len(pool),'train',len(training),'min',scores.min(),flush=True)
        angles = fit(angles,training,f'minimax_{epoch:02d}.json')
        scores = ensemble.evaluate(angles,False)
        incumbent = load(ROOT/'robust_best.json')
        incumbent_score = float(ensemble.evaluate(incumbent,False).min())
        print('MINIMAX AFTER',epoch,'min',scores.min(),'incumbent',incumbent_score,flush=True)
        if scores.min() > incumbent_score:
            save(angles,'robust_best.json')
            save(angles)
        (ROOT/'stress_scenarios.json').write_text(json.dumps({'scenarios':pool}))
        if scores.min() > .956:
            break

if __name__ == '__main__':
    main()
