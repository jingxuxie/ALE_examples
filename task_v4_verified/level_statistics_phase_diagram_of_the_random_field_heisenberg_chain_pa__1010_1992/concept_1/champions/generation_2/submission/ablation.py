import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
import numpy as np
from experiment import read, ROOT
from smooth_models import neural_trials

arrays = np.load('public_features.npz')
training = read(ROOT / 'train.jsonl') + read(ROOT / 'auxiliary_train_L10_L12.jsonl') + read(ROOT / 'auxiliary_validation_L10_L12.jsonl')
validation = read(ROOT / 'validation.jsonl')
target = np.array([case['f'] for case in training])
subsets = {
    'base': np.arange(250),
    'cluster': np.r_[np.arange(304), np.arange(393, 417)],
    'compact': np.r_[np.arange(250), np.arange(317, 330), np.arange(343, 356), np.arange(393, 417)],
    'hybrid': np.r_[np.arange(304), np.arange(317, 330), np.arange(343, 356), np.arange(393, 417)],
}
for name, indices in subsets.items():
    print('CONFIGURATION', name, len(indices), flush=True)
    neural_trials(arrays['train'][:, indices], arrays['test'][:, indices], target, validation, prefix='ablation_' + name, epochs=800, seeds=2)
