import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
import copy
import json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent
if not (ROOT / 'solution.py').is_file():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
import solution
sys.path.insert(0, os.environ['P'] + '/input')
from moments import MomentModel

episodes = json.load(open(os.environ['P'] + '/input/training.json'))['episodes']
rng = np.random.default_rng(913)

def walsh(values):
    output = values.copy()
    width = 1
    while width < output.shape[-1]:
        blocks = output.reshape(output.shape[:-1] + (-1, 2 * width))
        first = blocks[..., :width].copy()
        second = blocks[..., width:].copy()
        blocks[..., :width] = first + second
        blocks[..., width:] = first - second
        width *= 2
    return output

for episode in (0, 2, 5):
    spec = copy.deepcopy(episodes[episode]['spec'])
    spec['actions'] = [spec['actions'][action] for action in (0, 3, 10, 15)]
    model = solution.Model(spec)
    rates = np.array(episodes[episode]['rates'])
    size = 4096
    masks = np.ascontiguousarray(model.all_masks & (size - 1))
    probability = np.zeros((model.actions, size))
    jacobian = np.zeros((model.actions, model.channels, size))
    solution.LIB.distribution(size, model.channels, model.actions, masks, model.exposures,
                              model.weights, model.alternate, rates, probability, jacobian)
    assert np.max(np.abs(probability.sum(axis=1) - 1)) < 1e-12
    selected = rng.choice(size, 100, replace=False)
    original_parities = np.zeros(len(selected), dtype=np.int64)
    for detector in range(model.dimension):
        original_parities |= np.array([(int(code) & int(model.mapping[1 << detector])).bit_count() % 2
                                       for code in selected]) << detector
    exact, derivative = MomentModel(spec, original_parities).predict(np.log(rates), True)
    assert np.max(np.abs(walsh(probability)[:, selected] - exact)) < 2e-12
    assert np.max(np.abs(walsh(jacobian)[:, :, selected] - derivative)) < 2e-12
    counts = np.array([rng.multinomial(1500, row / row.sum()) for row in probability], dtype=float)
    gradient = np.zeros(model.channels)
    value = solution.LIB.evaluate(size, model.channels, model.actions, masks, model.exposures,
                                  model.weights, model.alternate, rates, counts, gradient)
    exact_gradient = -np.einsum('as,aks->k', counts / probability, jacobian)
    assert np.max(np.abs(gradient - exact_gradient)) < 1e-7
    for channel in rng.choice(model.channels, 8, replace=False):
        shifted = rates.copy()
        shifted[channel] *= np.exp(1e-5)
        unused = np.zeros(model.channels)
        plus = solution.LIB.evaluate(size, model.channels, model.actions, masks, model.exposures,
                                     model.weights, model.alternate, shifted, counts, unused)
        shifted[channel] *= np.exp(-2e-5)
        minus = solution.LIB.evaluate(size, model.channels, model.actions, masks, model.exposures,
                                      model.weights, model.alternate, shifted, counts, unused)
        assert abs((plus - minus) / 2e-5 - gradient[channel]) < 0.003
    print('kernel checks passed', episode)
