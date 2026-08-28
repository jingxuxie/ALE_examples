import itertools
import os
import sys
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import numpy as np
from scipy import linalg, sparse

import solver


def test_cliffords():
    rng = np.random.default_rng(553)
    for qubit_count in (1, 2, 4, 5, 7, 20, 24):
        for trial in range(20):
            operations = []
            for operation in range(35):
                opcode = int(rng.integers(1, 6 if qubit_count > 1 else 3))
                first = int(rng.integers(qubit_count))
                second = int(rng.integers(qubit_count - 1)) if opcode > 2 else -1
                if second >= first:
                    second += 1
                operations.append((opcode, first, second))
            operations = np.array(operations)
            clifford = solver.Clifford(operations, qubit_count)
            before_x = rng.integers(0, 1 << qubit_count, 100)
            before_z = rng.integers(0, 1 << qubit_count, 100)
            after_x, after_z, signs = solver.inverse_primitives(before_x, before_z, operations)
            for index in range(100):
                actual = clifford.apply(int(before_x[index]), int(before_z[index]))
                assert actual == (after_x[index], after_z[index], signs[index]), (qubit_count, actual, (after_x[index], after_z[index], signs[index]))
    paulis = [np.eye(2), np.array([[0, 1], [1, 0]]), np.array([[0, -1j], [1j, 0]]), np.diag([1, -1])]
    hadamard = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
    phase = np.diag([1, 1j])
    cx = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]])
    cz = np.diag([1, 1, 1, -1])
    swap = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
    for opcode, unitary in enumerate((np.kron(hadamard, np.eye(2)), np.kron(phase, np.eye(2)), cx, cz, swap), start=1):
        clifford = solver.Clifford(np.array([[opcode, 0, -1 if opcode <= 2 else 1]]), 2)
        for axes in itertools.product(range(4), repeat=2):
            before_x, before_z = solver.pauli_bits(np.array(axes)[None])
            after_x, after_z, sign = clifford.apply(int(before_x[0]), int(before_z[0]))
            output_axes = []
            for qubit in range(2):
                code = ((after_x >> qubit) & 1) + 2 * ((after_z >> qubit) & 1)
                output_axes.append((0, 1, 3, 2)[code])
            actual = (1 - 2 * sign) * np.kron(paulis[output_axes[0]], paulis[output_axes[1]])
            expected = unitary.conj().T @ np.kron(paulis[axes[0]], paulis[axes[1]]) @ unitary
            assert np.max(np.abs(actual - expected)) < 1e-12
    print('Clifford tests passed', flush=True)


