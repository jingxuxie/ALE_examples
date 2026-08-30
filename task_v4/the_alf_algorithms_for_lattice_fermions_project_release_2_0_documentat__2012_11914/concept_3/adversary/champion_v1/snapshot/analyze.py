import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import sys
import numpy as np
sys.path.insert(0, '../../participant/input')
from scoring import score_prediction
from physics import observables, wasserstein

prefix = sys.argv[2] if len(sys.argv) > 2 else '../../participant/input/validation'
data = dict(np.load(prefix + '_input.npz'))
labels = dict(np.load(prefix + '_labels.npz'))
debug = dict(np.load(sys.argv[1] + '.debug.npz'))
family = labels['family_id']
truth = labels['spectral_mass']


def report(mass, quantiles=None, name=''):
    if quantiles is None:
        low = mass[:, 120:136].sum(axis=1)
        quantiles = np.clip(low[:, None] + np.array([-.006, 0, .006]), 0, 1)
    prediction = dict(sample_id=data['sample_id'], spectral_mass=mass, low_mass_quantiles=quantiles)
    score = score_prediction(prediction, data, labels)
    print(name, round(score['core_score'], 3), {key: round(value, 3) for key, value in score['family_scores'].items()}, flush=True)
    return score


if __name__ == '__main__':
    report(dict(np.load(sys.argv[1]))['spectral_mass'], name='current_fixedquantiles')
    selected = np.argmin(debug['score'], axis=1)
    for label in range(6):
        print('family', label, 'chosen', np.bincount(selected[family == label], minlength=8), 'mean_chi', np.round(np.median(debug['chi'][family == label], axis=0), 1), 'mean_score', np.round(np.median(debug['score'][family == label], axis=0), 1))
    oracle = np.empty_like(truth)
    for row in range(len(family)):
        options = [[0], [1], [2], [3, 4], [5, 6], [7]][family[row]]
        winner = options[np.argmin(debug['chi'][row, options])]
        oracle[row] = debug['mass'][row, winner]
    report(oracle, name='oracle_family')
    for penalty in [0, 10, 20, 30, 40, 50, 60]:
        scores = debug['score'].copy()
        scores[:, 7] += penalty
        weights = np.exp(-.5 * (scores - scores.min(axis=1)[:, None]))
        weights /= weights.sum(axis=1)[:, None]
        mass = (weights[:, :, None] * debug['mass']).sum(axis=1)
        report(mass, name='penalty' + str(penalty))
    for model in range(8):
        report(debug['mass'][:, model], name='model' + str(model))
    dimensions = np.array([7, 8, 7, 10, 10, 7, 7, 0])
    for extra in [20, 40, 60, 80]:
        scores = debug['chi'] + dimensions * 2
        scores[:, 7] += extra
        weights = np.exp(-.5 * (scores - scores.min(axis=1)[:, None]))
        weights /= weights.sum(axis=1)[:, None]
        report((weights[:, :, None] * debug['mass']).sum(axis=1), name='fixedextra' + str(extra))
