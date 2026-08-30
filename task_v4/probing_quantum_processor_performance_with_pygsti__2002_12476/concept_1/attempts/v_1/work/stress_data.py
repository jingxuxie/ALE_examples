import json
from pathlib import Path

import numpy as np

from optimize import BASELINE, sparse_risks
from fast_features import features_fast, sample_parameters


def main():
    training = np.load('qmc_training.npz')
    pool = np.load('qmc_test.npz')
    pool_features = pool['features']
    baseline = sparse_risks(pool_features, BASELINE)
    ratios = []
    for name in ['design_initial.json', 'design_search.json', 'design_qmc.json']:
        batches = np.array(json.loads(Path(name).read_text())['batches'])
        ratios.append(sparse_risks(pool_features, batches) / baseline)
    ratio = np.max(ratios, axis=0)
    mixed = np.flatnonzero(pool['families'] == 'mixed')
    selected = mixed[np.argsort(ratio[mixed])[-64:]]
    generator = np.random.default_rng(81864)
    parameters = []
    for axis in range(3):
        for angle in [-0.057, -np.pi / 64, -0.04, 0.04, np.pi / 64, 0.057]:
            for repeat in range(4):
                parameter = sample_parameters(generator, 'mixed')
                parameter[6:9] = generator.uniform(-0.004, 0.004, 3)
                parameter[6 + axis] = angle + generator.uniform(-0.001, 0.001)
                parameters.append(parameter)
    parameters = np.array(parameters)
    features = features_fast(parameters)
    stress_count = len(selected) + len(parameters)
    np.savez('stress_training.npz',
             features=np.concatenate([training['features'], pool_features[selected], features]),
             parameters=np.concatenate([training['parameters'], pool['parameters'][selected], parameters]),
             families=np.concatenate([training['families'], pool['families'][selected], np.repeat('mixed', len(parameters))]),
             stress_weights=np.concatenate([np.zeros(len(training['families'])), np.full(stress_count, 0.12 / stress_count)]))
    print('stress scenarios', stress_count, flush=True)


if __name__ == '__main__':
    main()
