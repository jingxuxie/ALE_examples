import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh, eigh_tridiagonal
from scipy.optimize import minimize


class SpinModel:
    def __init__(self, case):
        self.exchange = np.asarray(case["exchange_meV"], dtype=float)
        self.anisotropy = np.asarray(case["anisotropy_meV"], dtype=float)
        self.field = np.asarray(case["field_meV"], dtype=float)
        self.minimum_a = np.asarray(case["minimum_a"], dtype=float)
        self.minimum_b = np.asarray(case["minimum_b"], dtype=float)
        self.count = len(self.minimum_a)
        self.scale = max(np.max(self.exchange), np.max(np.abs(self.anisotropy)), 0.01)

    def energy_gradient(self, spins):
        anis_spins = np.einsum("nij,...nj->...ni", self.anisotropy, spins)
        energy = -np.sum(self.exchange * np.sum(spins[..., :-1, :] * spins[..., 1:, :], axis=-1), axis=-1)
        energy -= np.sum(spins * anis_spins + spins * self.field, axis=(-2, -1))
        gradient = -2 * anis_spins - self.field
        gradient[..., :-1, :] -= self.exchange[:, None] * spins[..., 1:, :]
        gradient[..., 1:, :] -= self.exchange[:, None] * spins[..., :-1, :]
        return energy, gradient

    def tangent_basis(self, spins):
        axes = np.eye(3)[np.argmin(np.abs(spins), axis=1)]
        first = np.cross(spins, axes)
        first /= np.linalg.norm(first, axis=1)[:, None]
        second = np.cross(spins, first)
        return np.stack((first, second), axis=-1)

    def derivatives(self, spins):
        energy, gradient = self.energy_gradient(spins)
        basis = self.tangent_basis(spins)
        tangent = np.einsum("nik,ni->nk", basis, gradient)
        multipliers = np.sum(spins * gradient, axis=1)
        diagonal = -2 * np.einsum("nik,nij,njl->nkl", basis, self.anisotropy, basis)
        diagonal -= multipliers[:, None, None] * np.eye(2)
        offdiagonal = -self.exchange[:, None, None] * np.einsum("nik,nil->nkl", basis[:-1], basis[1:])
        hessian = np.zeros((2 * self.count, 2 * self.count))
        for site in range(self.count):
            hessian[2 * site:2 * site + 2, 2 * site:2 * site + 2] = diagonal[site]
        for bond in range(self.count - 1):
            hessian[2 * bond:2 * bond + 2, 2 * bond + 2:2 * bond + 4] = offdiagonal[bond]
            hessian[2 * bond + 2:2 * bond + 4, 2 * bond:2 * bond + 2] = offdiagonal[bond].T
        return float(energy), tangent.ravel(), hessian, basis

    def plane(self):
        vectors = np.concatenate((self.minimum_a, self.minimum_b, self.field[None, :]))
        _, singular, directions = np.linalg.svd(vectors, full_matrices=False)
        normal = directions[-1]
        if singular[-1] > 1e-8 * singular[0]:
            return None
        if np.max(np.abs(np.einsum("nij,j->ni", self.anisotropy, normal) @ directions[:2].T)) > 1e-9 * self.scale:
            return None
        return directions[:2].T

    def relax(self, initial):
        def objective(coordinates):
            coordinates = coordinates.reshape(-1, 3)
            lengths = np.linalg.norm(coordinates, axis=1, keepdims=True)
            spins = coordinates / lengths
            energy, gradient = self.energy_gradient(spins)
            gradient -= np.sum(gradient * spins, axis=1, keepdims=True) * spins
            energy += 0.5 * self.scale * np.sum((lengths - 1.0)**2)
            gradient = gradient / lengths + self.scale * (lengths - 1.0) * spins
            return float(energy), gradient.ravel()

        result = minimize(objective, initial.ravel(), jac=True, method="L-BFGS-B", options={"gtol": 2e-10, "ftol": 1e-15, "maxiter": 2000, "maxls": 30, "maxcor": 20})
        spins = result.x.reshape(-1, 3)
        spins /= np.linalg.norm(spins, axis=1, keepdims=True)
        for iteration in range(8):
            energy, gradient, hessian, basis = self.derivatives(spins)
            if np.max(np.abs(gradient)) < 1e-10:
                break
            values, vectors = eigh(hessian, check_finite=False)
            if values[0] <= 0:
                break
            step = -(vectors @ ((vectors.T @ gradient) / values)).reshape(-1, 2)
            if np.max(np.linalg.norm(step, axis=1)) > 0.1:
                break
            spins = sphere_step(spins, np.einsum("nik,nk->ni", basis, step))
        return spins


