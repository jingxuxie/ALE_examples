import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import json
from pathlib import Path
import numpy as np
import solution
import sys
sys.path.insert(0, str(Path(os.environ['PART']) / 'input'))
from moments import MomentModel
if '--portable' in sys.argv:
    import ctypes
    portable = ctypes.CDLL(str(Path(solution.__file__).parent / 'kernel.so'))
    for name in ('evaluate', 'distribution', 'joint_evaluate'):
        getattr(portable, name).argtypes = getattr(solution.LIB, name).argtypes
        getattr(portable, name).restype = getattr(solution.LIB, name).restype
    solution.LIB = portable

spec = json.loads((Path(os.environ['PART']) / 'input/training.json').read_text())['episodes'][5]['spec']
channels = len(spec['channels'])
actions = [3, 7, 17]
exposures = np.array([spec['actions'][action]['exposures'] for action in actions])
weights = np.array([spec['actions'][action]['mode_weights'] for action in actions])
alternate = np.array([spec['actions'][action]['alternate_probability'] for action in actions])
original = np.array([channel['masks'] for channel in spec['channels']], dtype=np.int64)
bounds = np.log([channel['rate_bounds'] for channel in spec['channels']])
point = bounds.mean(axis=1)
rng = np.random.default_rng(912)
masks = np.ascontiguousarray(original & 1023, dtype=np.int32)
probabilities = np.zeros((3, 1024))
jacobian = np.zeros((3, channels, 1024))
solution.LIB.distribution(1024, channels, 3, masks, exposures, weights, alternate, np.exp(point), probabilities, jacobian)
selected_spec = dict(spec)
selected_spec['actions'] = [spec['actions'][action] for action in actions]
moment_model = MomentModel(selected_spec, np.arange(1024, dtype=np.int64))
expected_moments, expected_derivatives = moment_model.predict(point, gradient=True)

def walsh(values):
    result = values.copy()
    width = 1
    while width < result.shape[-1]:
        chunks = result.reshape(result.shape[:-1] + (-1, 2, width))
        first = chunks[..., 0, :].copy()
        second = chunks[..., 1, :].copy()
        chunks[..., 0, :] = first + second
        chunks[..., 1, :] = first - second
        width *= 2
    return result

assert np.max(abs(walsh(probabilities) - expected_moments)) < 1e-11
assert np.max(abs(walsh(jacobian) - expected_derivatives)) < 1e-11
print('Exact public parity law agrees with native probabilities and derivatives')
counts = np.stack([rng.multinomial(5000, probability / probability.sum()) for probability in probabilities]).astype(float)
gradient = np.zeros(channels)
expected = solution.LIB.evaluate(1024, channels, 3, masks, exposures, weights, alternate, np.exp(point), counts, gradient)
widths = [3, 6, 3, 9, 6, 10, 9]
sizes = np.array([1 << width for width in widths], dtype=np.int32)
signs = np.array([1, 1, -1, 1, -1, 1, -1], dtype=float)
block_masks = np.stack([masks & (size - 1) for size in sizes])
offsets = np.arange(4, dtype=np.int32) * 1024
projections = np.stack([np.tile(np.arange(1024, dtype=np.int32) & (size - 1), 3) for size in sizes])

def evaluate(candidate):
    actual_gradient = np.zeros(channels)
    actual = solution.LIB.joint_evaluate(channels, 3, 7, 3072, sizes, block_masks, offsets, projections,
                                        signs, exposures, weights, alternate, np.exp(candidate), counts.ravel(), actual_gradient)
    return actual, actual_gradient

actual, actual_gradient = evaluate(point)
print('exact value', actual - expected, 'exact gradient', np.max(abs(actual_gradient - gradient)))
assert abs(actual - expected) < 1e-4
assert np.max(abs(actual_gradient - gradient)) < 1e-4
for channel in np.argsort(abs(gradient))[-5:]:
    step = np.zeros(channels)
    step[channel] = 1e-5
    numeric = (evaluate(point + step)[0] - evaluate(point - step)[0]) / 2e-5
    print('finite difference', channel, numeric, actual_gradient[channel])
    assert abs(numeric - actual_gradient[channel]) < 0.003
print('OK')
