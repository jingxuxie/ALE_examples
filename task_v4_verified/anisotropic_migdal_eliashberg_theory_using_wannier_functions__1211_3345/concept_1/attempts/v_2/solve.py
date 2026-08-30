import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import argparse
import sys
import time

import numpy as np
from scipy.fft import dct, dst, idct, idst, next_fast_len, rfft
from scipy.sparse.linalg import LinearOperator, gmres


class Model:
    def __init__(self, instance):
        self.temperature = float(instance["temperature"])
        self.n_freq = int(instance["n_freq"])
        self.weights = np.asarray(instance["weights"], dtype=np.float64)
        self.omega = np.asarray(instance["omega"], dtype=np.float64)
        self.shape = (len(self.weights), self.n_freq)
        self.frequencies = np.pi * self.temperature * (2 * np.arange(self.n_freq) + 1)
        self.prefactor = np.pi * self.temperature
        self.weighted_coupling = instance["coupling"] * self.weights[None, None, :]
        self.weighted_coulomb = instance["coulomb"] * self.weights[None, :]
        self.transform_length = next_fast_len(2 * self.n_freq)
        distances = 2 * self.prefactor * np.arange(2 * self.n_freq)
        kernel = self.omega[:, None] ** 2 / (self.omega[:, None] ** 2 + distances[None, :] ** 2)
        embedding = np.zeros((len(self.omega), 2 * self.transform_length))
        embedding[:, :2 * self.n_freq] = kernel
        embedding[:, -(2 * self.n_freq - 1):] = kernel[:, 1:][:, ::-1]
        self.kernel_fft = rfft(embedding, workers=1).real
        self.spectral = np.ascontiguousarray(np.einsum(
            "sab,sk->abk", self.weighted_coupling, self.kernel_fft, optimize=True))
        self.calls = 0

    def convolve(self, values, parity):
        self.calls += 1
        if parity == 1:
            transformed = dct(values, type=2, n=self.transform_length, workers=1)
            kernels = self.spectral[:, :, :-1]
        else:
            transformed = dst(values, type=2, n=self.transform_length, workers=1)
            kernels = self.spectral[:, :, 1:]
        combined = np.einsum("abk,bk->ak", kernels, transformed, optimize=False)
        if parity == 1:
            return idct(combined, type=2, workers=1)[:, :self.n_freq]
        return idst(combined, type=2, workers=1)[:, :self.n_freq]

    def map(self, delta):
        radius = np.hypot(self.frequencies[None, :], delta)
        normal = self.convolve(self.frequencies[None, :] / radius, -1)
        ratio = delta / radius
        pairing = self.convolve(ratio, 1)
        pairing -= 2 * (self.weighted_coulomb @ ratio.sum(axis=1))[:, None]
        renormalization = 1 + self.prefactor * normal / self.frequencies[None, :]
        return renormalization, self.prefactor * pairing / renormalization

    def linearize(self, delta, renormalization, mapped):
        radius = np.hypot(self.frequencies[None, :], delta)
        normal_derivative = -self.frequencies[None, :] * delta / radius ** 3
        anomalous_derivative = self.frequencies[None, :] ** 2 / radius ** 3

        def product(direction):
            change_z = self.prefactor * self.convolve(normal_derivative * direction, -1)
            change_z /= self.frequencies[None, :]
            change_ratio = anomalous_derivative * direction
            change_pair = self.convolve(change_ratio, 1)
            change_pair -= 2 * (self.weighted_coulomb @ change_ratio.sum(axis=1))[:, None]
            return direction - (self.prefactor * change_pair - mapped * change_z) / renormalization

        return product


def solve(instance):
    started = time.process_time()
    model = Model(instance)
    delta = np.asarray(instance["initial_delta"], dtype=np.float64).copy()
    verbose = os.environ.get("SOLVER_VERBOSE")
    for iteration in range(10):
        renormalization, mapped = model.map(delta)
        delta = 0.2 * delta + 0.8 * mapped
    last_step = np.inf
    for iteration in range(40):
        renormalization, mapped = model.map(delta)
        scale = np.maximum(np.max(np.abs(delta), axis=1), model.prefactor * 1e-10)[:, None]
        residual = (delta - mapped) / scale
        error = np.max(np.abs(residual))
        if verbose:
            print(iteration, "res", error, "step", last_step, "low", delta[:, 0],
                  "cpu", time.process_time() - started, "calls", model.calls, file=sys.stderr, flush=True)
        if error < 2e-12 and last_step < 2e-7:
            break
        product = model.linearize(delta, renormalization, mapped)

        def scaled_product(direction):
            return (product(direction.reshape(model.shape) * scale) / scale).ravel()

        operator = LinearOperator((delta.size, delta.size), matvec=scaled_product, dtype=np.float64)
        tolerance = min(0.005, max(2e-10, 0.02 * np.sqrt(error)))
        correction, info = gmres(operator, -residual.ravel(), tol=tolerance, atol=0,
                                 restart=40, maxiter=3)
        correction = correction.reshape(model.shape) * scale
        damping = 1.0
        decreasing = correction[:, 0] < 0
        if np.any(decreasing):
            damping = min(damping, 0.95 * np.min(-delta[decreasing, 0] / correction[decreasing, 0]))
        last_step = np.max(np.abs(damping * correction) / scale)
        delta += damping * correction
    renormalization = model.map(delta)[0]
    return delta, renormalization


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as archive:
        instance = {key: np.array(archive[key], copy=True) for key in archive.files}
    delta, renormalization = solve(instance)
    np.savez(args.output, delta=delta, z=renormalization)


if __name__ == "__main__":
    main()
