import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
from scipy.fft import fftn, ifftn
from scipy.interpolate import BSpline
from scipy.optimize import Bounds, LinearConstraint, minimize

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/xmds2_fast_scalable_simulation_of_coupled_stochastic_partial_different__1204_4255/concept_3/participant')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'workspace'))
import field_control as fc

PROTOCOL = fc.read_json(ROOT / 'input/protocol.json')
PUBLIC = fc.read_json(ROOT / 'input/public_cases.json')
BASE = fc.read_json(ROOT / 'baseline/control.json')
KNOTS = fc.knot_vector(PROTOCOL)


def artifact(coefficients):
    return {'schema_version': 1, 'controls': {name: coefficients[index].tolist() for index, name in enumerate(fc.CHANNELS)}}


def coefficients_from(path):
    return np.array([fc.read_json(path)['controls'][name] for name in fc.CHANNELS])


class Problem:
    def __init__(self, cases, shape=(48, 24), dt=0.05, risk=0.0, leakage=0.0, minimax=0.0):
        self.cases = cases
        self.shape = shape
        self.dt = dt
        self.risk = risk
        self.minimax = minimax
        self.initial, self.target, residual = fc.references(cases, shape, OUT / 'cache')
        self.position_x, self.position_y, kinetic, self.volume = fc.geometry(shape)
        self.boundary = (np.abs(self.position_x) >= 7.9) | (np.abs(self.position_y) >= 4.5)
        self.leakage_weight = leakage * dt / 8 * self.volume / len(cases)
        self.parameters = fc.case_arrays(cases)
        self.kinetic_phase = np.exp(-0.5j * dt * kinetic)
        self.steps = round(8 / dt)
        self.basis = BSpline(KNOTS, np.eye(25), 3)((np.arange(self.steps) + 0.5) * dt)
        self.fixed = coefficients_from(ROOT / 'baseline/control.json')
        self.fixed[:, 3:-3] = 0
        self.history = np.empty((self.steps, 4) + self.initial.shape, dtype=np.complex128)
        self.evaluations = 0
        self.started = time.monotonic()
        self.last_values = None

    def unpack(self, vector):
        coefficients = self.fixed.copy()
        coefficients[:, 3:-3] = vector.reshape(6, 19)
        return coefficients

    def kinetic(self, state, backwards=False, full=False):
        phase = self.kinetic_phase.conj() if backwards else self.kinetic_phase
        if full:
            phase = phase * phase
        return ifftn(fftn(state, axes=fc.AXES) * phase, axes=fc.AXES)

    def local_reverse(self, state, phase, adjoint):
        imaginary = np.imag(np.conj(adjoint) * state * phase)
        coupling = self.parameters['g']
        cross = self.parameters['cross_ratio']
        correction = np.stack((coupling * (imaginary[:, 0] + cross * imaginary[:, 1]), coupling * (cross * imaginary[:, 0] + self.parameters['self_ratio'] * imaginary[:, 1])), axis=1)
        return phase.conj() * adjoint + self.dt * state * correction, self.dt * imaginary

    def evaluate(self, vector, gradient=True):
        controls = self.basis @ self.unpack(vector).T
        state = self.initial.copy()
        leakage_loss = np.zeros(len(self.cases))
        gain = self.parameters['rf_gain']
        for step, values in enumerate(controls):
            trap = fc.potential(self.parameters, self.position_x, self.position_y, values)
            state = self.kinetic(state, full=step > 0)
            if self.leakage_weight:
                leakage_loss += self.leakage_weight * np.sum(np.abs(state) ** 2 * self.boundary, axis=(1, 2, 3))
            first_phase = np.exp(-0.5j * self.dt * (trap + fc.nonlinear_potential(state, self.parameters)))
            if gradient:
                self.history[step, 0] = state
                self.history[step, 1] = first_phase
            state = fc.rotate(state * first_phase, gain * values[2], gain * values[3], self.dt)
            second_phase = np.exp(-0.5j * self.dt * (trap + fc.nonlinear_potential(state, self.parameters)))
            if gradient:
                self.history[step, 2] = state
                self.history[step, 3] = second_phase
            state = state * second_phase
        state = self.kinetic(state)
        if self.leakage_weight:
            leakage_loss += self.leakage_weight * np.sum(np.abs(state) ** 2 * self.boundary, axis=(1, 2, 3))
        overlap = self.volume * np.sum(self.target.conj() * state, axis=(1, 2, 3))
        losses = 1 - np.abs(overlap) ** 2
        weights = np.full(len(losses), 1 / len(losses))
        loss = np.mean(losses)
        if self.risk:
            loss += self.risk * np.mean(losses ** 2)
            weights *= 1 + 2 * self.risk * losses
        loss += np.sum(leakage_loss)
        leakage_factor = 1
        if self.minimax:
            weights = np.ones(len(losses))
            leakage_factor = len(losses)
            case_costs = losses + leakage_loss * len(losses)
        self.last_values = 1 - losses
        if not gradient:
            return case_costs if self.minimax else loss
        adjoint = -self.volume * (weights * overlap)[:, None, None, None] * self.target
        if self.leakage_weight:
            adjoint += leakage_factor * self.leakage_weight * self.boundary * state
        control_gradient = np.zeros((self.steps, len(self.cases), 6))
        for step in range(self.steps - 1, -1, -1):
            values = controls[step]
            first_state, first_phase, second_state, second_phase = self.history[step]
            adjoint = self.kinetic(adjoint, backwards=True, full=step < self.steps - 1)
            adjoint, second_potential_gradient = self.local_reverse(second_state, second_phase, adjoint)
            drive_x, drive_y = gain * values[2], gain * values[3]
            radius = np.hypot(drive_x, drive_y)
            cosine = np.cos(0.5 * self.dt * radius)
            sine = 0.5 * self.dt * np.sinc(0.5 * self.dt * radius / np.pi)
            factor = np.divide(0.5 * self.dt * cosine - sine, radius ** 2, out=np.full_like(radius, -(0.5 * self.dt) ** 3 / 3), where=radius > 1e-10)
            rf_input = first_state * first_phase
            hamiltonian_input = np.stack(((drive_x - 1j * drive_y) * rf_input[:, 1], (drive_x + 1j * drive_y) * rf_input[:, 0]), axis=1)
            for channel, drive in ((2, drive_x), (3, drive_y)):
                pauli = rf_input[:, ::-1].copy()
                if channel == 3:
                    pauli[:, 0] *= -1j
                    pauli[:, 1] *= 1j
                derivative = (-0.5 * self.dt * sine * drive)[:, None] * rf_input - 1j * (factor * drive)[:, None] * hamiltonian_input - 1j * sine[:, None] * pauli
                control_gradient[step, :, channel] = 2 * np.real(np.sum(adjoint.conj() * derivative * gain[:, None], axis=(1, 2, 3)))
            adjoint = fc.rotate(adjoint, -drive_x, -drive_y, self.dt)
            adjoint, first_potential_gradient = self.local_reverse(first_state, first_phase, adjoint)
            if self.leakage_weight:
                adjoint += leakage_factor * self.leakage_weight * self.boundary * first_state
            potential_gradient = first_potential_gradient + second_potential_gradient
            left = self.position_x - values[0] + values[1]
            right = self.position_x - values[0] - values[1]
            frequency = self.parameters['trap_x'] ** 2
            left_gradient, right_gradient = potential_gradient[:, 0], potential_gradient[:, 1]
            control_gradient[step, :, 0] = -np.sum(frequency * values[5] * (left_gradient * left + right_gradient * right), axis=(-2, -1))
            control_gradient[step, :, 1] = np.sum(frequency * values[5] * (left_gradient * left - right_gradient * right), axis=(-2, -1))
            control_gradient[step, :, 4] = 0.5 * np.sum(left_gradient - right_gradient, axis=(-2, -1))
            control_gradient[step, :, 5] = 0.5 * np.sum(frequency * (left_gradient * left ** 2 + right_gradient * right ** 2), axis=(-2, -1))
        gradient_coefficients = np.einsum('tbc,tk->bck', control_gradient, self.basis)[:, :, 3:-3].reshape(len(self.cases), 114)
        self.evaluations += 1
        if not getattr(self, 'quiet', False):
            print('eval', self.evaluations, 'seconds', round(time.monotonic() - self.started, 1), 'mean', round(float(np.mean(1 - losses)), 8), 'worst', round(float(np.min(1 - losses)), 8), 'loss', round(float(loss), 9), flush=True)
        if self.minimax:
            return case_costs * 100, gradient_coefficients * 100
        return loss * 100, gradient_coefficients.sum(axis=0) * 100


