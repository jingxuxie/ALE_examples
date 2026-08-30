import ctypes
from pathlib import Path

import numpy as np

from fast_infer import FastLikelihood


LIBRARY = ctypes.CDLL(str(Path(__file__).resolve().parent / 'strip.so'))
DOUBLE_POINTER = ctypes.POINTER(ctypes.c_double)
LIBRARY.strip_partition.argtypes = [DOUBLE_POINTER, DOUBLE_POINTER, ctypes.c_double, DOUBLE_POINTER, DOUBLE_POINTER]
LIBRARY.strip_partition.restype = ctypes.c_double


def pointer(array):
    return None if array is None else array.ctypes.data_as(DOUBLE_POINTER)


class NativeLikelihood(FastLikelihood):
    def partition(self, values, beta, moments=True):
        gradient = np.empty(268) if moments else None
        value = LIBRARY.strip_partition(pointer(values), pointer(self.signs), beta, pointer(gradient), None)
        return (value, gradient) if moments else value

    def marginals(self, values, beta):
        marginals = np.empty((12, 256))
        LIBRARY.strip_partition(pointer(values), pointer(self.signs), beta, None, pointer(marginals))
        return marginals

    def predict(self, values, queries):
        states = self.states
        by_beta = {beta: self.marginals(values, beta) for beta in set(query['beta'] for query in queries)}
        predictions = []
        for query in queries:
            readout = np.asarray(query['readout'])
            codes = ((states[:, readout % 8].astype(np.int64) + 1) // 2) @ (1 << np.arange(6))
            marginal = by_beta[query['beta']][readout[0] // 8].copy()
            for site, value in zip(query['field_indices'], query['field_values']):
                marginal *= np.exp(query['beta'] * value * states[:, site % 8])
            marginal /= marginal.sum()
            predictions.append(np.bincount(codes, weights=marginal, minlength=64))
        return np.asarray(predictions)


if __name__ == '__main__':
    import json
    import time
    from infer import ASSETS, Likelihood, load_data, prediction
    configurations, betas, spec = load_data()
    likelihood = Likelihood(configurations, betas, spec)
    native = NativeLikelihood(likelihood)
    fast = FastLikelihood(likelihood)
    values = np.load('fit.npz')['theta']
    for beta in [0.65, 1.0, 1.3]:
        value, gradient = native.partition(values, beta)
        reference_value, reference_gradient = fast.partition(values, beta)
        print('native errors', beta, value - reference_value, np.max(np.abs(gradient - reference_gradient)))
        assert abs(value - reference_value) < 1e-10
        assert np.max(np.abs(gradient - reference_gradient)) < 1e-10
    queries = json.loads((ASSETS / 'input/queries.json').read_text())
    assert np.max(np.abs(native.predict(values, queries) - prediction(values, spec, queries))) < 1e-12
    start = time.monotonic()
    for iteration in range(100):
        native.evaluate(values)
    print('evaluation seconds', (time.monotonic() - start) / 100)
