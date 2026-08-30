import argparse
import json
import multiprocessing
import sys
import time
from pathlib import Path

import numpy as np
from scipy.fft import dct, fft, ifft, fftn, ifftn
from scipy.interpolate import BSpline
from scipy.optimize import Bounds, LinearConstraint, minimize

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/xmds2_fast_scalable_simulation_of_coupled_stochastic_partial_different__1204_4255/concept_3/participant')
sys.path.insert(0, str(ROOT / 'workspace'))
import field_control as fc

PROTOCOL = fc.read_json(ROOT / 'input/protocol.json')
PUBLIC = fc.read_json(ROOT / 'input/public_cases.json')
AXES = (-2, -1)
BASE = np.array([[PROTOCOL['channels'][name]['start']] * 3 + [0.] * 19 + [PROTOCOL['channels'][name]['end']] * 3 for name in fc.CHANNELS])
KNOTS = fc.knot_vector(PROTOCOL)


def unpack(vector):
    coefficients = BASE.copy()
    coefficients[:, 3:22] = vector.reshape(6, 19)
    return coefficients


def artifact(coefficients):
    return {'schema_version': 1, 'controls': {name: values.tolist() for name, values in zip(fc.CHANNELS, coefficients)}}


def load(path):
    control = fc.read_json(path)['controls']
    return np.array([control[name] for name in fc.CHANNELS])[:, 3:22].ravel()


def constraints():
    basis = BSpline(KNOTS, np.eye(25), 3)
    matrices, lowers, uppers = [], [], []
    low, high = [], []
    for channel, name in enumerate(fc.CHANNELS):
        limits = PROTOCOL['channels'][name]
        low.extend([limits['range'][0]] * 19)
        high.extend([limits['range'][1]] * 19)
        for degree, bound in [(1, limits['slew']), (2, limits['acceleration'])]:
            derivative = basis.derivative(degree).c
            matrix = np.zeros((len(derivative), 114))
            matrix[:, channel * 19:(channel + 1) * 19] = derivative[:, 3:22]
            offset = derivative @ BASE[channel]
            matrices.append(matrix)
            lowers.extend(-bound - offset)
            uppers.extend(bound - offset)
    linear = LinearConstraint(np.vstack(matrices), lowers, uppers)

    def radius(vector):
        values = vector.reshape(6, 19)
        return 2.799 ** 2 - values[2] ** 2 - values[3] ** 2

    def radius_jac(vector):
        values = vector.reshape(6, 19)
        jacobian = np.zeros((19, 114))
        jacobian[:, 38:57] = np.diag(-2 * values[2])
        jacobian[:, 57:76] = np.diag(-2 * values[3])
        return jacobian

    return Bounds(low, high), [linear, {'type': 'ineq', 'fun': radius, 'jac': radius_jac}]


def make_cases(mode):
    if mode == 'public':
        return PUBLIC
    if mode.endswith('.json'):
        return fc.read_json(mode)
    cases = PUBLIC.copy()
    random = np.random.default_rng(813)
    names = list(PROTOCOL['uncertainty'])
    count = int(mode)
    for index in range(count):
        values = dict(PROTOCOL['nominal'])
        signs = random.choice([-1., 1.], 8) if index < count // 2 else random.uniform(-1, 1, 8)
        for name, sign in zip(names, signs):
            lower, upper = PROTOCOL['uncertainty'][name]
            values[name] = (lower + upper) / 2 + sign * (upper - lower) / 2
        cases.append(dict(id='joint_%02d' % index, family='joint', **values))
    return cases


