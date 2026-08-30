"""Builder-owned full-grid operator and isolated-sheet linear calibration."""

import importlib.util
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.sparse.linalg import LinearOperator, eigsh, gmres


ROOT = Path(__file__).resolve().parents[2]
specification = importlib.util.spec_from_file_location("frozen_public_operator", ROOT / "participant" / "input" / "eliashberg.py")
public = importlib.util.module_from_spec(specification)
specification.loader.exec_module(public)


class Model(public.Model):
    def __init__(self, instance):
        super().__init__(instance)
        count = self.n_freq
        position = np.arange(count)
        temperature = np.longdouble(float(instance["temperature"]))
        prefactor = np.longdouble(str(np.pi)) * temperature
        distance = 2 * prefactor * np.arange(2 * count, dtype=np.longdouble)
        normal = np.zeros(self.shape, dtype=np.longdouble)
        for energy, matrix in zip(self.omega, self.weighted_coupling):
            energy = np.longdouble(energy)
            prefix = np.cumsum(energy ** 2 / (energy ** 2 + distance ** 2))
            rows = 2 * prefix[position] + prefix[count - 1 - position] - prefix[count + position] - 1
            normal += matrix.astype(np.longdouble).sum(axis=1)[:, None] * rows[None, :]
        frequencies = prefactor * (2 * position + 1)
        self.normal_z = np.asarray(1 + prefactor * normal / frequencies, dtype=float)

    def map(self, delta):
        radius = np.hypot(self.frequencies, delta)
        correction = -(delta / radius) * (delta / (radius + self.frequencies))
        renormalization = self.normal_z + np.pi * self.temperature * self.convolve(correction, -1) / self.frequencies
        ratio = delta / radius
        pairing = self.convolve(ratio, 1)
        pairing -= 2 * (self.weighted_coulomb @ ratio.sum(axis=1))[:, None]
        return renormalization, np.pi * self.temperature * pairing / renormalization


def leading(instance):
    model = Model(instance)
    inner = np.sqrt(model.weights[:, None] * model.normal_z / model.frequencies[None, :])

    def product(vector):
        delta = vector.reshape(model.shape) / inner
        ratio = delta / model.frequencies
        pairing = model.convolve(ratio, 1)
        pairing -= 2 * (model.weighted_coulomb @ ratio.sum(axis=1))[:, None]
        return (inner * np.pi * model.temperature * pairing / model.normal_z).ravel()

    operator = LinearOperator((inner.size, inner.size), matvec=product, dtype=float)
    values, vectors = eigsh(operator, k=1, which="LA", ncv=20, tol=2e-13,
                           v0=(np.abs(instance["initial_delta"]) * inner).ravel(), maxiter=400)
    mode = vectors[:, 0].reshape(model.shape) / inner
    if np.dot(instance["weights"], mode[:, 0]) < 0:
        mode = -mode
    mode /= np.max(np.abs(mode))
    return float(values[0]), mode


def calibrate(instance, target):
    original = instance["coupling"].copy()
    history = []

    def objective(multiplier):
        instance["coupling"] = original * multiplier
        value, mode = leading(instance)
        history.append({"multiplier": float(multiplier), "eigenvalue": value})
        return value - target

    multiplier = brentq(objective, 0.015, 8, xtol=1e-14, rtol=1e-14)
    instance["coupling"] = original * multiplier
    value, mode = leading(instance)
    return value, mode, multiplier, history


def refine(instance, initial, iterations=32):
    model = Model(instance)
    delta = initial.copy()
    history = []
    recent = []
    for iteration in range(iterations):
        renormalization, mapped = model.map(delta)
        scale = np.maximum(np.max(np.abs(delta), axis=1), np.pi * model.temperature * 1e-14)[:, None]
        residual = (delta - mapped) / scale
        derivative = model.linearize(delta)

        def product(direction):
            return (derivative(direction.reshape(model.shape) * scale) / scale).ravel()

        operator = LinearOperator((delta.size, delta.size), matvec=product, dtype=float)
        step, info = gmres(operator, -residual.ravel(), tol=1e-7, atol=0, restart=50, maxiter=6)
        step = step.reshape(model.shape) * scale
        fraction = 1.0
        decreasing = step[:, 0] < 0
        if np.any(decreasing):
            fraction = min(1, 0.9 * np.min(-delta[decreasing, 0] / step[decreasing, 0]))
        error = float(np.max(np.abs(residual)))
        change = float(np.max(np.abs(fraction * step) / scale))
        history.append({"iteration": iteration, "residual": error, "relative_step": change, "gmres_info": int(info)})
        delta += fraction * step
        if error < 2e-13 and change < 2e-6:
            recent.append(delta.copy())
            if len(recent) >= 3:
                delta = np.mean(recent[-3:], axis=0)
                break
    return delta, model.map(delta)[0], history
