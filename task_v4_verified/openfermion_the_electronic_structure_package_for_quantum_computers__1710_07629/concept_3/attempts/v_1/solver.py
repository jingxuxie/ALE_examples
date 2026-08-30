import json
import os
from pathlib import Path
import sys

for variable in (
    'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
    'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS',
):
    os.environ[variable] = '1'
sys.dont_write_bytecode = True

import numpy as np

from physics import predict


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: solver.py REQUEST_JSON PREDICTIONS_JSON')
    request = json.loads(Path(sys.argv[1]).read_text())
    if request['schema_version'] != 1:
        raise ValueError('unsupported schema version')
    if request['target_order'] != ['charge_gap', 'spin_gap']:
        raise ValueError('unsupported target order')
    with np.load(request['inputs'], allow_pickle=False) as archive:
        inputs = {key: archive[key] for key in (
            'hopping', 'interaction', 'potential', 'n_sites', 'family',
        )}
    if len(inputs['n_sites']) != request['n_instances']:
        raise ValueError('input row count differs from request')
    predictions = predict(inputs)
    Path(sys.argv[2]).write_text(json.dumps(
        {'schema_version': 1, 'predictions': predictions},
        allow_nan=False, separators=(',', ':'),
    ) + '\n')


if __name__ == '__main__':
    main()
