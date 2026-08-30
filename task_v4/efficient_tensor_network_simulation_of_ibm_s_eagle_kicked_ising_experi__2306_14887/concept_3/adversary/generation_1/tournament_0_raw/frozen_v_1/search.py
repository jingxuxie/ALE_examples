import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import ctypes
import itertools
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT.parent.parent / 'participant'
sys.path.insert(0, str(ASSETS / 'workspace'))
from simulator import fidelities, training_scenarios, save_pulses

LIBRARY = ctypes.CDLL(str(ROOT / 'gaussian.so'))
ARRAY = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
LIBRARY.evaluate.argtypes = [ARRAY, ARRAY, ctypes.c_int, ARRAY, ARRAY]

def evaluate(angles, errors):
    angles = np.ascontiguousarray(angles, dtype=float).reshape(48)
    errors = np.ascontiguousarray(errors, dtype=float).reshape(-1, 15)
    scores = np.empty(len(errors))
    gradients = np.empty((len(errors), 48))
    LIBRARY.evaluate(angles, errors, len(errors), scores, gradients)
    return scores, gradients

def to_errors(scenarios):
    return np.asarray([[entry['gain_a'], entry['gain_b'], entry['zz_common'], *entry['zz_local']] for entry in scenarios])

def scenarios_from_errors(errors):
    return [dict(gain_a=row[0], gain_b=row[1], zz_common=row[2], zz_local=row[3:].tolist()) for row in errors]

def stress_set():
    rows = list(to_errors(training_scenarios()))
    for gain_a, gain_b, common in itertools.product((-0.025, 0.025), (-0.025, 0.025), (-0.015, 0.015)):
        patterns = [np.full(12, 0.005), np.full(12, -0.005), 0.005*(-1.)**np.arange(12), -0.005*(-1.)**np.arange(12)]
        patterns += [0.005*np.cos(2*np.pi*np.arange(12)/12+phase) for phase in np.arange(4)*np.pi/2]
        for pattern in patterns:
            rows.append(np.r_[gain_a, gain_b, common, pattern])
    return np.array(rows)

def verify():
    random = np.random.default_rng(123)
    errors = stress_set()[[0, 1, 8, 20, 40]]
    angles = random.uniform(-3, 3, 48)
    fast, gradient = evaluate(angles, errors)
    exact = fidelities(angles.reshape(24, 2), scenarios_from_errors(errors))
    print('fidelity comparison', fast, exact, 'max error', np.max(abs(fast-exact)), flush=True)
    numerical = []
    for index in range(48):
        step = np.zeros(48)
        step[index] = 1e-5
        numerical.append((evaluate(angles+step, errors)[0]-evaluate(angles-step, errors)[0])/2e-5)
    print('gradient max error', np.max(abs(gradient-np.array(numerical).T)), flush=True)
    assert np.max(abs(fast-exact)) < 1e-10
    assert np.max(abs(gradient-np.array(numerical).T)) < 1e-8
    start = time.monotonic()
    for repeat in range(100):
        evaluate(angles, stress_set())
    print('seconds per evaluation', (time.monotonic()-start)/100, flush=True)

def optimize(angles, errors, temperature, iterations=1000, global_only=False, label=''):
    start = time.monotonic()
    evaluations = 0
    def objective(controls):
        nonlocal evaluations
        expanded = np.repeat(controls, 2) if global_only else controls
        scores, gradients = evaluate(expanded, errors)
        if temperature:
            logits = -scores/temperature
            normalizer = logsumexp(logits)
            weights = np.exp(logits-normalizer)
            loss = temperature*(normalizer-np.log(len(scores)))
        else:
            weights = np.full(len(scores), 1/len(scores))
            loss = -np.mean(scores)
        gradient = -weights@gradients
        if global_only:
            gradient = gradient.reshape(24, 2).sum(axis=1)
        evaluations += 1
        if evaluations % 100 == 0:
            print(label, evaluations, 'min', scores.min(), 'mean', scores.mean(), 'seconds', time.monotonic()-start, flush=True)
        return loss, gradient
    initial = np.asarray(angles).reshape(24, 2)[:, 0] if global_only else np.asarray(angles).reshape(48)
    result = minimize(objective, initial, jac=True, method='L-BFGS-B', bounds=[(-np.pi, np.pi)]*len(initial),
                      options=dict(maxiter=iterations, ftol=1e-13, gtol=1e-8, maxls=40, maxcor=30))
    final = np.repeat(result.x, 2) if global_only else result.x
    scores = evaluate(final, errors)[0]
    print('DONE', label, result.message, 'iterations', result.nit, 'min', scores.min(), 'mean', scores.mean(), 'seconds', time.monotonic()-start, flush=True)
    return final

def main():
    verify()
    baseline = np.array(json.loads((ASSETS / 'baseline' / 'pulses.json').read_text())['angles']).reshape(48)
    save_pulses(ROOT, baseline.reshape(24, 2))
    errors = stress_set()
    print('baseline', evaluate(baseline, errors)[0], flush=True)
    angles = baseline
    for temperature in (0.02, 0.005, 0.001):
        angles = optimize(angles, errors, temperature, 1500, label=f'baseline temp={temperature}')
        save_pulses(ROOT, angles.reshape(24, 2))
        np.save(ROOT / f'candidate_{temperature}.npy', angles)
    scores = fidelities(angles.reshape(24, 2), scenarios_from_errors(errors))
    print('EXACT STRESS', scores.min(), scores.mean(), flush=True)
    (ROOT / 'stress_validation.json').write_text(json.dumps(dict(min_fidelity=float(scores.min()), mean_fidelity=float(scores.mean()), fidelities=scores.tolist()), indent=2)+'\n')

if __name__ == '__main__':
    main()