class PlanarModel:
    def __init__(self, model, plane):
        self.model = model
        self.plane = plane
        self.exchange = model.exchange
        self.anisotropy = np.einsum("ik,nij,jl->nkl", plane, model.anisotropy, plane)
        self.field = plane.T @ model.field
        self.start = self.angles(model.minimum_a)
        self.finish = self.start + wrap(self.angles(model.minimum_b) - self.start)
        self.count = model.count
        self.stiffness = 4 * np.max(self.exchange) + 4 * np.max(np.abs(self.anisotropy)) + np.linalg.norm(self.field)

    def angles(self, spins):
        projected = spins @ self.plane
        return np.unwrap(np.arctan2(projected[:, 1], projected[:, 0]))

    def spins(self, angles):
        return np.stack((np.cos(angles), np.sin(angles)), axis=-1) @ self.plane.T

    def energy_gradient(self, angles):
        cosine = np.cos(angles)
        sine = np.sin(angles)
        difference = angles[..., :-1] - angles[..., 1:]
        coupling = self.anisotropy[:, 0, 0] - self.anisotropy[:, 1, 1]
        mixed = self.anisotropy[:, 0, 1]
        energy = -np.sum(self.exchange * np.cos(difference), axis=-1)
        energy -= np.sum(self.anisotropy[:, 0, 0] * cosine**2 + self.anisotropy[:, 1, 1] * sine**2 + 2 * mixed * sine * cosine + self.field[0] * cosine + self.field[1] * sine, axis=-1)
        gradient = 2 * coupling * sine * cosine - 2 * mixed * (cosine**2 - sine**2) + self.field[0] * sine - self.field[1] * cosine
        bond_gradient = self.exchange * np.sin(difference)
        gradient[..., :-1] += bond_gradient
        gradient[..., 1:] -= bond_gradient
        return energy, gradient

    def hessian(self, angles):
        coupling = self.anisotropy[:, 0, 0] - self.anisotropy[:, 1, 1]
        mixed = self.anisotropy[:, 0, 1]
        diagonal = 2 * coupling * np.cos(2 * angles) + 4 * mixed * np.sin(2 * angles)
        diagonal += self.field[0] * np.cos(angles) + self.field[1] * np.sin(angles)
        offdiagonal = -self.exchange * np.cos(angles[:-1] - angles[1:])
        diagonal[:-1] -= offdiagonal
        diagonal[1:] -= offdiagonal
        return diagonal, offdiagonal

    def relax(self, initial):
        result = minimize(self.energy_gradient, initial, jac=True, method="L-BFGS-B", options={"gtol": 2e-10, "ftol": 1e-15, "maxiter": 1600, "maxls": 30, "maxcor": 15})
        angles = result.x
        for iteration in range(8):
            _, gradient = self.energy_gradient(angles)
            if np.max(np.abs(gradient)) < 1e-10:
                break
            diagonal, offdiagonal = self.hessian(angles)
            values, vectors = eigh_tridiagonal(diagonal, offdiagonal, check_finite=False)
            if values[0] <= 0:
                break
            step = vectors @ ((vectors.T @ gradient) / values)
            if np.max(np.abs(step)) > 0.1:
                break
            angles -= step
        return angles


def wrap(angles):
    return (angles + np.pi) % (2 * np.pi) - np.pi


