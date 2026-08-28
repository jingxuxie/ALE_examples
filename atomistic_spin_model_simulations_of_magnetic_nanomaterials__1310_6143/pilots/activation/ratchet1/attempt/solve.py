import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eig_banded, eigh_tridiagonal, solve_banded
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import minimize, minimize_scalar
from scipy.signal import find_peaks


def diagnostic(*items):
    if os.environ.get("SPIN_VERBOSE"):
        print(*items, file=sys.stderr, flush=True)


def wrap(angles):
    return (angles + np.pi) % (2 * np.pi) - np.pi


def sphere_step(spins, tangent):
    lengths = np.linalg.norm(tangent, axis=-1, keepdims=True)
    result = np.cos(lengths) * spins + np.sinc(lengths / np.pi) * tangent
    return result / np.linalg.norm(result, axis=-1, keepdims=True)


def sphere_log(start, finish):
    cosine = np.clip(np.sum(start * finish, axis=-1, keepdims=True), -1, 1)
    tangent = finish - cosine * start
    lengths = np.linalg.norm(tangent, axis=-1, keepdims=True)
    return tangent * np.arccos(cosine) / np.maximum(lengths, 1e-15)


def capped_minimize(objective, initial, scale, block=1, maxiter=1000):
    coordinates = initial.copy()
    energy, gradient = objective(coordinates)
    history = []
    for iteration in range(maxiter):
        if np.max(np.abs(gradient)) < 2e-9:
            break
        direction = gradient.copy()
        coefficients = []
        for displacement, change, reciprocal in reversed(history):
            coefficient = reciprocal * np.dot(displacement, direction)
            coefficients.append(coefficient)
            direction -= coefficient * change
        if history:
            displacement, change, reciprocal = history[-1]
            direction *= np.dot(displacement, change) / np.dot(change, change)
        else:
            direction /= scale
        for (displacement, change, reciprocal), coefficient in zip(history, reversed(coefficients)):
            direction += displacement * (coefficient - reciprocal * np.dot(change, direction))
        direction *= -1
        if np.dot(direction, gradient) >= 0:
            direction = -gradient / scale
            history.clear()
        direction /= max(1, np.max(np.linalg.norm(direction.reshape(-1, block), axis=1)) / 0.18)
        slope = np.dot(direction, gradient)
        for backtrack in range(24):
            trial_energy, trial_gradient = objective(coordinates + direction)
            if trial_energy <= energy + 1e-4 * slope + 2e-13:
                break
            direction *= 0.5
            slope *= 0.5
        if backtrack == 23:
            break
        change = trial_gradient - gradient
        curvature = np.dot(direction, change)
        if curvature > 1e-10 * np.linalg.norm(direction) * np.linalg.norm(change):
            history.append((direction.copy(), change, 1 / curvature))
            if len(history) > 10:
                history.pop(0)
        coordinates += direction
        energy, gradient = trial_energy, trial_gradient
    return coordinates


