import json
import time

import numpy as np
from scipy.optimize import minimize

from infer import ASSETS, OUTPUT, Likelihood, load_data
from native import NativeLikelihood


configurations, betas, spec = load_data()
likelihood = NativeLikelihood(Likelihood(configurations, betas, spec))
queries = json.loads((ASSETS / 'input/queries.json').read_text())
reference = np.load(OUTPUT / 'fit.npz')
reference_prediction = likelihood.predict(reference['theta'], queries)
rng = np.random.default_rng(369281)
report = []
for restart in range(5):
    started = time.monotonic()
    initial = np.concatenate((rng.uniform(0.3, 0.95, 172), rng.uniform(-0.12, 0.12, 96)))
    result = minimize(likelihood.evaluate, initial, jac=True, bounds=[(0.3, 0.95)] * 172 + [(-0.12, 0.12)] * 96, method='L-BFGS-B', options={'maxiter': 1800, 'maxcor': 40, 'ftol': 3e-13, 'gtol': 1e-7})
    predicted = likelihood.predict(result.x, queries)
    item = {'restart': restart, 'loss': float(result.fun), 'loss_difference': float(result.fun - reference['loss']), 'max_predictive_tv': float(np.max(0.5 * np.sum(np.abs(predicted - reference_prediction), axis=1))), 'iterations': int(result.nit), 'seconds': time.monotonic() - started}
    report.append(item)
    print(json.dumps(item), flush=True)
    np.savez(OUTPUT / f'restart_{restart}.npz', theta=result.x, loss=result.fun, predictions=predicted)
(OUTPUT / 'multistart.json').write_text(json.dumps(report, indent=2))