def make_data(qubit_count=3, channel_count=3, parallel=False, computational=False, seed=51, training_per_channel=0):
    rng = np.random.default_rng(seed)
    gate_ops = []
    gate_ptr = [0]
    gate_noise = []
    factors = []
    factor_channels = []
    for channel in (-2, -1):
        for qubit in range(qubit_count):
            factors.append((qubit,))
            factor_channels.append(channel)
        if qubit_count > 2:
            for qubit in range(0, qubit_count - 1, 3):
                factors.append((qubit, qubit + 1))
                factor_channels.append(channel)
    for channel in range(channel_count):
        if parallel:
            qubits = rng.permutation(qubit_count).tolist()
            operations = [(3 + channel % 2, qubits[position], qubits[position + 1]) for position in range(0, qubit_count - 1, 2)]
            noise_factors = [(qubit,) for qubit in range(qubit_count)] + [(qubit, (qubit + 1) % qubit_count) for qubit in range(qubit_count)]
        else:
            first = channel % qubit_count
            second = (first + 1) % qubit_count
            operations = [(3 + channel % 2, first, second)]
            if channel % 3 == 2:
                operations.append((2, first, -1))
            noise_factors = [(first,), (second,), (first, second)]
        gate_ops.extend(operations)
        gate_ptr.append(len(gate_ops))
        gate_noise.append(channel)
        for factor in noise_factors:
            factors.append(tuple(sorted(factor)))
            factor_channels.append(channel)
    for qubit in range(qubit_count):
        for opcode in (1, 2):
            gate_ops.append((opcode, qubit, -1))
            gate_ptr.append(len(gate_ops))
            gate_noise.append(-1)
    masks = np.zeros((len(factors), qubit_count), dtype=np.int8)
    for index, factor in enumerate(factors):
        masks[index, list(factor)] = 1
    data = dict(schema_version=np.array(1), n_qubits=np.array(qubit_count), gate_ptr=np.array(gate_ptr), gate_ops=np.array(gate_ops), gate_noise=np.array(gate_noise), factor_channel=np.array(factor_channels), factor_mask=masks)
    if qubit_count < 5 and not training_per_channel:
        all_paulis = np.array(list(itertools.product(range(4), repeat=qubit_count))[1:])
        training_sequences = [[] for pauli in all_paulis]
        training_observables = all_paulis.tolist()
        for channel in range(channel_count):
            for pauli in all_paulis:
                training_sequences.append([channel])
                training_observables.append(pauli.tolist())
    else:
        training_sequences = []
        training_observables = []
        for sector in range(channel_count + 1):
            count = training_per_channel or (qubit_count * (28 if parallel else 5))
            for record in range(count):
                if computational:
                    pauli = 3 * rng.integers(0, 2, qubit_count)
                else:
                    pauli = rng.integers(0, 4, qubit_count)
                if record % 3:
                    sites = rng.choice(qubit_count, min(qubit_count, int(rng.integers(1, 5))), replace=False)
                    pauli[np.setdiff1d(np.arange(qubit_count), sites)] = 0
                repeat = int(rng.choice((1, 2, 4, 8, 16)))
                sequence = [sector] * repeat if sector < channel_count else []
                training_sequences.append(sequence)
                training_observables.append(pauli.tolist())
    holdout_sequences = []
    holdout_observables = []
    for record in range(150):
        if qubit_count < 5:
            sequence = rng.integers(0, len(gate_noise), int(rng.integers(1, 50))).tolist()
        else:
            channel = int(rng.integers(channel_count))
            sequence = [channel] * int(rng.integers(1, 26))
        pauli = 3 * rng.integers(0, 2, qubit_count) if computational else rng.integers(0, 4, qubit_count)
        holdout_sequences.append(sequence)
        holdout_observables.append(pauli.tolist())
    for prefix, sequences, observables in (('train', training_sequences, training_observables), ('holdout', holdout_sequences, holdout_observables)):
        data[prefix + '_ptr'] = np.r_[0, np.cumsum([len(sequence) for sequence in sequences])]
        data[prefix + '_gates'] = np.array([gate for sequence in sequences for gate in sequence], dtype=np.int16)
        data[prefix + '_observable'] = np.array(observables, dtype=np.int8)
    data['train_shots'] = rng.choice((384, 1024, 4096, 16384, 65536), len(training_sequences))
    data['train_plus'] = data['train_shots'].copy()
    query_channels = []
    query_paulis = []
    query_coefficients = []
    query_pointers = [0]
    for query in range(150):
        channel = int(rng.integers(-2, channel_count))
        pauli = rng.integers(0, 4, qubit_count)
        if query % 4 == 0:
            pauli = 3 * rng.integers(0, 2, qubit_count)
        channels = [channel]
        paulis = [pauli]
        if query % 5 == 0:
            channels = [-2, -1]
            paulis = [pauli, pauli]
        for term_channel, term_pauli in zip(channels, paulis):
            query_channels.append(term_channel)
            query_paulis.append(term_pauli)
            query_coefficients.append(1.0)
        query_pointers.append(len(query_channels))
    data['query_ptr'] = np.array(query_pointers)
    data['query_channel'] = np.array(query_channels)
    data['query_pauli'] = np.array(query_paulis)
    data['query_coeff'] = np.array(query_coefficients)
    return data


def null_support(matrix, queries):
    basis = linalg.null_space(matrix.toarray(), rcond=1e-10)
    residual = np.linalg.norm(queries @ basis, axis=1)
    norms = np.sqrt(np.asarray(queries.multiply(queries).sum(axis=1)).ravel())
    return residual < 1e-7 * np.maximum(1, norms)


