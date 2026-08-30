import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import argparse
import time

import numpy as np
from scipy.fft import dct, dst, idct, idst, next_fast_len, rfft
from scipy.sparse.linalg import LinearOperator, gmres
from scipy.sparse import csr_matrix


class Model:
    def __init__(self, instance):
        self.temperature = float(instance['temperature'])
        self.n_freq = int(instance['n_freq'])
        self.weights = instance['weights']
        self.omega = instance['omega']
        self.shape = (len(self.weights), self.n_freq)
        self.frequencies = np.pi * self.temperature * (2 * np.arange(self.n_freq) + 1)
        self.coupling = instance['coupling'] * self.weights[None, None, :]
        self.coulomb = instance['coulomb'] * self.weights[None, :]
        self.length = next_fast_len(2 * self.n_freq)
        distances = 2 * np.pi * self.temperature * np.arange(self.length + 1)
        kernel = self.omega[:, None] ** 2 / (self.omega[:, None] ** 2 + distances[None, :] ** 2)
        embedding = np.concatenate((kernel[:, :-1], np.zeros((len(self.omega), 1)), kernel[:, 1:-1][:, ::-1]), axis=1)
        self.kernel_fft = rfft(embedding, workers=1).real
        indices = np.arange(self.n_freq)
        increments = 2 * kernel[:, indices] - kernel[:, self.n_freq - indices] - kernel[:, self.n_freq + indices]
        increments[:, 0] = kernel[:, 0] - kernel[:, self.n_freq]
        normal = self.coupling.sum(axis=2).T @ np.cumsum(increments, axis=1)
        self.z_normal = 1 + np.pi * self.temperature * normal / self.frequencies
        self.calls = 0
        self.quadrature = np.ones(self.n_freq)

    def convolve(self, values, parity):
        self.calls += 1
        if parity == 1:
            transformed = dct(values, type=2, n=self.length, workers=1)
            kernels = self.kernel_fft[:, :self.length]
        else:
            transformed = dst(values, type=2, n=self.length, workers=1)
            kernels = self.kernel_fft[:, 1:self.length + 1]
        mixed = np.zeros_like(transformed)
        for coupling, kernel in zip(self.coupling, kernels):
            mixed += (coupling @ transformed) * kernel
        if parity == 1:
            result = idct(mixed, type=2, workers=1)
        else:
            result = idst(mixed, type=2, workers=1)
        return result[:, :self.n_freq]

    def map(self, delta):
        radius = np.hypot(self.frequencies, delta)
        normal_ratio = -delta * delta / (radius * (radius + self.frequencies))
        normal = self.convolve(normal_ratio, -1)
        ratio = delta / radius
        pairing = self.convolve(ratio, 1)
        pairing -= 2 * (self.coulomb @ (ratio @ self.quadrature))[:, None]
        renormalization = self.z_normal + np.pi * self.temperature * normal / self.frequencies
        return renormalization, np.pi * self.temperature * pairing / renormalization

    def derivative(self, delta, z, mapped):
        radius = np.hypot(self.frequencies, delta)
        normal_derivative = -self.frequencies * delta / radius ** 3
        anomalous_derivative = self.frequencies ** 2 / radius ** 3

        def product(direction):
            change_z = np.pi * self.temperature * self.convolve(normal_derivative * direction, -1) / self.frequencies
            ratio = anomalous_derivative * direction
            pairing = self.convolve(ratio, 1)
            pairing -= 2 * (self.coulomb @ (ratio @ self.quadrature))[:, None]
            return direction - (np.pi * self.temperature * pairing - mapped * change_z) / z

        return product


