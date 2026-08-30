"""Input-derived exact Fourier fusion and prefix-moment modal preconditioning."""

import json
import sys
import time

import numpy as np
from scipy.fft import dct, dst, idct, idst
from scipy.linalg import svd
from scipy.linalg.blas import dgemm
import v4


def log_phase(phase, **values):
    print(json.dumps(dict(phase=phase, cpu=time.process_time(), **values)), file=sys.stderr, flush=True)


class FusedModel(v4.Model):
    def __init__(self, instance):
        super().__init__(instance)
        self.symbol = None

    def convolve(self, values, parity):
        self.calls += 1
        if self.symbol is None:
            patches = self.shape[0]
            matrices = self.coupling.reshape(len(self.omega), patches * patches)
            combined = dgemm(1.0, matrices.T, self.kernel_fft)
            self.symbol = combined.T.reshape(self.length + 1, patches, patches)
            del self.kernel_fft
            log_phase("exact_symbol_ready", megabytes=self.symbol.nbytes / 1024 ** 2)
        if parity == 1:
            transformed = dct(values, type=2, n=self.length, workers=1)
            symbol = self.symbol[:-1]
        else:
            transformed = dst(values, type=2, n=self.length, workers=1)
            symbol = self.symbol[1:]
        transformed = np.ascontiguousarray(transformed.T)
        mixed = np.einsum("fab,fb->fa", symbol, transformed, optimize=False)
        mixed = np.ascontiguousarray(mixed.T)
        result = idct(mixed, type=2, workers=1) if parity == 1 else idst(mixed, type=2, workers=1)
        return result[:, :self.n_freq]


def frequency_nodes(count, spacing=0.10):
    indices = list(range(min(24, count)))
    while indices[-1] < count - 1:
        indices.append(max(indices[-1] + 1, int((indices[-1] + 0.5) * np.exp(spacing) - 0.5)))
    indices[-1] = count - 1
    boundary = list(range(min(12, count)))
    while boundary[-1] < count // 3:
        boundary.append(max(boundary[-1] + 1, int((boundary[-1] + 0.5) * np.exp(0.16) - 0.5)))
    return np.unique(indices + [count - 1 - offset for offset in boundary])


