#!/usr/bin/env python3
import os
import sys
import json
import time

STARTED = time.monotonic()
CPU_STARTED = time.process_time()
for thread_variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[thread_variable] = "1"

import numpy as np
from scipy.optimize import least_squares


AXES = "IXYZ"
SINGLE = np.array([np.eye(2), [[0, 1], [1, 0]], [[0, -1j], [1j, 0]], [[1, 0], [0, -1]]], dtype=complex)
PAULI = np.array([np.kron(left, right) for left in SINGLE for right in SINGLE])
BOUNDS = np.array([[-5, 5], [-2, 2], [-3, 3], [-1.4, 1.4], [-2.5, 2.5], [.78, .995], [.78, .95], [-.045, .045], [.006, .16]])
SCALES = np.array([.5, .25, .5, .25, .5, .1, .1, .03, .05])


def experiment(prep, measure, duration, shots):
    return {"type": "experiment", "prep": list(prep), "measure": measure, "time": float(duration), "shots": int(shots)}


class Batch:
    def __init__(self, experiments):
        self.times = np.array([item["time"] for item in experiments])
        self.shots = np.array([item["shots"] for item in experiments])
        self.control = np.array([4 * AXES.index(item["prep"][0][0]) for item in experiments])
        self.target = np.array([AXES.index(item["prep"][1][0]) for item in experiments])
        self.control_sign = np.array([1 if item["prep"][0][1] == "+" else -1 for item in experiments])
        self.target_sign = np.array([1 if item["prep"][1][1] == "+" else -1 for item in experiments])
        self.measure = np.array([4 * AXES.index(item["measure"][0]) + AXES.index(item["measure"][1]) for item in experiments])
        self.linear = (self.control_sign[:, None, None] * PAULI[self.control] + self.target_sign[:, None, None] * PAULI[self.target]) / 4
        self.quadratic = (self.control_sign * self.target_sign)[:, None, None] * PAULI[self.control + self.target] / 4
        self.observables = PAULI[self.measure]


def evolution(parameters, times):
    unitary = np.zeros((len(times), 4, 4), complex)
    derivative = np.zeros((5, len(times), 4, 4), complex)
    half_time = times / 2
    for block_index, control_sign in enumerate((1, -1)):
        axis_x = parameters[0] + control_sign * parameters[1]
        axis_z = parameters[2] + control_sign * parameters[3]
        frequency = np.hypot(axis_x, axis_z)
        cosine = np.cos(frequency * half_time)
        sine_ratio = half_time * np.sinc(frequency * half_time / np.pi)
        if frequency > 1e-5:
            radial = (half_time * cosine - sine_ratio) / frequency**2
        else:
            radial = -half_time**3 / 3 + frequency**2 * half_time**5 / 30
        generator = axis_x * SINGLE[1] + axis_z * SINGLE[3]
        phase = np.exp(-1j * control_sign * parameters[4] * half_time)
        block = phase[:, None, None] * (cosine[:, None, None] * SINGLE[0] - 1j * sine_ratio[:, None, None] * generator)
        derivative_x = phase[:, None, None] * (-half_time[:, None, None] * sine_ratio[:, None, None] * axis_x * SINGLE[0] - 1j * (radial[:, None, None] * axis_x * generator + sine_ratio[:, None, None] * SINGLE[1]))
        derivative_z = phase[:, None, None] * (-half_time[:, None, None] * sine_ratio[:, None, None] * axis_z * SINGLE[0] - 1j * (radial[:, None, None] * axis_z * generator + sine_ratio[:, None, None] * SINGLE[3]))
        section = slice(2 * block_index, 2 * block_index + 2)
        unitary[:, section, section] = block
        derivative[0, :, section, section] = derivative_x
        derivative[1, :, section, section] = control_sign * derivative_x
        derivative[2, :, section, section] = derivative_z
        derivative[3, :, section, section] = control_sign * derivative_z
        derivative[4, :, section, section] = (-1j * control_sign * half_time)[:, None, None] * block
    return unitary, derivative