def redistribute(path):
    segment = np.linalg.norm(np.diff(path, axis=0), axis=1)
    distance = np.concatenate(([0.0], np.cumsum(segment)))
    if distance[-1] < 1e-14:
        return path.copy()
    target = np.linspace(0.0, distance[-1], len(path))
    indices = np.clip(np.searchsorted(distance, target, side="right") - 1, 0, len(path) - 2)
    weight = (target - distance[indices]) / np.maximum(segment[indices], 1e-15)
    return path[indices] + weight[:, None] * (path[indices + 1] - path[indices])


def initial_path(model, direction, images=45):
    if direction == 0:
        return np.linspace(model.start, model.finish, images)
    anisotropy = np.linalg.eigvalsh(model.anisotropy)
    width = np.sqrt(np.median(model.exchange) / max(2 * np.median(anisotropy[:, 1] - anisotropy[:, 0]), 1e-4))
    width = np.clip(width, 0.6, model.count / 3)
    position = np.arange(model.count, dtype=float)
    if direction < 0:
        position = position[::-1]
    center = np.linspace(-7 * width, model.count - 1 + 7 * width, images)
    fraction = (2 / np.pi) * np.arctan(np.exp(np.clip((center[:, None] - position[None, :]) / width, -40, 40)))
    path = model.start + fraction * (model.finish - model.start)
    path[0] = model.start
    path[-1] = model.finish
    return redistribute(path)


def follow_saddle(model, initial, maxiter=160):
    angles = initial.copy()
    best = None
    for iteration in range(maxiter):
        energy, gradient = model.energy_gradient(angles)
        diagonal, offdiagonal = model.hessian(angles)
        values, vectors = eigh_tridiagonal(diagonal, offdiagonal, check_finite=False)
        residual = np.max(np.abs(gradient))
        if values[0] < -1e-8 and values[1] > 1e-9:
            if best is None or residual < best[0]:
                best = (residual, angles.copy())
            if residual < 2e-11:
                return angles
        projected = vectors.T @ gradient
        denominator = np.maximum(np.abs(values), 1e-3)
        step = -projected / denominator
        step[0] *= -1
        if residual < 1e-10 and values[0] > 0:
            return None
        step = vectors @ step
        largest = max(np.max(np.abs(step)) / 0.22, np.linalg.norm(step) / 0.65, 1.0)
        step /= largest
        if values[0] < 0 and values[1] > 0 and residual < 0.02:
            trial = angles + step
            for backtrack in range(8):
                if np.linalg.norm(model.energy_gradient(trial)[1]) < np.linalg.norm(gradient):
                    break
                step *= 0.5
                trial = angles + step
            angles = trial
        else:
            angles += step
    if best is not None and best[0] < 2e-6:
        return best[1]
    return None


def string_search(model, path, deadline, steps=2200):
    timestep = 1.4 / model.stiffness
    candidates = []
    previous_peak = np.inf
    unchanged = 0
    for iteration in range(steps):
        energies, gradients = model.energy_gradient(path)
        path[1:-1] -= timestep * gradients[1:-1]
        path = redistribute(path)
        if iteration % 100 == 99:
            energies, gradients = model.energy_gradient(path)
            peak = int(np.argmax(energies))
            if peak == 0 or peak == len(path) - 1:
                break
            if abs(energies[peak] - previous_peak) < 2e-8:
                unchanged += 1
            else:
                unchanged = 0
            previous_peak = energies[peak]
            if iteration >= 299:
                candidate = follow_saddle(model, path[peak], maxiter=70)
                if candidate is not None:
                    candidates.append(candidate)
                    if unchanged >= 1 or iteration >= 799:
                        break
            if time.monotonic() > deadline:
                break
    if not candidates:
        energies, _ = model.energy_gradient(path)
        peak = int(np.argmax(energies))
        if 0 < peak < len(path) - 1:
            candidate = follow_saddle(model, path[peak])
            if candidate is not None:
                candidates.append(candidate)
    return candidates, path


