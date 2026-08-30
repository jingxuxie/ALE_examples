import argparse
import math
import time
import numpy as np
from scipy.optimize import minimize
import fermion
from search import Engine, LIB, DOUBLE


LIB.sparse_options.argtypes = [DOUBLE, DOUBLE, DOUBLE]


def optimize(engine, labels, angles, evaluations=200):
    def objective(parameters):
        state, jacobian = engine.state_jac(labels, parameters)
        return 1 - np.sum(state**4), -4 * (jacobian.T @ (state**3))
    result = minimize(objective, np.asarray(angles), jac=True, method='L-BFGS-B', options={'maxiter': evaluations, 'ftol': 1e-13, 'gtol': 1e-9, 'maxls': 30})
    return np.array(labels, np.int32), (result.x + math.pi) % (2 * math.pi) - math.pi, result.fun


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, default=0)
    parser.add_argument('--seconds', type=float, default=300)
    parser.add_argument('--seed', type=int, default=100)
    args = parser.parse_args()
    case = fermion.load_cases()[args.case]
    engine = Engine(case)
    original = engine.initial.copy()
    engine.initial = engine.target.copy()
    rng = np.random.default_rng(args.seed)
    best = 1.0
    iteration = 0
    while time.time() - engine.started < args.seconds:
        iteration += 1
        labels = np.empty(0, np.int32)
        angles = np.empty(0)
        for position in range(case.max_gates):
            state, _ = engine.state_jac(labels, angles)
            gains, optimal = np.empty(250), np.empty(250)
            LIB.sparse_options(state, gains, optimal)
            top = np.argsort(gains)[-5:][::-1]
            if iteration > 1 and position < 6:
                top = rng.choice(np.argsort(gains)[-20:], 5, replace=False)
            trials = [optimize(engine, np.append(labels, label), np.append(angles, optimal[label]), 150) for label in top]
            labels, angles, loss = min(trials, key=lambda trial: trial[2])
            if iteration == 1 and position % 4 == 3:
                print(case.case_id, 'reverse',position+1,'quarticloss',loss,flush=True)
        state, _ = engine.state_jac(labels, angles)
        if loss < best:
            best = loss
            print('BEST reverse',iteration,'quarticloss',loss,'basis',np.argmax(abs(state)),'ref',np.argmax(original),'elapsed',time.time()-engine.started,flush=True)
            engine.save(labels, angles, loss, 'reverse')
        if loss < 1e-10:
            break


if __name__ == '__main__':
    main()
