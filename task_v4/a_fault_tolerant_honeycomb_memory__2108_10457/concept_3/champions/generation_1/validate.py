import csv
import importlib.util
import json
import os
import time
from pathlib import Path

import solve
import numpy as np
from scipy.optimize import brentq
from scipy.special import xlogy


def interval(row):
    shots = row['num_shots']
    failures = row['failures']
    observed = failures / shots

    def objective(log_probability):
        probability = np.exp(log_probability)
        return (xlogy(failures, observed / probability)
                + xlogy(shots-failures, (1-observed) / (1-probability)) - np.log(1000))

    lower = -np.inf if failures == 0 else brentq(objective, -100, np.log(observed))
    upper = brentq(objective, np.log(max(observed, 1e-40)), -1e-10)
    return np.array([lower, upper]) / np.log(10)


def score(rows, predictions):
    cells = {}
    for row, prediction in zip(rows, predictions):
        lower, upper = interval(row)
        residual = max(lower-np.log10(prediction), np.log10(prediction)-upper, 0)
        group = row['circuit_style'], row['decoder'], row['preserved_observable']
        cells.setdefault(group, []).append(residual**2)
    families = sorted({group[:2] for group in cells})
    losses = {str(group): float(np.sqrt(np.mean([np.mean(values) for key, values in cells.items()
                                                if key[:2] == group]))) for group in families}
    return {'worst_score': 10**(-max(losses.values())), 'family_losses': losses}


def baseline_predict(baseline, training, queries):
    models = {group: baseline.fit([row for row in training if baseline.family(row) == group])
              for group in sorted({baseline.family(row) for row in training})}
    return np.array([float((.5 * baseline.expit(baseline.features([row]) @ models[baseline.family(row)]))[0])
                     for row in queries])


def main():
    root = Path(os.environ['TASK_ROOT'])
    rows = solve.read_rows(root / 'input/train.csv')
    queries = solve.read_rows(root / 'input/queries.csv')
    specification = importlib.util.spec_from_file_location('baseline', root / 'baseline/solve.py')
    baseline = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(baseline)
    results = {}
    split_masks = {'size': [row['code_distance'] < 10 for row in rows]}
    for threshold in [.0005, .0007, .001]:
        split_masks['noise_from_' + str(threshold)] = [row['noise'] >= threshold for row in rows]
    for name, mask in split_masks.items():
        training = [row for row, keep in zip(rows, mask) if keep]
        validation = [row for row, keep in zip(rows, mask) if not keep]
        started = time.perf_counter()
        predictions = solve.predict(training, validation)
        result = score(validation, predictions)
        result['seconds'] = time.perf_counter() - started
        baseline_result = score(validation, baseline_predict(baseline, training, validation))
        results[name] = {'submission': result, 'baseline': baseline_result}
        print(name, 'submission', round(result['worst_score'], 4),
              'baseline', round(baseline_result['worst_score'], 4), flush=True)
    started = time.perf_counter()
    full_predictions = solve.predict(rows, queries)
    runtime = time.perf_counter() - started
    with open('predictions.csv', newline='') as stream:
        output = list(csv.DictReader(stream))
    assert len(output) == len(queries) == 692
    assert len({row['query_id'] for row in output}) == 692
    assert set(output[0]) == {'query_id', 'p_failure'}
    assert {row['query_id'] for row in output} == {row['query_id'] for row in queries}
    assert all(np.isfinite(float(row['p_failure'])) and 1e-15 <= float(row['p_failure']) <= 1-1e-15
               for row in output)
    assert np.allclose(full_predictions, [float(row['p_failure']) for row in output], rtol=1e-10, atol=0)
    shuffled = np.random.default_rng(42).permutation(len(queries))
    shuffled_predictions = solve.predict(rows, [queries[index] for index in shuffled])
    assert np.allclose(shuffled_predictions, full_predictions[shuffled], rtol=1e-10, atol=0)
    results['interface'] = {'valid': True, 'rows': len(output), 'runtime_seconds': runtime,
                            'minimum': float(full_predictions.min()), 'maximum': float(full_predictions.max()),
                            'query_order_invariant': True}
    with open('validation_results.json', 'w') as stream:
        json.dump(results, stream, indent=2)
    print('interface', results['interface'], flush=True)


if __name__ == '__main__':
    main()
