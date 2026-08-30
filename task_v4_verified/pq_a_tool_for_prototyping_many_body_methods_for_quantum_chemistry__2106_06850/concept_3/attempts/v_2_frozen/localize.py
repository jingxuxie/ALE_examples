import argparse
import time
import numpy as np
from scipy.optimize import minimize
import fermion
from search import Engine


parser = argparse.ArgumentParser()
parser.add_argument('--case', type=int, default=0)
parser.add_argument('--restarts', type=int, default=50)
args = parser.parse_args()
engine = Engine(fermion.load_cases()[args.case])
engine.initial = engine.target.copy()
labels = np.arange(20, dtype=np.int32)
rng = np.random.default_rng(100)
best = 100
for restart in range(args.restarts):
    angles = rng.uniform(-np.pi, np.pi, 20)
    for epsilon in [0.03, 0.003, 0.0001, 1e-7]:
        def objective(parameters):
            state, jacobian = engine.state_jac(labels, parameters)
            absolute = np.sqrt(state * state + epsilon * epsilon)
            return np.sum(absolute), jacobian.T @ (state / absolute)
        result = minimize(objective, angles, jac=True, method='BFGS', options={'gtol': 1e-8, 'maxiter': 300})
        angles = result.x
    state, _ = engine.state_jac(labels, angles)
    value = np.sum(abs(state))
    if value < best:
        best = value
        print('best',restart,'l1',value,'ipr',sum(state**4),'zeros',sum(abs(state)<1e-5),'largest',np.sort(abs(state))[-10:],'elapsed',time.time()-engine.started,flush=True)
        np.savez(engine.case.case_id + '_localized.npz', state=state, angles=angles, labels=labels)