class SpinModel:
    def __init__(self, exchange, anisotropy, field, minimum_a, minimum_b):
        self.exchange = np.asarray(exchange, dtype=float)
        self.anisotropy = np.asarray(anisotropy, dtype=float)
        self.start = np.asarray(minimum_a, dtype=float)
        self.finish = np.asarray(minimum_b, dtype=float)
        self.count = len(self.start)
        self.field = np.broadcast_to(field, self.start.shape).copy()
        self.scale = max(np.max(self.exchange, initial=0), np.max(np.abs(self.anisotropy)), 0.01)

    def energy_gradient(self, spins):
        anis_spins = np.einsum("nij,...nj->...ni", self.anisotropy, spins)
        energy = -np.sum(self.exchange * np.sum(spins[..., :-1, :] * spins[..., 1:, :], axis=-1), axis=-1)
        energy -= np.sum(spins * (anis_spins + self.field), axis=(-2, -1))
        gradient = -2 * anis_spins - self.field
        gradient[..., :-1, :] -= self.exchange[:, None] * spins[..., 1:, :]
        gradient[..., 1:, :] -= self.exchange[:, None] * spins[..., :-1, :]
        return energy, gradient

    def difference(self, spins, reference):
        delta = spins - reference
        onsite = np.einsum("nij,nj->ni", self.anisotropy, spins + reference) + self.field
        bonds = np.sum(delta[:-1] * spins[1:] + reference[:-1] * delta[1:], axis=1)
        return float(-np.sum(self.exchange * bonds) - np.sum(delta * onsite))

    def plane(self):
        vectors = np.concatenate((self.start, self.finish, self.field[:1]))
        _, singular, directions = np.linalg.svd(vectors, full_matrices=False)
        if singular[-1] > 2e-9 * singular[0]:
            return None
        normal = directions[-1]
        mixing = np.einsum("nij,j->ni", self.anisotropy, normal) @ directions[:2].T
        if np.max(np.abs(mixing)) > 1e-10 * self.scale:
            return None
        return directions[:2].T

    def basis(self, spins):
        axes = np.eye(3)[np.argmin(np.abs(spins), axis=1)]
        first = np.cross(spins, axes)
        first /= np.linalg.norm(first, axis=1)[:, None]
        return np.stack((first, np.cross(spins, first)), axis=-1)

    def derivatives(self, spins):
        energy, gradient = self.energy_gradient(spins)
        basis = self.basis(spins)
        tangent = np.einsum("nik,ni->nk", basis, gradient)
        multipliers = np.sum(spins * gradient, axis=1)
        diagonal = -2 * np.einsum("nik,nij,njl->nkl", basis, self.anisotropy, basis)
        diagonal -= multipliers[:, None, None] * np.eye(2)
        offdiagonal = -self.exchange[:, None, None] * np.einsum("nik,nil->nkl", basis[:-1], basis[1:])
        return float(energy), tangent.ravel(), block_band(diagonal, offdiagonal), basis

    def window(self, low, high, outside=None):
        if outside is None:
            outside = self.start
        field = self.field[low:high].copy()
        if low:
            field[0] += self.exchange[low - 1] * outside[low - 1]
        if high < self.count:
            field[-1] += self.exchange[high - 1] * outside[high]
        return SpinModel(self.exchange[low:high - 1], self.anisotropy[low:high], field,
                         self.start[low:high], self.finish[low:high])

    def relax(self, initial, maxiter=700, safe=False):
        def objective(coordinates):
            coordinates = coordinates.reshape(-1, 3)
            lengths = np.linalg.norm(coordinates, axis=1, keepdims=True)
            spins = coordinates / lengths
            _, gradient = self.energy_gradient(spins)
            energy = self.difference(spins, initial)
            gradient -= np.sum(gradient * spins, axis=1, keepdims=True) * spins
            energy += 0.5 * self.scale * np.sum((lengths - 1)**2)
            gradient = gradient / lengths + self.scale * (lengths - 1) * spins
            return energy, gradient.ravel()

        if safe:
            coordinates = capped_minimize(objective, initial.ravel(), self.scale, block=3, maxiter=maxiter)
        else:
            coordinates = minimize(objective, initial.ravel(), jac=True, method="L-BFGS-B",
                                   options={"gtol": 2e-9, "ftol": 2e-15, "maxiter": maxiter, "maxls": 30, "maxcor": 12}).x
        spins = coordinates.reshape(-1, 3)
        spins /= np.linalg.norm(spins, axis=1, keepdims=True)
        for iteration in range(4):
            _, gradient, band, basis = self.derivatives(spins)
            if np.max(np.abs(gradient)) < 2e-10:
                break
            try:
                step = -band_solve(band, gradient)
            except np.linalg.LinAlgError:
                break
            if np.max(np.abs(step)) > 0.03 or np.dot(step, gradient) >= 0:
                break
            spins = sphere_step(spins, np.einsum("nik,nk->ni", basis, step.reshape(-1, 2)))
        return spins


def block_band(diagonal, offdiagonal):
    count = len(diagonal)
    band = np.zeros((4, 2 * count))
    band[0, 0::2] = diagonal[:, 0, 0]
    band[0, 1::2] = diagonal[:, 1, 1]
    band[1, 0::2] = diagonal[:, 1, 0]
    band[1, 1:-2:2] = offdiagonal[:, 1, 0]
    band[2, 0:-2:2] = offdiagonal[:, 0, 0]
    band[2, 1:-2:2] = offdiagonal[:, 1, 1]
    band[3, 0:-2:2] = offdiagonal[:, 0, 1]
    return band


def band_solve(band, gradient, shift=0):
    width = len(band) - 1
    symmetric = np.zeros((2 * width + 1, band.shape[1]))
    symmetric[width:] = band
    symmetric[width] += shift
    for offset in range(1, width + 1):
        symmetric[width - offset, offset:] = band[offset, :-offset]
    return solve_banded((width, width), symmetric, gradient, check_finite=False)


