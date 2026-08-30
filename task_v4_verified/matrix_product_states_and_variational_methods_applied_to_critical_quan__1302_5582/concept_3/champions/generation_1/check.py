import os

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import argparse
import json
import time
from pathlib import Path

import numpy as np
from solver import solve


TARGETS = ('odd_gap', 'even_gap', 'odd_spacing')
ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/matrix_product_states_and_variational_methods_applied_to_critical_quan__1302_5582/concept_3/participant')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=12)
    parser.add_argument('--split', default='validation')
    args = parser.parse_args()
    if args.split == 'train':
        cases = json.loads((ROOT / 'input/train.json').read_text())['cases']
        labels = {case['id']: case['targets'] for case in cases}
    else:
        cases = json.loads((ROOT / 'input/validation_inputs.json').read_text())['cases']
        labels = {case['id']: case['targets'] for case in json.loads((ROOT / 'input/validation_labels.json').read_text())['predictions']}
    errors = []
    records = []
    start = time.process_time()
    for case in cases:
        scale = (case['lambda'] / 6) ** (1 / 3)
        gaps = scale * solve(case['mu2'] / scale**2, case['kappa'] / scale**2, case['sites'], args.count)
        truth = np.array([labels[case['id']][target] for target in TARGETS])
        error = np.abs(np.log(np.maximum(gaps, 1e-20) / truth))
        errors.append(error)
        records.append({'id': case['id'], 'family': case['family'], 'gaps': gaps.tolist(), 'errors': error.tolist()})
        if np.max(error) > .001:
            print('ERROR', case['family'], case['mu2'] / scale**2, case['kappa'] / scale**2, gaps, error, flush=True)
    elapsed = time.process_time() - start
    errors = np.array(errors)
    print('TIME', elapsed, 'MEAN', errors.mean(), 'P95', np.quantile(errors, .95), 'MAX', errors.max(), flush=True)
    for family in sorted(set(case['family'] for case in cases)):
        selected = errors[[case['family'] == family for case in cases]]
        print(family, selected.mean(), selected.max(), flush=True)
    Path(f'check_{args.split}_{args.count}.json').write_text(json.dumps({'cpu_seconds': elapsed, 'records': records}))


if __name__ == '__main__':
    main()
