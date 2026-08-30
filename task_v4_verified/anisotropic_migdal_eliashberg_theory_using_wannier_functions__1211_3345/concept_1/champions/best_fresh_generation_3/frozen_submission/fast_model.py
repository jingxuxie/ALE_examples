import numpy as np
from scipy.fft import dct, dst, idct, idst, next_fast_len, rfft


class Model:
    def __init__(self, instance):
        self.temperature = float(instance['temperature'])
        self.n_freq = int(instance['n_freq'])
        self.weights = np.asarray(instance['weights'])
        self.omega = np.asarray(instance['omega'])
        self.shape = (len(self.weights), self.n_freq)
        self.frequencies = np.pi * self.temperature * (2 * np.arange(self.n_freq) + 1)
        self.weighted_coupling = np.ascontiguousarray(instance['coupling'] * self.weights[None, None, :])
        self.weighted_coulomb = np.ascontiguousarray(instance['coulomb'] * self.weights[None, :])
        self.length = next_fast_len(2 * self.n_freq)
        distances = 2 * np.pi * self.temperature * np.arange(2 * self.n_freq)
        kernel = self.omega[:, None] ** 2 / (self.omega[:, None] ** 2 + distances[None, :] ** 2)
        prefix = np.cumsum(kernel[:, :self.n_freq], axis=1)
        tail = np.empty_like(prefix)
        tail[:, 0] = kernel[:, self.n_freq]
        tail[:, 1:] = kernel[:, self.n_freq:self.n_freq + 1] + np.cumsum(
            kernel[:, self.n_freq - 1:0:-1] + kernel[:, self.n_freq + 1:], axis=1)
        normal_sum = 2 * prefix - 1 - tail
        self.normal_z = 1 + np.pi * self.temperature * (
            self.weighted_coupling.sum(axis=2).T @ normal_sum) / self.frequencies
        embedding = np.zeros((len(self.omega), 2 * self.length))
        embedding[:, :2 * self.n_freq] = kernel
        embedding[:, -(2 * self.n_freq - 1):] = kernel[:, 1:][:, ::-1]
        self.spectra = rfft(embedding, workers=1).real.copy()
        self.combined = None
        if len(self.omega) > 5:
            self.combined = (self.weighted_coupling.reshape(len(self.omega), -1).T @ self.spectra).reshape(self.shape[0], self.shape[0], self.length + 1)
        self.count = 0

    def convolve(self, values, parity):
        transform, inverse = (dct, idct) if parity == 1 else (dst, idst)
        transformed = transform(values, type=2, n=self.length, workers=1)
        section = slice(None, -1) if parity == 1 else slice(1, None)
        if self.combined is not None:
            result = np.einsum('abk,bk->ak', self.combined[:, :, section], transformed, optimize=False)
        else:
            result = np.zeros_like(transformed)
            for coupling, spectrum in zip(self.weighted_coupling, self.spectra):
                result += (coupling @ transformed) * spectrum[section]
        return inverse(result, type=2, workers=1)[:, :self.n_freq]

    def map(self, delta):
        self.count += 1
        radius = np.hypot(self.frequencies, delta)
        ratio = delta / radius
        normal = self.convolve(-ratio * (delta / (radius + self.frequencies)), -1)
        pairing = self.convolve(ratio, 1)
        pairing -= 2 * (self.weighted_coulomb @ ratio.sum(axis=1))[:, None]
        renormalization = self.normal_z + np.pi * self.temperature * normal / self.frequencies
        return renormalization, np.pi * self.temperature * pairing / renormalization

    def linearize(self, delta, renormalization=None, mapped=None):
        if renormalization is None:
            renormalization, mapped = self.map(delta)
        radius = np.hypot(self.frequencies, delta)
        normal_derivative = -self.frequencies * delta / radius ** 3
        anomalous_derivative = self.frequencies ** 2 / radius ** 3

        def product(direction):
            self.count += 1
            direction = np.asarray(direction).reshape(self.shape)
            change_z = np.pi * self.temperature * self.convolve(normal_derivative * direction, -1) / self.frequencies
            change_ratio = anomalous_derivative * direction
            change_pair = self.convolve(change_ratio, 1)
            change_pair -= 2 * (self.weighted_coulomb @ change_ratio.sum(axis=1))[:, None]
            return direction - (np.pi * self.temperature * change_pair - mapped * change_z) / renormalization
        return product
