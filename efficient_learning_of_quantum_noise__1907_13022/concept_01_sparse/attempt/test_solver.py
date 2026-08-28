import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import time
import numpy as np
from solver import Reconstruction


def simulate(seed=1, n=40, count=96, width=6, groups=3, extra=32,
             noise=0.00025, distribution='log', dynamic=30, background=0,
             weight=None, mass=0.15, commuting=False):
    random = np.random.default_rng(seed)
    dimension = 2 * n
    hashes = random.integers(0, 2, (groups, width, dimension), dtype=np.uint8)
    if commuting:
        for group in range(groups):
            symmetric = random.integers(0, 2, (n, n), dtype=np.uint8)
            symmetric = np.triu(symmetric) ^ np.triu(symmetric, 1).T
            hashes[group, :, 1::2] = (hashes[group, :, 0::2] @ symmetric) & 1
    offsets = np.concatenate((np.zeros((1, dimension), dtype=np.uint8),
                              np.eye(dimension, dtype=np.uint8),
                              random.integers(0, 2, (extra, dimension), dtype=np.uint8)))
    bits = random.integers(0, 2, (count, dimension), dtype=np.uint8)
    if weight is not None:
        bits[:] = 0
        for row in bits:
            indices = random.choice(n, size=weight, replace=False)
            entries = random.integers(1, 4, size=weight)
            row[indices * 2] = entries & 1
            row[indices * 2 + 1] = (entries >> 1) & 1
    if distribution == 'log':
        probabilities = np.exp(random.uniform(-np.log(dynamic), 0, count))
    elif distribution == 'equal':
        probabilities = np.ones(count)
    elif distribution == 'near':
        probabilities = random.uniform(0.85, 1.15, count)
    else:
        probabilities = random.pareto(1.5, count) + 0.1
    probabilities *= mass / probabilities.sum()
    floor = probabilities.min() * 0.8
    if background:
        background_bits = random.integers(0, 2, (background, dimension), dtype=np.uint8)
        bits = np.concatenate((bits, background_bits))
        probabilities = np.concatenate((probabilities, np.full(background, mass * 0.08 / background)))
    buckets = 1 << width
    rows = len(offsets)
    signs = 1.0 - 2.0 * ((bits @ offsets.T) & 1)
    identity = 1.0 - probabilities.sum()
    transformed = np.zeros((groups, buckets, rows))
    for group in range(groups):
        transformed[group, 0] += identity
        locations = ((bits @ hashes[group].T) & 1) @ (1 << np.arange(width))
        np.add.at(transformed[group], locations, probabilities[:, None] * signs)
    from solver import walsh
    observations = walsh(transformed.transpose(0, 2, 1)) * buckets
    sigma = noise * random.uniform(0.9, 1.1, (groups, rows))
    observations += random.normal(size=observations.shape) * sigma[:, :, None]
    data = dict(n_qubits=np.int64(n), hashes=hashes, offsets=offsets, eigenvalues=observations,
                noise_std=sigma, recovery_floor=np.float64(floor), max_terms=np.int64(max(512, count)))
    truth = {}
    for row, probability in zip(bits, probabilities):
        key = bytes(row)
        truth[key] = truth.get(key, 0.0) + probability
    return data, truth, identity


def evaluate(data, truth, identity, verbose=False):
    start = time.monotonic()
    reconstruction = Reconstruction(data)
    if verbose:
        for name in ['direct', 'soft', 'pairs', 'refine', 'doubletons', 'triples']:
            original = getattr(reconstruction, name)
            def wrapped(*args, _original=original, _name=name, **kwargs):
                before = time.monotonic()
                result = _original(*args, **kwargs)
                current = {bytes(row) for row in reconstruction.bits[1:]}
                correct = len(current & truth.keys())
                print(_name, kwargs, 'add', result, 'have', len(current), 'true', correct,
                      'sec', round(time.monotonic() - before, 3), flush=True)
                return result
            setattr(reconstruction, name, wrapped)
    paulis, probabilities, estimate_identity = reconstruction.solve()
    entries = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.uint8)[paulis]
    prediction = {bytes(row.reshape(-1)): probability for row, probability in zip(entries, probabilities)}
    floor = float(data['recovery_floor'])
    true_support = {key for key, value in truth.items() if value >= floor}
    estimated_support = {key for key, value in prediction.items() if value >= floor}
    correct = len(true_support & estimated_support)
    f1 = 2 * correct / max(1, len(true_support) + len(estimated_support))
    error = sum(abs(truth.get(key, 0) - prediction.get(key, 0)) for key in truth.keys() | prediction.keys())
    error += max(0.0, 1.0 - estimate_identity - sum(prediction.values()))
    l1 = error / sum(truth.values())
    l2 = np.sqrt(sum((truth.get(key, 0) - prediction.get(key, 0)) ** 2 for key in truth.keys() | prediction.keys()) /
                 sum(value ** 2 for value in truth.values()))
    print('RESULT', 'n',int(data['n_qubits']), 'K', len(truth), 'B', 1 << data['hashes'].shape[1],
          'floor',floor, 'F1',round(f1,6), 'A',round(l1,6), 'B',round(l2,6),
          'iderr',round(estimate_identity - identity,8), 'out',len(prediction),
          'time',round(time.monotonic()-start,3), flush=True)
    return reconstruction, prediction


if __name__ == '__main__':
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'basic'
    if mode == 'example':
        with np.load('../participant/input/example.npz') as data:
            reconstruction = Reconstruction(data)
        start = time.monotonic()
        paulis, probabilities, identity = reconstruction.solve()
        print('EXAMPLE',len(probabilities),identity,probabilities.sum(),probabilities[:10],time.monotonic()-start)
    elif mode == 'basic':
        for specification in [dict(), dict(n=100,count=256,width=7,groups=4,dynamic=100),
                              dict(n=100,count=512,width=8,groups=3,distribution='near',noise=0.0003),
                              dict(n=80,count=256,width=6,groups=3,distribution='equal'),
                              dict(n=60,count=160,width=6,groups=3,dynamic=3000,noise=0.00002,background=1000)]:
            data, truth, identity = simulate(**specification)
            evaluate(data, truth, identity, True)
