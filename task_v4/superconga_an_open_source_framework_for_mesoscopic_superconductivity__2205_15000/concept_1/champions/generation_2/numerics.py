import math
import time

import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix


class Budget:
    def __init__(self, seconds=55.0, origin=None):
        self.wall, self.cpu = origin or (time.monotonic(), time.process_time())
        self.seconds = seconds

    def elapsed(self):
        return max(time.monotonic() - self.wall, time.process_time() - self.cpu)

    def remaining(self):
        return self.seconds - self.elapsed()


class Model:
    def __init__(self, case):
        self.shape = tuple(case['shape'])
        self.mask = np.asarray(case['mask'], dtype=bool)
        self.size = int(self.mask.sum())
        self.h = float(case['h'])
        self.alpha = self.h ** 2 * np.asarray(case['alpha'], dtype=float)[self.mask]
        self.beta = self.h ** 2 * np.asarray(case['beta'], dtype=float)[self.mask]
        self.ux = np.exp(-1j * np.asarray(case['ax'], dtype=float))
        self.uy = np.exp(-1j * np.asarray(case['ay'], dtype=float))
        self.kx = np.asarray(case['kx'], dtype=float) * (self.mask[:, :-1] & self.mask[:, 1:])
        self.ky = np.asarray(case['ky'], dtype=float) * (self.mask[:-1] & self.mask[1:])
        initial = np.asarray(case['initial_real']) + 1j * np.asarray(case['initial_imag'])
        self.initial = np.ascontiguousarray(initial[self.mask], dtype=np.complex128)
        indices = np.full(self.shape, -1, dtype=int)
        indices[self.mask] = np.arange(self.size)
        sources = np.concatenate((indices[:, :-1].ravel(), indices[:-1].ravel()))
        targets = np.concatenate((indices[:, 1:].ravel(), indices[1:].ravel()))
        valid = (sources >= 0) & (targets >= 0)
        self.sources, self.targets = sources[valid], targets[valid]
        self.stiffness = np.concatenate((self.kx.ravel(), self.ky.ravel()))[valid]
        self.links = np.concatenate((self.ux.ravel(), self.uy.ravel()))[valid]
        diagonal = self.alpha + np.bincount(self.sources, weights=self.stiffness, minlength=self.size)
        diagonal += np.bincount(self.targets, weights=self.stiffness, minlength=self.size)
        rows = np.concatenate((np.arange(self.size), self.sources, self.targets))
        cols = np.concatenate((np.arange(self.size), self.targets, self.sources))
        values = np.concatenate((diagonal, -self.stiffness * self.links, -self.stiffness * self.links.conj()))
        self.matrix = coo_matrix((values, (rows, cols)), shape=(self.size, self.size)).tocsr()

    def full(self, field):
        result = np.zeros(self.shape, dtype=np.complex128)
        result[self.mask] = field
        return result

    def energy_gradient(self, field):
        density = field.real ** 2 + field.imag ** 2
        linear = self.matrix @ field
        nonlinear = self.beta * density
        energy = dot(field, linear) + 0.5 * np.dot(density, nonlinear)
        return float(energy), 2 * (linear + nonlinear * field)

    def phase(self, field):
        return np.angle(self.links * field[self.targets] * field[self.sources].conj())


class Topology:
    def __init__(self, model):
        rows, cols = np.nonzero(model.mask)
        self.points = cols + 1j * rows
        labels, count = ndimage.label(~model.mask, structure=np.ones((3, 3), dtype=int))
        outside = set(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
        holes = []
        for label in range(1, count + 1):
            if label in outside:
                continue
            rows, cols = np.nonzero(labels == label)
            points = cols + 1j * rows
            holes.append(points[np.argmin(abs(points - points.mean()))])
        self.holes = np.asarray(holes, dtype=np.complex128)


def dot(left, right):
    return float(np.vdot(left, right).real)


def line_step(derivative, linear, quadratic, cubic):
    upper = min(1.0, -derivative / linear) if linear > 0 else 1.0
    for iteration in range(60):
        value = derivative + upper * (linear + upper * (quadratic + upper * cubic))
        if value >= 0:
            break
        upper *= 2
    lower = 0.0
    step = upper
    for iteration in range(30):
        value = derivative + step * (linear + step * (quadratic + step * cubic))
        if abs(value) <= 1e-5 * abs(derivative):
            break
        if value < 0:
            lower = step
        else:
            upper = step
        slope = linear + step * (2 * quadratic + step * 3 * cubic)
        candidate = step - value / slope if slope > 0 else -1
        step = candidate if lower < candidate < upper else (lower + upper) / 2
    return step


def conjugate_relax(model, initial, budget, reserve=2.5, maxiter=2500, tolerance=1e-11):
    field = initial.copy()
    density = field.real ** 2 + field.imag ** 2
    linear = model.matrix @ field
    gradient = 2 * (linear + model.beta * density * field)
    energy = dot(field, linear) + 0.5 * np.dot(model.beta, density ** 2)
    direction = -gradient
    previous_decrease = np.inf
    gradient_square = dot(gradient, gradient)
    for iteration in range(maxiter):
        if iteration % 16 == 0 and (budget.remaining() <= reserve or gradient_square < 2e-14 * model.size):
            break
        matrix_direction = model.matrix @ direction
        parallel = 2 * (field.real * direction.real + field.imag * direction.imag)
        square = direction.real ** 2 + direction.imag ** 2
        derivative = dot(gradient, direction)
        if derivative >= 0 or not np.isfinite(derivative):
            direction = -gradient
            continue
        second = 2 * dot(direction, matrix_direction) + np.dot(model.beta, 2 * density * square + parallel ** 2)
        third = 3 * np.dot(model.beta, parallel * square)
        fourth = 2 * np.dot(model.beta, square ** 2)
        step = line_step(derivative, second, third, fourth)
        for backtrack in range(40):
            change = step * (derivative + step * (0.5 * second + step * (third / 3 + step * fourth / 4)))
            if change <= 1e-4 * step * derivative:
                break
            step *= 0.5
        field += step * direction
        linear += step * matrix_direction
        if iteration % 128 == 127:
            linear = model.matrix @ field
        density = field.real ** 2 + field.imag ** 2
        next_gradient = 2 * (linear + model.beta * density * field)
        next_energy = dot(field, linear) + 0.5 * np.dot(model.beta, density ** 2)
        decrease = energy - next_energy
        gradient_square = dot(next_gradient, next_gradient)
        threshold = tolerance * max(1, abs(energy))
        if 0 <= decrease < threshold and previous_decrease < threshold and gradient_square < 2e-8 * model.size:
            break
        difference = next_gradient - gradient
        curvature = dot(direction, difference)
        coefficient = 0.0
        if curvature > 1e-30:
            coefficient = (dot(difference, next_gradient)
                           - 2 * dot(difference, difference) * dot(direction, next_gradient) / curvature) / curvature
        direction = -next_gradient + coefficient * direction
        if dot(direction, next_gradient) > -0.01 * gradient_square:
            direction = -next_gradient
        gradient, energy = next_gradient, next_energy
        previous_decrease = decrease
    energy, gradient = model.energy_gradient(field)
    return energy, field, math.sqrt(dot(gradient, gradient) / (2 * model.size))