class CoarseModel(Model):
    def __init__(self, full, spacing=0.065, degree=11):
        self.temperature = full.temperature
        self.weights = full.weights
        self.omega = full.omega
        self.coupling = full.coupling
        self.coulomb = full.coulomb
        self.calls = 0
        indices = list(range(min(24, full.n_freq)))
        while indices[-1] < full.n_freq - 1:
            indices.append(max(indices[-1] + 1, int((indices[-1] + 0.5) * np.exp(spacing) - 0.5)))
        if len(indices) > 24 and indices[-2] > full.n_freq * np.exp(-0.4 * spacing):
            indices.pop()
        indices[-1] = full.n_freq - 1
        boundary = list(range(min(12, full.n_freq)))
        while boundary[-1] < full.n_freq // 3:
            boundary.append(max(boundary[-1] + 1, int((boundary[-1] + 0.5) * np.exp(0.13) - 0.5)))
        self.indices = np.unique(indices + [full.n_freq - 1 - offset for offset in boundary])
        self.n_freq = len(self.indices)
        self.shape = (full.shape[0], self.n_freq)
        self.frequencies = full.frequencies[self.indices]
        self.z_normal = full.z_normal[:, self.indices]
        locations = np.log(np.arange(full.n_freq) + 0.5)
        nodes = locations[self.indices]
        starts = np.clip(np.searchsorted(nodes, locations) - (degree + 1) // 2, 0, self.n_freq - degree - 1)
        columns = starts[:, None] + np.arange(degree + 1)
        coordinates = nodes[columns]
        coefficients = np.ones_like(coordinates)
        for offset in range(degree + 1):
            differences = coordinates - coordinates[:, offset, None]
            differences[:, offset] = 1
            factors = (locations[:, None] - coordinates[:, offset, None]) / differences
            factors[:, offset] = 1
            coefficients *= factors
        rows = np.broadcast_to(np.arange(full.n_freq)[:, None], columns.shape)
        self.interpolation = csr_matrix((coefficients.ravel(), (rows.ravel(), columns.ravel())), shape=(full.n_freq, self.n_freq))
        self.quadrature = np.asarray(self.interpolation.sum(axis=0)).ravel()
        differences = self.frequencies[:, None] - full.frequencies
        sums = self.frequencies[:, None] + full.frequencies
        self.plus = []
        self.minus = []
        for omega in full.omega:
            kernel_minus = omega ** 2 / (omega ** 2 + differences ** 2)
            kernel_plus = omega ** 2 / (omega ** 2 + sums ** 2)
            self.plus.append(np.asarray(self.interpolation.T @ (kernel_minus + kernel_plus).T).T.copy())
            self.minus.append(np.asarray(self.interpolation.T @ (kernel_minus - kernel_plus).T).T.copy())

    def convolve(self, values, parity):
        self.calls += 1
        result = np.zeros(self.shape)
        for coupling, kernel in zip(self.coupling, self.plus if parity == 1 else self.minus):
            result += coupling @ values @ kernel.T
        return result

    def expand(self, delta):
        return (self.interpolation @ delta.T).T.copy()


def newton_step(model, delta, z, mapped, residual):
    scales = np.maximum(np.max(np.abs(delta), axis=1)[:, None], np.pi * model.temperature * 1e-20)
    derivative = model.derivative(delta, z, mapped)

    def product(direction):
        return (derivative(direction.reshape(model.shape) * scales) / scales).ravel()

    operator = LinearOperator((delta.size, delta.size), matvec=product, dtype=np.float64)
    step, status = gmres(operator, (residual / scales).ravel(), tol=1e-5, atol=1e-18, restart=30, maxiter=3)
    return step.reshape(model.shape) * scales


def safeguarded_update(delta, step):
    factor = 1.0
    decreasing = step[:, 0] > 0
    if np.any(decreasing):
        factor = min(factor, np.min(0.8 * delta[decreasing, 0] / step[decreasing, 0]))
    increasing = step[:, 0] < 0
    if np.any(increasing):
        factor = min(factor, np.min(-2 * delta[increasing, 0] / step[increasing, 0]))
    return delta - factor * step


def newton(model, delta, verbose=False, deadline=np.inf):
    started = time.process_time()
    for iteration in range(80):
        z, mapped = model.map(delta)
        scales = np.maximum(np.max(np.abs(delta), axis=1)[:, None], np.pi * model.temperature * 1e-20)
        residual = delta - mapped
        residual_norm = np.max(np.abs(residual) / scales)
        if time.process_time() > deadline:
            break
        step = newton_step(model, delta, z, mapped, residual)
        step_norm = np.max(np.abs(step) / scales)
        if verbose:
            print(iteration, 'res', residual_norm, 'step', step_norm, 'd0', delta[:, 0].min(), delta[:, 0].max(), 'calls', model.calls, 'cpu', time.process_time() - started, flush=True)
        if residual_norm < 2e-12 and step_norm < 2e-5:
            delta -= step
            break
        delta = safeguarded_update(delta, step)
    z = model.map(delta)[0]
    return delta, z


def solve(instance, verbose=False, deadline=np.inf):
    started = time.process_time()
    model = Model(instance)
    maximum_omega = np.max(model.omega)
    profile = 0.4 * maximum_omega / (1 + (model.frequencies / maximum_omega) ** 2)
    initial = np.maximum(np.abs(instance['initial_delta']), profile)
    if model.n_freq > 512:
        coarse = CoarseModel(model)
        if verbose:
            print('coarse', coarse.shape, 'build', time.process_time() - started, flush=True)
        delta, unused = newton(coarse, initial[:, coarse.indices].copy(), verbose, deadline - 0.8)
        delta = coarse.expand(delta)
        for iteration in range(8):
            z, mapped = model.map(delta)
            scales = np.maximum(np.max(np.abs(delta), axis=1)[:, None], np.pi * model.temperature * 1e-20)
            residual = delta - mapped
            residual_norm = np.max(np.abs(residual) / scales)
            restricted = residual[:, coarse.indices]
            coarse_step = newton_step(coarse, delta[:, coarse.indices], z[:, coarse.indices], mapped[:, coarse.indices], restricted)
            step = residual + coarse.expand(coarse_step - restricted)
            step_norm = np.max(np.abs(step) / scales)
            if verbose:
                print('fine', iteration, 'res', residual_norm, 'step', step_norm, 'cpu', time.process_time() - started, flush=True)
            if (residual_norm < 2e-10 and step_norm < 2e-6) or time.process_time() > deadline:
                break
            delta = safeguarded_update(delta, step)
        else:
            z = model.map(delta)[0]
        return delta, z
    return newton(model, initial, verbose, deadline)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as archive:
        instance = {key: np.array(archive[key], copy=True) for key in archive.files}
    delta, z = solve(instance, args.verbose, deadline=10.5)
    np.savez(args.output, delta=delta, z=z)


if __name__ == '__main__':
    main()
