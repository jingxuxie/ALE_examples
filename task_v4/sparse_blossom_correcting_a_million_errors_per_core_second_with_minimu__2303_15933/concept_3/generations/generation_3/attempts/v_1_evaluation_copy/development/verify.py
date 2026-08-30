import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import sys
sys.dont_write_bytecode = True
import numpy as np
import solution
from solution import LIB, contiguous

rng = np.random.default_rng(91472)
channels, actions, size = 14, 3, 256
masks = rng.integers(1, 16, (channels, 2), dtype=np.int32)
masks[channels // 2:] <<= 4
exposures = contiguous(rng.uniform(0.1, 8, (actions, 2, channels)))
weights = contiguous([[1, 0], [0.8, 0.2], [0.35, 0.65]])
alternate = contiguous(rng.uniform(0.05, 0.8, (actions, channels)))
rates = contiguous(rng.uniform(0.003, 0.08, channels))
counts = contiguous(rng.integers(0, 8, (actions, size)))
gradient = np.zeros(channels)
full_value = LIB.evaluate(size, channels, actions, masks, exposures, weights, alternate, rates, counts, gradient)
remote_counts = contiguous(counts.reshape(actions, 16, 16).sum(axis=2))
remote_masks = contiguous(masks >> 4, np.int32)
remote_gradient = np.zeros(channels)
remote_value = LIB.evaluate(16, channels, actions, remote_masks, exposures, weights, alternate, rates, remote_counts, remote_gradient)
split_masks = contiguous(np.concatenate((masks & 15, remote_masks), axis=1), np.int32)
observations = contiguous(np.tile(np.stack((np.arange(size) & 15, np.arange(size) >> 4), axis=1), (actions, 1)), np.int32)
offsets = contiguous(np.arange(actions+1)*size, np.int32)
conditional_gradient = np.zeros(channels)
conditional_value = LIB.conditional(16, 16, channels, actions, split_masks, offsets, observations,
                                    exposures, weights, alternate, rates, counts.ravel(), conditional_gradient)
assert abs(conditional_value-(full_value-remote_value)) < 1e-7
assert np.max(np.abs(conditional_gradient-(gradient-remote_gradient))) < 1e-7
probabilities = np.zeros((actions, size))
jacobian = np.zeros((actions, channels, size))
LIB.distribution(size, channels, actions, masks, exposures, weights, alternate, rates, probabilities, jacobian)
assert np.allclose(probabilities.sum(axis=1), 1, atol=1e-12)
assert np.min(probabilities) > 0
sys.path.insert(0, os.environ['P'] + '/input')
from moments import MomentModel, parity
spec = {'channels': [{'masks': pair.tolist(), 'rate_bounds': [0.001, 0.1]} for pair in masks],
        'actions': [{'exposures': exposures[action].tolist(), 'mode_weights': weights[action].tolist(),
                     'alternate_probability': alternate[action].tolist()} for action in range(actions)]}
characters = 1 - 2*parity(np.arange(size)[:, None] & np.arange(size)[None])
expected, derivative = MomentModel(spec, np.arange(size)).predict(np.log(rates), gradient=True)
assert np.max(np.abs(probabilities @ characters-expected)) < 1e-11
assert np.max(np.abs(jacobian @ characters-derivative)) < 1e-11
for channel in [0, 5, 8, 13]:
    upper = rates.copy()
    lower = rates.copy()
    upper[channel] *= np.exp(1e-5)
    lower[channel] *= np.exp(-1e-5)
    temporary = np.zeros(channels)
    first = LIB.evaluate(size, channels, actions, masks, exposures, weights, alternate, upper, counts, temporary)
    second = LIB.evaluate(size, channels, actions, masks, exposures, weights, alternate, lower, counts, temporary)
    assert abs((first-second)/2e-5-gradient[channel]) < 1e-4
print('Exact moments, conditional probabilities, gradients, and normalization: PASS')
