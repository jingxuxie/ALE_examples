import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
import json
import time
from pathlib import Path
import numpy as np
from scipy.fft import fftn, ifftn
from scipy.interpolate import BSpline
from scipy.optimize import minimize, LinearConstraint, NonlinearConstraint, Bounds

ROOT = Path(__file__).resolve().parents[2] / 'participant'
sys.path.insert(0, str(ROOT / 'workspace'))
import field_control as fc
PROTOCOL = json.loads((ROOT / 'input/protocol.json').read_text())
PUBLIC = json.loads((ROOT / 'input/public_cases.json').read_text())
CHANNELS = fc.CHANNELS
KNOTS = fc.knot_vector(PROTOCOL)
FIXED = np.zeros((6, 25))
for channel_index, channel in enumerate(CHANNELS):
    FIXED[channel_index, :3] = PROTOCOL['channels'][channel]['start']
    FIXED[channel_index, -3:] = PROTOCOL['channels'][channel]['end']

def coefficients(vector):
    result = FIXED.copy()
    result[:, 3:-3] = vector.reshape(6, 19)
    return result

def artifact(vector):
    values = coefficients(vector)
    return {'schema_version': 1, 'controls': {name: values[index].tolist() for index, name in enumerate(CHANNELS)}}

def load(path):
    data = json.loads(Path(path).read_text())
    return np.array([data['controls'][name][3:-3] for name in CHANNELS]).ravel()

def write(path, vector):
    Path(path).write_text(json.dumps(artifact(vector), indent=2) + '\n')

def cases_for(mode):
    if mode == 'public':
        return PUBLIC
    if Path(mode).exists():
        return json.loads(Path(mode).read_text())
    rng = np.random.default_rng(8235)
    cases = PUBLIC.copy()
    for family, count, keys in [('interaction', 4, ['g', 'self_ratio', 'cross_ratio']), ('calibration', 4, ['rf_gain', 'bias', 'gradient']), ('trap', 4, ['trap_x', 'trap_y', 'gradient']), ('joint', 8, list(PROTOCOL['uncertainty']))]:
        for index in range(count):
            case = dict(PROTOCOL['nominal'], id=family + str(index), family=family)
            for key in keys:
                limits = PROTOCOL['uncertainty'][key]
                fraction = float(rng.integers(2)) if index < 4 else float(rng.uniform())
                case[key] = limits[0] + fraction * (limits[1] - limits[0])
            cases.append(case)
    return cases

