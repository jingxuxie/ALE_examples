import os
import time

START_WALL = time.monotonic()
START_CPU = time.process_time()
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'

import argparse
import json
import math

import numpy as np
from scipy import ndimage
from scipy.optimize import minimize
from scipy.sparse import coo_matrix


class Budget:
    def __init__(self, seconds=57.0, origin=None):
        self.wall, self.cpu = origin or (time.monotonic(), time.process_time())
        self.seconds = seconds

    def elapsed(self):
        return max(time.monotonic() - self.wall, time.process_time() - self.cpu)

    def remaining(self):
        return self.seconds - self.elapsed()


class TimeLimit(Exception):
    pass


class Model:
    def __init__(self, case):
        self.shape = tuple(case['shape'])
        self.mask = np.asarray(case['mask'], dtype=bool)
        self.size = int(self.mask.sum())
        self.h = float(case['h'])
        self.alpha_grid = np.asarray(case['alpha'], dtype=float)
        self.beta_grid = np.asarray(case['beta'], dtype=float)
        self.alpha = self.h ** 2 * self.alpha_grid[self.mask]
        self.beta = self.h ** 2 * self.beta_grid[self.mask]
        self.ax = np.asarray(case['ax'], dtype=float)
        self.ay = np.asarray(case['ay'], dtype=float)
        self.ux = np.exp(-1j * self.ax)
        self.uy = np.exp(-1j * self.ay)
        self.kx = np.asarray(case['kx'], dtype=float) * (self.mask[:, :-1] & self.mask[:, 1:])
        self.ky = np.asarray(case['ky'], dtype=float) * (self.mask[:-1] & self.mask[1:])
        initial = np.asarray(case['initial_real']) + 1j * np.asarray(case['initial_imag'])
        self.initial = np.ascontiguousarray(initial[self.mask], dtype=np.complex128)
        indices = np.full(self.shape, -1, dtype=int)
        indices[self.mask] = np.arange(self.size)
        sources = np.concatenate((indices[:, :-1].ravel(), indices[:-1].ravel()))
        targets = np.concatenate((indices[:, 1:].ravel(), indices[1:].ravel()))
        valid = (sources >= 0) & (targets >= 0)
        sources, targets = sources[valid], targets[valid]
        stiffness = np.concatenate((self.kx.ravel(), self.ky.ravel()))[valid]
        phases = np.concatenate((self.ux.ravel(), self.uy.ravel()))[valid]
        diagonal = self.alpha + np.bincount(sources, weights=stiffness, minlength=self.size) + np.bincount(targets, weights=stiffness, minlength=self.size)
        rows = np.concatenate((np.arange(self.size), sources, targets))
        cols = np.concatenate((np.arange(self.size), targets, sources))
        values = np.concatenate((diagonal, -stiffness * phases, -stiffness * phases.conj()))
        self.matrix = coo_matrix((values, (rows, cols)), shape=(self.size, self.size)).tocsr()
        density_scale = np.maximum(-self.alpha / self.beta, 0)
        self.amplitude = max(0.1, float(np.sqrt(np.percentile(density_scale, 70))))
        self.energy_scale = max(0.1, float(np.median(stiffness)) * self.amplitude ** 2) if len(stiffness) else 1.0
        self.lower_bound = -0.5 * float(np.sum(np.minimum(self.alpha, 0) ** 2 / self.beta))

    def full(self, field):
        result = np.zeros(self.shape, dtype=np.complex128)
        result[self.mask] = field
        return result

    def energy_gradient(self, field):
        density = field.real ** 2 + field.imag ** 2
        linear = self.matrix @ field
        nonlinear = self.beta * density
        energy = np.vdot(field, linear).real + 0.5 * np.dot(density, nonlinear)
        return float(energy), 2 * (linear + nonlinear * field)

    def objective(self, vector):
        energy, gradient = self.energy_gradient(vector.view(np.complex128))
        return energy, gradient.view(np.float64)

    def reference_objective(self, vector):
        field = self.full(vector[:self.size] + 1j * vector[self.size:])
        density = field.real * field.real + field.imag * field.imag
        onsite = self.alpha_grid * density + 0.5 * self.beta_grid * density * density
        energy = self.h ** 2 * np.sum(onsite[self.mask])
        delta_x = self.ux * field[:, 1:] - field[:, :-1]
        delta_y = self.uy * field[1:] - field[:-1]
        energy += np.sum(self.kx * (delta_x.real ** 2 + delta_x.imag ** 2))
        energy += np.sum(self.ky * (delta_y.real ** 2 + delta_y.imag ** 2))
        gradient = 2 * self.h ** 2 * (self.alpha_grid + self.beta_grid * density) * field
        flow_x = 2 * self.kx * delta_x
        flow_y = 2 * self.ky * delta_y
        gradient[:, :-1] -= flow_x
        gradient[:, 1:] += np.conjugate(self.ux) * flow_x
        gradient[:-1] -= flow_y
        gradient[1:] += np.conjugate(self.uy) * flow_y
        active = gradient[self.mask]
        return float(energy), np.concatenate((active.real, active.imag))


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