def connected_planar(model, candidate):
    diagonal, offdiagonal = model.hessian(candidate)
    values, vectors = eigh_tridiagonal(diagonal, offdiagonal, check_finite=False)
    if values[0] >= 0 or values[1] <= 0:
        return False
    unstable = vectors[:, 0]
    endpoints = [model.relax(candidate + sign * 0.12 * unstable) for sign in (-1, 1)]
    distances = np.array([[np.max(np.abs(wrap(endpoint - minimum))) for minimum in (model.start, model.finish)] for endpoint in endpoints])
    return min(max(distances[0, 0], distances[1, 1]), max(distances[0, 1], distances[1, 0])) < 2e-3


def search_planar(model, deadline):
    candidates = []
    for direction in (0, 1, -1):
        path = initial_path(model, direction)
        found, path = string_search(model, path, deadline)
        for angles in found:
            if all(np.max(np.abs(wrap(angles - other))) > 1e-4 for other in candidates):
                candidates.append(angles)
        if time.monotonic() > deadline:
            break
    candidates.sort(key=lambda angles: float(model.energy_gradient(angles)[0]))
    for angles in candidates:
        spins = model.spins(angles)
        _, gradient, hessian, _ = model.model.derivatives(spins)
        values = eigh(hessian, eigvals_only=True, check_finite=False)
        if values[0] < -1e-7 and values[1] > 1e-8:
            if connected_planar(model, angles):
                return spins
    return None


def sphere_step(spins, tangent):
    length = np.linalg.norm(tangent, axis=-1, keepdims=True)
    result = np.cos(length) * spins + np.sinc(length / np.pi) * tangent
    return result / np.linalg.norm(result, axis=-1, keepdims=True)


def follow_saddle_full(model, initial, maxiter=200):
    spins = initial.copy()
    best = None
    for iteration in range(maxiter):
        energy, gradient, hessian, basis = model.derivatives(spins)
        values, vectors = eigh(hessian, check_finite=False)
        residual = np.max(np.linalg.norm(gradient.reshape(-1, 2), axis=1))
        if values[0] < -1e-8 and values[1] > 1e-9:
            if best is None or residual < best[0]:
                best = (residual, spins.copy())
            if residual < 2e-10:
                return spins
        projected = vectors.T @ gradient
        step = -projected / np.maximum(np.abs(values), 1e-3)
        step[0] *= -1
        step = (vectors @ step).reshape(-1, 2)
        step /= max(np.max(np.linalg.norm(step, axis=1)) / 0.2, np.linalg.norm(step) / 0.65, 1.0)
        tangent = np.einsum("nik,nk->ni", basis, step)
        spins = sphere_step(spins, tangent)
        spins /= np.linalg.norm(spins, axis=1)[:, None]
    return best[1] if best is not None and best[0] < 1e-5 else None


def sphere_log(start, finish):
    cosine = np.clip(np.sum(start * finish, axis=-1, keepdims=True), -1.0, 1.0)
    tangent = finish - cosine * start
    length = np.linalg.norm(tangent, axis=-1, keepdims=True)
    return tangent * (np.arctan2(length, cosine) / np.maximum(length, 1e-15))


def connected_full(model, candidate):
    _, _, hessian, basis = model.derivatives(candidate)
    values, vectors = eigh(hessian, check_finite=False)
    if values[0] >= 0 or values[1] <= 0:
        return False
    unstable = np.einsum("nik,nk->ni", basis, vectors[:, 0].reshape(-1, 2))
    endpoints = [model.relax(sphere_step(candidate, sign * 0.12 * unstable)) for sign in (-1, 1)]
    distances = np.array([[np.max(np.linalg.norm(endpoint - minimum, axis=1)) for minimum in (model.minimum_a, model.minimum_b)] for endpoint in endpoints])
    return min(max(distances[0, 0], distances[1, 1]), max(distances[0, 1], distances[1, 0])) < 2e-3


def sphere_redistribute(path):
    logs = sphere_log(path[:-1], path[1:])
    segment = np.linalg.norm(logs, axis=(1, 2))
    distance = np.concatenate(([0.0], np.cumsum(segment)))
    target = np.linspace(0.0, distance[-1], len(path))
    indices = np.clip(np.searchsorted(distance, target, side="right") - 1, 0, len(path) - 2)
    weight = (target - distance[indices]) / np.maximum(segment[indices], 1e-15)
    result = sphere_step(path[indices], weight[:, None, None] * logs[indices])
    result[0] = path[0]
    result[-1] = path[-1]
    return result