def band_modes(band):
    values = eig_banded(band, lower=True, eigvals_only=True, select="i", select_range=(0, 1), check_finite=False)
    displacement = max(1e-9, min(1e-6, 1e-4 * (values[1] - values[0])))
    vector = np.random.default_rng(572).normal(size=band.shape[1])
    for iteration in range(4):
        vector = band_solve(band, vector, displacement - values[0])
        vector /= np.linalg.norm(vector)
    return values, vector


def follow_full(model, initial, deadline, maxiter=140):
    spins = initial.copy()
    best = None
    for iteration in range(maxiter):
        if iteration % 5 == 0 and time.monotonic() > deadline:
            break
        _, gradient, band, basis = model.derivatives(spins)
        values, unstable = band_modes(band)
        residual = np.max(np.linalg.norm(gradient.reshape(-1, 2), axis=1))
        index_one = values[0] < -1e-8 and values[1] > 1e-8
        if index_one and (best is None or residual < best[0]):
            best = residual, spins.copy()
        if index_one and residual < 2e-10:
            return spins
        if residual < 1e-10 and values[0] > 0:
            return None
        floor = 0.025
        shift = 0.0 if index_one else max(0.0, floor - values[0])
        step = -band_solve(band, gradient, shift)
        step += (1 / (values[0] + shift) + 1 / max(abs(values[0]), floor)) * np.dot(unstable, gradient) * unstable
        tangent = np.einsum("nik,nk->ni", basis, step.reshape(-1, 2))
        tangent /= max(1, np.max(np.linalg.norm(tangent, axis=1)) / 0.25)
        if index_one and residual < 0.06:
            for backtrack in range(10):
                trial = sphere_step(spins, tangent)
                _, trial_gradient = model.energy_gradient(trial)
                trial_gradient -= np.sum(trial_gradient * trial, axis=1, keepdims=True) * trial
                if np.linalg.norm(trial_gradient) < np.linalg.norm(gradient):
                    break
                tangent *= 0.5
        spins = sphere_step(spins, tangent)
    return best[1] if best is not None and best[0] < 3e-6 else None


def polish_full(model, initial):
    spins = initial.copy()
    for iteration in range(16):
        _, gradient, band, basis = model.derivatives(spins)
        if np.max(np.abs(gradient)) < 1e-11:
            break
        step = -band_solve(band, gradient)
        tangent = np.einsum("nik,nk->ni", basis, step.reshape(-1, 2))
        tangent /= max(1, np.max(np.linalg.norm(tangent, axis=1)) / 0.15)
        for backtrack in range(10):
            trial = sphere_step(spins, tangent)
            _, trial_gradient = model.energy_gradient(trial)
            trial_gradient -= np.sum(trial_gradient * trial, axis=1, keepdims=True) * trial
            if np.linalg.norm(trial_gradient) < np.linalg.norm(gradient):
                break
            tangent *= 0.5
        spins = sphere_step(spins, tangent)
    return spins


def basin_full(model, initial, halfspan, deadline):
    spins = initial.copy()
    if model.count <= 2 * halfspan:
        spins = model.relax(spins, maxiter=2500, safe=True)
    else:
        for iteration in range(8 * model.count // halfspan + 40):
            _, gradient = model.energy_gradient(spins)
            gradient -= np.sum(gradient * spins, axis=1, keepdims=True) * spins
            residual = np.linalg.norm(gradient, axis=1)
            if np.max(residual) < 2e-7 or time.monotonic() > deadline:
                break
            center = int(np.argmax(residual))
            low, high = max(0, center - halfspan), min(model.count, center + halfspan + 1)
            local = model.window(low, high, spins)
            spins[low:high] = local.relax(spins[low:high], safe=True)
    distances = [np.max(np.linalg.norm(spins - target, axis=1)) for target in (model.start, model.finish)]
    return int(np.argmin(distances)) if min(distances) < 2e-3 else -1


def redistribute_full(path):
    logs = sphere_log(path[:-1], path[1:])
    segment = np.linalg.norm(logs, axis=(1, 2))
    distance = np.r_[0, np.cumsum(segment)]
    target = np.linspace(0, distance[-1], len(path))
    indices = np.clip(np.searchsorted(distance, target, side="right") - 1, 0, len(path) - 2)
    weight = (target - distance[indices]) / np.maximum(segment[indices], 1e-15)
    result = sphere_step(path[indices], weight[:, None, None] * logs[indices])
    result[0], result[-1] = path[0], path[-1]
    return result


def string_full(model, final, deadline):
    logarithm = sphere_log(model.start, final)
    fractions = np.linspace(0, 1, 33)[:, None, None]
    path = sphere_step(model.start[None], fractions * logarithm[None])
    normal = np.cross(model.start, final)
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-15)
    path = sphere_step(path, 0.45 * np.sin(np.pi * fractions) * normal[None])
    for iteration in range(1000):
        _, gradient = model.energy_gradient(path)
        gradient -= np.sum(gradient * path, axis=-1, keepdims=True) * path
        path[1:-1] = sphere_step(path[1:-1], -0.3 / model.scale * gradient[1:-1])
        path = redistribute_full(path)
        if iteration % 100 == 99:
            energies, _ = model.energy_gradient(path)
            peak = int(np.argmax(energies))
            if peak == 0 or peak == len(path) - 1:
                return None
            candidate = follow_full(model, path[peak], deadline, maxiter=70)
            if candidate is not None:
                return candidate
            if time.monotonic() > deadline:
                return None
    return None


