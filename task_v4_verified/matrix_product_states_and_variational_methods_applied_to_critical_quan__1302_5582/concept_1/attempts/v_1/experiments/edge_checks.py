import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contractor import hamiltonian_terms, measure
from engine import optimize
from benchmark import uniform


for dimension in (6, 7, 9, 14):
    for sector in ('even', 'odd', 'any'):
        request = uniform('decoupled', 9, dimension, 7, -2.8, 1.2, 0., .55, sector)
        request['mass2'] = [-2.8, .8, -1.5, -.7, -2.4, .2, -2.8, -.8, -1.9]
        onsite, _ = hamiltonian_terms(request)
        costs = np.array([0., np.inf])
        for local in onsite:
            values = [eigh(local[charge::2, charge::2], eigvals_only=True)[0] for charge in (0, 1)]
            costs = np.array([min(costs[total ^ charge] + values[charge] for charge in (0, 1)) for total in (0, 1)])
        expected = min(costs) if sector == 'any' else costs[int(sector == 'odd')]
        request['budget_seconds'] = time.process_time() + 6
        report = measure(optimize(request), request)
        error = report['energy'] - expected
        print(dimension, sector, error, report, flush=True)
        assert abs(error) < 1e-8
print('Decoupled and odd-dimension checks passed')