def search_full(model, deadline):
    candidates = []
    start = model.minimum_a
    finish = model.minimum_b
    logs = sphere_log(start, finish)
    for direction in (0, 1, -1, 2, -2):
        fraction = np.linspace(0.0, 1.0, 45)[:, None]
        if direction:
            positions = np.linspace(0.15, 0.85, model.count)[None, :]
            if direction < 0:
                positions = positions[:, ::-1]
            fraction = 1 / (1 + np.exp(-16 * (fraction - positions)))
        path = sphere_step(start[None, :, :], fraction[:, :, None] * logs[None, :, :])
        if abs(direction) == 2:
            generator = np.random.default_rng(3571)
            perturbation = generator.normal(size=start.shape)
            perturbation -= np.sum(perturbation * start, axis=1, keepdims=True) * start
            perturbation *= 0.25 / np.maximum(np.linalg.norm(perturbation, axis=1, keepdims=True), 1e-15)
            perturbation = np.sin(np.linspace(0.0, np.pi, len(path)))[:, None, None] * perturbation[None, :, :]
            perturbation -= np.sum(perturbation * path, axis=-1, keepdims=True) * path
            path = sphere_step(path, perturbation)
        path[0], path[-1] = start, finish
        path = sphere_redistribute(path)
        for iteration in range(2400):
            energy, gradient = model.energy_gradient(path)
            gradient -= np.sum(gradient * path, axis=-1, keepdims=True) * path
            path[1:-1] = sphere_step(path[1:-1], -0.22 / model.scale * gradient[1:-1])
            path = sphere_redistribute(path)
            if iteration % 200 == 199:
                energy, _ = model.energy_gradient(path)
                peak = int(np.argmax(energy))
                if peak == 0 or peak == len(path) - 1:
                    break
                candidate = follow_saddle_full(model, path[peak], maxiter=100)
                if candidate is not None:
                    if connected_full(model, candidate):
                        candidates.append(candidate)
                        break
                if time.monotonic() > deadline:
                    break
        if time.monotonic() > deadline:
            break
        if direction == -1 and candidates:
            break
    return min(candidates, key=lambda spins: float(model.energy_gradient(spins)[0])) if candidates else None


def solve(case):
    started = time.monotonic()
    model = SpinModel(case)
    deadline = started + min(float(case.get("time_limit_seconds", 90)), 90.0) - 8.0
    plane = model.plane()
    saddle = None
    if plane is not None:
        saddle = search_planar(PlanarModel(model, plane), deadline)
    if saddle is None:
        saddle = search_full(model, deadline)
    if saddle is None:
        raise RuntimeError("No index-one transition state converged")
    saddle_energy, gradient, saddle_hessian, _ = model.derivatives(saddle)
    minimum_energy, _, minimum_hessian, _ = model.derivatives(model.minimum_a)
    minimum_values = eigh(minimum_hessian, eigvals_only=True, check_finite=False)
    saddle_values = eigh(saddle_hessian, eigvals_only=True, check_finite=False)
    if minimum_values[0] <= 0 or saddle_values[0] >= 0 or saddle_values[1] <= 0:
        raise RuntimeError("Transition-state Hessian has incorrect inertia")
    log_factor = 0.5 * (np.sum(np.log(minimum_values)) - np.sum(np.log(saddle_values[1:])))
    return {"saddle": saddle, "barrier_meV": saddle_energy - minimum_energy, "eigenvalues_min_meV": minimum_values, "eigenvalues_saddle_meV": saddle_values, "log_omega0": float(log_factor)}


def main():
    case = json.loads(Path(sys.argv[1]).read_text())
    result = solve(case)
    with open(sys.argv[2], "wb") as output:
        np.savez_compressed(output, **result)


if __name__ == "__main__":
    main()