def search_full(model, deadline):
    _, _, directions = np.linalg.svd(np.concatenate((model.start, model.finish, model.field[:1])), full_matrices=False)
    proxy = PlanarModel(model, directions[:2].T)
    sites, halfspan, widths = locations(proxy)
    halfspan = min(256, halfspan)
    candidates = []

    def add_candidate(candidate, low=0, high=None):
        if candidate is None:
            return False
        if high is None:
            high = model.count
        full = model.start.copy()
        full[low:high] = candidate
        full = polish_full(model, full)
        _, gradient, band, basis = model.derivatives(full)
        if np.max(np.abs(gradient)) > 3e-6:
            return False
        if any(np.max(np.linalg.norm(full - other[1], axis=1)) < 1e-4 for other in candidates):
            return True
        values, vector = band_modes(band)
        if values[0] >= -1e-8 or values[1] <= 1e-8:
            return False
        barrier = model.difference(full, model.start)
        if barrier > 0:
            unstable = np.einsum("nik,nk->ni", basis, vector.reshape(-1, 2))
            candidates.append((barrier, full, unstable))
            diagnostic("nonplanar candidate", low, high, "barrier", barrier)
            return True
        return False

    search_deadline = min(deadline - 8, time.monotonic() + 45)
    if model.count <= max(32, 5 * np.max(widths)):
        logarithm = sphere_log(model.start, model.finish)
        objective = lambda fraction: -float(model.energy_gradient(sphere_step(model.start, fraction * logarithm))[0])
        peak = minimize_scalar(objective, bounds=(0.05, 0.95), method="bounded").x
        add_candidate(follow_full(model, sphere_step(model.start, peak * logarithm), search_deadline))
    for center, direction in sites:
        if time.monotonic() > search_deadline:
            break
        low, high = max(0, center - halfspan), min(model.count, center + halfspan + 1)
        local = model.window(low, high)
        width = max(0.65, widths[center] * 0.85)
        distance = np.abs(np.arange(low, high) - center)
        logarithm = sphere_log(local.start, local.finish)
        found = False
        for radius in (1.5, 2.5, 0.6, 4.0, 6.0):
            fraction = 2 / np.pi * np.arctan(np.exp(np.clip(radius - distance / width, -40, 40)))
            candidate = follow_full(local, sphere_step(local.start, fraction[:, None] * logarithm), search_deadline)
            if add_candidate(candidate, low, high):
                found = True
                break
        if not found and time.monotonic() < search_deadline:
            normal = np.cross(local.start, local.finish)
            normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-15)
            for sign in (-1, 1):
                fraction = 2 / np.pi * np.arctan(np.exp(np.clip(1.8 - distance / width, -40, 40)))
                seed = sphere_step(local.start, fraction[:, None] * logarithm)
                seed = sphere_step(seed, sign * np.sin(np.pi * fraction[:, None]) * normal)
                candidate = follow_full(local, seed, search_deadline)
                if add_candidate(candidate, low, high):
                    found = True
        if not found and time.monotonic() < search_deadline:
            final = local.relax(local.finish)
            if np.max(np.linalg.norm(final - local.start, axis=1)) > 0.3:
                add_candidate(string_full(local, final, search_deadline), low, high)
    candidates.sort(key=lambda item: item[0])
    for barrier, candidate, unstable in candidates:
        amplitude = 0.10 / np.max(np.linalg.norm(unstable, axis=1))
        endpoints = [basin_full(model, sphere_step(candidate, sign * amplitude * unstable), halfspan, deadline)
                     for sign in (-1, 1)]
        diagnostic("nonplanar basins", barrier, endpoints)
        if sorted(endpoints) == [0, 1]:
            return candidate
        if time.monotonic() > deadline:
            break
    if model.count <= 256 and time.monotonic() < deadline:
        candidate = string_full(model, model.finish, deadline)
        if add_candidate(candidate):
            for barrier, candidate, unstable in candidates:
                amplitude = 0.10 / np.max(np.linalg.norm(unstable, axis=1))
                endpoints = [basin_full(model, sphere_step(candidate, sign * amplitude * unstable), halfspan, deadline)
                             for sign in (-1, 1)]
                if sorted(endpoints) == [0, 1]:
                    return candidate
    return None