class PrefixCoarse(v4.Model):
    def __init__(self, full):
        self.temperature = full.temperature
        self.weights = full.weights
        self.omega = full.omega
        self.coulomb = full.coulomb
        self.calls = 0
        self.full_count = full.n_freq
        self.indices = frequency_nodes(full.n_freq)
        self.n_freq = len(self.indices)
        self.shape = (full.shape[0], self.n_freq)
        self.frequencies = full.frequencies[self.indices]
        self.z_normal = full.z_normal[:, self.indices]
        left = self.indices[:-1]
        right = self.indices[1:]
        width = right - left
        self.quadrature = np.zeros(self.n_freq)
        self.quadrature[:-1] += (width + 1) / 2
        self.quadrature[1:] += (width - 1) / 2
        self.quadrature[-1] += 1
        distance = np.arange(2 * full.n_freq + 1)
        frequencies = 2 * np.pi * self.temperature * distance
        kernel = self.omega[:, None] ** 2 / (self.omega[:, None] ** 2 + frequencies[None, :] ** 2)
        prefix = np.cumsum(kernel, axis=1)
        moment = np.cumsum(kernel * distance[None, :], axis=1)

        def signed_prefix(arguments):
            nonnegative = np.maximum(arguments, 0)
            negative = np.maximum(-arguments - 1, 0)
            return np.where(arguments[None, :] >= 0, prefix[:, nonnegative], 1 - prefix[:, negative])

        def signed_moment(arguments):
            return moment[:, np.where(arguments >= 0, arguments, -arguments - 1)]

        row = self.indices[:, None]
        upper = row - left[None, :]
        lower = row - right[None, :]
        zeroth_difference = signed_prefix(upper) - signed_prefix(lower)
        first_difference = row[None, :] * zeroth_difference - (signed_moment(upper) - signed_moment(lower))
        upper = row + right[None, :]
        lower = row + left[None, :]
        zeroth_sum = prefix[:, upper] - prefix[:, lower]
        first_sum = moment[:, upper] - moment[:, lower] - (row[None, :] + 1) * zeroth_sum
        plus = np.zeros((len(self.omega), self.n_freq, self.n_freq))
        minus = np.zeros_like(plus)
        for destination, sign in ((plus, 1), (minus, -1)):
            zeroth = zeroth_difference + sign * zeroth_sum
            first = first_difference + sign * first_sum
            destination[:, :, :-1] += (right[None, None, :] * zeroth - first) / width[None, None, :]
            destination[:, :, 1:] += (first - left[None, None, :] * zeroth) / width[None, None, :]
            destination[:, :, -1] += kernel[:, np.abs(self.indices - (full.n_freq - 1))] + sign * kernel[:, self.indices + full.n_freq]
        strengths = np.linalg.norm(full.coupling.reshape(len(self.omega), -1), axis=1)
        strengths = np.maximum(strengths, np.finfo(float).tiny)
        bank = np.concatenate((plus.reshape(len(self.omega), -1), minus.reshape(len(self.omega), -1)), axis=1)
        bank *= strengths[:, None]
        left_vectors, singular_values, right_vectors = svd(bank, full_matrices=False, overwrite_a=True, check_finite=False)
        rank = max(1, int(np.count_nonzero(singular_values > singular_values[0] * 1e-8)))
        coefficients = left_vectors[:, :rank] * singular_values[None, :rank] / strengths[:, None]
        matrices = dgemm(1.0, full.coupling.reshape(len(self.omega), -1).T, coefficients)
        patches = full.shape[0]
        self.coupling = [np.array(matrix, order="F") for matrix in matrices.T.reshape(rank, patches, patches)]
        size = self.n_freq ** 2
        self.plus = [np.array(matrix, order="F") for matrix in right_vectors[:rank, :size].reshape(rank, self.n_freq, self.n_freq)]
        self.minus = [np.array(matrix, order="F") for matrix in right_vectors[:rank, size:].reshape(rank, self.n_freq, self.n_freq)]
        self.rank = rank
        log_phase("prefix_modal_ready", frequencies=self.n_freq, rank=rank, modes=len(self.omega))

    def convolve(self, values, parity):
        self.calls += 1
        values = np.asarray(values, order="F")
        result = np.zeros(self.shape, order="F")
        for coupling, kernel in zip(self.coupling, self.plus if parity == 1 else self.minus):
            mixed = dgemm(1.0, coupling, values)
            result = dgemm(1.0, mixed, kernel, trans_b=True, beta=1.0, c=result, overwrite_c=1)
        return result

    def expand(self, delta):
        positions = np.arange(self.full_count)
        return np.vstack([np.interp(positions, self.indices, row) for row in delta])


def solve(instance, exact_newton=False):
    if len(instance["omega"]) <= 8:
        return v4.solve(instance, deadline=10.5)
    full = FusedModel(instance)
    coarse = PrefixCoarse(full)
    maximum = float(np.max(full.omega))
    initial = np.maximum(np.abs(instance["initial_delta"][:, coarse.indices]),
                         0.4 * maximum / (1 + (coarse.frequencies / maximum) ** 2))
    delta, unused = v4.newton(coarse, initial, deadline=8.2)
    delta = coarse.expand(delta)
    log_phase("warm_complete", coarse_calls=coarse.calls)
    for iteration in range(16):
        renormalization, mapped = full.map(delta)
        scales = np.maximum(np.max(np.abs(delta), axis=1)[:, None], np.pi * full.temperature * 1e-20)
        residual = delta - mapped
        error = float(np.max(np.abs(residual) / scales))
        if exact_newton and iteration >= 1:
            step = v4.newton_step(full, delta, renormalization, mapped, residual)
        else:
            restricted = residual[:, coarse.indices]
            small_step = v4.newton_step(coarse, delta[:, coarse.indices], renormalization[:, coarse.indices],
                                        mapped[:, coarse.indices], restricted)
            step = residual + coarse.expand(small_step - restricted)
        change = float(np.max(np.abs(step) / scales))
        log_phase("full_correction", iteration=iteration, residual=error, step=change)
        if (error < 2e-11 and change < 2e-6) or time.process_time() > 10.5:
            return delta, renormalization
        delta = v4.safeguarded_update(delta, step)
    return delta, full.map(delta)[0]
