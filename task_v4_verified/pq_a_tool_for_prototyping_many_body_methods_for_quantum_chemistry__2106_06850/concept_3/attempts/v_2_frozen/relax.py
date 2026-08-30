import argparse
import ctypes
import math
import time
import numpy as np
from scipy.optimize import minimize
import fermion
from search import Engine, LIB, DOUBLE


LIB.mixture.argtypes = [ctypes.c_int, DOUBLE, DOUBLE, DOUBLE, ctypes.c_double, DOUBLE, DOUBLE]
LIB.mixture.restype = ctypes.c_double
parser = argparse.ArgumentParser()
parser.add_argument('--case', type=int, default=0)
parser.add_argument('--seconds', type=float, default=300)
parser.add_argument('--seed', type=int, default=100)
parser.add_argument('--warm', action='store_true')
args = parser.parse_args()
engine = Engine(fermion.load_cases()[args.case])
engine.best = engine.load()[2]
length = engine.case.max_gates
total = length * 250
rng = np.random.default_rng(args.seed)
iteration = 0
while time.time() - engine.started < args.seconds:
    iteration += 1
    logits = rng.normal(0, 0.5, (length, 250))
    angles = rng.normal(0, 1.0, (length, 250))
    if args.warm:
        labels, old_angles, old_loss = engine.load()
        logits[np.arange(length), labels] = 6.0
        angles[np.arange(length), labels] = old_angles
    parameters = np.concatenate((logits.ravel(), angles.ravel()))
    gradient = np.empty_like(parameters)
    metrics = np.empty(2)
    for penalty in [0.00001, 0.0001, 0.001, 0.01, 0.1, 1.0]:
        def objective(values):
            loss = LIB.mixture(length, values, engine.initial, engine.target, penalty, gradient, metrics)
            return loss, gradient.copy()
        result = minimize(objective, parameters, jac=True, method='L-BFGS-B', bounds=[(-12, 12)] * total + [(-math.pi, math.pi)] * total, options={'maxiter': 600, 'ftol': 1e-12, 'gtol': 1e-7, 'maxls': 30, 'maxcor': 10})
        parameters = result.x
        objective(parameters)
        labels = np.argmax(parameters[:total].reshape(length, 250), axis=1).astype(np.int32)
        chosen_angles = parameters[total:].reshape(length, 250)[np.arange(length), labels]
        labels, chosen_angles, loss = engine.optimize(labels, chosen_angles, 400)
        engine.save(labels, chosen_angles, loss)
        logits = parameters[:total].reshape(length, 250)
        probability = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        probability /= probability.sum(axis=1, keepdims=True)
        print('round',iteration,'penalty',penalty,'relaxed',metrics.copy(),'pure',np.mean(np.max(probability,axis=1)),'hardloss',loss,'elapsed',time.time()-engine.started,flush=True)
        np.save(engine.case.case_id + '_relaxed.npy', parameters)