class PlanarModel:
    def __init__(self, model, plane):
        self.model = model
        self.plane = plane
        self.exchange = model.exchange
        self.anisotropy = np.einsum("ik,nij,jl->nkl", plane, model.anisotropy, plane)
        self.field = model.field @ plane
        self.start = self.angles(model.start)
        self.finish = self.start + wrap(self.angles(model.finish) - self.start)
        self.count = model.count
        self.scale = model.scale
        self.coupling = self.anisotropy[:, 0, 0] - self.anisotropy[:, 1, 1]
        self.mixed = self.anisotropy[:, 0, 1]

    def angles(self, spins):
        projected = spins @ self.plane
        return np.unwrap(np.arctan2(projected[:, 1], projected[:, 0]))

    def spins(self, angles):
        return np.stack((np.cos(angles), np.sin(angles)), axis=-1) @ self.plane.T

    def energy_gradient(self, angles):
        cosine, sine = np.cos(angles), np.sin(angles)
        difference = angles[..., :-1] - angles[..., 1:]
        energy = -np.sum(self.exchange * np.cos(difference), axis=-1)
        energy -= np.sum(self.anisotropy[:, 0, 0] * cosine**2 + self.anisotropy[:, 1, 1] * sine**2
                         + 2 * self.mixed * sine * cosine + self.field[:, 0] * cosine + self.field[:, 1] * sine, axis=-1)
        gradient = 2 * self.coupling * sine * cosine - 2 * self.mixed * (cosine**2 - sine**2)
        gradient += self.field[:, 0] * sine - self.field[:, 1] * cosine
        bond_gradient = self.exchange * np.sin(difference)
        gradient[..., :-1] += bond_gradient
        gradient[..., 1:] -= bond_gradient
        return energy, gradient

    def hessian(self, angles):
        diagonal = 2 * self.coupling * np.cos(2 * angles) + 4 * self.mixed * np.sin(2 * angles)
        diagonal += self.field[:, 0] * np.cos(angles) + self.field[:, 1] * np.sin(angles)
        offdiagonal = -self.exchange * np.cos(angles[:-1] - angles[1:])
        diagonal[:-1] -= offdiagonal
        diagonal[1:] -= offdiagonal
        return diagonal, offdiagonal

    def window(self, low, high, outside=None):
        cartesian = None if outside is None else self.spins(outside)
        return PlanarModel(self.model.window(low, high, cartesian), self.plane)

    def relax(self, initial, maxiter=700, safe=False):
        reference_energy = float(self.energy_gradient(initial)[0])

        def objective(angles):
            energy, gradient = self.energy_gradient(angles)
            return float(energy) - reference_energy, gradient

        if safe:
            angles = capped_minimize(objective, initial, self.scale, maxiter=maxiter)
        else:
            angles = minimize(objective, initial, jac=True, method="L-BFGS-B",
                              options={"gtol": 2e-9, "ftol": 2e-15, "maxiter": maxiter, "maxls": 30, "maxcor": 12}).x
        for iteration in range(4):
            _, gradient = self.energy_gradient(angles)
            if np.max(np.abs(gradient)) < 2e-10:
                break
            diagonal, offdiagonal = self.hessian(angles)
            try:
                step = tri_solve(diagonal, offdiagonal, -gradient)
            except np.linalg.LinAlgError:
                break
            if np.max(np.abs(step)) > 0.03 or np.dot(step, gradient) >= 0:
                break
            angles += step
        return angles


