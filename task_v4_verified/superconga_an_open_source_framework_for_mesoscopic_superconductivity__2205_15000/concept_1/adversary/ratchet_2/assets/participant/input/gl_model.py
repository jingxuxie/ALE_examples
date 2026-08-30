import json
from pathlib import Path

import numpy as np


class GLModel:
    def __init__(self, case):
        self.case = case
        if case.get("schema_version") != 1:
            raise ValueError("unsupported case schema")
        self.shape = tuple(case["shape"])
        if len(self.shape) != 2 or min(self.shape) < 2:
            raise ValueError("shape must be [ny, nx]")
        self.h = float(case["h"])
        if not np.isfinite(self.h) or self.h <= 0:
            raise ValueError("h must be positive")
        raw_mask = np.asarray(case["mask"])
        if raw_mask.shape != self.shape or not np.isin(raw_mask, [0, 1]).all():
            raise ValueError("mask must be binary and match shape")
        self.mask = raw_mask.astype(bool)
        self.size = int(self.mask.sum())
        if self.size == 0:
            raise ValueError("empty domain")
        self.alpha = self._array("alpha", self.shape)
        self.beta = self._array("beta", self.shape)
        if np.any(self.beta <= 0):
            raise ValueError("beta must be positive")
        ny, nx = self.shape
        self.ax = self._array("ax", (ny, nx - 1))
        self.ay = self._array("ay", (ny - 1, nx))
        self.kx = self._array("kx", (ny, nx - 1))
        self.ky = self._array("ky", (ny - 1, nx))
        if np.any(self.kx <= 0) or np.any(self.ky <= 0):
            raise ValueError("link stiffness must be positive")
        self.kx = self.kx * (self.mask[:, :-1] & self.mask[:, 1:])
        self.ky = self.ky * (self.mask[:-1, :] & self.mask[1:, :])
        self.ux = np.exp(-1j * self.ax)
        self.uy = np.exp(-1j * self.ay)
        self.initial = self._array("initial_real", self.shape) + 1j * self._array(
            "initial_imag", self.shape
        )
        self.initial[~self.mask] = 0

    def _array(self, name, shape):
        array = np.asarray(self.case[name], dtype=np.float64)
        if array.shape != shape or not np.isfinite(array).all():
            raise ValueError("invalid array: " + name)
        return array

    def pack(self, psi):
        field = np.asarray(psi, dtype=np.complex128)
        if field.shape != self.shape:
            raise ValueError("field shape mismatch")
        active = field[self.mask]
        return np.concatenate((active.real, active.imag))

    def unpack(self, vector):
        vector = np.asarray(vector, dtype=np.float64)
        if vector.shape != (2 * self.size,):
            raise ValueError("packed vector shape mismatch")
        field = np.zeros(self.shape, dtype=np.complex128)
        field[self.mask] = vector[:self.size] + 1j * vector[self.size:]
        return field

    def energy_gradient(self, psi):
        field = np.asarray(psi, dtype=np.complex128)
        if field.shape != self.shape:
            raise ValueError("field shape mismatch")
        density = field.real * field.real + field.imag * field.imag
        onsite = self.alpha * density + 0.5 * self.beta * density * density
        energy = self.h**2 * np.sum(onsite[self.mask])
        delta_x = self.ux * field[:, 1:] - field[:, :-1]
        delta_y = self.uy * field[1:, :] - field[:-1, :]
        energy += np.sum(self.kx * (delta_x.real**2 + delta_x.imag**2))
        energy += np.sum(self.ky * (delta_y.real**2 + delta_y.imag**2))
        gradient = 2 * self.h**2 * (self.alpha + self.beta * density) * field
        flow_x = 2 * self.kx * delta_x
        flow_y = 2 * self.ky * delta_y
        gradient[:, :-1] -= flow_x
        gradient[:, 1:] += np.conjugate(self.ux) * flow_x
        gradient[:-1, :] -= flow_y
        gradient[1:, :] += np.conjugate(self.uy) * flow_y
        gradient[~self.mask] = 0
        return float(energy), gradient

    def energy(self, psi):
        return self.energy_gradient(psi)[0]

    def objective(self, vector):
        energy, gradient = self.energy_gradient(self.unpack(vector))
        return energy, self.pack(gradient)

    def gradient_rms(self, psi):
        gradient = self.energy_gradient(psi)[1][self.mask]
        return float(np.sqrt(np.mean(np.abs(gradient)**2) / 2))


def load_case(path):
    with Path(path).open() as stream:
        return GLModel(json.load(stream))