class Objective:
    def __init__(self, cases, shape=(64, 32), dt=0.04, risk=0.0, boundary_weight=0.0):
        self.cases = cases
        self.shape = shape
        self.dt = dt
        self.risk = risk
        self.boundary_weight = boundary_weight
        self.initial, self.target, self.residual = fc.references(cases, shape, Path('cache'))
        self.parameters = fc.case_arrays(cases)
        self.position_x, self.position_y, kinetic, self.volume = fc.geometry(shape)
        self.boundary_mask = (np.abs(self.position_x) >= 7.7) | (np.abs(self.position_y) >= 4.6)
        self.phase = np.exp(-0.5j * dt * kinetic)
        self.full_phase = self.phase ** 2
        self.steps = int(round(8 / dt))
        self.basis = BSpline(KNOTS, np.eye(25), 3)((np.arange(self.steps) + 0.5) * dt)
        history_shape = (self.steps, 2) + self.initial.shape
        history_dtype = np.complex64 if np.prod(history_shape) * 16 > 200000000 else np.complex128
        self.history = np.empty(history_shape, dtype=np.complex128)
        self.calls = 0
        self.started = time.monotonic()
        self.last_vector = None

    def kinetic(self, state, reverse=False, full=False):
        phase = self.full_phase if full else self.phase
        return ifftn(fftn(state, axes=(-2, -1)) * (phase.conj() if reverse else phase), axes=(-2, -1))

    def local_backward(self, state, adjoint, trap):
        half = self.dt / 2
        phase = np.exp(1j * half * (trap + fc.nonlinear_potential(state, self.parameters)))
        original = state * phase
        imaginary = np.imag(np.conj(adjoint) * state)
        left = self.parameters['g'] * (imaginary[:, 0] + self.parameters['cross_ratio'] * imaginary[:, 1])
        right = self.parameters['g'] * (self.parameters['self_ratio'] * imaginary[:, 1] + self.parameters['cross_ratio'] * imaginary[:, 0])
        return adjoint * phase + 2 * half * original * np.stack((left, right), axis=1), 2 * half * imaginary

    def __call__(self, vector):
        if self.last_vector is not None and np.array_equal(self.last_vector, vector):
            return self.last_result
        controls = self.basis @ coefficients(vector).T
        parameters = self.parameters
        state = self.kinetic(self.initial)
        monitored_states = {}
        for index, values in enumerate(controls):
            trap = fc.potential(parameters, self.position_x, self.position_y, values)
            state *= np.exp(-0.5j * self.dt * (trap + fc.nonlinear_potential(state, parameters)))
            self.history[index, 0] = state
            state = fc.rotate(state, parameters['rf_gain'] * values[2], parameters['rf_gain'] * values[3], self.dt)
            state *= np.exp(-0.5j * self.dt * (trap + fc.nonlinear_potential(state, parameters)))
            self.history[index, 1] = state
            if self.boundary_weight and (index % 10 == 0 or index == self.steps - 1):
                monitored_states[index] = self.kinetic(state)
            state = self.kinetic(state, full=index < self.steps - 1)
        overlap = self.volume * np.sum(self.target.conj() * state, axis=(1, 2, 3))
        self.scores = np.abs(overlap) ** 2
        errors = 1 - self.scores
        weights = np.array([case.get('weight', 1.0) for case in self.cases])
        weights /= np.sum(weights)
        objective = np.sum(weights * errors)
        boundary_weights = weights.copy()
        monitor_weights = {}
        if self.boundary_weight:
            boundary_weights *= self.boundary_weight / len(monitored_states)
            for monitor_index, monitored_state in monitored_states.items():
                mass = self.volume * np.sum(np.abs(monitored_state) ** 2 * self.boundary_mask, axis=(1, 2, 3))
                excess = np.maximum(mass - 1e-9, 0)
                objective += np.sum(boundary_weights * excess ** 2 / 2e-9)
                monitor_weights[monitor_index] = boundary_weights * excess / 1e-9
        if self.risk < 0:
            excess = np.maximum(errors - 0.017, 0.0)
            objective -= self.risk * np.sum(weights * excess ** 2)
            weights *= 1 - 2 * self.risk * excess
        elif self.risk:
            objective += self.risk * np.sum(weights * errors ** 2)
            weights *= 1 + 2 * self.risk * errors
        adjoint = -(weights * overlap)[:, None, None, None] * self.target * self.volume
        adjoint = self.kinetic(adjoint, reverse=True)
        gradients = np.zeros_like(controls)
        for index in range(self.steps - 1, -1, -1):
            values = controls[index]
            trap = fc.potential(parameters, self.position_x, self.position_y, values)
            if index in monitored_states:
                adjoint += self.kinetic(self.volume * monitor_weights[index][:, None, None, None] * monitored_states[index] * self.boundary_mask, reverse=True)
            adjoint, trap_gradient = self.local_backward(self.history[index, 1], adjoint, trap)
            original = self.history[index, 0]
            radius = np.hypot(values[2], values[3])
            factor = self.dt * parameters['rf_gain'] / 2
            angle = factor * radius
            cosine = np.cos(angle)
            sine_over = factor * np.sinc(angle / np.pi)
            if radius > 1e-6:
                derivative_over = (angle * cosine - np.sin(angle)) / radius ** 3
            else:
                derivative_over = -factor ** 3 / 3 + factor ** 5 * radius ** 2 / 30
            coupled = np.stack(((values[2] - 1j * values[3]) * original[:, 1], (values[2] + 1j * values[3]) * original[:, 0]), axis=1)
            for offset in range(2):
                sigma = original[:, ::-1] if offset == 0 else np.stack((-1j * original[:, 1], 1j * original[:, 0]), axis=1)
                derivative = -(factor * sine_over * values[2 + offset])[:, None] * original - 1j * (derivative_over * values[2 + offset])[:, None] * coupled - 1j * sine_over[:, None] * sigma
                gradients[index, 2 + offset] = 2 * np.real(np.sum(adjoint.conj() * derivative))
            adjoint = fc.rotate(adjoint, parameters['rf_gain'] * values[2], parameters['rf_gain'] * values[3], -self.dt)
            adjoint, first_gradient = self.local_backward(self.history[index, 0], adjoint, trap)
            trap_gradient += first_gradient
            displacement = np.stack((np.broadcast_to(self.position_x - values[0] + values[1], self.shape), np.broadcast_to(self.position_x - values[0] - values[1], self.shape)), axis=0)[None]
            trap_force = parameters['trap_x'][:, None] ** 2 * values[5] * displacement
            gradients[index, 0] = -np.sum(trap_gradient * trap_force)
            gradients[index, 1] = np.sum(trap_gradient[:, 0] * trap_force[:, 0]) - np.sum(trap_gradient[:, 1] * trap_force[:, 1])
            gradients[index, 4] = 0.5 * (np.sum(trap_gradient[:, 0]) - np.sum(trap_gradient[:, 1]))
            gradients[index, 5] = 0.5 * np.sum(trap_gradient * parameters['trap_x'][:, None] ** 2 * displacement ** 2)
            if index > 0:
                adjoint = self.kinetic(adjoint, reverse=True, full=True)
        result_gradient = (gradients.T @ self.basis)[:, 3:-3].ravel()
        self.calls += 1
        self.last_vector = vector.copy()
        self.last_result = float(objective), result_gradient
        return self.last_result

