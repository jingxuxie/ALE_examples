import numpy as np
import itertools
from scipy.special import expit
from model import whiten


def align_sheets(reference, candidate):
    permutations = np.array(list(itertools.permutations(range(3))))
    scales = np.array([.008] * 7 + [.010, .012, .012, .012, .010, .008, .006])
    choices = candidate[:, permutations]
    costs = np.sum(((choices - reference[:, None]) / scales) ** 2, axis=(2, 3))
    return choices[np.arange(len(reference)), np.argmin(costs, axis=1)]


def predict_network(observed, sigma, path):
    with np.load(path, allow_pickle=False) as archive:
        values = (whiten(observed, archive['sigma']) @ archive['basis']).reshape(len(observed), -1)
        amplitude = sigma[:, 0, 0, 0] / archive['sigma'][0, 0, 0]
        values = np.concatenate([(values - archive['center']) @ archive['projection'], np.log(amplitude / .0012)[:, None]], axis=1).astype(np.float32)
        layer = 0
        while 'weight' + str(layer) in archive.files:
            values = values @ archive['weight' + str(layer)].T + archive['bias' + str(layer)]
            if 'weight' + str(layer + 1) in archive.files:
                values *= expit(values)
            layer += 1
        prediction = (values * archive['scales'] + archive['target_center']).reshape(-1, 3, 14)
    prediction = np.maximum(prediction, 0)
    totals = prediction.sum(axis=2, keepdims=True)
    prediction = np.where(totals > 0, prediction / np.maximum(totals, 1e-300), 1 / 14)
    return prediction
