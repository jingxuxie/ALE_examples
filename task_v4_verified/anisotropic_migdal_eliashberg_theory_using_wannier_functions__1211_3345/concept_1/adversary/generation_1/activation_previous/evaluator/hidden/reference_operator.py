"""Builder-owned fast operator; independent direct summation certifies its output."""

import numpy as np
from scipy.fft import irfft, next_fast_len, rfft


class ReferenceModel:
    def __init__(self, instance):
        self.temperature = float(instance["temperature"])
        self.weights = instance["weights"]
        self.shape = (len(self.weights), int(instance["n_freq"]))
        self.frequencies = (np.arange(self.shape[1]) * 2 + 1) * np.pi * self.temperature
        self.weighted_coupling = instance["coupling"] * self.weights[None, None, :]
        self.weighted_coulomb = instance["coulomb"] * self.weights[None, :]
        self.size = next_fast_len(4 * self.shape[1])
        separation = np.minimum(np.arange(self.size), self.size - np.arange(self.size))
        energies = instance["omega"][:, None]
        kernels = energies ** 2 / (energies ** 2 + (2 * np.pi * self.temperature * separation) ** 2)
        self.transforms = rfft(kernels, axis=1, workers=1)

    def convolve(self, values, parity):
        count = self.shape[1]
        padded = np.zeros((self.shape[0], self.size))
        padded[:, :count] = parity * values[:, ::-1]
        padded[:, count:2 * count] = values
        transformed = rfft(padded, workers=1)
        result = np.zeros(self.shape)
        for matrix, kernel in zip(self.weighted_coupling, self.transforms):
            convolution = irfft(transformed * kernel, n=self.size, workers=1)[:, count:2 * count]
            result += matrix @ convolution
        return result

    def map(self, delta):
        radius = np.hypot(delta, self.frequencies[None, :])
        normal = self.convolve(self.frequencies[None, :] / radius, -1)
        ratio = delta / radius
        pairing = self.convolve(ratio, 1)
        pairing -= 2 * (self.weighted_coulomb @ ratio.sum(axis=1))[:, None]
        renormalization = 1 + np.pi * self.temperature * normal / self.frequencies
        return renormalization, np.pi * self.temperature * pairing / renormalization

    def linearize(self, delta):
        radius = np.hypot(delta, self.frequencies)
        renormalization, mapped = self.map(delta)

        def product(direction):
            normal = -self.frequencies * delta * direction / radius ** 3
            change_z = np.pi * self.temperature * self.convolve(normal, -1) / self.frequencies
            ratio = self.frequencies ** 2 * direction / radius ** 3
            pairing = self.convolve(ratio, 1)
            pairing -= 2 * (self.weighted_coulomb @ ratio.sum(axis=1))[:, None]
            return direction - (np.pi * self.temperature * pairing - mapped * change_z) / renormalization

        return product