def worker(connection, cases, shape, dt, risk, leakage, minimax):
    problem = Problem(cases, shape, dt, risk, leakage, minimax)
    problem.quiet = True
    while True:
        request = connection.recv()
        if request is None:
            return
        vector, gradient = request
        result = problem.evaluate(vector, gradient)
        connection.send((result, problem.last_values))


class ParallelProblem(Problem):
    def __init__(self, cases, shape, dt, risk, workers, leakage=0.0, minimax=0.0):
        self.fixed = coefficients_from(ROOT / 'baseline/control.json')
        self.fixed[:, 3:-3] = 0
        self.connections = []
        self.processes = []
        self.sizes = []
        self.evaluations = 0
        self.started = time.monotonic()
        self.minimax = minimax
        for indices in np.array_split(np.arange(len(cases)), workers):
            parent, child = mp.Pipe()
            process = mp.Process(target=worker, args=(child, [cases[index] for index in indices], shape, dt, risk, leakage, minimax))
            process.start()
            self.connections.append(parent)
            self.processes.append(process)
            self.sizes.append(len(indices))

    def evaluate(self, vector, gradient=True):
        for connection in self.connections:
            connection.send((vector, gradient))
        outputs = [connection.recv() for connection in self.connections]
        self.last_values = np.concatenate([output[1] for output in outputs])
        if not gradient:
            if self.minimax:
                costs = np.concatenate([output[0] for output in outputs])
                maximum = np.max(costs)
                return maximum + np.log(np.mean(np.exp(self.minimax * (costs - maximum)))) / self.minimax + 0.2 * np.mean(costs)
            return sum(output[0] * size for output, size in zip(outputs, self.sizes)) / sum(self.sizes)
        if not self.minimax:
            loss = sum(output[0][0] * size for output, size in zip(outputs, self.sizes)) / sum(self.sizes)
            jacobian = sum(output[0][1] * size for output, size in zip(outputs, self.sizes)) / sum(self.sizes)
        if self.minimax:
            costs = np.concatenate([output[0][0] for output in outputs]) / 100
            derivatives = np.concatenate([output[0][1] for output in outputs]) / 100
            maximum = np.max(costs)
            exponentials = np.exp(self.minimax * (costs - maximum))
            weights = exponentials / np.sum(exponentials)
            loss = 100 * (maximum + np.log(np.mean(exponentials)) / self.minimax + 0.2 * np.mean(costs))
            jacobian = 100 * (weights @ derivatives + 0.2 * np.mean(derivatives, axis=0))
        self.evaluations += 1
        print('eval', self.evaluations, 'seconds', round(time.monotonic() - self.started, 1), 'mean', round(float(np.mean(self.last_values)), 8), 'worst', round(float(np.min(self.last_values)), 8), 'loss', round(float(loss / 100), 9), flush=True)
        return loss, jacobian

    def close(self):
        for connection in self.connections:
            connection.send(None)
        for process in self.processes:
            process.join()