def tri_solve(diagonal, offdiagonal, rhs, shift=0):
    if len(diagonal) == 1:
        return rhs / (diagonal + shift)
    band = np.zeros((3, len(diagonal)))
    band[1] = diagonal + shift
    band[0, 1:] = offdiagonal
    band[2, :-1] = offdiagonal
    return solve_banded((1, 1), band, rhs, check_finite=False)


def low_modes(diagonal, offdiagonal, number=2):
    if len(diagonal) == 1:
        return diagonal.copy(), np.ones((1, 1))
    return eigh_tridiagonal(diagonal, offdiagonal, select="i", select_range=(0, min(number, len(diagonal)) - 1),
                            check_finite=False, tol=1e-12)


def follow_planar(model, initial, deadline, maxiter=130):
    angles = initial.copy()
    best = None
    for iteration in range(maxiter):
        if iteration % 10 == 0 and time.monotonic() > deadline:
            break
        _, gradient = model.energy_gradient(angles)
        diagonal, offdiagonal = model.hessian(angles)
        values, vectors = low_modes(diagonal, offdiagonal)
        residual = np.max(np.abs(gradient))
        index_one = values[0] < -1e-8 and (len(values) == 1 or values[1] > 1e-8)
        if index_one and (best is None or residual < best[0]):
            best = residual, angles.copy()
        if index_one and residual < 2e-10:
            return angles
        if residual < 1e-10 and values[0] > 0:
            return None
        floor = 0.025
        shift = 0.0 if index_one else max(0.0, floor - values[0])
        step = -tri_solve(diagonal, offdiagonal, gradient, shift)
        unstable = vectors[:, 0]
        step += (1 / (values[0] + shift) + 1 / max(abs(values[0]), floor)) * np.dot(unstable, gradient) * unstable
        step /= max(np.max(np.abs(step)) / 0.25, 1)
        if index_one and residual < 0.06:
            for backtrack in range(10):
                if np.linalg.norm(model.energy_gradient(angles + step)[1]) < np.linalg.norm(gradient):
                    break
                step *= 0.5
        angles += step
    return best[1] if best is not None and best[0] < 3e-6 else None


def polish_planar(model, initial):
    angles = initial.copy()
    for iteration in range(14):
        _, gradient = model.energy_gradient(angles)
        if np.max(np.abs(gradient)) < 1e-11:
            break
        diagonal, offdiagonal = model.hessian(angles)
        step = -tri_solve(diagonal, offdiagonal, gradient)
        step /= max(1, np.max(np.abs(step)) / 0.15)
        for backtrack in range(10):
            if np.linalg.norm(model.energy_gradient(angles + step)[1]) < np.linalg.norm(gradient):
                break
            step *= 0.5
        angles += step
    return angles


def redistribute(path):
    segment = np.linalg.norm(np.diff(path, axis=0), axis=1)
    distance = np.r_[0, np.cumsum(segment)]
    target = np.linspace(0, distance[-1], len(path))
    indices = np.clip(np.searchsorted(distance, target, side="right") - 1, 0, len(path) - 2)
    weight = (target - distance[indices]) / np.maximum(segment[indices], 1e-15)
    return path[indices] + weight[:, None] * (path[indices + 1] - path[indices])


def string_planar(model, final, deadline, initial_path=None):
    path = np.linspace(model.start, final, 33) if initial_path is None else initial_path.copy()
    timestep = 0.35 / model.scale
    for iteration in range(900):
        _, gradient = model.energy_gradient(path)
        path[1:-1] -= timestep * gradient[1:-1]
        path = redistribute(path)
        if iteration % 100 == 99:
            energies, _ = model.energy_gradient(path)
            peak = int(np.argmax(energies))
            if peak == 0 or peak == len(path) - 1:
                return None
            candidate = follow_planar(model, path[peak], deadline, maxiter=70)
            if candidate is not None:
                return candidate
            if time.monotonic() > deadline:
                return None
    return None


def length_scale(model):
    diagonal, offdiagonal = model.hessian(model.start)
    onsite = diagonal.copy()
    onsite[:-1] += offdiagonal
    onsite[1:] += offdiagonal
    stiffness = np.maximum(onsite, 0.02)
    exchange = np.zeros(model.count)
    if model.count > 1:
        exchange[:-1] += model.exchange
        exchange[1:] += model.exchange
        exchange[1:-1] *= 0.5
    return np.sqrt(exchange / stiffness), stiffness


