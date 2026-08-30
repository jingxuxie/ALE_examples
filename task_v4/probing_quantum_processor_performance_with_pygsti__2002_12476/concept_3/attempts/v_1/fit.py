import argparse
import json
import time

import numpy as np
from scipy.optimize import least_squares

from model import CENTER, ROOT, SCALE, combine, deviance, load, predict, report, select


class Objective:
    def __init__(self, data, ridge, label):
        self.data = data
        self.ridge = ridge
        self.label = label
        self.last = None
        self.evaluations = 0
        self.started = time.monotonic()

    def evaluate(self, scaled):
        if self.last is not None and np.array_equal(scaled, self.last):
            return
        self.last = scaled.copy()
        probabilities, jacobian = predict(CENTER + SCALE*scaled, self.data, True)
        self.residual, derivative = deviance(probabilities, self.data)
        self.jacobian = jacobian * derivative[:, None] * SCALE
        if self.ridge:
            self.residual = np.concatenate([self.residual, self.ridge*scaled])
            self.jacobian = np.concatenate([self.jacobian, self.ridge*np.eye(54)])
        self.evaluations += 1
        if self.evaluations % 10 == 1:
            print(self.label, 'eval', self.evaluations, 'chi2/row', np.sum(self.residual**2)/len(self.data['length']), 'seconds', time.monotonic()-self.started, flush=True)

    def fun(self, scaled):
        self.evaluate(scaled)
        return self.residual

    def jac(self, scaled):
        self.evaluate(scaled)
        return self.jacobian


def optimize(data, start, ridge, label, max_nfev=150):
    objective = Objective(data, ridge, label)
    result = least_squares(objective.fun, start, jac=objective.jac, bounds=(-np.ones(54), np.ones(54)),
                           max_nfev=max_nfev, ftol=1e-9, xtol=1e-9, gtol=1e-6, verbose=0)
    print(label, 'finished', result.message, 'nfev', result.nfev, 'cost', result.cost, 'optimality', result.optimality, flush=True)
    params = CENTER+SCALE*result.x
    np.savez(ROOT / (label+'.npz'), params=params, scaled=result.x, jacobian=result.jac,
             cost=result.cost, optimality=result.optimality)
    return result.x


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', type=int, required=True)
    parser.add_argument('--resume', type=str)
    parser.add_argument('--include-development', action='store_true')
    parser.add_argument('--tag', default='fit')
    args = parser.parse_args()
    train = load('train')
    train = select(train, train['device'] == args.device)
    development = load('development')
    development = select(development, development['device'] == args.device)
    start = np.zeros(54)
    if args.resume:
        start = (np.load(args.resume)['params']-CENTER)/SCALE
    else:
        for depth, ridge in [(24, 1.0), (64, 0.2)]:
            subset = select(train, train['length'] <= depth)
            start = optimize(subset, start, ridge, f'{args.tag}_d{args.device}_depth{depth}')
    start = optimize(train, start, 0, f'{args.tag}_d{args.device}_train')
    print('TRAIN', json.dumps(report(CENTER+SCALE*start, train)), flush=True)
    print('HELDOUT DEVELOPMENT', json.dumps(report(CENTER+SCALE*start, development)), flush=True)
    if args.include_development:
        start = optimize(combine(train, development), start, 0, f'{args.tag}_d{args.device}_all')
        print('COMBINED DEVELOPMENT', json.dumps(report(CENTER+SCALE*start, development)), flush=True)
    print('PARAMETERS', (CENTER+SCALE*start).tolist(), flush=True)


if __name__ == '__main__':
    main()
