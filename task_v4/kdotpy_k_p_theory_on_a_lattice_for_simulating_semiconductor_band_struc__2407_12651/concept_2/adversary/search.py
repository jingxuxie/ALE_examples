import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy.optimize import differential_evolution, minimize


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
from model import LOWER, UPPER, diagnose


def loss(parameters, size=19):
    metrics = diagnose(parameters, size)
    windows = np.array(metrics['windows'])
    chern = round(metrics['chern'])
    signed = windows * chern
    violation = 6 * max(0, .60 - metrics['sampled_gap']) ** 2
    violation += 20 * (abs(chern) != 1)
    violation += 2 * max(0, .21 - signed.mean()) ** 2
    violation += 2 * max(0, signed.mean() - .38) ** 2
    violation += 40 * np.var(windows)
    violation += 20 * max(0, .018 - metrics['retained_optical_min']) ** 2
    violation += 2 * max(0, abs(metrics['full'] - chern) - .01) ** 2
    return violation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=900)
    parser.add_argument('--seed', type=int, default=94821)
    parser.add_argument('--start')
    options = parser.parse_args()
    started = time.monotonic()
    record = {'evaluations': 0, 'best_loss': float('inf')}
    generator = np.random.default_rng(options.seed)
    bounds = list(zip(LOWER, UPPER))
    def objective(parameters):
        value = loss(parameters)
        record['evaluations'] += 1
        if value < record['best_loss']:
            record['best_loss'] = value
            record['elapsed'] = time.monotonic() - started
            record['parameters'] = parameters.tolist()
            (ROOT / 'adversary' / 'search_best.json').write_text(json.dumps(record, indent=2))
        if time.monotonic() - started > options.seconds:
            raise TimeoutError
        return value
    initial = json.loads(Path(options.start).read_text())['parameters'] if options.start else None
    try:
        while time.monotonic() - started < options.seconds:
            if initial is None:
                result = differential_evolution(objective, bounds, maxiter=45, popsize=4, polish=False,
                                                seed=int(generator.integers(2 ** 30)))
                initial = result.x
            result = minimize(objective, initial, method='L-BFGS-B', bounds=bounds,
                              options={'maxiter': 160, 'ftol': 1e-14})
            initial = np.clip(result.x + generator.normal(size=25) * .045, LOWER, UPPER)
    except TimeoutError:
        pass
    best = record['parameters']
    record['fine_metrics'] = diagnose(best, 97)
    (ROOT / 'adversary' / 'search_result.json').write_text(json.dumps(record, indent=2))
    (ROOT / 'adversary' / 'best_witness.json').write_text(json.dumps({'parameters': best}, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
