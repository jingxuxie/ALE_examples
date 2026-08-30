import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
sys.argv = ['structured_search.py', '519']
import json
import time
import numpy as np
from scipy.optimize import minimize
from gradient_search import Objective
from search import OUT, evaluate, save

random = np.random.default_rng(511953)
started = time.time()
mappings = [np.array([2 * (site // 4 % 2) + site % 2 for site in range(16)]),
            np.array([site // 4 for site in range(16)]),
            np.array([(site // 4 + site % 4) % 4 for site in range(16)]),
            np.array([2 * (site // 8) + (site % 4) // 2 for site in range(16)])]

def main():
    best = 10
    archives = [[] for mapping in mappings]
    for restart in range(10000):
        if (OUT / 'witness.json').exists() or (OUT / 'STOP_STRUCTURED').exists():
            return
        mode = restart % len(mappings)
        mapping = mappings[mode]
        archive = archives[mode]
        if not archive or random.random() < 0.3:
            fields = random.choice([-1, 1], size=(16, 4)).astype(float)
        else:
            fields = archive[int(random.integers(min(8, len(archive))))][1].copy()
            for site in random.choice(4, size=int(random.integers(1, 5)), replace=False):
                fields[:, site] = np.roll(fields[:, site], int(random.integers(1, 16)))
            if random.random() < .3:
                fields *= random.choice([-1, 1], size=fields.shape, p=[.15, .85])
        for beta in ([.75] if restart % 3 else [1.5, 1.1, .9, .8, .75]):
            full_objective = Objective(beta)
            def objective(flat):
                full = flat.reshape(16, 4)[:, mapping]
                value, gradient = full_objective(full.ravel())
                gradient = gradient.reshape(16, 16)
                reduced = np.stack([gradient[:, mapping == site].sum(axis=1) for site in range(4)], axis=1)
                return value, reduced.ravel()
            result = minimize(objective, fields.ravel(), jac=True, bounds=[(-1, 1)] * 64,
                              method='L-BFGS-B', options={'maxiter': 400, 'ftol': 1e-13, 'gtol': 1e-8, 'maxls': 30})
            fields = result.x.reshape(16, 4)
        rounded = np.where(fields > 0, 1, -1)
        full = rounded[:, mapping]
        score = evaluate(full)[0]
        if score < best:
            best = score
            save(full, 'structured_best.json')
            print(f'{time.time()-started:.2f}s restart={restart} mode={mode} best={score:.12g} continuous={result.fun:.12g}', flush=True)
        if score < -1e-5:
            save(full)
            print('FOUND', flush=True)
            return
        if all(np.count_nonzero(rounded != np.sign(previous[1])) > 3 for previous in archive):
            archive.append((score, fields.copy()))
            archive.sort(key=lambda entry: entry[0])
            archives[mode] = archive[:16]
        if restart % 40 == 0:
            print(f'{time.time()-started:.2f}s restart={restart} mode={mode} score={score:.12g}', flush=True)

if __name__ == '__main__':
    main()