def predict(parameters, batch):
    visibility, contrast, bias, decay = parameters[5:]
    unitary, derivative = evolution(parameters, batch.times)
    adjoint = unitary.conj().transpose(0, 2, 1)
    observable_back = adjoint @ batch.observables @ unitary
    linear = np.einsum("nij,nji->n", observable_back, batch.linear).real
    quadratic = np.einsum("nij,nji->n", observable_back, batch.quadratic).real
    mean = visibility * linear + visibility**2 * quadratic
    envelope = contrast * np.exp(-decay * batch.times)
    density = visibility * batch.linear + visibility**2 * batch.quadratic
    right = density @ adjoint @ batch.observables
    gradient = np.empty((len(batch.times), 9))
    gradient[:, :5] = np.einsum("anij,nji->na", derivative, right).real * envelope[:, None]
    gradient[:, 5] = envelope * (linear + 2 * visibility * quadratic) / 2
    gradient[:, 6] = np.exp(-decay * batch.times) * mean / 2
    gradient[:, 7] = .5
    gradient[:, 8] = -batch.times * envelope * mean / 2
    probability = np.clip((1 + bias + envelope * mean) / 2, 1e-9, 1 - 1e-9)
    return probability, gradient


def pool_predictions(parameters, experiments):
    durations, time_index = np.unique([item["time"] for item in experiments], return_inverse=True)
    control = np.array([4 * AXES.index(item["prep"][0][0]) for item in experiments])
    target = np.array([AXES.index(item["prep"][1][0]) for item in experiments])
    sign_control = np.array([1 if item["prep"][0][1] == "+" else -1 for item in experiments])
    sign_target = np.array([1 if item["prep"][1][1] == "+" else -1 for item in experiments])
    measure = np.array([4 * AXES.index(item["measure"][0]) + AXES.index(item["measure"][1]) for item in experiments])
    unitary, derivative = evolution(parameters, durations)
    adjoint = unitary.conj().transpose(0, 2, 1)
    evolved = unitary[:, None] @ PAULI[None] @ adjoint[:, None]
    transfer = np.einsum("mij,tpji->tmp", PAULI, evolved).real / 4
    evolved_derivative = derivative[:, :, None] @ PAULI[None, None] @ adjoint[None, :, None]
    transfer_derivative = np.einsum("mij,atpji->atmp", PAULI, evolved_derivative).real / 2
    linear = sign_control * transfer[time_index, measure, control] + sign_target * transfer[time_index, measure, target]
    quadratic = sign_control * sign_target * transfer[time_index, measure, control + target]
    linear_derivative = sign_control[None] * transfer_derivative[:, time_index, measure, control] + sign_target[None] * transfer_derivative[:, time_index, measure, target]
    quadratic_derivative = (sign_control * sign_target)[None] * transfer_derivative[:, time_index, measure, control + target]
    visibility, contrast, bias, decay = parameters[5:]
    times = durations[time_index]
    mean = visibility * linear + visibility**2 * quadratic
    envelope = contrast * np.exp(-decay * times)
    gradient = np.empty((len(experiments), 9))
    gradient[:, :5] = ((visibility * linear_derivative + visibility**2 * quadratic_derivative) * envelope[None] / 2).T
    gradient[:, 5] = envelope * (linear + 2 * visibility * quadratic) / 2
    gradient[:, 6] = np.exp(-decay * times) * mean / 2
    gradient[:, 7] = .5
    gradient[:, 8] = -times * envelope * mean / 2
    probability = np.clip((1 + bias + envelope * mean) / 2, 1e-9, 1 - 1e-9)
    return probability, gradient