def locations(model):
    widths, stiffness = length_scale(model)
    halfspan = min(model.count, max(32, int(16 * np.max(widths))))
    sites = [(0, 1), (model.count - 1, -1)]
    if model.count < 12:
        return sites, halfspan, widths
    density = np.sqrt(np.maximum(stiffness, 0.01) * np.maximum(widths**2 * stiffness, 0.01))
    smooth = gaussian_filter1d(density, max(1, float(np.median(widths))))
    peaks, _ = find_peaks(-smooth, distance=max(3, int(3 * np.median(widths))), prominence=0.002 * np.max(smooth))
    interior = sorted(peaks, key=lambda site: smooth[site])[:6]
    jumps = np.abs(np.diff(density))
    for bond in np.argsort(jumps)[::-1][:8]:
        if jumps[bond] < 0.03 * np.max(density):
            break
        site = int(bond if density[bond] < density[bond + 1] else bond + 1)
        if min(site, model.count - 1 - site) > max(4, 2 * widths[site]) and all(abs(site - other) > 3 * widths[site] for other in interior):
            interior.append(site)
    sites.extend((int(site), 0) for site in interior[:8])
    return sites, halfspan, widths


def planar_spectrum(model, angles):
    diagonal, offdiagonal = model.hessian(angles)
    parallel = diagonal if model.count == 1 else eigh_tridiagonal(diagonal, offdiagonal, eigvals_only=True, lapack_driver="sterf", check_finite=False)
    spins = model.spins(angles)
    _, gradient = model.model.energy_gradient(spins)
    normal = np.cross(model.plane[:, 0], model.plane[:, 1])
    transverse = -2 * np.einsum("i,nij,j->n", normal, model.model.anisotropy, normal)
    transverse -= np.sum(spins * gradient, axis=1)
    perpendicular = transverse if model.count == 1 else eigh_tridiagonal(transverse, -model.exchange, eigvals_only=True, lapack_driver="sterf", check_finite=False)
    return np.sort(np.r_[parallel, perpendicular])


def planar_inertia(model, angles):
    diagonal, offdiagonal = model.hessian(angles)
    values, vectors = low_modes(diagonal, offdiagonal)
    if values[0] >= -1e-8 or (len(values) > 1 and values[1] <= 1e-8):
        return None
    spins = model.spins(angles)
    _, gradient = model.model.energy_gradient(spins)
    normal = np.cross(model.plane[:, 0], model.plane[:, 1])
    transverse = -2 * np.einsum("i,nij,j->n", normal, model.model.anisotropy, normal) - np.sum(spins * gradient, axis=1)
    value = low_modes(transverse, -model.exchange, number=1)[0][0]
    return vectors[:, 0] if value > 1e-8 else None


