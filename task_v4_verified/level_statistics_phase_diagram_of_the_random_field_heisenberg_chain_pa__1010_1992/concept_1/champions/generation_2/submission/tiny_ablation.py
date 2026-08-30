import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
from pathlib import Path
import numpy as np
from experiment import read, ROOT
from features import feature_matrix
from smooth_models import neural_trials

training = read(ROOT / 'train.jsonl') + read(ROOT / 'auxiliary_train_L10_L12.jsonl') + read(ROOT / 'auxiliary_validation_L10_L12.jsonl')
validation = read(ROOT / 'validation.jsonl')
target = np.array([case['f'] for case in training])
path = Path('tiny_features.npz')
if path.exists():
    arrays = np.load(path)
    features, test = arrays['train'], arrays['test']
else:
    features, test = feature_matrix(training, kind='tiny'), feature_matrix(validation, kind='tiny')
    np.savez(path, train=features, test=test)
neural_trials(features, test, target, validation, prefix='ablation_tiny', epochs=800, seeds=3)
