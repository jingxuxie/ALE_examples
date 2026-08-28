import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import resource
import subprocess
import sys
import time
import numpy as np
from solver import Reconstruction, walsh
from test_solver import simulate, evaluate


def validate(paulis, probabilities, identity, n, maximum):
    assert paulis.dtype == np.uint8 and paulis.shape == (len(probabilities), n)
    assert len(paulis) <= maximum and np.all(paulis <= 3)
    assert np.all(paulis.any(axis=1)) and len(np.unique(paulis, axis=0)) == len(paulis)
    assert probabilities.dtype == np.float64 and np.isfinite(probabilities).all()
    assert np.all(probabilities >= 0) and np.isfinite(identity) and identity >= 0
    assert identity + probabilities.sum() <= 1.0 + 1e-8


data, truth, identity = simulate(n=40, count=8, noise=0.0, commuting=True)
data['hashes'][:] = 0
for row in range(data['hashes'].shape[1]):
    data['hashes'][:, row, 2 * row + 1] = 1
model = Reconstruction(data)
bits = np.array([np.frombuffer(key, dtype=np.uint8) for key in truth])
signs = model.signatures(bits)
locations = model.locations(bits)
transformed = model.uniform * 0.05
transformed[:, 0] += identity - 0.05
for group in range(model.groups):
    np.add.at(transformed[group], locations[group], np.array(list(truth.values()))[:, None] * signs)
data['eigenvalues'] = walsh(transformed.transpose(0, 2, 1)) * model.buckets
model = Reconstruction(data)
model.bits = np.concatenate((np.zeros((1, model.dimension), dtype=np.uint8), bits))
model.fit_weights = np.random.default_rng(30).lognormal(0.0, 0.7, model.values.shape)
model.uniform_norm = np.sum(model.uniform ** 2 * model.fit_weights)
model.uniform_data = np.sum(model.uniform * model.values * model.fit_weights)
model.fit()
signs = model.signatures(model.bits)
locations = model.locations(model.bits)
columns = []
for index in range(len(model.bits)):
    column = -model.uniform.copy()
    for group in range(model.groups):
        column[group, locations[group, index]] += signs[index]
    columns.append(column.ravel())
design = np.column_stack(columns) * np.sqrt(model.fit_weights.ravel())[:, None]
target = (model.values - model.uniform).ravel() * np.sqrt(model.fit_weights.ravel())
reference = np.linalg.lstsq(design, target, rcond=None)[0]
assert np.max(np.abs(reference - model.probabilities)) < 1e-10
result = Reconstruction(data).solve()
validate(*result, 40, 512)
assert len(result[0]) == len(truth)
assert abs(result[2] - (identity - 0.05)) < 1e-9
print('WEIGHTED_AND_STRUCTURED', np.max(np.abs(reference - model.probabilities)), flush=True)


for mass, maximum in [(0.15, 0), (0.15, 1), (1.0, 512), (0.95, 512)]:
    data, truth, identity = simulate(n=40, count=32, mass=mass, noise=0.0001, commuting=True)
    data['max_terms'] = maximum
    result = Reconstruction(data).solve()
    validate(*result, 40, maximum)
    print('EDGE', mass, maximum, len(result[0]), result[2], flush=True)

for identity in [0.0, 0.4, 1.0]:
    data, truth, previous_identity = simulate(n=100, count=1, width=8, groups=5, extra=48, commuting=True)
    basis = Reconstruction(data)
    transformed = (1.0 - identity) * basis.uniform
    transformed[:, 0, :] += identity
    random = np.random.default_rng(25)
    data['eigenvalues'] = walsh(transformed.transpose(0, 2, 1)) * basis.buckets
    data['eigenvalues'] += random.normal(size=data['eigenvalues'].shape) * data['noise_std'][:, :, None]
    result = Reconstruction(data).solve()
    validate(*result, 100, 512)
    assert len(result[0]) == 0
    assert abs(result[2] - identity) < 1e-5
    print('EMPTY', identity, result[2], flush=True)

data, truth, identity = simulate(seed=77, n=100, count=512, width=8, groups=5,
                                extra=48, dynamic=100, commuting=True)
np.savez('resource_case.npz', **data)


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))


start = time.monotonic()
subprocess.run([sys.executable, 'solver.py', 'resource_case.npz', 'resource_output.npz'],
               preexec_fn=limits, timeout=120, check=True)
with np.load('resource_output.npz', allow_pickle=False) as output:
    assert set(output.files) == {'paulis', 'probabilities', 'p_identity'}
    validate(output['paulis'], output['probabilities'], output['p_identity'], 100, 512)
    print('RESOURCE', len(output['paulis']), 'seconds', time.monotonic() - start,
          'peak_rss_kib', resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss, flush=True)
