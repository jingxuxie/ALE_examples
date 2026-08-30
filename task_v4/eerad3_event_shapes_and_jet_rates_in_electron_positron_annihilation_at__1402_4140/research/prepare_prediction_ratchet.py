import json
import shutil
from pathlib import Path

import numpy as np

from build_prediction import CONCEPT, generate_split, native_values


def main():
    baseline = CONCEPT / 'adversary/ratchet_champion_baseline'
    baseline.mkdir(parents=True, exist_ok=True)
    for name in ['predict.py', 'kernel.cpp']:
        shutil.copyfile(CONCEPT / 'champions/generation_1' / name, baseline / name)
    shutil.copyfile(CONCEPT / 'adversary/optimized/champion_fast.so', baseline / 'kernel.so')
    (baseline / 'BUILD.txt').write_text('g++ -std=c++17 -O3 -ffast-math -march=native -fPIC -shared kernel.cpp -o kernel.so\n')
    private = CONCEPT / 'adversary/native_fast_submission'
    private.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONCEPT / 'adversary/native_predict.py', private / 'predict.py')
    shutil.copyfile(CONCEPT / 'adversary/optimized/native_fast.so', private / 'kernel16.so')
    data, rejected = generate_split(np.random.default_rng(452709332), 40000, CONCEPT / 'adversary/native')
    np.savez_compressed(CONCEPT / 'evaluator/hidden/test.npz', **data)
    approximation = native_values(data['s'], CONCEPT / 'adversary/native', 8)
    difference = np.log(approximation) - data['log_weight']
    provenance = {'generation': 2, 'cases': len(data['s']), 'per_family': 40000,
                  'independent_seed': 452709332, 'rejected': rejected,
                  'labels': 'all labels evaluated by quadruple-precision native source',
                  'native_double_log_rmse': float(np.sqrt(np.mean(difference ** 2))),
                  'native_double_max_abs_log_error': float(np.max(np.abs(difference))),
                  'target_cpu_seconds_per_million': 12.0,
                  'target_fixed_before_launch': True}
    (CONCEPT / 'adversary/generation_2_data_provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