class Fitter:
    def __init__(self, experiments, counts, bounds, deadline, regularize=False):
        self.batch = Batch(experiments)
        self.target = np.arcsin(np.sqrt((np.asarray(counts) + .375) / (self.batch.shots + .75)))
        self.weights = 2 * np.sqrt(self.batch.shots)
        self.bounds = bounds
        self.deadline = deadline
        self.last_parameters = None
        self.regularize = regularize
        if regularize:
            self.prior_center = np.mean(bounds[5:], axis=1)
            self.prior_weights = np.sqrt(12) / (bounds[5:, 1] - bounds[5:, 0])
            self.prior_gradient = np.zeros((4, 9))
            self.prior_gradient[:, 5:] = np.diag(self.prior_weights)

    def evaluate(self, parameters):
        if time.monotonic() > self.deadline or time.process_time() - CPU_STARTED > 15.5:
            raise TimeoutError
        if self.last_parameters is None or not np.array_equal(parameters, self.last_parameters):
            probability, gradient = predict(parameters, self.batch)
            self.last_parameters = parameters.copy()
            self.residual = self.weights * (np.arcsin(np.sqrt(probability)) - self.target)
            self.gradient = gradient * (self.weights / (2 * np.sqrt(probability * (1 - probability))))[:, None]
            if self.regularize:
                self.residual = np.r_[self.residual, self.prior_weights * (parameters[5:] - self.prior_center)]
                self.gradient = np.vstack([self.gradient, self.prior_gradient])

    def fun(self, parameters):
        self.evaluate(parameters)
        return self.residual

    def jac(self, parameters):
        self.evaluate(parameters)
        return self.gradient

    def fit(self, initial, evaluations=80):
        initial = np.clip(initial, self.bounds[:, 0] + 1e-8, self.bounds[:, 1] - 1e-8)
        fit = least_squares(self.fun, initial, jac=self.jac, bounds=(self.bounds[:, 0], self.bounds[:, 1]), x_scale=SCALES, max_nfev=evaluations, ftol=2e-7, xtol=2e-7, gtol=2e-7)
        return float(fit.fun @ fit.fun), fit.x


def initial_schedule():
    calibration = [(("Z+", "X+"), "IX"), (("Z+", "X-"), "IX"), (("Z+", "Z+"), "ZZ"), (("Z-", "Z+"), "ZZ")]
    result = [experiment(prep, measure, 0, 256) for prep, measure in calibration]
    settings = [((control, target), "I" + axis) for control in ("Z+", "Z-") for target in ("X+", "Z+") for axis in "XYZ"]
    settings += [(("X+", target), axis + "I") for target in ("X+", "Z+") for axis in "XY"]
    for duration in (.15, .34, .61, .97):
        result.extend(experiment(prep, measure, duration, 64) for prep, measure in settings)
    return result


def family_bounds(high_noise):
    bounds = BOUNDS.copy()
    if high_noise:
        bounds[5:] = [[.78, .86], [.78, .85], [-.045, .045], [.1, .16]]
    else:
        bounds[5:] = [[.91, .99], [.9, .95], [-.025, .025], [.008, .045]]
    return bounds


def initial_guess(experiments, counts):
    values = 2 * np.asarray(counts) / np.array([item["shots"] for item in experiments]) - 1
    single_amplitude = (values[0] - values[1]) / 2
    double_amplitude = (values[2] - values[3]) / 2
    visibility = np.clip(double_amplitude / max(single_amplitude, .1), .78, .99)
    contrast = np.clip(single_amplitude / visibility, .78, .95)
    bias = np.clip(np.mean(values[:4]), -.045, .045)
    amplitude = max(single_amplitude, .5)
    early = (values[4:20] - bias) / amplitude / .15
    omega_ix = -(early[4] + early[10]) / 2
    omega_zx = -(early[4] - early[10]) / (2 * visibility)
    omega_iz = (early[1] + early[7]) / 2
    omega_zz = (early[1] - early[7]) / (2 * visibility)
    omega_zi = (early[13] + early[15] - visibility * (omega_zx + omega_zz)) / 2
    high_noise = single_amplitude + double_amplitude < 1.4625
    bounds = family_bounds(high_noise)
    decay = .13 if high_noise else .026
    parameters = np.array([omega_ix, omega_zx, omega_iz, omega_zz, omega_zi, visibility, contrast, bias, decay])
    return np.clip(parameters, bounds[:, 0] + 1e-7, bounds[:, 1] - 1e-7), bounds