def objective_worker(connection, cases, shape, dt, risk, boundary_weight):
    objective = Objective(cases, shape, dt, risk, boundary_weight)
    connection.send(True)
    while True:
        vector = connection.recv()
        if vector is None:
            return
        value, gradient = objective(vector)
        connection.send((value, gradient, objective.scores))

class ParallelObjective:
    def __init__(self, cases, shape, dt, risk, workers, boundary_weight=0.0):
        import multiprocessing
        self.cases = cases
        self.started = time.monotonic()
        self.calls = 0
        self.last_vector = None
        self.connections = []
        self.processes = []
        self.weights = []
        context = multiprocessing.get_context('fork')
        for indices in np.array_split(np.arange(len(cases)), workers):
            parent, child = context.Pipe()
            process = context.Process(target=objective_worker, args=(child, [cases[index] for index in indices], shape, dt, risk, boundary_weight), daemon=True)
            process.start()
            self.connections.append(parent)
            self.processes.append(process)
            self.weights.append(sum(cases[index].get('weight', 1.0) for index in indices) / sum(case.get('weight', 1.0) for case in cases))
        for connection in self.connections:
            connection.recv()

    def __call__(self, vector):
        if self.last_vector is not None and np.array_equal(self.last_vector, vector):
            return self.last_result
        for connection in self.connections:
            connection.send(vector)
        results = [connection.recv() for connection in self.connections]
        self.scores = np.concatenate([result[2] for result in results])
        self.last_result = (sum(weight * result[0] for weight, result in zip(self.weights, results)), sum(weight * result[1] for weight, result in zip(self.weights, results)))
        self.last_vector = vector.copy()
        self.calls += 1
        return self.last_result

