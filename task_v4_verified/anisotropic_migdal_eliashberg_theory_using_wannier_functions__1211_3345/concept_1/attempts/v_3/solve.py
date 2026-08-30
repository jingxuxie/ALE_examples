import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import argparse
import time

import numpy as np
from scipy.fft import dct, dst, idct, idst, next_fast_len
from scipy.linalg.blas import dgemm
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import LinearOperator, gmres


class Model:
    def __init__(self, instance):
        self.temperature = float(instance['temperature'])
        self.n_freq = int(instance['n_freq'])
        self.weights = instance['weights']
        self.omega = instance['omega']
        self.shape = (self.weights.size, self.n_freq)
        self.frequencies = np.pi * self.temperature * (2 * np.arange(self.n_freq) + 1)
        self.weighted_coupling = instance['coupling'] * self.weights[None, None, :]
        self.weighted_coulomb = instance['coulomb'] * self.weights[None, :]
        self.length = next_fast_len(2 * self.n_freq)
        distances = 2 * np.pi * self.temperature * np.arange(self.length + 1)
        kernel = self.omega[:, None] ** 2 / (self.omega[:, None] ** 2 + distances[None, :] ** 2)
        self.kernel_fft = dct(kernel, type=1)
        indices = np.arange(self.n_freq)
        cumulative = np.cumsum(kernel[:, :2 * self.n_freq], axis=1) - 1
        rows = 1 + 2 * cumulative[:, indices] + cumulative[:, self.n_freq - 1 - indices] - cumulative[:, self.n_freq + indices]
        self.normal_z = 1 + np.pi * self.temperature * np.einsum('sa,sn->an', self.weighted_coupling.sum(axis=2), rows) / self.frequencies

    def convolve(self, values, parity):
        if parity == 1:
            transformed = dct(values, type=2, n=self.length, workers=1)
            kernels = self.kernel_fft[:, :-1]
        else:
            transformed = dst(values, type=2, n=self.length, workers=1)
            kernels = self.kernel_fft[:, 1:]
        result = np.zeros_like(transformed)
        for matrix, kernel in zip(self.weighted_coupling, kernels):
            result = dgemm(1, (transformed * kernel).T, matrix.T, beta=1, c=result.T, overwrite_c=1).T
        if parity == 1:
            return idct(result, type=2, workers=1)[:, :self.n_freq]
        return idst(result, type=2, workers=1)[:, :self.n_freq]

    def map(self, delta):
        radius = np.hypot(self.frequencies, delta)
        normal_ratio = -(delta / radius) * (delta / (radius + self.frequencies))
        normal = self.convolve(normal_ratio, -1)
        ratio = delta / radius
        pairing = self.convolve(ratio, 1)
        pairing -= 2 * (self.weighted_coulomb @ self.sum_ratio(ratio))[:, None]
        renormalization = self.normal_z + np.pi * self.temperature * normal / self.frequencies
        return renormalization, np.pi * self.temperature * pairing / renormalization

    def linearize(self, delta, renormalization, mapped):
        radius = np.hypot(self.frequencies, delta)
        normal_derivative = -self.frequencies * delta / radius ** 3
        anomalous_derivative = self.frequencies ** 2 / radius ** 3

        def product(direction):
            change_z = np.pi * self.temperature * self.convolve(normal_derivative * direction, -1) / self.frequencies
            ratio = anomalous_derivative * direction
            change_pair = self.convolve(ratio, 1)
            change_pair -= 2 * (self.weighted_coulomb @ self.sum_ratio(ratio))[:, None]
            return direction - (np.pi * self.temperature * change_pair - mapped * change_z) / renormalization

        return product

    def sum_ratio(self, ratio):
        return ratio.sum(axis=1)


def interpolation_matrix(nodes, count):
    points = np.arange(count)
    starts = np.clip(np.searchsorted(nodes, points) - 2, 0, len(nodes) - 4)
    indices = starts[:, None] + np.arange(4)
    selected = nodes[indices]
    coefficients = np.ones((count, 4))
    for column in range(4):
        for other in range(4):
            if column != other:
                coefficients[:, column] *= (points - selected[:, other]) / (selected[:, column] - selected[:, other])
    return csr_matrix((coefficients.ravel(), indices.ravel(), np.arange(count + 1) * 4), shape=(count, len(nodes)))


