"""Finite-cutoff, Fermi-surface-patch imaginary-axis Eliashberg operator."""

import numpy as np
from scipy.fft import irfft, next_fast_len, rfft


INPUT_KEYS = ("temperature", "n_freq", "weights", "omega", "coupling", "coulomb", "initial_delta")


def load_instance(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: np.array(archive[key], copy=True) for key in INPUT_KEYS}


class Model:
    def __init__(self, instance):
        self.temperature = float(instance["temperature"])
        self.n_freq = int(instance["n_freq"])
        self.weights = np.asarray(instance["weights"], dtype=np.float64)
        self.omega = np.asarray(instance["omega"], dtype=np.float64)
        self.coupling = np.asarray(instance["coupling"], dtype=np.float64)
        self.coulomb = np.asarray(instance["coulomb"], dtype=np.float64)
        self.shape = (len(self.weights), self.n_freq)
        self.frequencies = np.pi * self.temperature * (2 * np.arange(self.n_freq) + 1)
        self.weighted_coupling = self.coupling * self.weights[None, None, :]
        self.weighted_coulomb = self.coulomb * self.weights[None, :]
        self.fft_length = next_fast_len(4 * self.n_freq)
        distances = 2 * np.pi * self.temperature * np.arange(2 * self.n_freq)
        kernel = self.omega[:, None] ** 2 / (self.omega[:, None] ** 2 + distances[None, :] ** 2)
        embedding = np.zeros((len(self.omega), self.fft_length))
        embedding[:, :2 * self.n_freq] = kernel
        embedding[:, -(2 * self.n_freq - 1):] = kernel[:, 1:][:, ::-1]
        self.kernel_fft = rfft(embedding, workers=1)

    def convolve(self, values, parity):
        extended = np.concatenate((parity * values[:, ::-1], values), axis=1)
        transformed = rfft(extended, n=self.fft_length, workers=1)
        result = np.zeros(self.shape)
        for mode_index, kernel in enumerate(self.kernel_fft):
            filtered = irfft(transformed * kernel[None, :], n=self.fft_length, workers=1)
            result += self.weighted_coupling[mode_index] @ filtered[:, self.n_freq:2 * self.n_freq]
        return result

    def fields(self, delta):
        delta = np.asarray(delta, dtype=np.float64).reshape(self.shape)
        radius = np.hypot(self.frequencies[None, :], delta)
        normal = self.convolve(self.frequencies[None, :] / radius, -1)
        anomalous_ratio = delta / radius
        pairing = self.convolve(anomalous_ratio, 1)
        pairing -= 2 * (self.weighted_coulomb @ anomalous_ratio.sum(axis=1))[:, None]
        renormalization = 1 + np.pi * self.temperature * normal / self.frequencies[None, :]
        return renormalization, np.pi * self.temperature * pairing

    def map(self, delta):
        renormalization, pairing = self.fields(delta)
        return renormalization, pairing / renormalization

    def residual(self, delta):
        return np.asarray(delta).reshape(self.shape) - self.map(delta)[1]

    def linearize(self, delta):
        delta = np.asarray(delta, dtype=np.float64).reshape(self.shape)
        radius = np.hypot(self.frequencies[None, :], delta)
        renormalization, mapped = self.map(delta)
        normal_derivative = -self.frequencies[None, :] * delta / radius ** 3
        anomalous_derivative = self.frequencies[None, :] ** 2 / radius ** 3

        def product(direction):
            direction = np.asarray(direction).reshape(self.shape)
            change_z = np.pi * self.temperature * self.convolve(normal_derivative * direction, -1)
            change_z /= self.frequencies[None, :]
            change_ratio = anomalous_derivative * direction
            change_pair = self.convolve(change_ratio, 1)
            change_pair -= 2 * (self.weighted_coulomb @ change_ratio.sum(axis=1))[:, None]
            return direction - (np.pi * self.temperature * change_pair - mapped * change_z) / renormalization

        return product

    def residual_norms(self, delta, renormalization):
        expected_z, mapped = self.map(delta)
        scale = np.maximum(np.max(np.abs(delta), axis=1), np.pi * self.temperature * 1e-10)
        gap_residual = np.max(np.abs(delta - mapped) / scale[:, None])
        z_residual = np.max(np.abs(renormalization - expected_z) / np.maximum(expected_z, 1))
        return float(gap_residual), float(z_residual)