def basin_planar(model, initial, halfspan, deadline):
    angles = initial.copy()
    if model.count <= 2 * halfspan:
        angles = model.relax(angles, maxiter=2500, safe=True)
    else:
        for iteration in range(8 * model.count // halfspan + 40):
            _, gradient = model.energy_gradient(angles)
            if np.max(np.abs(gradient)) < 2e-7 or time.monotonic() > deadline:
                break
            center = int(np.argmax(np.abs(gradient)))
            low, high = max(0, center - halfspan), min(model.count, center + halfspan + 1)
            local = model.window(low, high, angles)
            angles[low:high] = local.relax(angles[low:high], safe=True)
    distances = [np.max(np.abs(wrap(angles - target))) for target in (model.start, model.finish)]
    return int(np.argmin(distances)) if min(distances) < 2e-3 else -1


def search_planar(model, deadline):
    sites, halfspan, widths = locations(model)
    candidates = []

    def add_candidate(candidate, low=0, high=None):
        if candidate is None:
            return False
        if high is None:
            high = model.count
        full = model.start.copy()
        full[low:high] = candidate
        full = polish_planar(model, full)
        if np.max(np.abs(model.energy_gradient(full)[1])) > 3e-6:
            return False
        if any(np.max(np.abs(wrap(full - other[1]))) < 1e-4 for other in candidates):
            return True
        unstable = planar_inertia(model, full)
        if unstable is None:
            return False
        barrier = model.model.difference(model.spins(full), model.model.start)
        if barrier > 0:
            candidates.append((barrier, full, unstable))
            diagnostic("planar candidate", low, high, "barrier", barrier)
            return True
        return False

    search_deadline = min(deadline - 5, time.monotonic() + 35)
    if model.count <= max(32, 5 * np.max(widths)):
        objective = lambda fraction: -float(model.energy_gradient(model.start + fraction * (model.finish - model.start))[0])
        peak = minimize_scalar(objective, bounds=(0.05, 0.95), method="bounded").x
        add_candidate(follow_planar(model, model.start + peak * (model.finish - model.start), search_deadline))
    for center, direction in sites:
        if time.monotonic() > search_deadline:
            break
        low, high = max(0, center - halfspan), min(model.count, center + halfspan + 1)
        local = model.window(low, high)
        width = max(0.65, widths[center] * 0.85)
        distance = np.abs(np.arange(low, high) - center)
        found = False
        for radius in (1.5, 2.5, 0.6, 4.0, 6.0):
            fraction = 2 / np.pi * np.arctan(np.exp(np.clip(radius - distance / width, -40, 40)))
            seed = local.start + fraction * (local.finish - local.start)
            candidate = follow_planar(local, seed, search_deadline)
            if add_candidate(candidate, low, high):
                found = True
                break
        if not found and time.monotonic() < search_deadline:
            final = local.relax(local.finish)
            if np.max(np.abs(wrap(final - local.start))) > 0.3:
                add_candidate(string_planar(local, final, search_deadline), low, high)
    candidates.sort(key=lambda item: item[0])
    for barrier, candidate, unstable in candidates:
        amplitude = 0.10 / np.max(np.abs(unstable))
        endpoints = [basin_planar(model, candidate + sign * amplitude * unstable, halfspan, deadline)
                     for sign in (-1, 1)]
        diagnostic("planar basins", barrier, endpoints)
        if sorted(endpoints) == [0, 1]:
            return candidate
        if time.monotonic() > deadline:
            break
    final = model.finish
    if model.count <= 256 and time.monotonic() < deadline:
        candidate = string_planar(model, final, deadline)
        if add_candidate(candidate):
            for barrier, candidate, unstable in candidates:
                amplitude = 0.10 / np.max(np.abs(unstable))
                endpoints = [basin_planar(model, candidate + sign * amplitude * unstable, halfspan, deadline)
                             for sign in (-1, 1)]
                if sorted(endpoints) == [0, 1]:
                    return candidate
    return None


def solve(case):
    started = time.monotonic()
    deadline = started + min(float(case.get("time_limit_seconds", 90)), 90) - 9
    model = SpinModel(case["exchange_meV"], case["anisotropy_meV"], case["field_meV"], case["minimum_a"], case["minimum_b"])
    plane = model.plane()
    if plane is not None:
        planar = PlanarModel(model, plane)
        angles = search_planar(planar, deadline)
        saddle = None if angles is None else planar.spins(angles)
    else:
        saddle = None
    if saddle is None:
        saddle = search_full(model, deadline)
        if saddle is None:
            raise RuntimeError("No transition state converged")
        minimum_values = eig_banded(model.derivatives(model.start)[2], lower=True, eigvals_only=True, check_finite=False)
        saddle_values = eig_banded(model.derivatives(saddle)[2], lower=True, eigvals_only=True, check_finite=False)
    else:
        minimum_values = planar_spectrum(planar, planar.start)
        saddle_values = planar_spectrum(planar, angles)
    if minimum_values[0] <= 0 or saddle_values[0] >= 0 or saddle_values[1] <= 0:
        raise RuntimeError("The transition has incorrect Hessian inertia")
    log_factor = 0.5 * (np.sum(np.log(minimum_values)) - np.sum(np.log(saddle_values[1:])))
    diagnostic("completed", model.count, "spins in", time.monotonic() - started, "seconds")
    return {"saddle": saddle, "barrier_meV": model.difference(saddle, model.start),
            "eigenvalues_min_meV": minimum_values, "eigenvalues_saddle_meV": saddle_values,
            "log_omega0": float(log_factor)}


def main():
    case = json.loads(Path(sys.argv[1]).read_text())
    result = solve(case)
    with open(sys.argv[2], "wb") as output:
        np.savez_compressed(output, **result)


if __name__ == "__main__":
    main()
