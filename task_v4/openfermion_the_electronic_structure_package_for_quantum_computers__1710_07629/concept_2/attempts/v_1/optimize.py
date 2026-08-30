import argparse
import time
from scipy.optimize import least_squares
from peel import *


def gate_data(parameters):
    horizontal, vertical = parameters
    radius = np.hypot(horizontal, vertical)
    cosine = np.cos(radius)
    if radius < 1e-5:
        sinc = 1 - radius ** 2 / 6 + radius ** 4 / 120
        factor = -1 / 3 + radius ** 2 / 30 - radius ** 4 / 840
    else:
        sinc = np.sin(radius) / radius
        factor = (radius * cosine - np.sin(radius)) / radius ** 3
    coefficient = (horizontal + 1j * vertical) * sinc
    derivative_horizontal = sinc + (horizontal + 1j * vertical) * horizontal * factor
    derivative_vertical = 1j * sinc + (horizontal + 1j * vertical) * vertical * factor
    gate = np.array([[cosine, -coefficient.conjugate()], [coefficient, cosine]])
    derivative_first = np.array([[-sinc * horizontal, -derivative_horizontal.conjugate()], [derivative_horizontal, -sinc * horizontal]])
    derivative_second = np.array([[-sinc * vertical, -derivative_vertical.conjugate()], [derivative_vertical, -sinc * vertical]])
    return gate, derivative_first, derivative_second


class Fit:
    def __init__(self, instance, edges):
        self.instance = instance
        self.edges = np.array(edges, dtype=int)
        values, vectors = np.linalg.eigh(target(instance))
        self.empty = vectors[:, :instance['n_modes'] - instance['n_particles']].conj().T
        self.initial = np.eye(instance['n_modes'], dtype=complex)[:, instance['initial_occupied']]
        self.previous = None
        self.calls = 0

    def evaluate(self, parameters):
        if self.previous is not None and np.array_equal(parameters, self.previous):
            return self.residual, self.jacobian
        self.previous = parameters.copy()
        self.calls += 1
        parameters = parameters.reshape(-1, 2)
        frame = self.initial.copy()
        history = []
        for endpoints, pair in zip(self.edges, parameters):
            gate, derivative_first, derivative_second = gate_data(pair)
            rows = frame[endpoints].copy()
            history.append((gate, derivative_first, derivative_second, rows))
            frame[endpoints] = gate @ rows
        leakage = self.empty @ frame
        residual = np.concatenate((leakage.real.ravel(), leakage.imag.ravel()))
        jacobian = np.empty((len(residual), parameters.size))
        backward = self.empty.copy()
        for index in range(len(self.edges) - 1, -1, -1):
            endpoints = self.edges[index]
            gate, derivative_first, derivative_second, rows = history[index]
            columns = backward[:, endpoints].copy()
            for direction, derivative in enumerate((derivative_first, derivative_second)):
                tangent = columns @ derivative @ rows
                jacobian[:, 2 * index + direction] = np.concatenate((tangent.real.ravel(), tangent.imag.ravel()))
            backward[:, endpoints] = columns @ gate
        self.residual, self.jacobian = residual, jacobian
        return residual, jacobian

    def solve(self, parameters, evaluations=150, tolerance=1e-12):
        method = 'lm' if parameters.size <= 2 * self.empty.shape[0] * self.initial.shape[1] else 'trf'
        result = least_squares(lambda values: self.evaluate(values)[0], parameters.ravel(),
                               jac=lambda values: self.evaluate(values)[1], method=method,
                               ftol=tolerance, xtol=tolerance, gtol=tolerance, max_nfev=evaluations)
        return result.x.reshape(-1, 2), np.linalg.norm(result.fun) * np.sqrt(2)


def unpack(circuit):
    edges, parameters = [], []
    for layer in circuit['layers']:
        for gate in layer:
            edges.append((gate['u'], gate['v']))
            parameters.append((gate['theta'] * np.cos(gate['phi']), gate['theta'] * np.sin(gate['phi'])))
    return edges, np.array(parameters)


def pack(instance, edges, parameters):
    gates = []
    for (first, second), (horizontal, vertical) in zip(edges, parameters):
        theta = float(np.hypot(horizontal, vertical))
        phi = float(np.arctan2(vertical, horizontal))
        theta = (theta + np.pi) % (2 * np.pi) - np.pi
        gates.append((first, second, theta, phi))
    return dict(id=instance['id'], layers=schedule(gates, instance['n_modes']))


def prune(instance, circuit):
    edges, parameters = unpack(circuit)
    fit = Fit(instance, edges)
    parameters, error = fit.solve(parameters)
    singular = np.linalg.svd(fit.evaluate(parameters.ravel())[1], compute_uv=False)
    print(instance['id'], 'START', len(edges), error, 'rank', sum(singular > 1e-8), 'params',parameters.size, flush=True)
    while len(edges) > instance['budgets']['max_gates']:
        best = None
        for removed in range(len(edges)):
            trial_edges = edges[:removed] + edges[removed + 1:]
            trial_parameters = np.delete(parameters, removed, axis=0)
            solver = Fit(instance, trial_edges)
            trial_parameters, error = solver.solve(trial_parameters, evaluations=100)
            if best is None or error < best[0]:
                best = error, trial_edges, trial_parameters
            print('DELETE', removed, 'err', error, flush=True)
            if error < 1e-10:
                break
        error, trial_edges, trial_parameters = best
        if error > 1e-8:
            print('NO EXACT PRUNE', error, flush=True)
            break
        edges, parameters = trial_edges, trial_parameters
        Path(instance['id'] + '_optimized.json').write_text(json.dumps(pack(instance, edges, parameters)))
        print('PRUNED', len(edges), error, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--source', default='local')
    arguments = parser.parse_args()
    instance = INSTANCES[arguments.index]
    circuit = json.loads(Path(instance['id'] + '_' + arguments.source + '.json').read_text())
    prune(instance, circuit)
