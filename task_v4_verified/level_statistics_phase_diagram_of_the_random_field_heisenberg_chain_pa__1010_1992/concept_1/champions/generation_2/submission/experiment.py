import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
import json
import time
import pickle
from pathlib import Path
import numpy as np
from sklearn.experimental import enable_hist_gradient_boosting
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.kernel_ridge import KernelRidge
from features import feature_matrix

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/level_statistics_phase_diagram_of_the_random_field_heisenberg_chain_pa__1010_1992/concept_1/generations/generation_2/participant/input')


def read(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def report(cases, predictions, label):
    truth = np.array([case['f'] for case in cases])
    error = (np.clip(predictions, 0, 1) - truth)**2
    groups = {family: float(np.sqrt(error[[case['family'] == family for case in cases]].mean()))
              for family in sorted({case['family'] for case in cases})}
    print(label, round(float(np.sqrt(error.mean())), 6), groups, flush=True)
    return float(np.sqrt(error.mean()))


if __name__ == '__main__':
    training = read(ROOT / 'train.jsonl') + read(ROOT / 'auxiliary_train_L10_L12.jsonl') + read(ROOT / 'auxiliary_validation_L10_L12.jsonl')
    validation = read(ROOT / 'validation.jsonl')
    cache = Path('public_features.npz')
    started = time.monotonic()
    if cache.exists():
        arrays = np.load(cache)
        features, test = arrays['train'], arrays['test']
    else:
        features = feature_matrix(training)
        test = feature_matrix(validation)
        np.savez(cache, train=features, test=test)
    print('features', features.shape, time.monotonic() - started, flush=True)
    target = np.array([case['f'] for case in training])
    predictions = {}
    for selection, columns in [('base', slice(0, 250)), ('transport', slice(0, 304)), ('particle', slice(0, 369)), ('all', slice(None))]:
        for leaf in (1, 3):
            model = ExtraTreesRegressor(n_estimators=300, max_features=.85, min_samples_leaf=leaf, n_jobs=4, random_state=10101992)
            started = time.monotonic()
            model.fit(features[:, columns], target)
            prediction = model.predict(test[:, columns])
            label = f'ET_{selection}_{leaf}'
            predictions[label] = prediction
            report(validation, prediction, label)
            print('seconds', time.monotonic() - started, flush=True)
            if selection == 'all' and leaf == 1:
                with open('trial_model.pkl', 'wb') as stream:
                    pickle.dump(model, stream)
                np.save('feature_importance.npy', model.feature_importances_)
    for leaves in (7, 15, 25):
        for regularization in (1., 10.):
            model = HistGradientBoostingRegressor(max_iter=450, learning_rate=.045, max_leaf_nodes=leaves, l2_regularization=regularization, min_samples_leaf=15, early_stopping=False)
            model.fit(features, target)
            prediction = model.predict(test)
            label = f'HGB_{leaves}_{regularization}'
            predictions[label] = prediction
            report(validation, prediction, label)
    np.savez('trial_predictions.npz', **predictions)
