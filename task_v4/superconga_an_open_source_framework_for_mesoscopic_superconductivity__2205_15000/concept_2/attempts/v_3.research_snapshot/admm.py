import json
import time

import numpy as np
from scipy.optimize import least_squares
from scipy.ndimage import label

from invert import Model, OUT, ROOT, load_problem, response, discrepancies, validate_design


def main():
    model = Model(stride=2)
    config, target = load_problem(ROOT / 'input')
    binary = np.asarray(json.loads((OUT / 'design.json').read_text())['pattern'], dtype=float)
    pattern = binary.copy()
    dual = np.zeros(144)
    penalty = .05
    best = discrepancies(config, response(config, binary), target)['relative_rmse']
    started = time.time()
    for iteration in range(50):
        factor = np.sqrt(penalty / 144)
        def objective(values):
            residual, derivative = model.objective(values, budget=30)
            return np.concatenate([residual, factor * (values - binary + dual)])
        def jacobian(values):
            residual, derivative = model.objective(values, budget=30)
            return np.vstack([derivative, factor * np.eye(144)])
        result = least_squares(objective, np.clip(pattern, 0, 1), jac=jacobian, bounds=(0, 1), max_nfev=15, ftol=1e-5, xtol=1e-7, gtol=1e-6)
        pattern = result.x
        previous = binary.copy()
        binary = np.zeros(144)
        material = np.ones(256, dtype=int)
        for candidate in np.argsort(pattern + dual)[::-1]:
            material[model.candidates[candidate]] = 0
            if label(material.reshape(16, 16))[1] == 1:
                binary[candidate] = 1
            else:
                material[model.candidates[candidate]] = 1
            if binary.sum() == 54:
                break
        dual += pattern - binary
        dual /= 1.07
        penalty *= 1.07
        metrics = discrepancies(config, response(config, binary), target)
        try:
            validate_design(config, binary)
            feasible = True
        except ValueError:
            feasible = False
        print('ADMM', iteration, 'continuous', np.linalg.norm(model.objective(pattern)[0]), 'binary', metrics['relative_rmse'], 'feasible', feasible, 'changed', np.sum(binary != previous), 'penalty', penalty, 'time', round(time.time() - started, 1), flush=True)
        if feasible and metrics['relative_rmse'] < best:
            best = metrics['relative_rmse']
            (OUT / 'admm_best.json').write_text(json.dumps({'pattern': binary.astype(int).tolist()}) + '\n')
            np.save(OUT / 'admm_best.npy', binary)
            print('BEST', metrics, flush=True)
            if metrics['core_score'] >= .96 and metrics['worst_family_score'] >= .94:
                (OUT / 'design.json').write_text(json.dumps({'pattern': binary.astype(int).tolist()}) + '\n')
                (OUT / 'match.json').write_text(json.dumps(metrics) + '\n')
                return


if __name__ == '__main__':
    main()
