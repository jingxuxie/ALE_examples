import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'

import concurrent.futures
import gzip
import json
from pathlib import Path
import pickle
import sys
import numpy as np
from scipy.special import expit
from transforms import transform
from native_features import describe_cases


BUNDLE = None


def assemble(cases, variants):
    if not variants.issubset({'base', 'structure', 'algebra'}):
        raise ValueError('Unsupported model descriptors')
    features = describe_cases(cases, spectral=variants != {'algebra'})
    return {variant: features[:, np.r_[0:226, 594:889]] if variant == 'algebra'
            else features[:, :782] if variant == 'base' else features for variant in variants}


def neural_predict(model, features, normalized=None):
    matrix = transform(model['transformer'], features).astype(np.float32) if normalized is None else normalized
    matrix = matrix[:, :model['snapshots'][0]['0.weight'].shape[1]]
    predictions = np.zeros(len(features))
    for snapshot in model['snapshots']:
        hidden = matrix @ snapshot['0.weight'].T + snapshot['0.bias']
        hidden = hidden * expit(hidden)
        hidden = hidden @ snapshot['3.weight'].T + snapshot['3.bias']
        hidden = hidden * expit(hidden)
        hidden = hidden @ snapshot['6.weight'].T + snapshot['6.bias']
        predictions += expit(hidden).ravel()
    return predictions / len(model['snapshots'])


def kernel_predict(model, features):
    predictions = np.zeros(len(features))
    distances = {}
    for component in model['models']:
        key = id(component['transformer'])
        if key not in distances:
            matrix = transform(component['transformer'], features[:, component['columns']]) * component['weights']
            matrix = np.ascontiguousarray(matrix)
            reference = component['train']
            squared = np.sum(matrix ** 2, axis=1)[:, None] + np.sum(reference ** 2, axis=1)[None, :] - 2 * (matrix @ reference.T)
            distances[key] = np.sqrt(np.maximum(squared, 0))
        distance = distances[key] * (np.sqrt(5) / component['scale'])
        kernel = (1 + distance + distance ** 2 / 3) * np.exp(-distance)
        predictions += np.clip(kernel @ component['solution'] + .7, 0, 1)
    return predictions / len(model['models'])


def predict_chunk(bundle, cases):
    variants = {component['model']['variant'] for component in bundle}
    matrices = assemble(cases, variants)
    prediction = np.zeros(len(cases))
    normalized = {}
    for component in bundle:
        model = component['model']
        features = matrices[model['variant']]
        if component['kind'] == 'neural':
            key = id(model['transformer'])
            if key not in normalized:
                normalized[key] = transform(model['transformer'], features).astype(np.float32)
            values = neural_predict(model, features, normalized[key])
        else:
            values = kernel_predict(model, features)
        prediction += component['weight'] * values
    return np.clip(prediction, 0, 1)


def predict_worker(cases):
    return predict_chunk(BUNDLE, cases)


def main():
    global BUNDLE
    with gzip.open(Path(__file__).with_name('model.pkl.gz'), 'rb') as stream:
        BUNDLE = pickle.load(stream)
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    warm_case = {'L': 14, 'fields': np.linspace(-2., 2., 14).tolist()}
    futures = [executor.submit(predict_worker, [warm_case]) for repeat in range(4)]
    for future in futures:
        future.result()
    print('READY', flush=True)
    payload = json.loads(sys.stdin.readline())
    cases = payload['cases']
    if cases:
        chunk_size = (len(cases) + 3) // 4
        batches = [cases[start:start + chunk_size] for start in range(0, len(cases), chunk_size)]
        futures = [executor.submit(predict_worker, batch) for batch in batches]
        predictions = np.concatenate([future.result() for future in futures])
    else:
        predictions = []
    executor.shutdown(wait=True)
    result = {'predictions': [{'id': case['id'], 'f': float(value)} for case, value in zip(cases, predictions)]}
    print(json.dumps(result, allow_nan=False, separators=(',', ':')), flush=True)
    os._exit(0)


if __name__ == '__main__':
    main()