class Objective:
    def __init__(self, cases, shape, dt, risk=0., record=True, leak=0., symmetric=False):
        self.cases = cases
        self.shape = shape
        self.dt = dt
        self.risk = risk
        self.record = record
        self.leak = leak
        self.symmetric = symmetric
        self.density_scale = 1.
        self.steps = round(8 / dt)
        self.position_x, self.position_y, kinetic, self.volume = fc.geometry(shape)
        self.boundary = (np.abs(self.position_x) >= 7.5) | (np.abs(self.position_y) >= 4.5)
        self.parameters = fc.case_arrays(cases)
        self.initial, self.target, residual = fc.references(cases, shape, Path('cache'))
        if symmetric:
            indices = np.r_[np.arange(shape[1] // 2, shape[1]), 0]
            self.density_scale = np.full(shape[1] // 2 + 1, 2.)
            self.density_scale[[0, -1]] = 1.
            self.initial = self.initial[..., indices] * np.sqrt(self.density_scale)
            self.target = self.target[..., indices] * np.sqrt(self.density_scale)
            self.position_y = (12 / shape[1] * np.arange(shape[1] // 2 + 1))[None, :]
            momentum_x = 2 * np.pi * np.fft.fftfreq(shape[0], 20 / shape[0])[:, None]
            momentum_y = np.pi / 6 * np.arange(shape[1] // 2 + 1)[None, :]
            kinetic = .5 * (momentum_x ** 2 + momentum_y ** 2)
            self.boundary = (np.abs(self.position_x) >= 7.5) | (np.abs(self.position_y) >= 4.5)
        self.phase = np.exp(-1j * dt * kinetic)
        self.half_phase = np.exp(-.5j * dt * kinetic)
        self.basis = BSpline(KNOTS, np.eye(25), 3)((np.arange(self.steps) + .5) * dt)
        self.calls = 0
        self.started = time.time()
        self.best = np.inf
        self.last = None

    def kinetic(self, state, phase):
        if self.symmetric:
            spectrum = dct(fft(state, axis=-2, workers=1), type=1, norm='ortho', axis=-1, workers=1)
            return ifft(dct(spectrum * phase, type=1, norm='ortho', axis=-1, workers=1), axis=-2, workers=1)
        return ifftn(fftn(state, axes=AXES, workers=1) * phase, axes=AXES, workers=1)

    def nonlinear(self, state):
        density = np.abs(state) ** 2 / self.density_scale
        parameters = self.parameters
        left = parameters['g'] * (density[:, 0] + parameters['cross_ratio'] * density[:, 1])
        right = parameters['g'] * (parameters['self_ratio'] * density[:, 1] + parameters['cross_ratio'] * density[:, 0])
        return np.stack((left, right), axis=1)

    def nonlinear_back(self, before, adjoint, trap):
        half = self.dt / 2
        phase = np.exp(-1j * half * (trap + self.nonlinear(before)))
        after = phase * before
        imaginary = (np.conj(adjoint) * after).imag
        parameters = self.parameters
        left = parameters['g'] * (imaginary[:, 0] + parameters['cross_ratio'] * imaginary[:, 1])
        right = parameters['g'] * (parameters['self_ratio'] * imaginary[:, 1] + parameters['cross_ratio'] * imaginary[:, 0])
        adjoint = np.conj(phase) * adjoint + 2 * half * before * np.stack((left, right), axis=1) / self.density_scale
        return adjoint, 2 * half * imaginary * self.volume

    def evaluate(self, vector):
        coefficients = unpack(vector)
        controls = self.basis @ coefficients.T
        state = self.kinetic(self.initial, self.half_phase)
        tape = np.empty((self.steps, 3) + state.shape, dtype=np.complex128)
        gain = self.parameters['rf_gain']
        leakage = 0.
        leak_factor = self.leak / (self.steps * len(self.cases))
        for index, control in enumerate(controls):
            trap = fc.potential(self.parameters, self.position_x, self.position_y, control)
            tape[index, 0] = state
            state = state * np.exp(-.5j * self.dt * (trap + self.nonlinear(state)))
            tape[index, 1] = state
            state = fc.rotate(state, gain * control[2], gain * control[3], self.dt)
            tape[index, 2] = state
            state = state * np.exp(-.5j * self.dt * (trap + self.nonlinear(state)))
            state = self.kinetic(state, self.half_phase if index == self.steps - 1 else self.phase)
            if self.leak:
                leakage += leak_factor * self.volume * np.sum(np.abs(state) ** 2 * self.boundary)
        overlaps = self.volume * np.sum(np.conj(self.target) * state, axis=(1, 2, 3))
        fidelities = np.abs(overlaps) ** 2
        errors = 1 - fidelities
        weights = (1 + 2 * self.risk * errors) / len(errors)
        loss = np.mean(errors + self.risk * errors ** 2) + leakage
        adjoint = -weights[:, None, None, None] * overlaps[:, None, None, None] * self.target
        gradient = np.zeros_like(controls)
        for index in range(self.steps - 1, -1, -1):
            if self.leak:
                current = state if index == self.steps - 1 else tape[index + 1, 0]
                adjoint += leak_factor * self.boundary * current
            control = controls[index]
            trap = fc.potential(self.parameters, self.position_x, self.position_y, control)
            adjoint = self.kinetic(adjoint, np.conj(self.half_phase if index == self.steps - 1 else self.phase))
            adjoint, trap_gradient = self.nonlinear_back(tape[index, 2], adjoint, trap)
            drive_x, drive_y = gain * control[2], gain * control[3]
            radius = np.hypot(drive_x, drive_y)
            angle = .5 * self.dt * radius
            sine_ratio = .5 * self.dt * np.sinc(angle / np.pi)
            derivative_ratio = np.where(radius > 1e-6, (.5 * self.dt * np.cos(angle) - sine_ratio) / np.maximum(radius ** 2, 1e-24), -(self.dt / 2) ** 3 / 3)
            before = tape[index, 1]
            coupling = drive_x - 1j * drive_y
            coupled = np.stack((coupling * before[:, 1], coupling.conj() * before[:, 0]), axis=1)
            for channel, drive, factor in [(2, drive_x, 1.), (3, drive_y, -1j)]:
                derivative = (-.5 * self.dt * np.sin(angle) * drive / np.maximum(radius, 1e-24))[:, None] * before
                derivative -= 1j * (derivative_ratio * drive)[:, None] * coupled
                direction = np.stack((factor * before[:, 1], np.conj(factor) * before[:, 0]), axis=1)
                derivative -= 1j * sine_ratio[:, None] * direction
                gradient[index, channel] = 2 * self.volume * np.sum((np.conj(adjoint) * derivative).real * gain[:, None])
            adjoint = fc.rotate(adjoint, drive_x, drive_y, -self.dt)
            adjoint, trap_first = self.nonlinear_back(tape[index, 0], adjoint, trap)
            trap_gradient += trap_first
            axial = self.parameters['trap_x'] ** 2
            left = self.position_x - control[0] + control[1]
            right = self.position_x - control[0] - control[1]
            gradient[index, 0] = np.sum(-axial * control[5] * (left * trap_gradient[:, 0] + right * trap_gradient[:, 1]))
            gradient[index, 1] = np.sum(axial * control[5] * (left * trap_gradient[:, 0] - right * trap_gradient[:, 1]))
            gradient[index, 4] = .5 * np.sum(trap_gradient[:, 0] - trap_gradient[:, 1])
            gradient[index, 5] = .5 * np.sum(axial * (left ** 2 * trap_gradient[:, 0] + right ** 2 * trap_gradient[:, 1]))
        vector_gradient = (gradient.T @ self.basis)[:, 3:22].ravel()
        self.calls += 1
        self.last = (vector.copy(), loss, vector_gradient.copy(), fidelities.copy())
        if self.record and loss < self.best:
            try:
                fc.validate_artifact(artifact(coefficients), PROTOCOL)
                self.best = loss
                Path('best.tmp').write_text(json.dumps(artifact(coefficients), indent=2) + '\n')
                Path('best.tmp').replace('best.json')
            except ValueError:
                pass
        if self.record:
            print('eval', self.calls, 'seconds', round(time.time() - self.started, 1), 'loss', round(loss, 9), 'F', np.round(fidelities, 6).tolist(), 'grad', round(float(np.linalg.norm(vector_gradient)), 6), flush=True)
        return loss, vector_gradient


WORKER_OBJECTIVE = None


def worker_evaluate(task):
    global WORKER_OBJECTIVE
    cases, shape, dt, risk, leak, symmetric, vector = task
    if WORKER_OBJECTIVE is None or WORKER_OBJECTIVE.cases != cases:
        WORKER_OBJECTIVE = Objective(cases, shape, dt, risk, record=False, leak=leak, symmetric=symmetric)
    WORKER_OBJECTIVE.risk = risk
    WORKER_OBJECTIVE.leak = leak
    loss, gradient = WORKER_OBJECTIVE.evaluate(vector)
    return loss, gradient, WORKER_OBJECTIVE.last[3]


class Distributed:
    def __init__(self, cases, shape, dt, risk, workers, leak=0., symmetric=False, settings=''):
        self.groups = [cases[index::workers] for index in range(workers)]
        self.pools = [multiprocessing.Pool(1) for index in range(workers)]
        self.shape, self.dt, self.risk = shape, dt, risk
        self.leak = leak
        self.symmetric = symmetric
        self.settings = settings
        self.case_file = ''
        self.best = np.inf
        self.calls = 0
        self.started = time.time()

    def evaluate(self, vector):
        if self.settings:
            settings = fc.read_json(self.settings)
            if settings.get('stop', False):
                raise StopIteration('requested checkpoint stop')
            if settings.get('cases', '') != self.case_file:
                self.case_file = settings['cases']
                cases = make_cases(self.case_file)
                self.groups = [cases[index::len(self.pools)] for index in range(len(self.pools))]
                self.best = np.inf
            risk, leak = settings.get('risk', self.risk), settings.get('leak', self.leak)
            if (risk, leak) != (self.risk, self.leak):
                self.best = np.inf
                self.risk, self.leak = risk, leak
        pending = [pool.apply_async(worker_evaluate, ((group, self.shape, self.dt, self.risk, self.leak, self.symmetric, vector),)) for pool, group in zip(self.pools, self.groups)]
        results = [future.get() for future in pending]
        sizes = np.array([len(group) for group in self.groups])
        weights = sizes / sizes.sum()
        loss = sum(weight * result[0] for weight, result in zip(weights, results))
        gradient = sum(weight * result[1] for weight, result in zip(weights, results))
        fidelities = np.zeros(sizes.sum())
        for index, result in enumerate(results):
            fidelities[index::len(results)] = result[2]
        self.calls += 1
        Path('latest_raw.tmp').write_text(json.dumps(artifact(unpack(vector)), indent=2) + '\n')
        Path('latest_raw.tmp').replace('latest_raw.json')
        if loss < self.best:
            coefficients = unpack(vector)
            baseline = unpack(load(ROOT / 'baseline/control.json'))
            radius = np.max(np.hypot(coefficients[2], coefficients[3]))
            coefficients[2:4] *= min(1., (2.8 - 1e-9) / radius)
            coefficients = (1 - 1e-8) * coefficients + 1e-8 * baseline
            try:
                fc.validate_artifact(artifact(coefficients), PROTOCOL)
                self.best = loss
                Path('best.tmp').write_text(json.dumps(artifact(coefficients), indent=2) + '\n')
                Path('best.tmp').replace('best.json')
            except ValueError:
                pass
        print('eval', self.calls, 'seconds', round(time.time() - self.started, 1), 'loss', round(loss, 9), 'F', np.round(fidelities, 6).tolist(), 'grad', round(float(np.linalg.norm(gradient)), 6), flush=True)
        return loss, gradient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--initial', default=str(ROOT / 'baseline/control.json'))
    parser.add_argument('--cases', default='public')
    parser.add_argument('--nx', type=int, default=48)
    parser.add_argument('--ny', type=int, default=24)
    parser.add_argument('--dt', type=float, default=.04)
    parser.add_argument('--iterations', type=int, default=200)
    parser.add_argument('--risk', type=float, default=0.)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--leak', type=float, default=0.)
    parser.add_argument('--scale', type=float, default=1.)
    parser.add_argument('--symmetric', action='store_true')
    parser.add_argument('--precondition', action='store_true')
    parser.add_argument('--settings', default='')
    args = parser.parse_args()
    vector = load(args.initial)
    if args.workers == 1:
        objective = Objective(make_cases(args.cases), (args.nx, args.ny), args.dt, args.risk, leak=args.leak, symmetric=args.symmetric)
    else:
        objective = Distributed(make_cases(args.cases), (args.nx, args.ny), args.dt, args.risk, args.workers, args.leak, args.symmetric, args.settings)
    if args.check:
        value, gradient = objective.evaluate(vector)
        direction = np.random.default_rng(123).normal(size=114)
        direction /= np.linalg.norm(direction)
        epsilon = 1e-5
        positive = objective.evaluate(vector + epsilon * direction)[0]
        negative = objective.evaluate(vector - epsilon * direction)[0]
        print('CHECK', (positive - negative) / (2 * epsilon), gradient @ direction, flush=True)
        return
    bounds, cons = constraints()
    scaling = np.repeat([.2, .2, 1., 1., 1., .2], 19) if args.precondition else np.ones(114)
    physical_radius = cons[1]
    cons = [LinearConstraint(cons[0].A * scaling, cons[0].lb, cons[0].ub), {'type': 'ineq', 'fun': lambda values: physical_radius['fun'](values * scaling), 'jac': lambda values: physical_radius['jac'](values * scaling) * scaling}]
    bounds = Bounds(bounds.lb / scaling, bounds.ub / scaling)
    def scaled_objective(values):
        loss, gradient = objective.evaluate(values * scaling)
        return args.scale * loss, args.scale * gradient * scaling
    try:
        result = minimize(scaled_objective, vector / scaling, jac=True, method='SLSQP', bounds=bounds, constraints=cons, options={'maxiter': args.iterations, 'ftol': 1e-10, 'disp': True})
    except StopIteration:
        print('Stopped with checkpoint saved', flush=True)
        return
    Path('last.json').write_text(json.dumps(artifact(unpack(result.x * scaling)), indent=2) + '\n')
    print(result.message, flush=True)


if __name__ == '__main__':
    main()