def test_identification():
    rng = np.random.default_rng(12)
    for trial in range(12):
        data = make_data(qubit_count=2 + trial % 2, channel_count=3, seed=trial)
        if trial % 3 == 0:
            factor_selection = rng.uniform(size=len(data['factor_channel'])) > 0.2
            data['factor_channel'] = data['factor_channel'][factor_selection]
            data['factor_mask'] = data['factor_mask'][factor_selection]
        model = solver.Model(data)
        training, holdout, training_signs, holdout_signs = model.experiments(data)
        queries = model.queries(data)
        structural = model.structural(queries)
        expected_structural = null_support(training, queries)
        assert np.array_equal(structural, expected_structural), (trial, np.flatnonzero(structural != expected_structural))
        for fraction in (0.1, 0.3, 0.8, 1):
            selection = rng.uniform(size=training.shape[0]) < fraction
            calibration = solver.calibration_identifiability(training[selection], queries, structural)
            expected_calibration = null_support(training[selection], queries)
            assert np.array_equal(calibration, expected_calibration), (trial, fraction, np.flatnonzero(calibration != expected_calibration))
            compressed, compressed_holdout, compressed_queries, consistent = solver.compress_parameters(training[selection], holdout, queries)
            compressed_calibration = solver.calibration_identifiability(compressed, compressed_queries, structural & consistent)
            assert np.array_equal(compressed_calibration, expected_calibration), (trial, fraction, 'compression', np.flatnonzero(compressed_calibration != expected_calibration))
    print('Identification tests passed', flush=True)


def benchmark(qubit_count=20, channel_count=24, parallel=False, computational=False, training_per_channel=0):
    start = time.monotonic()
    data = make_data(qubit_count, channel_count, parallel, computational, training_per_channel=training_per_channel)
    model = solver.Model(data)
    training, holdout, training_signs, holdout_signs = model.experiments(data)
    queries = model.queries(data)
    print('Built benchmark', qubit_count, channel_count, parallel, computational, training.shape, training.nnz, time.monotonic() - start, flush=True)
    rng = np.random.default_rng(124)
    rates = rng.lognormal(-6.5 if parallel else -6.0, 0.5, model.parameter_count)
    for channel in (-2, -1):
        begin, end = model.channel_ranges[channel]
        rates[begin:end] = rng.uniform(0.007, 0.03, end - begin)
    true_training_means = training_signs * np.exp(-training @ rates)
    data['train_plus'] = rng.binomial(data['train_shots'], (1 + true_training_means) / 2)
    stem = f'benchmark_{qubit_count}_{channel_count}_{int(parallel)}_{int(computational)}'
    np.savez(stem + '.npz', **data)
    np.savez(stem + '_truth.npz', rates=rates, training_mean=true_training_means, holdout_mean=holdout_signs * np.exp(-holdout @ rates), query_log_estimate=queries @ rates)
    solver.solve(stem + '.npz', stem + '_output.npz')
    with np.load(stem + '_output.npz') as output:
        selected = output['calibration_identifiable'] > 0.5
        prediction_mse = np.mean((output['holdout_mean'] - holdout_signs * np.exp(-holdout @ rates)) ** 2)
        query_mse = np.mean((output['query_log_estimate'][selected] - (queries @ rates)[selected]) ** 2)
        print('Benchmark result', prediction_mse, query_mse, np.sum(selected), 'seconds', time.monotonic() - start, flush=True)


def test_edge_cases():
    rng = np.random.default_rng(5191)
    data = make_data(3, 3, seed=412)
    model = solver.Model(data)
    training, holdout, training_signs, holdout_signs = model.experiments(data)
    queries = model.queries(data)
    training = training[rng.choice(training.shape[0], 25, replace=False)]
    expected = null_support(training, queries)
    expected_structural = model.structural(queries)
    for factor in (1e-12, 1e-6, 1, 1e6, 1e12):
        scaled_queries = queries * factor
        structural = model.structural(scaled_queries)
        reduced, reduced_holdout, reduced_queries, consistent = solver.compress_parameters(training, holdout, scaled_queries)
        calibration = solver.calibration_identifiability(reduced, reduced_queries, structural & consistent)
        assert np.array_equal(structural, expected_structural)
        assert np.array_equal(calibration, expected)
    calibration = solver.calibration_identifiability(training[:0], queries, expected_structural)
    assert np.array_equal(calibration, np.asarray(queries.multiply(queries).sum(axis=1)).ravel() == 0)
    reduced, reduced_holdout, reduced_queries, consistent = solver.compress_parameters(training[:0], holdout, queries)
    calibration = solver.calibration_identifiability(reduced, reduced_queries, expected_structural & consistent)
    assert np.array_equal(calibration, np.asarray(queries.multiply(queries).sum(axis=1)).ravel() == 0)
    print('Scale and empty-calibration tests passed', flush=True)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        test_cliffords()
        test_identification()
        test_edge_cases()
    else:
        benchmark(int(sys.argv[1]), int(sys.argv[2]), bool(int(sys.argv[3])), bool(int(sys.argv[4])), int(sys.argv[5]) if len(sys.argv) > 5 else 0)
