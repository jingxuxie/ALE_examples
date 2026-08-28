import itertools
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import svd
from scipy.optimize import minimize


def clifford_tables():
    identity = np.eye(2, dtype=complex)
    paulis = [identity, np.array([[0, 1], [1, 0]]),
              np.array([[0, -1j], [1j, 0]]), np.diag([1, -1])]
    unitaries = {
        1: np.array([[1, 1], [1, -1]]) / np.sqrt(2),
        2: np.diag([1, 1j]),
        3: np.array([[1, 0, 0, 0], [0, 1, 0, 0],
                     [0, 0, 0, 1], [0, 0, 1, 0]]),
        4: np.diag([1, 1, 1, -1]),
        5: np.array([[1, 0, 0, 0], [0, 0, 1, 0],
                     [0, 1, 0, 0], [0, 0, 0, 1]]),
    }
    tables = {}
    for opcode, unitary in unitaries.items():
        width = 1 if opcode < 3 else 2
        labels = list(itertools.product(range(4), repeat=width))
        matrices = [paulis[label[0]] if width == 1 else
                    np.kron(paulis[label[0]], paulis[label[1]]) for label in labels]
        table = {}
        for label, matrix in zip(labels, matrices):
            transformed = unitary.conj().T @ matrix @ unitary
            overlaps = np.array([np.trace(candidate.conj().T @ transformed).real /
                                 len(unitary) for candidate in matrices])
            position = int(np.argmax(np.abs(overlaps)))
            table[label] = (labels[position], int(np.rint(overlaps[position])))
        tables[opcode] = table
    return tables


TABLES = clifford_tables()


def row_basis(matrix):
    if not len(matrix):
        return np.empty((0, matrix.shape[1]))
    _, values, right = svd(matrix, full_matrices=False, check_finite=False)
    rank = int(np.sum(values > max(matrix.shape) * values[0] * 2e-12)) if values[0] else 0
    return right[:rank]


def membership(rows, basis):
    residual = rows - (rows @ basis.T) @ basis
    return np.linalg.norm(residual, axis=1) < 2e-8 * np.maximum(1, np.linalg.norm(rows, axis=1))


class Model:
    def __init__(self, data):
        self.data = data
        self.qubits = int(data['n_qubits'])
        self.noise = data['gate_noise']
        self.operations = [data['gate_ops'][begin:end] for begin, end in
                           zip(data['gate_ptr'][:-1], data['gate_ptr'][1:])]
        self.factors = {}
        channels, supports, labels = [], [], []
        for channel, mask in zip(data['factor_channel'], data['factor_mask']):
            channel = int(channel)
            sites = tuple(np.flatnonzero(mask))
            self.factors.setdefault(channel, []).append(sites)
            choices = [()] if channel < 0 else itertools.product((1, 2, 3), repeat=len(sites))
            for choice in choices:
                pauli = np.zeros(self.qubits, dtype=np.int8)
                if channel >= 0:
                    pauli[list(sites)] = choice
                channels.append(channel)
                supports.append(mask)
                labels.append(pauli)
        self.channels = np.array(channels, dtype=np.int16)
        self.supports = np.array(supports, dtype=bool)
        self.labels = np.array(labels, dtype=np.int8)
        self.parameter_count = len(channels)
        self.indices = {channel: np.flatnonzero(self.channels == channel)
                        for channel in self.factors}
        self.generator_x = (self.labels == 1) | (self.labels == 2)
        self.generator_z = (self.labels == 2) | (self.labels == 3)
        self.cache = {}

    def feature(self, channel, pauli):
        key = (int(channel), tuple(pauli))
        if key in self.cache:
            return self.cache[key]
        row = np.zeros(self.parameter_count)
        indices = self.indices[int(channel)]
        if channel < 0:
            row[indices] = np.any(self.supports[indices] & (pauli != 0), axis=1)
        else:
            pauli_x = ((pauli == 1) | (pauli == 2)).astype(np.int16)
            pauli_z = ((pauli == 2) | (pauli == 3)).astype(np.int16)
            row[indices] = 2 * ((self.generator_x[indices] @ pauli_z +
                                self.generator_z[indices] @ pauli_x) % 2)
        if len(self.cache) < 30000:
            self.cache[key] = row
        return row

    def backward(self, gate, pauli):
        pauli = pauli.copy()
        sign = 1
        for opcode, first, second in self.operations[int(gate)][::-1]:
            sites = [first] if opcode < 3 else [first, second]
            label, local_sign = TABLES[int(opcode)][tuple(pauli[sites])]
            pauli[sites] = label
            sign *= local_sign
        return pauli, sign

    def trace(self, sequence, observable, terms=False):
        pauli = np.asarray(observable, dtype=np.int8).copy()
        row = self.feature(-1, pauli).copy()
        components = [(-1, pauli.copy(), 1.0)]
        sign = 1
        for gate in reversed(sequence):
            pauli, local_sign = self.backward(gate, pauli)
            sign *= local_sign
            channel = int(self.noise[int(gate)])
            if channel >= 0:
                row += self.feature(channel, pauli)
                if terms:
                    components.append((channel, pauli.copy(), 1.0))
        row += self.feature(-2, pauli)
        if terms:
            components.append((-2, pauli.copy(), 1.0))
        return row, sign, components

    def experiments(self, prefix):
        rows, signs = [], []
        pointers = self.data[prefix + '_ptr']
        gates = self.data[prefix + '_gates']
        for begin, end, observable in zip(pointers[:-1], pointers[1:],
                                          self.data[prefix + '_observable']):
            row, sign, _ = self.trace(gates[begin:end], observable)
            rows.append(row)
            signs.append(sign)
        return np.array(rows), np.array(signs)

    def queries(self):
        rows = []
        for begin, end in zip(self.data['query_ptr'][:-1], self.data['query_ptr'][1:]):
            row = np.zeros(self.parameter_count)
            for position in range(begin, end):
                row += self.data['query_coeff'][position] * self.feature(
                    self.data['query_channel'][position], self.data['query_pauli'][position])
            rows.append(row)
        return np.array(rows)

    def dependencies(self, gate):
        dependencies = [set() for _ in range(self.qubits)]
        for site in range(self.qubits):
            for axis in (1, 3):
                basis = np.zeros(self.qubits, dtype=np.int8)
                basis[site] = axis
                transformed, _ = self.backward(gate, basis)
                for destination in np.flatnonzero(transformed):
                    dependencies[destination].add(site)
        return dependencies

    def rooted_experiments(self):
        experiments = []
        noisy_gates = [int(np.flatnonzero(self.noise == channel)[0])
                       for channel in sorted(self.factors) if channel >= 0]
        for gate in [None] + noisy_gates:
            scopes = set(self.factors[-1])
            if gate is None:
                scopes.update(self.factors[-2])
            else:
                dependencies = self.dependencies(gate)
                for factor in self.factors[-2] + self.factors[int(self.noise[gate])]:
                    scopes.add(tuple(sorted(set().union(*(dependencies[site] for site in factor)))))
            observables = set()
            for scope in scopes:
                for local in itertools.product(range(4), repeat=len(scope)):
                    if not any(local):
                        continue
                    pauli = [0] * self.qubits
                    for site, axis in zip(scope, local):
                        pauli[site] = axis
                    observables.add(tuple(pauli))
            for observable in sorted(observables):
                experiments.append(([] if gate is None else [gate],
                                    np.array(observable, dtype=np.int8)))
        return experiments

    def structural_basis(self):
        rows = np.array([self.trace(sequence, observable)[0] for sequence, observable
                         in self.rooted_experiments()])
        return row_basis(rows)


