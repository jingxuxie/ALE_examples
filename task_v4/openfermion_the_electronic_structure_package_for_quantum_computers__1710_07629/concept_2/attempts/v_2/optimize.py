import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares, minimize

from synthesize import load_instances, projector, schedule


def coefficients(parameters):
    horizontal = parameters[::2]
    vertical = parameters[1::2]
    radius = np.hypot(horizontal, vertical)
    cosine = np.cos(radius)
    sinc = np.sinc(radius / np.pi)
    derivative = np.empty_like(radius)
    large = radius > 1e-4
    derivative[large] = (radius[large] * cosine[large] - np.sin(radius[large])) / radius[large] ** 3
    derivative[~large] = -1 / 3 + radius[~large] ** 2 / 30
    complex_parameter = horizontal + 1j * vertical
    factor = sinc * complex_parameter
    cosine_derivatives = np.stack((-sinc * horizontal, -sinc * vertical), axis=1)
    factor_derivatives = np.stack((sinc + derivative * horizontal * complex_parameter,
                                   1j * sinc + derivative * vertical * complex_parameter), axis=1)
    return cosine, factor, cosine_derivatives, factor_derivatives


class Objective:
    def __init__(self, instance, edges):
        self.instance = instance
        self.edges = edges
        self.size = instance['n_modes']
        self.particles = instance['n_particles']
        self.initial = np.eye(self.size, dtype=complex)[:, instance['initial_occupied']]
        _, vectors = np.linalg.eigh(projector(instance))
        self.vacant = vectors[:, :self.size - self.particles].conj().T.copy()
        self.last_parameters = None
        self.last_residual = None
        self.last_jacobian = None
        self.evaluations = 0

    def compute(self, parameters):
        if self.last_parameters is not None and np.array_equal(parameters, self.last_parameters):
            return self.last_residual, self.last_jacobian
        cosine, factor, cosine_derivatives, factor_derivatives = coefficients(parameters)
        frame = self.initial.copy()
        derivative = np.zeros((self.size, self.particles, len(parameters)), dtype=complex)
        for index, (first, second) in enumerate(self.edges):
            upper, lower = frame[first].copy(), frame[second].copy()
            frame[first] = cosine[index] * upper - factor[index].conjugate() * lower
            frame[second] = factor[index] * upper + cosine[index] * lower
            upper_derivative = derivative[first].copy()
            lower_derivative = derivative[second].copy()
            derivative[first] = cosine[index] * upper_derivative - factor[index].conjugate() * lower_derivative
            derivative[second] = factor[index] * upper_derivative + cosine[index] * lower_derivative
            for component in range(2):
                derivative[first, :, 2 * index + component] += cosine_derivatives[index, component] * upper - factor_derivatives[index, component].conjugate() * lower
                derivative[second, :, 2 * index + component] += factor_derivatives[index, component] * upper + cosine_derivatives[index, component] * lower
        overlap = self.vacant @ frame
        overlap_derivative = (self.vacant @ derivative.reshape(self.size, -1)).reshape(-1, len(parameters))
        residual = np.concatenate((overlap.real.ravel(), overlap.imag.ravel()))
        jacobian = np.concatenate((overlap_derivative.real, overlap_derivative.imag), axis=0)
        self.last_parameters = parameters.copy()
        self.last_residual = residual
        self.last_jacobian = jacobian
        self.evaluations += 1
        return residual, jacobian

    def residual(self, parameters):
        return self.compute(parameters)[0]

    def jacobian(self, parameters):
        return self.compute(parameters)[1]

    def value_gradient(self, parameters):
        residual, jacobian = self.compute(parameters)
        return 0.5 * np.dot(residual, residual), jacobian.T @ residual

    def fast_value_gradient(self, parameters):
        cosine, factor, cosine_derivatives, factor_derivatives = coefficients(parameters)
        frame = self.initial.copy()
        history = []
        for index, (first, second) in enumerate(self.edges):
            upper, lower = frame[first].copy(), frame[second].copy()
            history.append((upper, lower))
            frame[first] = cosine[index] * upper - factor[index].conjugate() * lower
            frame[second] = factor[index] * upper + cosine[index] * lower
        overlap = self.vacant @ frame
        adjoint = self.vacant.conj().T @ overlap
        gradient = np.empty(len(parameters))
        for index in range(len(self.edges) - 1, -1, -1):
            first, second = self.edges[index]
            upper, lower = history[index]
            upper_adjoint, lower_adjoint = adjoint[first].copy(), adjoint[second].copy()
            upper_derivative = cosine_derivatives[index, :, None] * upper - factor_derivatives[index, :, None].conjugate() * lower
            lower_derivative = factor_derivatives[index, :, None] * upper + cosine_derivatives[index, :, None] * lower
            gradient[2 * index:2 * index + 2] = (upper_derivative @ upper_adjoint.conjugate() + lower_derivative @ lower_adjoint.conjugate()).real
            adjoint[first] = cosine[index] * upper_adjoint + factor[index].conjugate() * lower_adjoint
            adjoint[second] = -factor[index] * upper_adjoint + cosine[index] * lower_adjoint
        return 0.5 * np.vdot(overlap, overlap).real, gradient


def gate_parameters(gates):
    return np.array([[gate['theta'] * math.cos(gate['phi']), gate['theta'] * math.sin(gate['phi'])]
                     for gate in gates]).ravel()


def parameters_gates(edges, parameters):
    gates = []
    for (first, second), (horizontal, vertical) in zip(edges, parameters.reshape(-1, 2)):
        theta = float(np.hypot(horizontal, vertical))
        phi = float(np.arctan2(vertical, horizontal))
        theta = (theta + math.pi) % (2 * math.pi) - math.pi
        gates.append(dict(u=int(first), v=int(second), theta=theta, phi=phi))
    return gates


def fit(instance, edges, parameters=None, max_evaluations=500, tolerance=1e-12):
    objective = Objective(instance, edges)
    if parameters is None:
        parameters = np.random.default_rng(42).normal(0, 0.1, 2 * len(edges))
    result = least_squares(objective.residual, parameters, jac=objective.jacobian,
                           ftol=tolerance, xtol=tolerance, gtol=tolerance,
                           max_nfev=max_evaluations,
                           method='lm' if len(parameters) <= 2 * instance['n_particles'] * (instance['n_modes'] - instance['n_particles']) else 'trf')
    error = float(np.linalg.norm(result.fun) * math.sqrt(2))
    return result.x, error, result.nfev


def check_derivative():
    from scipy.optimize._numdiff import approx_derivative
    instance = load_instances()[0]
    edges = instance['edges'] * 2
    parameters = np.random.default_rng(0).normal(0, 0.1, 2 * len(edges))
    objective = Objective(instance, edges)
    difference = objective.jacobian(parameters) - approx_derivative(objective.residual, parameters)
    print('derivative error', np.linalg.norm(difference), flush=True)


if __name__ == '__main__':
    check_derivative()
