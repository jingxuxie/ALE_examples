import itertools
import json
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
from regional import LocalMixture, configurations
from optimization import FullRefinement

strength = float(sys.argv[1])
local_spins = configurations(4)
local_couplings = np.full((4, 4), -strength)
np.fill_diagonal(local_couplings, 0)
local_target = .5 * np.sum(local_spins * (local_spins @ local_couplings), axis=1) + strength * local_spins.sum(axis=1)
local_target -= logsumexp(local_target)
orders = [(rotation + direction * np.arange(4)) % 4 for rotation in range(4) for direction in [1, -1]]
fit = LocalMixture(local_target, orders)

def evaluate(parameters):
    value, gradient = fit.evaluate(np.tile(parameters, 8), regularization=.002)
    return value, gradient.reshape(8, -1).sum(axis=0)

result = minimize(evaluate, fit.initial.reshape(8, -1).mean(axis=0), jac=True, method='L-BFGS-B',
                  options={'maxiter': 3000, 'maxcor': 20, 'ftol': 1e-13, 'gtol': 1e-9})
fit.parameters = np.tile(result.x, 8)
fit.evaluate(fit.parameters, regularization=.002)
local_weights, local_biases = fit.artifact()
local_logs = -np.logaddexp(0, -local_spins[None, :, :] *
                         (local_spins @ local_weights.transpose(0, 2, 1) + local_biases[:, None, :])).sum(axis=2)
deviations = np.exp(local_logs - local_target) - 1
covariance = (deviations * np.exp(local_target)) @ deviations.T
print('local fit', fit.last, 'component variance', np.trace(covariance) / 8, flush=True)
permutations = np.asarray(list(itertools.permutations(range(8))))
candidates = covariance[permutations[:, :, None], permutations[:, None, :]]
flattened = candidates.reshape(-1, 64)
choices = [0] * 5
for sweep in range(8):
    for block in range(5):
        other_covariance = sum(candidates[choice] for index, choice in enumerate(choices) if index != block)
        choices[block] = int(np.argmin(flattened @ other_covariance.reshape(-1)))
weights = np.zeros((8, 20, 20))
biases = np.zeros((8, 20))
global_orders = [[] for component in range(8)]
for block, choice in enumerate(choices):
    for component, local_component in enumerate(permutations[choice]):
        weights[component, 4 * block:4 * block + 4, 4 * block:4 * block + 4] = local_weights[local_component]
        biases[component, 4 * block:4 * block + 4] = local_biases[local_component]
        global_orders[component].extend((4 * block + fit.orders[local_component]).tolist())
initial = {'mixing': [.125] * 8, 'weights': weights.tolist(), 'biases': biases.tolist(), 'orders': global_orders}
couplings = np.zeros((20, 20))
for block in range(5):
    couplings[4 * block:4 * block + 4, 4 * block:4 * block + 4] = local_couplings
instance = {'n': 20, 'couplings': couplings.tolist(), 'fields': [strength] * 20}
optimizer = FullRefinement(instance, initial, seconds=float(sys.argv[3]), verbose=True, threads=4)
model = optimizer.fit(iterations=2000)
Path(sys.argv[2]).write_text(json.dumps({'strength': strength, 'model': model}, separators=(',', ':')))
