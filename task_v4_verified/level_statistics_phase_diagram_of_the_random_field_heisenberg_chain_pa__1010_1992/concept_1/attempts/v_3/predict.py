import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[variable] = '1'
import json
import sys
from pathlib import Path
import numpy as np
from runtime_features import feature_matrix


def sigmoid(values):
    return 1.0 / (1.0 + np.exp(-np.clip(values, -60, 60)))


def load_model(path=None):
    asset = np.load(path or Path(__file__).with_name('model.npz'))
    return {key: asset[key] for key in asset.files}


def estimate(features, model):
    transformed = np.sign(features) * np.log1p(np.abs(features))
    predictions = []
    for index in range(int(model['count'])):
        prefix = str(index) + '_'
        hidden = np.clip((transformed - model[prefix + 'mean']) / model[prefix + 'scale'], -10, 10).astype(np.float32)
        for layer in (0, 3):
            hidden = hidden @ model[prefix + str(layer) + '.weight'].T + model[prefix + str(layer) + '.bias']
            hidden = hidden * sigmoid(hidden)
        output = hidden @ model[prefix + '6.weight'].T + model[prefix + '6.bias']
        predictions.append(sigmoid(output).ravel())
    return np.clip(np.mean(predictions, axis=0), 0, 1)


def predict_cases(cases, model):
    if not cases:
        return {'predictions': []}
    features = feature_matrix(cases)
    predictions = estimate(features, model)
    return {'predictions': [{'id': case['id'], 'f': float(value)} for case, value in zip(cases, predictions)]}


def main():
    model = load_model()
    warm = [{'L': 14, 'fields': np.linspace(-1, 1, 14).tolist()}]
    estimate(feature_matrix(warm), model)
    print('READY', flush=True)
    request = json.loads(sys.stdin.readline())
    result = predict_cases(request['cases'], model)
    print(json.dumps(result, allow_nan=False, separators=(',', ':')), flush=True)
    os._exit(0)


if __name__ == '__main__':
    main()
