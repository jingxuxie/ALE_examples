from __future__ import annotations

import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "4"

from pathlib import Path
import sys

import numpy as np
from scipy.fft import rfft2, irfft2


def input_directory():
    configured = os.environ.get("ALE_INPUT_DIR")
    if configured:
        return Path(configured)
    script = Path(__file__).resolve()
    candidates = (
        Path.cwd() / "input",
        script.parent / "input",
        script.parent.parent / "input",
        script.parent.parent.parent / "participant" / "input",
    )
    for candidate in candidates:
        if (candidate / "checkpoints").is_dir():
            return candidate
    raise FileNotFoundError("Set ALE_INPUT_DIR to the supplied input directory")


def time_features(instants):
    instants = np.asarray(instants, dtype=np.float64)
    angles = 2.0 * np.pi * np.arange(1, 11)[:, None] * instants.reshape(1, -1)
    return np.concatenate((np.sin(angles), np.cos(angles), np.ones((1, angles.shape[1]))))


class Geometry:
    def __init__(self, orbits, size, profile):
        source = orbits.shape[0]
        self.size = size
        self.zero_orbit = int(orbits[source // 2, source // 2])
        if profile == "native":
            if size != source:
                raise ValueError("Native profile requires the source lattice size")
            self.origin = source // 2
            self.orbits = orbits
            self.weights = np.ones((size, size), dtype=np.float64)
        elif profile == "transfer":
            if source != 32 or not 33 <= size <= 64:
                raise ValueError("Transfer requires a size-32 source and target size 33 through 64")
            self.origin = (size - 1) // 2
            support_indices = np.arange(source + 1) % source
            support_orbits = orbits[support_indices[:, None], support_indices[None, :]]
            axis_weights = np.ones(source + 1, dtype=np.float64)
            axis_weights[[0, source]] = 0.5
            self.orbits = np.zeros((size, size), dtype=orbits.dtype)
            self.weights = np.zeros((size, size), dtype=np.float64)
            start = self.origin - source // 2
            region = slice(start, start + source + 1)
            self.orbits[region, region] = support_orbits
            self.weights[region, region] = axis_weights[:, None] * axis_weights[None, :]
        else:
            raise ValueError("Unknown profile")
        self.fft_orbits = np.roll(self.orbits, (-self.origin, -self.origin), axis=(0, 1))
        self.fft_weights = np.roll(self.weights, (-self.origin, -self.origin), axis=(0, 1))

    def expand(self, coefficients):
        return coefficients[self.orbits] * self.weights[..., None]

    def fourier(self, coefficients):
        kernel = coefficients[self.fft_orbits] * self.fft_weights[..., None]
        return rfft2(np.moveaxis(kernel, -1, 0), workers=1).real

    def fourier_basis(self, coefficients):
        kernel = coefficients[self.fft_orbits] * self.fft_weights[..., None, None]
        transformed = rfft2(kernel.transpose(2, 3, 0, 1), workers=1).real
        return np.ascontiguousarray(np.moveaxis(transformed, 1, -1).reshape(-1, coefficients.shape[-1]))


class ScalarFlow:
    def __init__(self, request):
        name = str(request["model"])
        if name not in ("single-L32", "single-L64", "range-L32"):
            raise ValueError("Unknown model")
        with np.load(input_directory() / "checkpoints" / (name + ".npz"), allow_pickle=False) as archive:
            params = {}
            for key in archive.files:
                value = archive[key]
                params[key] = value.astype(np.float64) if value.dtype.kind == "f" else value
        self.phi = np.asarray(request["phi"], dtype=np.float64)
        self.batch, self.size, second_size = self.phi.shape
        if self.batch not in (1, 2) or second_size != self.size:
            raise ValueError("Expected phi with shape (B,L,L), B in {1,2}")
        self.volume = self.size * self.size
        self.frequencies = params["phi_freq"]
        self.feature_count = self.frequencies.size + 1
        self.conditional = name == "range-L32"
        self.geometry = Geometry(params["orbits"], self.size, str(request["profile"]))
        self.need_derivative = self.conditional and str(request["operation"]) == "probe"
        couplings = np.broadcast_to(np.asarray(request["lam"], dtype=np.float64), (self.batch,))
        if not self.conditional or np.all(couplings == couplings[0]):
            couplings = couplings[:1]
        feature_matrices = []
        time_matrices = []
        weights = []
        feature_derivatives = []
        time_derivatives = []
        weight_derivatives = []
        for coupling in couplings:
            if self.conditional:
                centers = np.arange(50, dtype=np.float64) / 49.0
                beta = np.logaddexp(0.0, params["width_factor"]) * 49.0
                scores = -beta * ((coupling - 4.0) / 2.0 - centers) ** 2
                gaussian = np.exp(scores - scores.max())
                gaussian /= gaussian.sum()
                feature_matrices.append(params["freq_superpos"] @ gaussian / self.feature_count)
                time_matrices.append(params["time_superpos"] @ gaussian / 21.0)
                reshaped = params["w"].reshape(params["w"].shape[0], 20, 20, 50)
                weights.append(reshaped @ gaussian)
                if self.need_derivative:
                    gaussian_derivative = beta * gaussian * (centers - gaussian @ centers)
                    feature_derivatives.append(params["freq_superpos"] @ gaussian_derivative / self.feature_count)
                    time_derivatives.append(params["time_superpos"] @ gaussian_derivative / 21.0)
                    weight_derivatives.append(reshaped @ gaussian_derivative)
            else:
                feature_matrices.append(params["freq_superpos"] / self.feature_count)
                time_matrices.append(params["time_superpos"] / 21.0)
                weights.append(params["w"])
        self.feature_matrices = np.asarray(feature_matrices)
        self.time_matrices = np.asarray(time_matrices)
        self.weights = np.asarray(weights)
        self.unique_count = len(couplings)
        if self.need_derivative:
            self.feature_derivatives = np.asarray(feature_derivatives)
            self.time_derivatives = np.asarray(time_derivatives)
            self.weight_derivatives = np.asarray(weight_derivatives)
        self.phases = np.empty((self.batch, self.feature_count - 1, self.volume), dtype=np.float64)
        self.features = np.empty((self.batch, self.feature_count, self.volume), dtype=np.float64)

    def embed(self, fields):
        flattened = fields.reshape(self.batch, self.volume)
        np.multiply(flattened[:, None, :], self.frequencies[None, :, None], out=self.phases)
        np.sin(self.phases, out=self.features[:, :-1, :])
        self.features[:, -1, :] = flattened
        embedded = self.feature_matrices @ self.features
        embedded = embedded.reshape(self.batch, 20, self.size, self.size)
        return rfft2(embedded, workers=1)

    def derivative_sums(self):
        np.cos(self.phases, out=self.phases)
        return self.phases.sum(axis=-1) * self.frequencies

    def convolve(self, embedding, kernel):
        contracted = np.einsum("bcij,bcij->bij", embedding, kernel, optimize=False)
        return irfft2(contracted, s=(self.size, self.size), workers=1)

    def trace(self, derivative_sums, center_features):
        return np.sum(derivative_sums * center_features[..., :-1], axis=-1) + self.volume * center_features[..., -1]

    def probe(self, instant):
        temporal = (self.time_matrices @ time_features(instant))[..., 0]
        coefficients = np.einsum("bocd,bd->boc", self.weights, temporal, optimize=False)
        kernels = np.asarray([self.geometry.expand(coefficient) for coefficient in coefficients])
        kernel_fft = np.asarray([self.geometry.fourier(coefficient) for coefficient in coefficients])
        center = coefficients[:, self.geometry.zero_orbit]
        center_features = np.einsum("bc,bcf->bf", center, self.feature_matrices, optimize=False)
        embedding = self.embed(self.phi)
        velocity = self.convolve(embedding, kernel_fft)
        derivative_sums = self.derivative_sums()
        result = {
            "velocity": velocity,
            "divergence": self.trace(derivative_sums, center_features),
            "kernel": np.broadcast_to(kernels, (self.batch, self.size, self.size, 20)),
        }
        if self.need_derivative:
            temporal_derivative = (self.time_derivatives @ time_features(instant))[..., 0]
            coefficient_derivative = (
                np.einsum("bocd,bd->boc", self.weight_derivatives, temporal, optimize=False)
                + np.einsum("bocd,bd->boc", self.weights, temporal_derivative, optimize=False)
            )
            kernel_derivative = np.asarray([
                self.geometry.fourier(coefficient) for coefficient in coefficient_derivative
            ])
            embedding_derivative = rfft2(
                (self.feature_derivatives @ self.features).reshape(self.batch, 20, self.size, self.size),
                workers=1,
            )
            result["dlam_velocity"] = (
                self.convolve(embedding_derivative, kernel_fft)
                + self.convolve(embedding, kernel_derivative)
            )
            center_derivative = coefficient_derivative[:, self.geometry.zero_orbit]
            center_feature_derivative = (
                np.einsum("bc,bcf->bf", center_derivative, self.feature_matrices, optimize=False)
                + np.einsum("bc,bcf->bf", center, self.feature_derivatives, optimize=False)
            )
            result["dlam_divergence"] = self.trace(derivative_sums, center_feature_derivative)
        return result

    def prepare_grid(self, steps):
        temporal = self.time_matrices @ time_features(np.linspace(0.0, 1.0, 2 * steps + 1))
        kernel_shape = (2 * steps + 1, self.unique_count, 20, self.size, self.size // 2 + 1)
        self.grid_kernels = np.empty(kernel_shape, dtype=np.float64)
        self.grid_centers = np.empty((2 * steps + 1, self.unique_count, self.feature_count), dtype=np.float64)
        for row in range(self.unique_count):
            basis = self.geometry.fourier_basis(self.weights[row])
            self.grid_kernels[:, row] = (basis @ temporal[row]).T.reshape(kernel_shape[:1] + kernel_shape[2:])
            center_basis = self.feature_matrices[row].T @ self.weights[row, self.geometry.zero_orbit]
            self.grid_centers[:, row] = (center_basis @ temporal[row]).T

    def grid_rhs(self, fields, grid_index):
        embedding = self.embed(fields)
        velocity = self.convolve(embedding, self.grid_kernels[grid_index])
        divergence = self.trace(self.derivative_sums(), self.grid_centers[grid_index])
        return velocity, divergence

    def transport(self, logp, reverse=False, steps=100):
        self.prepare_grid(steps)
        if self.batch * self.feature_count * self.volume >= 200000:
            from fast_transport import integrate
            return integrate(self, logp, reverse, steps)
        fields = self.phi.copy()
        density_change = np.zeros(self.batch, dtype=np.float64)
        direction = -1 if reverse else 1
        increment = direction / steps
        for step in range(steps):
            start = 2 * steps - 2 * step if reverse else 2 * step
            midpoint = start + direction
            end = start + 2 * direction
            first, first_divergence = self.grid_rhs(fields, start)
            second, second_divergence = self.grid_rhs(fields + 0.5 * increment * first, midpoint)
            third, third_divergence = self.grid_rhs(fields + 0.5 * increment * second, midpoint)
            fourth, fourth_divergence = self.grid_rhs(fields + increment * third, end)
            fields += (increment / 6.0) * (first + 2.0 * second + 2.0 * third + fourth)
            density_change -= (increment / 6.0) * (
                first_divergence + 2.0 * second_divergence + 2.0 * third_divergence + fourth_divergence
            )
        return {"phi": fields, "logp": np.asarray(logp, dtype=np.float64) + density_change}


def solve(request):
    model = ScalarFlow(request)
    operation = str(request["operation"])
    if operation == "probe":
        return model.probe(float(request["t"]))
    if operation not in ("forward", "reverse"):
        raise ValueError("Unknown operation")
    return model.transport(request["logp"], reverse=operation == "reverse")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: solve.py INPUT.npz OUTPUT.npz")
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        request = dict(archive)
    result = solve(request)
    np.savez(sys.argv[2], **result)


if __name__ == "__main__":
    main()
