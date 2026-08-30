import numpy as np
from optimization import FullRefinement

rng = np.random.default_rng(719)
count = 6
couplings = rng.normal(0, .2, size=(count, count))
couplings = np.triu(couplings, 1)
couplings += couplings.T
instance = {'n': count, 'couplings': couplings.tolist(), 'fields': rng.normal(0, .1, count).tolist()}
weights = np.zeros((8, count, count))
orders = [rng.permutation(count) for component in range(8)]
for component, order in enumerate(orders):
    for position, site in enumerate(order):
        weights[component, site, order[:position]] = rng.normal(0, .2, size=position)
model = {'mixing': [.125] * 8, 'weights': weights.tolist(),
         'biases': rng.normal(0, .2, size=(8, count)).tolist(), 'orders': [order.tolist() for order in orders]}
optimizer = FullRefinement(instance, model, seconds=30, threads=2)
try:
    vector = rng.normal(0, .01, optimizer.size)
    objective, gradient = optimizer.evaluate(vector)
    errors = []
    for index in rng.choice(optimizer.size, 20, replace=False):
        delta = np.zeros_like(vector)
        delta[index] = 1e-6
        numerical = (optimizer.evaluate(vector + delta)[0] - optimizer.evaluate(vector - delta)[0]) / 2e-6
        errors.append(abs(numerical - gradient[index]))
    print('maximum gradient error', max(errors))
    assert max(errors) < 1e-7
finally:
    optimizer.executor.shutdown()