def constraints(problem):
    lower, upper, matrices, limits = [], [], [], []
    for channel, name in enumerate(fc.CHANNELS):
        rule = PROTOCOL['channels'][name]
        lower.extend([rule['range'][0]] * 19)
        upper.extend([rule['range'][1]] * 19)
        for degree, bound in ((1, rule['slew']), (2, rule['acceleration'])):
            matrix = BSpline(KNOTS, np.eye(25), 3).derivative(degree).c
            block = np.zeros((len(matrix), 114))
            block[:, channel * 19:(channel + 1) * 19] = matrix[:, 3:-3]
            constant = matrix @ problem.fixed[channel]
            matrices.append(block)
            limits.append((np.full(len(matrix), -bound + 2e-8) - constant, np.full(len(matrix), bound - 2e-8) - constant))
    matrix = np.concatenate(matrices)
    linear = LinearConstraint(matrix, np.concatenate([pair[0] for pair in limits]), np.concatenate([pair[1] for pair in limits]))

    def radius(vector):
        coefficients = vector.reshape(6, 19)
        return 2.8 ** 2 - 2e-8 - coefficients[2] ** 2 - coefficients[3] ** 2

    def radius_jac(vector):
        coefficients = vector.reshape(6, 19)
        jacobian = np.zeros((19, 114))
        indices = np.arange(19)
        jacobian[indices, 38 + indices] = -2 * coefficients[2]
        jacobian[indices, 57 + indices] = -2 * coefficients[3]
        return jacobian

    return Bounds(lower, upper), [linear, {'type': 'ineq', 'fun': radius, 'jac': radius_jac}]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default=str(ROOT / 'baseline/control.json'))
    parser.add_argument('--cases')
    parser.add_argument('--iterations', type=int, default=100)
    parser.add_argument('--nx', type=int, default=48)
    parser.add_argument('--ny', type=int, default=24)
    parser.add_argument('--dt', type=float, default=0.05)
    parser.add_argument('--risk', type=float, default=10)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--name', default='control')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--scale', type=float, default=100)
    parser.add_argument('--seconds', type=float, default=1e8)
    parser.add_argument('--leakage', type=float, default=0)
    parser.add_argument('--minimax', type=float, default=0)
    args = parser.parse_args()
    cases = fc.read_json(args.cases) if args.cases else PUBLIC
    problem = Problem(cases, (args.nx, args.ny), args.dt, args.risk, args.leakage, args.minimax) if args.workers == 1 else ParallelProblem(cases, (args.nx, args.ny), args.dt, args.risk, args.workers, args.leakage, args.minimax)
    vector = coefficients_from(args.start)[:, 3:-3].ravel()
    bounds, restrictions = constraints(problem)
    if args.check:
        loss, jacobian = problem.evaluate(vector)
        random = np.random.default_rng(123)
        for index in random.choice(len(vector), 8, replace=False):
            direction = np.zeros_like(vector)
            direction[index] = 1e-5
            finite = (problem.evaluate(vector + direction, False) - problem.evaluate(vector - direction, False)) * 100 / 2e-5
            print('gradient', index, jacobian[index], finite, flush=True)
        return
    iteration = 0
    best_loss = np.inf
    best_vector = vector.copy()

    def objective(current):
        nonlocal best_loss, best_vector
        loss, jacobian = problem.evaluate(current)
        if loss < best_loss:
            best_loss = loss
            best_vector = current.copy()
        if time.monotonic() - problem.started > args.seconds:
            raise TimeoutError('optimization time limit')
        return loss * args.scale / 100, jacobian * args.scale / 100

    def checkpoint(current):
        nonlocal iteration
        iteration += 1
        result = artifact(problem.unpack(current))
        try:
            fc.validate_artifact(result, PROTOCOL)
        except ValueError as error:
            projection = minimize(lambda candidate: (0.5 * np.sum((candidate - current) ** 2), candidate - current), current, jac=True, method='SLSQP', bounds=bounds, constraints=restrictions, options={'maxiter': 100, 'ftol': 1e-13})
            result = artifact(problem.unpack(projection.x))
            fc.validate_artifact(result, PROTOCOL)
            print('projected checkpoint', float(np.linalg.norm(projection.x - current)), flush=True)
        (OUT / (args.name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
        if iteration % 20 == 0:
            (OUT / (args.name + '_%03d.json' % iteration)).write_text(json.dumps(result) + '\n')
        print('checkpoint', iteration, flush=True)

    try:
        result = minimize(objective, vector, method='SLSQP', jac=True, bounds=bounds, constraints=restrictions, callback=checkpoint, options={'maxiter': args.iterations, 'ftol': 2e-9, 'disp': True})
        checkpoint(result.x)
        print(result.message, flush=True)
    except TimeoutError:
        checkpoint(best_vector)
        print('Time limit reached', flush=True)
    finally:
        if args.workers > 1:
            problem.close()


if __name__ == '__main__':
    main()
