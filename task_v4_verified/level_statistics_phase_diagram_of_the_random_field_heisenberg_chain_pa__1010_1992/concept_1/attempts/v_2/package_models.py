import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
import gzip
import json
from pathlib import Path
import pickle
import numpy as np
from descriptors import feature_matrix
from test_stream import metrics


def load_model(path):
    with gzip.open(path, 'rb') as stream:
        model = pickle.load(stream)
    return model


def main():
    model10 = load_model('candidate10_hist31.pkl.gz')
    model12 = load_model('candidate_hist31.pkl.gz')
    for length, model in ((10, model10), (12, model12)):
        with gzip.open(f'model{length}.pkl.gz', 'wb', compresslevel=3) as stream:
            pickle.dump(model, stream, protocol=4)
    cases = [json.loads(line) for line in Path('../../participant/input/validation.jsonl').read_text().splitlines()]
    features = feature_matrix(cases).astype(np.float32)
    estimates = np.empty(len(cases))
    for length, model in ((10, model10), (12, model12)):
        selected = [index for index, case in enumerate(cases) if case['L'] == length]
        estimates[selected] = model.predict(features[selected])
    result = metrics(cases, {'predictions': [{'id': case['id'], 'f': float(np.clip(value, 0, 1))}
                                           for case, value in zip(cases, estimates)]})
    result.update(training_records_by_length={'10': 8800, '12': 6800},
                  validation_used_for_training=False, numerical_corrections=False)
    print(json.dumps(result, indent=2))
    Path('surrogate_metrics.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
