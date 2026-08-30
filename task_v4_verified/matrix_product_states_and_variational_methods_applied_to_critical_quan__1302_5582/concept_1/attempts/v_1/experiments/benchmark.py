import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contractor import measure, hamiltonian_terms
from engine import Budget, DMRG


def uniform(name, length, dimension, cap, mass, quartic, spring, omega, sector):
    return dict(version=1, case_id=name, seed=1234, n_sites=length, local_dim=dimension,
                bond_cap=cap, sector=sector, mass2=[mass] * length,
                lambda4=[quartic] * length, omega=[omega] * length,
                coupling=[spring] * (length - 1), field=[0.] * length,
                budget_seconds=40., wall_seconds=120.)


def cases():
    result = [uniform('sym22', 22, 14, 12, 0.4, 2., 1.5, 1., 'even'),
              uniform('cross16', 16, 12, 10, -0.7, 2., 1., 1., 'even'),
              uniform('odd18', 18, 12, 10, -0.8, 2., 1., 0.8, 'odd'),
              uniform('deep22', 22, 14, 12, -2.8, 1.2, 1.5, 0.55, 'even'),
              uniform('deepodd16', 16, 12, 10, -2.4, 1.6, 1., 1.85, 'odd'),
              uniform('field18', 18, 14, 12, -1.8, 2., 0.8, 1., 'any'),
              uniform('interface22', 22, 14, 12, -1., 2., 1., 1., 'any'),
              uniform('weak22', 22, 14, 12, -1.4, 2., 0.9, 0.8, 'even')]
    result[5]['field'] = [0.001 * np.cos(site / 3) for site in range(18)]
    generator = np.random.default_rng(234)
    result[6]['mass2'] = np.linspace(-2.6, .7, 22).tolist()
    result[6]['omega'] = generator.uniform(.55, 1.85, 22).tolist()
    result[6]['lambda4'] = generator.uniform(1.2, 2.8, 22).tolist()
    result[6]['coupling'] = generator.uniform(.06, 1.5, 21).tolist()
    result[6]['field'] = generator.uniform(-.004, .004, 22).tolist()
    result[7]['coupling'][10] = .06
    return result


def run(request, seconds=40, initialization='product', pair_sweeps=30):
    start = time.process_time()
    request = dict(request, budget_seconds=start + seconds)
    budget = Budget(request)
    engine = DMRG(request, budget, initialization)
    print(request['case_id'], 'init', time.process_time() - start, flush=True)
    previous = np.inf
    for sweep_index in range(pair_sweeps):
        active = min(request['bond_cap'], 4 if sweep_index == 0 else request['bond_cap'])
        energy, complete = engine.sweep(active, 2e-5 if sweep_index == 0 else 2e-8, 70)
        report = measure(engine.output(), request)
        print(sweep_index, time.process_time() - start, energy, report, complete, flush=True)
        if not complete or (sweep_index > 1 and abs(previous - energy) < 1e-9 * request['n_sites']):
            break
        previous = energy
    if complete:
        print('reflection', engine.reflect_if_better(), flush=True)
        previous = np.inf
        for sweep_index in range(30):
            energy, complete = engine.refine()
            print('refine', sweep_index, time.process_time() - start, measure(engine.output(), request), complete, flush=True)
            if not complete or abs(previous - energy) < 2e-11 * request['n_sites']:
                break
            previous = energy
    return engine.output()


if __name__ == '__main__':
    selected = cases()
    if len(sys.argv) > 1:
        selected = [request for request in selected if request['case_id'] in sys.argv[1:]]
    for request in selected:
        Path(__file__).with_name(request['case_id'] + '.json').write_text(json.dumps(request))
        run(request, initialization='cat' if '--cat' in sys.argv else 'product', pair_sweeps=2 if '--two' in sys.argv else 30)