def likelihood_fit(matrix, signs, shots, plus, channels):
    aligned_plus = np.where(signs > 0, plus, shots - plus).astype(float)
    minus = shots - aligned_plus
    initial = np.where(channels < 0, 0.025, 0.0015)
    attenuation = matrix @ initial
    contrast = np.exp(-attenuation)
    information = shots * contrast ** 2 / np.maximum(1 - contrast ** 2, 1e-10)
    scale = 1 / np.sqrt(np.maximum(np.mean(matrix ** 2 * information[:, None], axis=0), 1))
    scaled = matrix * scale
    normalization = len(matrix)

    def objective(coordinates):
        attenuation = np.maximum(scaled @ coordinates, 1e-14)
        contrast = np.exp(-attenuation)
        loss = -aligned_plus @ np.log1p(contrast) - minus @ np.log(-np.expm1(-attenuation))
        derivative = aligned_plus * contrast / (1 + contrast) - minus / np.expm1(
            np.minimum(attenuation, 700))
        return loss / normalization, scaled.T @ derivative / normalization

    result = minimize(objective, initial / scale, jac=True, method='L-BFGS-B',
                      bounds=[(1e-11, None)] * len(initial),
                      options={'ftol': 2e-12, 'gtol': 2e-7, 'maxiter': 1200, 'maxls': 40})
    if not np.all(np.isfinite(result.x)):
        raise RuntimeError('Nonfinite likelihood fit')
    return result.x * scale, {'success': bool(result.success), 'iterations': int(result.nit),
                              'message': str(result.message)}


def solve(data, diagnostics=False):
    model = Model(data)
    calibration, signs = model.experiments('train')
    heldout, heldout_signs = model.experiments('holdout')
    queries = model.queries()
    structural = model.structural_basis()
    observed = row_basis(calibration)
    rates, fit_info = likelihood_fit(calibration, signs, data['train_shots'],
                                    data['train_plus'], model.channels)
    output = {
        'structural_identifiable': membership(queries, structural).astype(float),
        'calibration_identifiable': membership(queries, observed).astype(float),
        'query_log_estimate': queries @ rates,
        'holdout_mean': heldout_signs * np.exp(-heldout @ rates),
    }
    if diagnostics:
        fit_info.update(parameters=model.parameter_count, structural_rank=len(structural),
                        calibration_rank=len(observed), heldout_estimable=bool(
                            np.all(membership(heldout, observed))))
        return output, fit_info
    return output


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: solver.py INPUT.npz OUTPUT.npz')
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    output = solve(data)
    with Path(sys.argv[2]).open('wb') as stream:
        np.savez_compressed(stream, **output)


if __name__ == '__main__':
    main()