def constraints():
    rows, lower, upper = [], [], []
    bounds_lower, bounds_upper = [], []
    for channel_index, channel in enumerate(CHANNELS):
        limits = PROTOCOL['channels'][channel]
        bounds_lower.extend([limits['range'][0]] * 19)
        bounds_upper.extend([limits['range'][1]] * 19)
        for order, label in [(1, 'slew'), (2, 'acceleration')]:
            derivative = BSpline(KNOTS, np.eye(25), 3).derivative(order).c
            matrix = np.zeros((len(derivative), 114))
            matrix[:, channel_index * 19:(channel_index + 1) * 19] = derivative[:, 3:-3]
            offset = derivative @ FIXED[channel_index]
            rows.append(matrix)
            lower.extend(-limits[label] + 1e-8 - offset)
            upper.extend(limits[label] - 1e-8 - offset)
    linear = LinearConstraint(np.concatenate(rows), np.array(lower), np.array(upper))
    def circles(vector):
        values = vector.reshape(6, 19)
        return values[2] ** 2 + values[3] ** 2
    def circle_jac(vector):
        values = vector.reshape(6, 19)
        matrix = np.zeros((19, 114))
        matrix[:, 38:57] = np.diag(2 * values[2])
        matrix[:, 57:76] = np.diag(2 * values[3])
        return matrix
    nonlinear = NonlinearConstraint(circles, np.full(19, -np.inf), np.full(19, 2.8 ** 2 - 1e-8), jac=circle_jac)
    return Bounds(bounds_lower, bounds_upper), [linear, nonlinear]

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default=str(ROOT / 'baseline/control.json'))
    parser.add_argument('--output', default='control.json')
    parser.add_argument('--cases', default='public')
    parser.add_argument('--iterations', type=int, default=200)
    parser.add_argument('--dt', type=float, default=0.04)
    parser.add_argument('--nx', type=int, default=64)
    parser.add_argument('--risk', type=float, default=0)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--boundary-weight', type=float, default=0)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    cases = cases_for(args.cases)
    Path(args.output + '.cases.json').write_text(json.dumps(cases, indent=2))
    vector = load(args.input)
    if args.workers == 1:
        objective = Objective(cases, (args.nx, args.nx // 2), args.dt, args.risk, args.boundary_weight)
    else:
        objective = ParallelObjective(cases, (args.nx, args.nx // 2), args.dt, args.risk, args.workers, args.boundary_weight)
    value, gradient = objective(vector)
    print('INITIAL', value, objective.scores.tolist(), 'seconds', time.monotonic() - objective.started, flush=True)
    if args.check:
        for index in [2, 21, 40, 63, 80, 98]:
            plus, minus = vector.copy(), vector.copy()
            plus[index] += 1e-5
            minus[index] -= 1e-5
            numeric = (objective(plus)[0] - objective(minus)[0]) / 2e-5
            print('GRADIENT', index, gradient[index], numeric, flush=True)
        return
    bounds, conditions = constraints()
    iterations = [0]
    best = [float('inf')]
    def callback(current):
        iterations[0] += 1
        value, grad = objective(current)
        checkpoint = current.copy().reshape(6, 19)
        peak = np.max(np.hypot(checkpoint[2], checkpoint[3]))
        if peak > 2.8 - 1e-9:
            checkpoint[2:4] *= (2.8 - 1e-9) / peak
        checkpoint = checkpoint.ravel()
        valid = True
        try:
            fc.validate_artifact(artifact(checkpoint), PROTOCOL)
        except ValueError:
            valid = False
        if valid and value < best[0]:
            best[0] = value
            write(args.output, checkpoint)
        write(args.output + '.progress.json', checkpoint)
        print('ITER', iterations[0], 'calls', objective.calls, 'loss', value, 'mean', np.mean(objective.scores), 'min', min(objective.scores), 'valid', valid, 'seconds', round(time.monotonic() - objective.started, 2), flush=True)
        if iterations[0] % 10 == 0:
            print('SCORES', objective.scores.tolist(), flush=True)
    result = minimize(objective, vector, jac=True, method='SLSQP', bounds=bounds, constraints=conditions, callback=callback, options={'maxiter': args.iterations, 'ftol': 1e-10, 'disp': True})
    write(args.output + '.last.json', result.x)
    print(result.message, flush=True)

if __name__ == '__main__':
    main()
