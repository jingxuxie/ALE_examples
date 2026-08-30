import os
for variable in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS'):
    os.environ[variable] = '1'
import ctypes
import json
import sys
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT.parent.parent / 'participant'
sys.path.insert(0, str(ASSETS / 'workspace'))
from simulator import fidelities, training_scenarios

library = ctypes.CDLL(str(ROOT / os.environ.get('CONTROL_LIBRARY', 'control.so')))
array_pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
library.create_ensemble.argtypes = [array_pointer, ctypes.c_int]
library.create_ensemble.restype = ctypes.c_void_p
library.delete_ensemble.argtypes = [ctypes.c_void_p]
library.evaluate.argtypes = [ctypes.c_void_p, array_pointer, array_pointer, ctypes.c_void_p, ctypes.c_int]
library.evaluate_full.argtypes = [ctypes.c_void_p, array_pointer, array_pointer, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]

def encode(scenario):
    return [scenario['gain_a'], scenario['gain_b'], scenario['zz_common']] + list(scenario['zz_local']) + list(scenario.get('z_drift_radians_per_layer', [0.] * 12))

class Ensemble:
    def __init__(self, scenarios):
        self.parameters = np.ascontiguousarray([encode(scenario) for scenario in scenarios], dtype=np.float64)
        self.pointer = library.create_ensemble(self.parameters, len(scenarios))

    def evaluate(self, angles, gradient=True):
        angles = np.ascontiguousarray(angles, dtype=np.float64).ravel()
        scores = np.empty(len(self.parameters))
        gradients = np.empty((len(scores), 48)) if gradient else None
        library.evaluate(self.pointer, angles, scores, None if gradients is None else gradients.ctypes.data, 4)
        return (scores, gradients) if gradient else scores

    def __del__(self):
        if hasattr(self, 'pointer'):
            library.delete_ensemble(self.pointer)

    def evaluate_errors(self, angles):
        angles = np.ascontiguousarray(angles, dtype=np.float64).ravel()
        scores = np.empty(len(self.parameters))
        gradients = np.empty((len(scores), 48))
        error_gradients = np.empty((len(scores), 27))
        library.evaluate_full(self.pointer, angles, scores, gradients.ctypes.data, error_gradients.ctypes.data, 4)
        return scores, error_gradients

def save(angles, filename='pulses.json'):
    (ROOT / filename).write_text(json.dumps({'schema_version': 1, 'angles': np.asarray(angles).reshape(24, 2).tolist()}, indent=2) + '\n')

def load(filename):
    return np.array(json.loads(Path(filename).read_text())['angles']).ravel()

def optimize(angles, scenarios, iterations=500, temperature=.005, filename='pulses.json'):
    ensemble = Ensemble(scenarios)
    started = time.time()
    counter = 0
    best = -np.inf
    def objective(controls):
        nonlocal counter, best
        scores, gradients = ensemble.evaluate(controls)
        losses = -scores / temperature
        weights = np.exp(losses - logsumexp(losses))
        value = temperature * logsumexp(losses)
        gradient = -weights @ gradients
        counter += 1
        if scores.min() > best:
            best = float(scores.min())
            save(controls, filename)
        if counter % 20 == 0 or counter == 1:
            print(f'eval={counter} seconds={time.time()-started:.1f} min={scores.min():.9f} mean={scores.mean():.9f} best={best:.9f}', flush=True)
        return value, gradient
    result = minimize(objective, angles, jac=True, method='L-BFGS-B', bounds=[(-np.pi, np.pi)] * 48,
                      options={'maxiter': iterations, 'ftol': 1e-13, 'gtol': 1e-8, 'maxls': 30, 'maxcor': 20})
    print(result.message, 'iterations', result.nit, flush=True)
    return load(ROOT / filename)

def main():
    scenarios = training_scenarios()
    angles = load(ASSETS / 'baseline' / 'pulses.json')
    save(angles)
    ensemble = Ensemble(scenarios)
    started = time.time()
    scores, gradients = ensemble.evaluate(angles)
    reference = fidelities(angles.reshape(24, 2), scenarios)
    print('reference error', np.max(abs(scores-reference)), 'initial min', scores.min(), 'nominal', scores[0], 'seconds', time.time()-started, flush=True)
    for index in [0, 13, 47]:
        shifted = angles.copy()
        shifted[index] += 1e-6
        positive = ensemble.evaluate(shifted, False)
        shifted[index] -= 2e-6
        negative = ensemble.evaluate(shifted, False)
        print('gradient', index, np.max(abs((positive-negative)/2e-6-gradients[:,index])), flush=True)
    angles = optimize(angles, scenarios, 700, .01)
    angles = optimize(angles, scenarios, 400, .002)
    scores = fidelities(angles.reshape(24, 2), scenarios)
    print('FINAL PUBLIC', scores.min(), scores.mean(), flush=True)
    (ROOT / 'public_validation.json').write_text(json.dumps({'min': float(scores.min()), 'fidelities': scores.tolist()}, indent=2))

if __name__ == '__main__':
    main()