def conjugate_relax(model, initial, budget, reserve=3.0, maxiter=4000, tolerance=1e-9, shift=None):
    field = initial.copy()
    density = field.real ** 2 + field.imag ** 2
    linear = model.matrix @ field
    if shift is not None:
        linear += shift * field
    gradient = 2 * (linear + model.beta * density * field)
    energy = dot(field, linear) + 0.5 * np.dot(model.beta, density ** 2)
    direction = -gradient
    previous_decrease = np.inf
    gradient_square = dot(gradient, gradient)
    for iteration in range(maxiter):
        if iteration % 16 == 0 and (budget.remaining() <= reserve or gradient_square < 2e-12 * model.size):
            break
        matrix_direction = model.matrix @ direction
        if shift is not None:
            matrix_direction += shift * direction
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
            if shift is not None:
                linear += shift * field
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
        coefficient = (dot(difference, next_gradient) - 2 * dot(difference, difference) * dot(direction, next_gradient) / curvature) / curvature if curvature > 1e-30 else 0.0
        direction = -next_gradient + coefficient * direction
        if dot(direction, next_gradient) > -0.01 * gradient_square:
            direction = -next_gradient
        gradient, energy = next_gradient, next_energy
        previous_decrease = decrease
    energy, gradient = model.energy_gradient(field)
    return energy, field, math.sqrt(dot(gradient, gradient) / (2 * model.size))


def lbfgs_relax(model, initial, budget, reference=False, reserve=0.3, maxiter=1600):
    vector = np.concatenate((initial.real, initial.imag)) if reference else initial.copy().view(np.float64)
    objective = model.reference_objective if reference else model.objective
    saved = [float('inf'), vector.copy()]

    def evaluate(coordinates):
        if budget.remaining() <= reserve:
            raise TimeLimit
        energy, gradient = objective(coordinates)
        if np.isfinite(energy) and energy < saved[0]:
            saved[0], saved[1] = energy, coordinates.copy()
        return energy, gradient

    try:
        result = minimize(evaluate, vector, jac=True, method='L-BFGS-B', options={'maxiter': maxiter, 'ftol': 1e-12 if reference else 1e-14, 'gtol': 2e-6 if reference else 1e-7, 'maxcor': 10})
        vector = result.x
    except TimeLimit:
        vector = saved[1]
    field = vector[:model.size] + 1j * vector[model.size:] if reference else vector.view(np.complex128).copy()
    energy, gradient = model.energy_gradient(field)
    return energy, field, math.sqrt(dot(gradient, gradient) / (2 * model.size))


