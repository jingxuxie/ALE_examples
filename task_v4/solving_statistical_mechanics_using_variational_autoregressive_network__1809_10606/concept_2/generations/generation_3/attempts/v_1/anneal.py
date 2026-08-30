import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from exact import LIMIT, LOWER, evaluate
from optimize import Model
from minimax import minimax
from sectors import best_sector


def train(witness, beta):
    witness = dict(witness, beta=beta)
    model = Model(witness)
    original = model.pack()
    split = np.r_[np.maximum(original[:120], 0), np.maximum(-original[:120], 0), beta]
    row_jac = np.zeros((15, 241))
    row_jac[LOWER[0] - 1, np.arange(120)] = -1
    row_jac[LOWER[0] - 1, np.arange(120) + 120] = -1

    def merge(parameters):
        return np.r_[parameters[:120] - parameters[120:240], parameters[-1]]

    def transform(derivative):
        return np.r_[derivative[:120], -derivative[:120], derivative[-1]]

    def objective(parameters):
        values, derivative = model.calc(merge(parameters))
        return values[2], transform(derivative[2])

    def constraints(parameters):
        values, derivative = model.calc(merge(parameters))
        return np.r_[LIMIT - 3e-12 + row_jac @ parameters, (.000999 - values[5]) * 100, values[1] - 3]

    def constraints_jac(parameters):
        values, derivative = model.calc(merge(parameters))
        return np.vstack([row_jac, -100 * transform(derivative[5]), transform(derivative[1])])

    result = minimize(objective, split, jac=True, method='SLSQP',
                      bounds=[(0, LIMIT)] * 240 + [(beta, beta)],
                      constraints={'type': 'ineq', 'fun': constraints, 'jac': constraints_jac},
                      options={'maxiter': 180, 'ftol': 1e-10})
    return model.unpack(merge(result.x))


def run(source, prefix):
    source = Path(source)
    original = json.loads(source.read_text())
    best = original
    best_score = evaluate(best)['core_score']
    start = time.time()
    for index, beta in enumerate([1.0, 1.25, 1.5, 2.0, 3.0]):
        trained = train(best, beta)
        print('trained',beta,round(time.time()-start,1),evaluate(trained),flush=True)
        trained['beta'] = 1.0
        result = minimax(trained, 140, verbose=False)
        result, _, _ = best_sector(result, strict=False)
        report = evaluate(result)
        Path(f'{prefix}_{index}.json').write_text(json.dumps(result))
        print('refined',beta,round(time.time()-start,1),report,flush=True)
        if report['core_score'] > best_score:
            best, best_score = result, report['core_score']
            Path(prefix + '_best.json').write_text(json.dumps(best))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--prefix', default='anneal')
    arguments = parser.parse_args()
    run(arguments.source, arguments.prefix)