def candidate_pool(maximum_time, phase):
    rng = np.random.default_rng(6513 + phase)
    times = np.unique(np.r_[0, np.linspace(.08, min(2, maximum_time), 23), rng.uniform(.1, maximum_time, 54), maximum_time])
    settings = [((control, target), left + right) for control in ("X+", "Y+", "Z+", "Z-") for target in ("X+", "X-", "Y+", "Y-", "Z+", "Z-") for left in AXES for right in AXES if left + right != "II"]
    return [experiment(prep, measure, duration, 1) for duration in times for prep, measure in settings]


def allocate(parameters, experiments, bounds, total_shots, block_shots, maximum_time, phase):
    batch = Batch(experiments)
    probability, gradient = predict(parameters, batch)
    features = gradient * SCALES[None] / np.sqrt(probability * (1 - probability))[:, None]
    information = features.T @ (features * batch.shots[:, None])
    prior = np.zeros(9)
    prior[5:] = 12 * SCALES[5:]**2 / (bounds[5:, 1] - bounds[5:, 0])**2
    information += np.diag(prior + 1e-7)
    covariance = np.linalg.inv(information)
    candidates = candidate_pool(maximum_time, phase)
    probability, gradient = pool_predictions(parameters, candidates)
    features = gradient * SCALES[None] / np.sqrt(probability * (1 - probability))[:, None]
    allocations = np.zeros(len(candidates), dtype=int)
    for block_index in range(total_shots // block_shots):
        projected = features @ covariance
        variance = np.einsum("ni,ni->n", projected, features)
        gains = np.sum(projected[:, :5]**2, axis=1) / (1 / block_shots + variance)
        gains[allocations + block_shots > 4096] = -1
        selected = int(np.argmax(gains))
        allocations[selected] += block_shots
        direction = projected[selected]
        covariance -= np.outer(direction, direction) / (1 / block_shots + variance[selected])
    schedule = []
    for selected in np.flatnonzero(allocations):
        item = candidates[selected].copy()
        item["shots"] = int(allocations[selected])
        schedule.append(item)
    return schedule


def calibrate(ask, started=None):
    started = STARTED if started is None else started
    deadline = started + 16.3
    experiments = initial_schedule()
    counts = [ask(item) for item in experiments]
    parameters, bounds = initial_guess(experiments, counts)
    fitter = Fitter(experiments, counts, bounds, deadline)
    rng = np.random.default_rng(3927)
    starts = [parameters.copy()]
    for start_index in range(4):
        candidate = parameters.copy()
        candidate[:5] += rng.normal(size=5) * [.7, .4, .7, .35, .5]
        starts.append(candidate)
    best_cost = np.inf
    try:
        for initial in starts:
            cost, fitted = fitter.fit(initial, 85)
            if cost < best_cost:
                best_cost, parameters = cost, fitted
            if time.monotonic() > started + 5:
                break
        other_bounds = family_bounds(bounds[5, 0] > .8)
        other_fitter = Fitter(experiments, counts, other_bounds, deadline)
        other_cost, other_parameters = other_fitter.fit(parameters, 85)
        if other_cost < best_cost:
            parameters, bounds = other_parameters, other_bounds
        for phase, (total_shots, block_shots, maximum_time) in enumerate(((4096, 128, 3.3), (6144, 192, 8), (9216, 256, 12))):
            if time.monotonic() > started + 13 or time.process_time() - CPU_STARTED > 12:
                break
            schedule = allocate(parameters, experiments, bounds, total_shots, block_shots, maximum_time, phase)
            for item in schedule:
                counts.append(ask(item))
                experiments.append(item)
            fitter = Fitter(experiments, counts, bounds, deadline, regularize=phase == 2)
            cost, parameters = fitter.fit(parameters, 100)
    except TimeoutError:
        pass
    return np.clip(parameters, BOUNDS[:, 0], BOUNDS[:, 1])


def main():
    greeting = json.loads(sys.stdin.readline())
    if greeting.get("type") != "start":
        raise ValueError("expected start")

    def ask(item):
        print(json.dumps(item, separators=(",", ":")), flush=True)
        response = json.loads(sys.stdin.readline())
        if response.get("type") != "result":
            raise ValueError("expected result")
        return response["plus"]

    parameters = calibrate(ask)
    print(json.dumps({"type": "estimate", "omega": parameters[:5].tolist(), "nuisance": parameters[5:].tolist()}, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
