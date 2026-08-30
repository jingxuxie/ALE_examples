import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '4' if variable == 'OMP_NUM_THREADS' else '1'
import argparse
import gzip
import json
from pathlib import Path
import pickle
import time
import numpy as np
from sklearn.experimental import enable_hist_gradient_boosting
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from descriptors import feature_matrix
from test_stream import metrics


def load_records(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--generated', default='generated.jsonl')
    parser.add_argument('--prefix', default='candidate')
    parser.add_argument('--length', type=int, choices=(10, 12), default=12)
    arguments = parser.parse_args()
    training = load_records('../../participant/input/train.jsonl') + load_records(arguments.generated)
    training = [case for case in training if case['L'] == arguments.length]
    validation = [case for case in load_records('../../participant/input/validation.jsonl') if case['L'] == arguments.length]
    features = feature_matrix(training).astype(np.float32)
    targets = np.array([case['f'] for case in training])
    valid_features = feature_matrix(validation).astype(np.float32)
    predictions = {}
    results = {}
    print('training', len(training), 'validation', len(validation), flush=True)
    configurations = {
        'et85': ExtraTreesRegressor(n_estimators=400, max_features=0.85, min_samples_leaf=1, n_jobs=4, random_state=20101992),
        'et60': ExtraTreesRegressor(n_estimators=400, max_features=0.60, min_samples_leaf=1, n_jobs=4, random_state=30101992),
        'hist15': HistGradientBoostingRegressor(max_iter=700, max_leaf_nodes=15, learning_rate=0.045,
                                              l2_regularization=0.1, min_samples_leaf=15, early_stopping=False, random_state=42),
        'hist31': HistGradientBoostingRegressor(max_iter=550, max_leaf_nodes=31, learning_rate=0.045,
                                              l2_regularization=0.2, min_samples_leaf=15, early_stopping=False, random_state=43),
    }
    for name, model in configurations.items():
        started = time.monotonic()
        model.fit(features, targets)
        estimates = np.clip(model.predict(valid_features), 0, 1)
        predictions[name] = estimates
        result = metrics(validation, {'predictions': [{'id': case['id'], 'f': float(value)}
                                                     for case, value in zip(validation, estimates)]})
        result['train_seconds'] = time.monotonic() - started
        results[name] = result
        print(name, json.dumps(result), flush=True)
        with gzip.open(f'{arguments.prefix}_{name}.pkl.gz', 'wb', compresslevel=3) as stream:
            pickle.dump(model, stream, protocol=4)
        np.savez(f'{arguments.prefix}_predictions.npz', **predictions)
        Path(f'{arguments.prefix}_metrics.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
