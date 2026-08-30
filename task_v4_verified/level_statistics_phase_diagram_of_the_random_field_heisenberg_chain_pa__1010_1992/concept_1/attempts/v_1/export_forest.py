import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'

import gzip
import json
from pathlib import Path
import pickle
import subprocess
import tempfile

import numpy as np

from descriptors import feature_matrix


if __name__ == '__main__':
    directory = Path(__file__).resolve().parent
    with gzip.open(directory / 'trained.pkl.gz', 'rb') as stream:
        model = pickle.load(stream)
    roots, features, thresholds, right_children, values = [], [], [], [], []
    offset = 0
    for estimator in model.estimators_:
        tree = estimator.tree_
        internal = tree.children_left >= 0
        assert np.all(tree.children_left[internal] == np.flatnonzero(internal) + 1)
        roots.append(offset)
        features.append(tree.feature.astype(np.int16))
        thresholds.append(tree.threshold)
        right_children.append(np.where(internal, tree.children_right + offset, -1).astype(np.int32))
        leaf_values = tree.value[:, 0, 0].astype(np.float32)
        leaf_values[internal] = 0
        values.append(leaf_values)
        offset += tree.node_count
    assert offset < 2**31
    np.savez_compressed(directory / 'forest.npz', roots=np.asarray(roots, dtype=np.int32),
                        features=np.concatenate(features), thresholds=np.concatenate(thresholds),
                        right_children=np.concatenate(right_children), values=np.concatenate(values))
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        environment = dict(os.environ, TMPDIR=temporary)
        subprocess.run(['cc', '-O3', '-std=c99', '-shared', '-fPIC', str(directory / 'forest.c'),
                        '-o', str(directory / 'forest.so'), '-lm'], check=True, env=environment)
    from native_forest import Forest
    compact = Forest()
    records = [json.loads(line) for line in Path('../../participant/input/validation.jsonl').read_text().splitlines()]
    matrix = np.asarray(feature_matrix(records), dtype=np.float32)
    trees = np.array([tree.predict(matrix, check_input=False) for tree in model.estimators_])
    means, deviations = compact.predict(matrix)
    metrics = {'nodes': offset, 'trees': len(roots),
               'maximum_prediction_difference': float(np.max(np.abs(means - trees.mean(axis=0)))),
               'maximum_uncertainty_difference': float(np.max(np.abs(deviations - trees.std(axis=0))))}
    assert metrics['maximum_prediction_difference'] < 1e-7
    assert metrics['maximum_uncertainty_difference'] < 1e-7
    Path('export_report.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(json.dumps(metrics), flush=True)
