import numpy as np


def spectrum(specification, frequency):
    frequencies = np.asarray(frequency, dtype=float)
    if specification['kind'] == 'flat':
        return np.ones_like(frequencies) * specification['strength']
    magnitude = np.abs(frequencies)
    temperature = specification.get('temperature', 0.0)
    density = specification['eta'] * magnitude * np.exp(-magnitude / specification['cutoff'])
    if temperature > 0:
        occupation = np.zeros_like(magnitude)
        nonzero = magnitude > 1e-12
        occupation[nonzero] = 1.0 / np.expm1(np.minimum(magnitude[nonzero] / temperature, 700))
        result = density * (occupation + (frequencies > 0))
        result = np.where(nonzero, result, specification['eta'] * temperature)
    else:
        result = density * (frequencies > 0)
    if specification['kind'] == 'filtered':
        width = specification['width']
        factor = specification.get('floor', 0.0) + width ** 2 / ((magnitude - specification['center']) ** 2 + width ** 2)
        result = result * factor
    return result
