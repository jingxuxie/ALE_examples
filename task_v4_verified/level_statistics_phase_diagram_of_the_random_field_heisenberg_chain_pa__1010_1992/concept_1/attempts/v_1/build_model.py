import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'

from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from pathlib import Path
import pickle
import time

import numpy as np
from sklearn.base import clone

from descriptors import feature_matrix
from generate_checks import initialize, label
from generators import sample_cases
from test_submission import score


if __name__ == '__main__':
    started = time.perf_counter()
    path = Path('additional_train.jsonl')
    if not path.exists():
        cases = sample_cases(800, np.random.default_rng(29475631))
        with ProcessPoolExecutor(4, initializer=initialize) as executor, path.open('w') as stream:
            for index, record in enumerate(executor.map(label, cases, chunksize=1)):
                stream.write(json.dumps(record) + '\n')
                if (index + 1) % 400 == 0:
                    stream.flush()
                    print('generated', index + 1, time.perf_counter() - started, flush=True)
    records = [json.loads(line) for filename in ('../../participant/input/train.jsonl', str(path))
               for line in Path(filename).read_text().splitlines()]
    assert len(records) == 8000
    with gzip.open('baseline.pkl.gz', 'rb') as stream:
        original = pickle.load(stream)
    model = clone(original)
    model.set_params(n_estimators=200, n_jobs=4, random_state=917324)
    print('fit', len(records), model.get_params(), flush=True)
    features = feature_matrix(records)
    targets = np.array([record['f'] for record in records])
    model.fit(features, targets)
    model.n_jobs = 1
    print('fitted', time.perf_counter() - started, flush=True)
    reports = {}
    for name, filename in (('validation', '../../participant/input/validation.jsonl'),
                           ('independent_1', 'independent_1.jsonl'),
                           ('independent_2', 'independent_2.jsonl')):
        heldout = [json.loads(line) for line in Path(filename).read_text().splitlines()]
        predictions = model.predict(feature_matrix(heldout))
        result = {'predictions': [{'id': record['id'], 'f': float(estimate)}
                                  for record, estimate in zip(heldout, predictions)]}
        reports[name] = score(heldout, result)
        print(name, reports[name], flush=True)
    with gzip.open('trained.pkl.gz', 'wb', compresslevel=3) as stream:
        pickle.dump(model, stream, protocol=4)
    Path('training_report.json').write_text(json.dumps({'training_records': len(records),
                                                      'elapsed_seconds': time.perf_counter() - started,
                                                      'surrogate_only': reports}, indent=2) + '\n')
    print('saved', time.perf_counter() - started, flush=True)
