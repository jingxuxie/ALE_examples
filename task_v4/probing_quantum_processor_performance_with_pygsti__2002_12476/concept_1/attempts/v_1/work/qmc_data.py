import time

import numpy as np
from scipy.stats import qmc

from fast_features import features_fast, FAMILIES


def parameters_from_uniform(uniforms, family):
    parameters = np.empty((len(uniforms), 14))
    parameters[:, :9] = -0.012 + 0.024 * uniforms[:, :9]
    parameters[:, 9:12] = 0.0008 + 0.0022 * uniforms[:, 9:12]
    parameters[:, 12] = -0.025 + 0.05 * uniforms[:, 12]
    parameters[:, 13] = 0.90 + 0.05 * uniforms[:, 13]
    if family == 'long_coherence':
        parameters[:, :9] = -0.035 + 0.070 * uniforms[:, :9]
        parameters[:, 9:12] = 0.00004 + 0.00026 * uniforms[:, 9:12]
    elif family == 'detuned':
        parameters[:, [2, 5, 8]] = -0.09 + 0.18 * uniforms[:, [2, 5, 8]]
    elif family == 'anisotropic':
        parameters[:, 9:12] = 0.0001 + 0.0009 * uniforms[:, 9:12]
        parameters = np.repeat(parameters, 3, axis=0)
        parameters[np.arange(len(parameters)), 9 + np.arange(len(parameters)) % 3] = np.repeat(0.012 + 0.018 * uniforms[:, 14], 3)
    elif family == 'readout':
        parameters[:, 12] = -0.055 + 0.110 * uniforms[:, 12]
        parameters[:, 13] = 0.76 + 0.10 * uniforms[:, 13]
    elif family == 'mixed':
        parameters[:, :9] = -0.06 + 0.12 * uniforms[:, :9]
        parameters[:, 9:12] = np.exp(np.log(0.00006) + np.log(0.025 / 0.00006) * uniforms[:, 9:12])
        parameters[:, 12] = -0.05 + 0.10 * uniforms[:, 12]
        parameters[:, 13] = 0.80 + 0.14 * uniforms[:, 13]
    return parameters


def generate_qmc(filename, seed, exponents):
    all_parameters = []
    families = []
    for index, (family, exponent) in enumerate(zip(FAMILIES, exponents)):
        uniforms = qmc.Sobol(15, scramble=True, seed=seed + index).random_base2(exponent)
        parameters = parameters_from_uniform(uniforms, family)
        all_parameters.append(parameters)
        families.extend([family] * len(parameters))
    parameters = np.concatenate(all_parameters)
    started = time.time()
    features = np.concatenate([features_fast(parameters[start:start + 12]) for start in range(0, len(parameters), 12)])
    np.savez(filename, parameters=parameters, families=np.array(families), features=features)
    print(filename, features.shape, time.time() - started, flush=True)


if __name__ == '__main__':
    generate_qmc('qmc_training.npz', 724, [6, 7, 6, 6, 6, 8])
    generate_qmc('qmc_test.npz', 82695, [7, 8, 7, 8, 7, 10])
