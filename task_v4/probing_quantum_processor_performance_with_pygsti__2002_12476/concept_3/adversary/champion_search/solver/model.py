import ctypes
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parents[1] / 'participant' / 'input'
LOWER = np.array([-0.018]*15 + [-0.008, -0.008, 0.028] + [-0.030]*4 + [-0.070]*2
                 + [0.82]*2 + [-0.009, -0.009, -0.018]*2 + [0.8]
                 + [-5.8, -0.8, -1.1, -0.5]*2 + [-0.8, -1.0, -0.7]
                 + [0.0001]*5 + [0.0001]*5)
UPPER = np.array([0.018]*15 + [0.008, 0.008, 0.062] + [0.030]*4 + [0.070]*2
                 + [0.97]*2 + [0.009, 0.009, 0.018]*2 + [1.5]
                 + [-3.8, 0.8, 1.1, 0.5]*2 + [0.8, 1.0, 0.7]
                 + [0.0012]*5 + [0.0009]*5)
CENTER = (LOWER + UPPER) / 2
SCALE = (UPPER - LOWER) / 2
LIBRARY = ctypes.CDLL(str(ROOT / 'simulator.so'))
LIBRARY.evaluate.argtypes = [ctypes.c_int, ctypes.c_int] + [ctypes.c_void_p]*8 + [ctypes.c_int]
LIBRARY.evaluate.restype = None


def load(split):
    with np.load(INPUT / (split + '.npz'), allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def select(data, mask):
    return {key: np.ascontiguousarray(value[mask]) for key, value in data.items()}


def combine(*datasets):
    width = max(data['gates'].shape[1] for data in datasets)
    result = {}
    for key in datasets[0]:
        if key == 'gates':
            result[key] = np.concatenate([np.pad(data[key], ((0, 0), (0, width-data[key].shape[1])), constant_values=-1) for data in datasets])
        else:
            result[key] = np.concatenate([data[key] for data in datasets])
    return result


def predict(params, data, jacobian=False, threads=None):
    params = np.ascontiguousarray(params, dtype=np.float64)
    count = len(data['length'])
    probabilities = np.empty(count)
    derivatives = np.empty((count, 54)) if jacobian else None
    arrays = [data['gates'], data['length'], data['preparation'], data['measurement'], data['time'], params, probabilities, derivatives]
    pointers = [array.ctypes.data if array is not None else None for array in arrays]
    LIBRARY.evaluate(count, data['gates'].shape[1], *pointers, int(threads or os.environ.get('OMP_NUM_THREADS', 2)))
    return (probabilities, derivatives) if jacobian else probabilities


def deviance(probabilities, data):
    observed = data['count_one'] / data['shots']
    difference = probabilities - observed
    variance = probabilities * (1-probabilities)
    divergence = -observed*np.log1p(difference/observed) - (1-observed)*np.log1p(-difference/(1-observed))
    residual = np.sign(difference)*np.sqrt(np.maximum(2*data['shots']*divergence, 0))
    derivative = np.sqrt(data['shots']/variance)
    stable = np.abs(difference) > 1e-7
    derivative[stable] = data['shots'][stable]*difference[stable]/(variance[stable]*residual[stable])
    return residual, derivative


def report(params, data):
    probabilities = predict(params, data)
    observed = data['count_one']/data['shots']
    noise = observed*(1-observed)/(data['shots']-1)
    results = {}
    for family in np.unique(data['family']):
        mask = data['family'] == family
        mse = np.mean((probabilities[mask]-observed[mask])**2)
        results[str(family)] = {'observed_rmse': float(np.sqrt(mse)), 'noise_corrected_rmse': float(np.sqrt(max(0, mse-np.mean(noise[mask]))))}
    results['deviance_per_row'] = float(np.mean(deviance(probabilities, data)[0]**2))
    return results
