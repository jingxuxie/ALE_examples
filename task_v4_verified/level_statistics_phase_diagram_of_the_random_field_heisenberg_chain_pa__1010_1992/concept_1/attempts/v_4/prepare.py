import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import json
from pathlib import Path
import time
import numpy as np
from data_io import load_data
from features import feature_matrix
from structure import structure_features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quantum', action='store_true')
    args = parser.parse_args()
    training, auxiliary, validation, simulated = load_data()
    cases = training + auxiliary + validation + simulated
    started = time.monotonic()
    arrays = {'features': feature_matrix(cases), 'structure': structure_features(cases)}
    if args.quantum:
        from quantum import quantum_features
        arrays['quantum'] = quantum_features(cases)
    np.savez('dataset.npz', **arrays)
    Path('dataset.json').write_text(json.dumps(cases))
    print(len(cases), {key: value.shape for key, value in arrays.items()}, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
