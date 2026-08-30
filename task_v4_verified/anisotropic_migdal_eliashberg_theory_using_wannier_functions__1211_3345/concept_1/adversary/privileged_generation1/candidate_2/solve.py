import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import argparse
import sys
import time

import numpy as np
from scipy.fft import dct, dst, idct, idst, next_fast_len, rfft
from scipy.sparse.linalg import LinearOperator, eigsh, gmres


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
        self.calls = 0

    def convolve(self, values, parity):
        self.calls += 1
        if parity == 1:
            transformed = dct(values, type=2, n=self.transform_length, workers=1)
            kernels = self.kernel_fft[:, :-1]
        else:
            transformed = dst(values, type=2, n=self.transform_length, workers=1)
            kernels = self.kernel_fft[:, 1:]
        combined = np.zeros_like(transformed)
        for matrix, kernel in zip(self.weighted_coupling, kernels):
            combined += (matrix @ transformed) * kernel[None, :]
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


def eigenmode_initial(model, initial):
    count = model.n_freq
    positions = np.arange(count)
    distances = 2 * model.prefactor * np.arange(2 * count)
    normal = np.zeros(model.shape)
    for energy, matrix in zip(model.omega, model.weighted_coupling):
        prefix = np.cumsum(energy ** 2 / (energy ** 2 + distances ** 2))
        difference = 2 * prefix[positions] + prefix[count - 1 - positions] - prefix[count + positions] - 1
        normal += matrix.sum(axis=1)[:, None] * difference[None, :]
    normal_z = 1 + model.prefactor * normal / model.frequencies[None, :]
    inner = np.sqrt(model.weights[:, None] * normal_z / model.frequencies[None, :])

    def linear_pairing(vector):
        delta = vector.reshape(model.shape) / inner
        ratio = delta / model.frequencies[None, :]
        pairing = model.convolve(ratio, 1)
        pairing -= 2 * (model.weighted_coulomb @ ratio.sum(axis=1))[:, None]
        return (inner * model.prefactor * pairing / normal_z).ravel()

    operator = LinearOperator((initial.size, initial.size), matvec=linear_pairing, dtype=np.float64)
    eigenvalues, eigenvectors = eigsh(operator, k=1, which="LA", ncv=8, tol=2e-10,
                                     maxiter=80, v0=(initial * inner).ravel())
    eigenvalue = float(eigenvalues[0])
    mode = eigenvectors[:, 0].reshape(model.shape) / inner
    if np.dot(model.weights, mode[:, 0]) < 0:
        mode = -mode
    mode /= np.max(np.abs(mode))
    if eigenvalue <= 1:
        return initial
    projected_weight = inner ** 2 * mode
    norm = np.sum(projected_weight * mode)
    amplitude = 0.1 * model.prefactor
    for iteration in range(2):
        mapped = model.map(amplitude * mode)[1] / amplitude
        defect = np.sum(projected_weight * (mode - mapped)) / norm
        nonlinear = max(defect + eigenvalue - 1, 1e-15)
        amplitude *= np.clip(np.sqrt((eigenvalue - 1) / nonlinear), 0.01, 100)
    return amplitude * mode


def solve(instance):
    started = time.process_time()
    model = Model(instance)
    delta = np.asarray(instance["initial_delta"], dtype=np.float64).copy()
    verbose = os.environ.get("SOLVER_VERBOSE")
    large_grid = model.n_freq >= 4096
    if large_grid:
        delta = eigenmode_initial(model, delta)
    for iteration in range(0 if large_grid else 10):
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
        if error < 1e-10 and last_step < 2e-6:
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