class ReducedModel(Model):
    def __init__(self, full, spacing=0.045):
        self.temperature = full.temperature
        self.weights = full.weights
        self.omega = full.omega
        self.weighted_coupling = full.weighted_coupling
        self.weighted_coulomb = full.weighted_coulomb
        nodes = [0]
        while nodes[-1] < full.n_freq - 1:
            nodes.append(min(full.n_freq - 1, nodes[-1] + max(1, int((nodes[-1] + 1) * spacing))))
        self.nodes = np.array(nodes)
        self.n_freq = len(nodes)
        self.shape = (len(self.weights), self.n_freq)
        self.frequencies = full.frequencies[self.nodes]
        self.normal_z = full.normal_z[:, self.nodes]
        self.interpolation = interpolation_matrix(self.nodes, full.n_freq)
        self.quadrature = np.asarray(self.interpolation.sum(axis=0)).ravel()
        self.kernels = [(np.empty((self.n_freq, self.n_freq)), np.empty((self.n_freq, self.n_freq))) for omega in self.omega]
        for start in range(0, self.n_freq, 16):
            section = slice(start, start + 16)
            difference = (self.frequencies[section, None] - full.frequencies[None, :]) ** 2
            addition = (self.frequencies[section, None] + full.frequencies[None, :]) ** 2
            for omega, kernels in zip(self.omega, self.kernels):
                minus = omega ** 2 / (omega ** 2 + difference)
                plus = omega ** 2 / (omega ** 2 + addition)
                kernels[0][section] = (self.interpolation.T @ (minus + plus).T).T
                kernels[1][section] = (self.interpolation.T @ (minus - plus).T).T

    def convolve(self, values, parity):
        result = np.zeros(self.shape)
        for matrix, kernels in zip(self.weighted_coupling, self.kernels):
            mixed = dgemm(1, values.T, matrix.T)
            result = dgemm(1, kernels[0 if parity == 1 else 1], mixed, beta=1, c=result.T, overwrite_c=1).T
        return result

    def sum_ratio(self, ratio):
        return ratio @ self.quadrature

    def expand(self, delta):
        return (self.interpolation @ delta.T).T.copy()


def solve_newton(model, delta, tolerance=2e-12, max_iterations=40, warmup=6, verbose=False):
    for iteration in range(warmup):
        delta = 0.2 * delta + 0.8 * model.map(delta)[1]
    for iteration in range(max_iterations):
        renormalization, mapped = model.map(delta)
        scale = np.maximum(np.max(np.abs(delta), axis=1), np.pi * model.temperature * 1e-10)[:, None]
        residual = delta - mapped
        error = np.max(np.abs(residual) / scale)
        if verbose:
            print('newton', model.shape, iteration, error, delta[:, 0].min(), delta[:, 0].max(), time.process_time(), flush=True)
        if error < tolerance:
            return delta, renormalization
        derivative = model.linearize(delta, renormalization, mapped)
        evaluations = [0]

        def product(direction):
            evaluations[0] += 1
            return (derivative(direction.reshape(model.shape) * scale) / scale).ravel()

        operator = LinearOperator((delta.size, delta.size), matvec=product, dtype=np.float64)
        step, info = gmres(operator, (residual / scale).ravel(), tol=0.002, atol=0, restart=24, maxiter=4)
        step = step.reshape(model.shape) * scale
        fraction = 1.0
        decreases = step[:, 0] > 0
        if np.any(decreases):
            fraction = min(fraction, np.min(0.95 * delta[decreases, 0] / step[decreases, 0]))
        if not np.isfinite(fraction) or fraction <= 0:
            delta = 0.35 * delta + 0.65 * mapped
        else:
            delta -= fraction * step
        if verbose:
            print('  gmres', evaluations[0], info, fraction, flush=True)
    return delta, model.map(delta)[0]


def refine(full, reduced, delta, verbose=False):
    for iteration in range(12):
        renormalization, mapped = full.map(delta)
        residual = delta - mapped
        scale = np.maximum(np.max(np.abs(delta), axis=1), np.pi * full.temperature * 1e-10)[:, None]
        error = np.max(np.abs(residual) / scale)
        if verbose:
            print('refine', iteration, error, delta[:, 0].min(), delta[:, 0].max(), time.process_time(), flush=True)
        if error < 1e-11:
            return delta, renormalization
        sampled = delta[:, reduced.nodes]
        reduced_z, reduced_mapped = reduced.map(sampled)
        derivative = reduced.linearize(sampled, reduced_z, reduced_mapped)

        def product(direction):
            return (derivative(direction.reshape(reduced.shape) * scale) / scale).ravel()

        operator = LinearOperator((sampled.size, sampled.size), matvec=product, dtype=np.float64)
        small_residual = residual[:, reduced.nodes]
        step, info = gmres(operator, (small_residual / scale).ravel(), tol=1e-5, atol=0, restart=24, maxiter=4)
        step = step.reshape(reduced.shape) * scale
        full_step = residual + reduced.expand(step - small_residual)
        fraction = 1.0
        decreases = full_step[:, 0] > 0
        if np.any(decreases):
            fraction = min(fraction, np.min(0.95 * delta[decreases, 0] / full_step[decreases, 0]))
        delta -= fraction * full_step
    return delta, full.map(delta)[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as archive:
        instance = {key: np.array(archive[key]) for key in archive.files}
    model = Model(instance)
    delta = instance['initial_delta'].copy()
    if model.n_freq > 1024:
        reduced = ReducedModel(model)
        delta, renormalization = solve_newton(reduced, delta[:, reduced.nodes], verbose=args.verbose)
        delta = reduced.expand(delta)
        delta, renormalization = refine(model, reduced, delta, verbose=args.verbose)
    else:
        delta, renormalization = solve_newton(model, delta, tolerance=5e-12, verbose=args.verbose)
    np.savez(args.output, delta=delta, z=renormalization)


if __name__ == '__main__':
    main()