class Topology:
    def __init__(self, model):
        self.model = model
        self.rows, self.cols = np.nonzero(model.mask)
        self.points = self.cols + 1j * self.rows
        mask = model.mask
        self.flux = model.ax[:-1] + model.ay[:, 1:] - model.ax[1:] - model.ay[:, :-1]
        self.faces = mask[:-1, :-1] & mask[:-1, 1:] & mask[1:, :-1] & mask[1:, 1:]
        self.sign = float(np.sign(np.median(self.flux[self.faces]))) if self.faces.any() else 1.0
        self.sign = self.sign or 1.0
        labels, count = ndimage.label(~mask)
        outer = set(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
        holes = []
        for label in range(1, count + 1):
            if label not in outer:
                rows, cols = np.nonzero(labels == label)
                center = np.mean(cols) + 1j * np.mean(rows)
                nearest = np.argmin(abs(cols + 1j * rows - center))
                holes.append(cols[nearest] + 1j * rows[nearest])
        negative = model.alpha_grid[mask & (model.alpha_grid < 0)]
        alpha_scale = float(np.median(-negative)) if len(negative) else 1.0
        labels, count = ndimage.label((model.alpha_grid > 0.2 * alpha_scale) & mask)
        pins = []
        for label in range(1, count + 1):
            rows, cols = np.nonzero(labels == label)
            weights = model.alpha_grid[rows, cols]
            pins.append(np.sum(weights * (cols + 1j * rows)) / np.sum(weights))
        self.holes = np.asarray(holes, dtype=complex)
        self.pins = np.asarray(pins, dtype=complex)
        self.centers = np.asarray(holes + pins, dtype=complex)
        stiffness = model.kx[model.kx > 0]
        typical_k = float(np.median(stiffness)) if len(stiffness) else 1.0
        self.core = max(0.5, min(5.0, math.sqrt(typical_k / alpha_scale) / model.h))
        self.bulk = np.sqrt(np.maximum(-model.alpha / model.beta, 0))
        distance = ndimage.distance_transform_edt(mask)[mask]
        self.interior = self.points[distance >= 1.5 * self.core]
        if not len(self.interior):
            self.interior = self.points
        self.alpha_scale = alpha_scale

    def vortices(self, field):
        full = self.model.full(field)
        phase_x = np.angle(self.model.ux * full[:, 1:] * full[:, :-1].conj())
        phase_y = np.angle(self.model.uy * full[1:] * full[:-1].conj())
        winding = np.rint((phase_x[:-1] + phase_y[:, 1:] - phase_x[1:] - phase_y[:, :-1] + self.flux) / (2 * np.pi))
        rows, cols = np.nonzero(self.faces & (abs(winding) > 0.5))
        return cols + 0.5 + 1j * (rows + 0.5), winding[rows, cols]

    def vortex(self, field, center, charge, remove=False):
        displacement = self.points - center
        rotation = np.exp(1j * charge * np.angle(displacement))
        if remove:
            magnitude = abs(field)
            healing = np.exp(-abs(displacement) ** 2 / (2 * self.core) ** 2)
            repaired = magnitude + np.maximum(0, self.bulk - magnitude) * healing
            return repaired * field / np.maximum(magnitude, 1e-30) * rotation
        return field * rotation * np.tanh(abs(displacement) / self.core)

    def target(self, rng, positions, source=None):
        if len(self.centers) and rng.random() < 0.65:
            weights = np.ones(len(self.centers))
            if len(positions):
                distances = np.min(abs(self.centers[:, None] - positions[None, :]), axis=1)
                weights *= 0.1 + np.minimum(distances / (2 * self.core), 1) ** 3
                weights[:len(self.holes)] = 1.0
            if source is not None:
                distances = abs(self.centers - source)
                weights *= np.exp(-distances / (7 * self.core)) + 0.05
                weights[distances < self.core] *= 0.03
            return rng.choice(self.centers, p=weights / weights.sum())
        if source is not None and rng.random() < 0.8:
            return source + rng.normal(0, 4 * self.core) + 1j * rng.normal(0, 4 * self.core)
        return rng.choice(self.interior) + 0.37 + 0.43j

    def modify(self, field, rng, kind, hole_index=None):
        if kind == 'hole' and len(self.holes):
            center = self.holes[(hole_index // 2) % len(self.holes)] if hole_index is not None else rng.choice(self.holes)
            charge = (1 if hole_index % 2 else -1) if hole_index is not None else rng.choice([-1, 1])
            return field * np.exp(1j * charge * np.angle(self.points - center))
        if kind in ('hole', 'insert', 'delete', 'relocate'):
            positions, charges = self.vortices(field)
            if kind in ('delete', 'relocate') and len(positions):
                selected = rng.integers(len(positions))
                source, charge = positions[selected], charges[selected]
                candidate = self.vortex(field, source, -charge, remove=True)
                if kind == 'delete':
                    return candidate
                return self.vortex(candidate, self.target(rng, positions, source), charge)
            target = self.target(rng, positions)
            row = min(max(int(target.imag), 0), self.flux.shape[0] - 1)
            col = min(max(int(target.real), 0), self.flux.shape[1] - 1)
            charge = (np.sign(self.flux[row, col]) or self.sign) if self.faces[row, col] else self.sign
            return self.vortex(field, target, charge)
        if kind == 'patch':
            center = rng.choice(self.points)
            width = rng.uniform(2, 7) * self.core
            weight = np.exp(-abs(self.points - center) ** 2 / width ** 2)
            return field * np.exp(rng.uniform(2.5, 4.5) * 1j * weight * rng.standard_normal(len(field)))
        return field * np.exp(1j * rng.uniform(1.3, 2.6) * rng.standard_normal(len(field)))

    def crossover(self, first, second, rng):
        center = rng.choice(self.points)
        normal = np.exp(1j * rng.uniform(0, 2 * np.pi))
        coordinate = ((self.points - center) * normal).real
        weight = 0.5 + 0.5 * np.tanh(coordinate / (2 * self.core))
        overlap = np.sum(weight * (1 - weight) * first * second.conj())
        rotation = overlap / abs(overlap) if abs(overlap) > 1e-20 else 1.0
        return (1 - weight) * first + weight * rotation * second


def solve(model, budget, progress=False):
    if np.all(model.alpha >= 0):
        return np.zeros(model.shape, dtype=np.complex128), 0
    generator = np.random.default_rng(104729)
    noise = generator.standard_normal(model.shape)[model.mask]
    baseline_starts = [model.initial, model.initial * np.exp(0.6j * noise)]
    results = [lbfgs_relax(model, field, budget, reference=True, reserve=3.0, maxiter=1100) for field in baseline_starts]
    best_energy, best, best_rms = min(results, key=lambda result: result[0])
    if budget.remaining() > 4.0:
        polished = conjugate_relax(model, best, budget, maxiter=2500, tolerance=1e-11)
        if polished[0] < best_energy:
            best_energy, best, best_rms = polished
    if best_energy - model.lower_bound < 1e-7 and best_rms < 1e-4:
        return model.full(best), 0
    feasible = (best_energy, best.copy(), best_rms) if best_rms < 0.0015 else None
    topology = Topology(model)
    archive = [(best_energy, best.copy())]
    current_energy, current = best_energy, best.copy()
    scale = model.energy_scale
    significant_best = best_energy
    last_improvement = budget.elapsed()
    random_trials = 0
    random_hits = 0
    trials = 0
    hole_counter = 0
    schedule = ['random', 'relocate', 'crossover', 'insert', 'patch', 'random', 'delete', 'hole', 'noise', 'relocate', 'crossover', 'thermal']
    while budget.remaining() > 3.2:
        if trials < 16:
            kind = 'random'
        elif trials < 16 + 2 * len(topology.holes):
            kind = 'hole'
        else:
            kind = schedule[(trials - 16 - 2 * len(topology.holes)) % len(schedule)]
        choice = generator.random()
        if kind == 'hole' or choice < 0.50:
            parent = best
        elif choice < 0.83:
            weights = np.exp(-np.array([energy - best_energy for energy, field in archive]) / (1.5 * scale))
            parent = archive[generator.choice(len(archive), p=weights / weights.sum())][1]
        else:
            parent = current
        if kind == 'random':
            candidate = 0.5 * model.amplitude * (generator.standard_normal(model.size) + 1j * generator.standard_normal(model.size))
            random_trials += 1
        elif kind == 'crossover' and len(archive) > 1:
            other = archive[generator.integers(len(archive))][1]
            candidate = topology.crossover(parent, other, generator)
        elif kind == 'thermal':
            if generator.random() < 0.55:
                shift = generator.uniform(0.35, 0.85) * (-model.h ** 2 * topology.alpha_scale - model.alpha)
            else:
                shift = generator.uniform(0.2, 0.55) * model.h ** 2 * topology.alpha_scale
            candidate = conjugate_relax(model, parent, budget, maxiter=650, tolerance=1e-7, shift=shift)[1]
            magnitude = math.sqrt(dot(candidate, candidate) / model.size)
            if magnitude < 0.1 * model.amplitude:
                candidate = candidate * (0.3 * model.amplitude / max(magnitude, 1e-20))
                candidate += 0.03 * model.amplitude * (generator.standard_normal(model.size) + 1j * generator.standard_normal(model.size))
        else:
            candidate = topology.modify(parent, generator, kind, hole_counter if kind == 'hole' else None)
            if kind == 'hole':
                hole_counter += 1
        energy, field, rms = conjugate_relax(model, candidate, budget)
        trials += 1
        if not np.isfinite(energy) or not np.isfinite(field).all():
            continue
        if rms < 0.0015 and (feasible is None or energy < feasible[0]):
            feasible = (energy, field.copy(), rms)
        if energy < best_energy:
            best_energy, best, best_rms = energy, field.copy(), rms
        if best_energy - model.lower_bound < 1e-7 and best_rms < 1e-4:
            break
        if best_energy < significant_best - 0.0005 * scale:
            significant_best = best_energy
            last_improvement = budget.elapsed()
            random_hits = 0
            if progress:
                print('improvement', trials, kind, best_energy, budget.elapsed(), flush=True)
        if kind == 'random' and abs(energy - best_energy) < 0.001 * scale:
            random_hits += 1
        temperature = scale * (0.12 + 0.65 * (1 - (trials % 48) / 48) ** 2)
        if energy < current_energy or generator.random() < math.exp(min(0.0, (current_energy - energy) / temperature)):
            current_energy, current = energy, field.copy()
        if trials % 23 == 0:
            current_energy, current = best_energy, best.copy()
        if energy < best_energy + 3 * scale:
            duplicate = None
            for index, (stored_energy, stored) in enumerate(archive):
                if abs(energy - stored_energy) < 0.002 * scale:
                    correlation = abs(np.vdot(stored, field)) ** 2 / max(dot(stored, stored) * dot(field, field), 1e-30)
                    if correlation > 0.995:
                        duplicate = index
                        break
            if duplicate is None:
                archive.append((energy, field.copy()))
            elif energy < archive[duplicate][0]:
                archive[duplicate] = (energy, field.copy())
            archive.sort(key=lambda item: item[0])
            archive = archive[:8]
        if budget.elapsed() > 16.0 and budget.elapsed() - last_improvement > 12.0 and random_trials >= 36 and random_hits >= 8:
            break
    if budget.remaining() > 0.5:
        energy, field, rms = lbfgs_relax(model, best, budget, maxiter=2200)
        if energy <= best_energy + 1e-9:
            best_energy, best, best_rms = energy, field, rms
    if best_rms > 0.0015 and feasible is not None:
        best_energy, best, best_rms = feasible
    if progress:
        print('finished', trials, random_trials, best_energy, best_rms, budget.elapsed(), flush=True)
    return model.full(best), trials


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    budget = Budget(origin=(START_WALL, START_CPU))
    with open(arguments.input) as stream:
        model = Model(json.load(stream))
    field, trials = solve(model, budget)
    with open(arguments.output, 'wb') as stream:
        np.savez_compressed(stream, psi=field)
    energy, gradient = model.energy_gradient(field[model.mask])
    rms = math.sqrt(dot(gradient, gradient) / (2 * model.size))
    print('energy=%.12g gradient_rms=%.6g trials=%d elapsed=%.3f' % (energy, rms, trials, budget.elapsed()))


if __name__ == '__main__':
    main()
