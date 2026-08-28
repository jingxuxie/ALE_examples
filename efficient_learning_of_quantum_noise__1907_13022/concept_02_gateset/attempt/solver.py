import os
import sys
import time
from array import array
from itertools import product

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import numpy as np
from scipy import linalg, optimize, sparse
from scipy.sparse import linalg as splinalg
from scipy.special import xlogy


START = time.monotonic()
VERBOSE = bool(os.environ.get('SOLVER_VERBOSE'))


def report(*values):
    if VERBOSE:
        print(round(time.monotonic() - START, 3), *values, file=sys.stderr, flush=True)


def pauli_bits(paulis):
    qubit_count = paulis.shape[-1]
    powers = np.left_shift(np.int64(1), np.arange(qubit_count))
    xbits = ((paulis == 1) | (paulis == 2)).astype(np.int64) @ powers
    zbits = ((paulis == 2) | (paulis == 3)).astype(np.int64) @ powers
    return xbits, zbits


def inverse_primitives(xbits, zbits, operations):
    xbits = xbits.copy()
    zbits = zbits.copy()
    signs = np.zeros_like(xbits)
    for opcode, first, second in operations[::-1]:
        first = int(first)
        second = int(second)
        first_x = (xbits >> first) & 1
        first_z = (zbits >> first) & 1
        if opcode == 1:
            signs ^= first_x & first_z
            changed = (first_x ^ first_z) << first
            xbits ^= changed
            zbits ^= changed
        elif opcode == 2:
            signs ^= first_x & (first_z ^ 1)
            zbits ^= first_x << first
        else:
            second_x = (xbits >> second) & 1
            second_z = (zbits >> second) & 1
            if opcode == 3:
                signs ^= first_x & second_z & (second_x ^ first_z ^ 1)
                xbits ^= first_x << second
                zbits ^= second_z << first
            elif opcode == 4:
                signs ^= first_x & second_x & (first_z ^ second_z)
                zbits ^= (first_x << second) | (second_x << first)
            elif opcode == 5:
                changed_x = first_x ^ second_x
                changed_z = first_z ^ second_z
                xbits ^= (changed_x << first) | (changed_x << second)
                zbits ^= (changed_z << first) | (changed_z << second)
    return xbits, zbits, signs


class Clifford:
    def __init__(self, operations, qubit_count):
        self.qubit_count = qubit_count
        active = sorted({int(qubit) for operation in operations for qubit in operation[1:] if qubit >= 0})
        self.mask = sum(1 << qubit for qubit in active)
        self.groups = []
        for offset in range(0, len(active), 4):
            group = active[offset:offset + 4]
            mask = sum(1 << qubit for qubit in group)
            codes = np.arange(4 ** len(group), dtype=np.int64)
            input_x = np.zeros(len(codes), dtype=np.int64)
            input_z = np.zeros(len(codes), dtype=np.int64)
            for position, qubit in enumerate(group):
                input_x |= ((codes >> (2 * position)) & 1) << qubit
                input_z |= ((codes >> (2 * position + 1)) & 1) << qubit
            output_x, output_z, signs = inverse_primitives(input_x, input_z, operations)
            table = {}
            for before_x, before_z, after_x, after_z, sign in zip(input_x.tolist(), input_z.tolist(), output_x.tolist(), output_z.tolist(), signs.tolist()):
                key = before_x | (before_z << qubit_count)
                if len(active) <= 4:
                    table[key] = (after_x ^ before_x, after_z ^ before_z, sign)
                else:
                    table[key] = (after_x, after_z, 2 * sign + (after_x & after_z).bit_count())
            self.groups.append((mask, table))

    def apply(self, xbits, zbits):
        if not self.groups:
            return xbits, zbits, 0
        if len(self.groups) == 1:
            mask, table = self.groups[0]
            delta_x, delta_z, sign = table[(xbits & mask) | ((zbits & mask) << self.qubit_count)]
            return xbits ^ delta_x, zbits ^ delta_z, sign
        output_x = xbits & ~self.mask
        output_z = zbits & ~self.mask
        phase = (output_x & output_z).bit_count()
        for mask, table in self.groups:
            key = (xbits & mask) | ((zbits & mask) << self.qubit_count)
            if key:
                next_x, next_z, next_phase = table[key]
                phase += next_phase + 2 * (output_z & next_x).bit_count()
                output_x ^= next_x
                output_z ^= next_z
        sign = ((phase - (output_x & output_z).bit_count()) & 3) >> 1
        return output_x, output_z, sign


class Model:
    def __init__(self, data):
        self.qubit_count = int(data['n_qubits'])
        self.gate_channels = data['gate_noise'].astype(int).tolist()
        self.cliffords = [Clifford(data['gate_ops'][begin:end], self.qubit_count) for begin, end in zip(data['gate_ptr'][:-1], data['gate_ptr'][1:])]
        self.factors = {}
        for channel, mask in zip(data['factor_channel'], data['factor_mask']):
            qubits = tuple(np.flatnonzero(mask).tolist())
            self.factors.setdefault(int(channel), []).append(qubits)
        self.channels = sorted(self.factors)
        self.parameter_count = 0
        self.factor_info = {}
        self.error_parameters = {}
        self.spam_parameters = {}
        self.channel_masks = {}
        self.channel_ranges = {}
        for channel in self.channels:
            channel_begin = self.parameter_count
            infos = []
            error_parameters = {}
            self.channel_masks[channel] = 0
            for qubits in sorted(self.factors[channel]):
                mask = sum(1 << qubit for qubit in qubits)
                self.channel_masks[channel] |= mask
                begin = self.parameter_count
                if channel < 0:
                    self.parameter_count += 1
                    self.spam_parameters[channel, mask] = begin
                    infos.append((qubits, begin, None))
                else:
                    axes_list = list(product((1, 2, 3), repeat=len(qubits)))
                    patterns = np.arange(4 ** len(qubits))
                    table = np.zeros((len(patterns), len(axes_list)))
                    for column, axes in enumerate(axes_list):
                        error_x = 0
                        error_z = 0
                        parity = np.zeros(len(patterns), dtype=np.int64)
                        for position, (qubit, axis) in enumerate(zip(qubits, axes)):
                            axis_x = int(axis in (1, 2))
                            axis_z = int(axis in (2, 3))
                            error_x |= axis_x << qubit
                            error_z |= axis_z << qubit
                            parity ^= (((patterns >> (2 * position)) & 1) * axis_z) ^ (((patterns >> (2 * position + 1)) & 1) * axis_x)
                        table[:, column] = 2 * parity
                        error_parameters[error_x | (error_z << self.qubit_count)] = begin + column
                    self.parameter_count += len(axes_list)
                    infos.append((qubits, begin, table))
            self.factor_info[channel] = infos
            self.error_parameters[channel] = error_parameters
            self.channel_ranges[channel] = (channel_begin, self.parameter_count)

    def event_matrix(self, record_count, events, initial_support=None, final_support=None, query=False):
        row_parts = []
        column_parts = []
        value_parts = []
        for channel in self.channels:
            if channel < 0 and not query:
                support = initial_support if channel == -2 else final_support
                for qubits, parameter, table in self.factor_info[channel]:
                    mask = sum(1 << qubit for qubit in qubits)
                    rows = np.flatnonzero(support & mask).astype(np.int32)
                    row_parts.append(rows)
                    column_parts.append(np.full(len(rows), parameter, dtype=np.int32))
                    value_parts.append(np.ones(len(rows)))
                continue
            if channel not in events or not len(events[channel][0]):
                continue
            if query:
                rows, states, weights = events[channel]
                rows = np.asarray(rows, dtype=np.int64)
                states = np.asarray(states, dtype=np.int64)
                weights = np.asarray(weights, dtype=float)
                record_ids, local_rows = np.unique(rows, return_inverse=True)
            else:
                rows, states = events[channel]
                rows = np.frombuffer(rows, dtype=np.uint32)
                states = np.frombuffer(states, dtype=np.uint64).astype(np.int64)
                changes = np.r_[True, rows[1:] != rows[:-1]]
                record_ids = rows[changes]
                local_rows = np.cumsum(changes) - 1
                weights = None
            xbits = states & ((1 << self.qubit_count) - 1)
            zbits = states >> self.qubit_count
            begin, end = self.channel_ranges[channel]
            block = np.zeros((len(record_ids), end - begin))
            for qubits, parameter, table in self.factor_info[channel]:
                if channel < 0:
                    mask = sum(1 << qubit for qubit in qubits)
                    supported = ((xbits | zbits) & mask) != 0
                    block[:, parameter - begin] = np.bincount(local_rows, weights=weights * supported, minlength=len(record_ids))
                else:
                    codes = np.zeros(len(states), dtype=np.int64)
                    for position, qubit in enumerate(qubits):
                        codes |= ((xbits >> qubit) & 1) << (2 * position)
                        codes |= ((zbits >> qubit) & 1) << (2 * position + 1)
                    histogram = np.bincount(local_rows * len(table) + codes, weights=weights, minlength=len(record_ids) * len(table)).reshape(len(record_ids), len(table))
                    block[:, parameter - begin:parameter - begin + table.shape[1]] = histogram @ table
            local_nonzero_rows, local_nonzero_cols = np.nonzero(block)
            row_parts.append(record_ids[local_nonzero_rows].astype(np.int32))
            column_parts.append((local_nonzero_cols + begin).astype(np.int32))
            value_parts.append(block[local_nonzero_rows, local_nonzero_cols])
        if not value_parts:
            return sparse.csr_matrix((record_count, self.parameter_count))
        matrix = sparse.coo_matrix((np.concatenate(value_parts), (np.concatenate(row_parts), np.concatenate(column_parts))), shape=(record_count, self.parameter_count)).tocsr()
        matrix.eliminate_zeros()
        return matrix

    def experiments(self, data):
        training_count = len(data['train_shots'])
        holdout_count = len(data['holdout_observable'])
        record_count = training_count + holdout_count
        signs = np.ones(record_count)
        initial_support = np.zeros(record_count, dtype=np.int64)
        final_support = np.zeros(record_count, dtype=np.int64)
        events = {channel: (array('I'), array('Q')) for channel in self.channels if channel >= 0}
        offset = 0
        gates = [(clifford.apply, channel, self.channel_masks.get(channel, 0)) for clifford, channel in zip(self.cliffords, self.gate_channels)]
        for prefix in ('train', 'holdout'):
            pointers = data[prefix + '_ptr']
            sequences = data[prefix + '_gates'].astype(int).tolist()
            all_x, all_z = pauli_bits(data[prefix + '_observable'])
            for local_record, (xbits, zbits) in enumerate(zip(all_x.tolist(), all_z.tolist())):
                record = offset + local_record
                final_support[record] = xbits | zbits
                sign = 0
                for gate in reversed(sequences[pointers[local_record]:pointers[local_record + 1]]):
                    transform, channel, mask = gates[gate]
                    xbits, zbits, delta_sign = transform(xbits, zbits)
                    sign ^= delta_sign
                    if channel >= 0 and mask:
                        event_rows, event_states = events[channel]
                        event_rows.append(record)
                        event_states.append((xbits & mask) | ((zbits & mask) << self.qubit_count))
                signs[record] = 1 - 2 * sign
                initial_support[record] = xbits | zbits
            offset += len(all_x)
        matrix = self.event_matrix(record_count, events, initial_support, final_support)
        return matrix[:training_count].tocsr(), matrix[training_count:].tocsr(), signs[:training_count], signs[training_count:]

    def queries(self, data):
        query_count = len(data['query_ptr']) - 1
        term_rows = np.repeat(np.arange(query_count), np.diff(data['query_ptr']))
        all_x, all_z = pauli_bits(data['query_pauli'])
        events = {}
        for row, channel, xbits, zbits, coefficient in zip(term_rows.tolist(), data['query_channel'].tolist(), all_x.tolist(), all_z.tolist(), data['query_coeff'].tolist()):
            rows, states, weights = events.setdefault(channel, ([], [], []))
            rows.append(row)
            states.append(xbits | (zbits << self.qubit_count))
            weights.append(coefficient)
        return self.event_matrix(query_count, events, query=True)

    def structural(self, queries):
        common_masks = sorted({mask for channel, mask in self.spam_parameters if channel == -2} & {mask for channel, mask in self.spam_parameters if channel == -1})
        gauge_count = len(common_masks)
        if not gauge_count:
            return np.ones(queries.shape[0], dtype=bool)
        null_rows = []
        null_cols = []
        null_values = []
        constraint_rows = []
        constraint_cols = []
        constraint_values = []
        constraint_count = 0
        terms = []
        for column, mask in enumerate(common_masks):
            null_rows.extend((self.spam_parameters[-2, mask], self.spam_parameters[-1, mask]))
            null_cols.extend((column, column))
            null_values.extend((16, -16))
            qubits = [qubit for qubit in range(self.qubit_count) if (mask >> qubit) & 1]
            coefficient = 16 // (4 ** len(qubits))
            for axes in product((0, 1, 2, 3), repeat=len(qubits)):
                if not any(axes):
                    continue
                xbits = sum((int(axis in (1, 2)) << qubit) for qubit, axis in zip(qubits, axes))
                zbits = sum((int(axis in (2, 3)) << qubit) for qubit, axis in zip(qubits, axes))
                terms.append((column, coefficient, xbits, zbits))
        for clifford, channel in zip(self.cliffords, self.gate_channels):
            if channel < 0:
                continue
            coefficients = {}
            for column, coefficient, xbits, zbits in terms:
                output_x, output_z, sign = clifford.apply(xbits, zbits)
                before = xbits | (zbits << self.qubit_count)
                after = output_x | (output_z << self.qubit_count)
                if before == after:
                    continue
                before_row = coefficients.setdefault(before, {})
                after_row = coefficients.setdefault(after, {})
                before_row[column] = before_row.get(column, 0) - coefficient
                after_row[column] = after_row.get(column, 0) + coefficient
            declared = self.error_parameters.get(channel, {})
            for error, entries in coefficients.items():
                entries = [(column, value) for column, value in entries.items() if value]
                if not entries:
                    continue
                if error in declared:
                    for column, value in entries:
                        null_rows.append(declared[error])
                        null_cols.append(column)
                        null_values.append(value)
                else:
                    for column, value in entries:
                        constraint_rows.append(constraint_count)
                        constraint_cols.append(column)
                        constraint_values.append(value)
                    constraint_count += 1
        gauge_map = sparse.coo_matrix((null_values, (null_rows, null_cols)), shape=(self.parameter_count, gauge_count)).tocsr()
        if constraint_count:
            constraints = sparse.coo_matrix((constraint_values, (constraint_rows, constraint_cols)), shape=(constraint_count, gauge_count)).astype(float).tocsr()
            gram = (constraints.T @ constraints).toarray()
            eigenvalues, eigenvectors = linalg.eigh(gram, check_finite=False)
            basis = eigenvectors[:, eigenvalues < max(1.0, eigenvalues[-1]) * 1e-10]
        else:
            basis = np.eye(gauge_count)
        if not basis.shape[1]:
            return np.ones(queries.shape[0], dtype=bool)
        query_gauges = (queries @ gauge_map).toarray()
        residual = np.linalg.norm(query_gauges @ basis, axis=1)
        query_norms = np.sqrt(np.asarray(queries.multiply(queries).sum(axis=1)).ravel())
        tolerance = 1e-8 * np.maximum(1e-300, np.maximum(query_norms, np.linalg.norm(query_gauges, axis=1)))
        report('structural gauges', basis.shape[1])
        return residual < tolerance


def equilibrate(matrix):
    result = matrix.copy().astype(float)
    column_scale = np.ones(matrix.shape[1])
    for iteration in range(3):
        row_norm = np.sqrt(np.asarray(result.multiply(result).sum(axis=1)).ravel())
        result = result.multiply((1 / np.maximum(row_norm, 1e-30))[:, None]).tocsr()
        column_norm = np.sqrt(np.asarray(result.multiply(result).sum(axis=0)).ravel())
        column_norm = np.where(column_norm > 0, column_norm, 1)
        result = result.multiply(1 / column_norm).tocsr()
        column_scale *= column_norm
    return result, column_scale


def compress_experiments(matrix, shots, plus, signs):
    matrix.sort_indices()
    adjusted_plus = np.where(signs > 0, plus, shots - plus)
    groups = {}
    representatives = []
    assignments = np.empty(matrix.shape[0], dtype=np.int32)
    for row in range(matrix.shape[0]):
        begin, end = matrix.indptr[row:row + 2]
        key = (matrix.indices[begin:end].tobytes(), matrix.data[begin:end].tobytes())
        group = groups.get(key)
        if group is None:
            group = len(representatives)
            groups[key] = group
            representatives.append(row)
        assignments[row] = group
    count = len(representatives)
    total_shots = np.bincount(assignments, weights=shots, minlength=count)
    total_plus = np.bincount(assignments, weights=adjusted_plus, minlength=count)
    return matrix[representatives].tocsr(), total_shots, total_plus


def compress_parameters(matrix, holdout, queries):
    columns = matrix.tocsc()
    columns.sort_indices()
    parameter_count = columns.shape[1]
    groups = {}
    representatives = []
    assignments = np.full(parameter_count, -1, dtype=np.int32)
    divisors = np.ones(parameter_count)
    for column in range(parameter_count):
        begin, end = columns.indptr[column:column + 2]
        if begin == end:
            continue
        values = columns.data[begin:end].astype(np.int64)
        divisor = int(np.gcd.reduce(values))
        divisors[column] = divisor
        key = (columns.indices[begin:end].tobytes(), (values // divisor).tobytes())
        group = groups.get(key)
        if group is None:
            group = len(representatives)
            groups[key] = group
            representatives.append(column)
        assignments[column] = group
    retained = np.flatnonzero(assignments >= 0)
    group_count = len(representatives)
    sizes = np.bincount(assignments[retained], minlength=group_count).astype(float)
    grouping = sparse.coo_matrix((np.ones(len(retained)), (retained, assignments[retained])), shape=(parameter_count, group_count)).tocsr()
    rescaled_queries = queries.multiply(1 / divisors).tocsr()
    sums = (rescaled_queries @ grouping).tocsr()
    reduced_queries = sums.multiply(1 / sizes).tocsr()
    original_norms = np.asarray(rescaled_queries.multiply(rescaled_queries).sum(axis=1)).ravel()
    projected_norms = np.asarray(sums.multiply(reduced_queries).sum(axis=1)).ravel()
    consistent = original_norms - projected_norms < 1e-11 * np.maximum(1e-300, original_norms)
    reduced_holdout = (holdout.multiply(1 / divisors) @ grouping).multiply(1 / sizes).tocsr()
    reduced_training = matrix[:, representatives].multiply(1 / divisors[representatives]).tocsr()
    report('compressed parameters', parameter_count, group_count)
    return reduced_training, reduced_holdout, reduced_queries, consistent


def calibration_identifiability(matrix, queries, structural):
    if not np.any(structural):
        return structural.copy()
    parameter_count = matrix.shape[1]
    if not parameter_count:
        return structural.copy()
    if not matrix.shape[0]:
        return structural & (np.asarray(queries.multiply(queries).sum(axis=1)).ravel() == 0)
    scaled, column_scale = equilibrate(matrix)
    scaled_queries = queries.multiply(1 / column_scale).tocsr()
    query_norms = np.sqrt(np.asarray(scaled_queries.multiply(scaled_queries).sum(axis=1)).ravel())
    generator = np.random.default_rng(829441)
    probes = generator.normal(size=(parameter_count, 3))
    dual = scaled.shape[0] < parameter_count
    dimension = min(scaled.shape)
    lengths = np.diff(scaled.tocsc().indptr if dual else scaled.indptr).astype(float)
    work_estimate = np.dot(lengths, lengths)
    use_direct = dimension <= 12000 or (dimension <= 18000 and work_estimate < 8e7)
    residual = None
    if use_direct:
        gram = (scaled @ scaled.T if dual else scaled.T @ scaled).tocsc()
        gram_nonzero = gram.nnz
        gram_bytes = gram.data.nbytes + gram.indices.nbytes + gram.indptr.nbytes
        ridge = 1e-10 * max(1.0, float(gram.diagonal().max()))
        use_sparse = gram_nonzero < 8000000 and gram_nonzero < 0.15 * dimension ** 2
        direct_solve = None
        try:
            if use_sparse:
                factorization = splinalg.splu(gram + ridge * sparse.eye(dimension, format='csc'), permc_spec='MMD_AT_PLUS_A', diag_pivot_thresh=0.0, options={'Equil': False, 'SymmetricMode': True})
                direct_solve = factorization.solve
            elif dimension <= 12000 and gram_bytes + 8 * dimension ** 2 < 2300000000:
                dense = gram.toarray(order='F')
                dense.flat[::dimension + 1] += ridge
                factorization = linalg.cho_factor(dense, overwrite_a=True, lower=True, check_finite=False)
                direct_solve = lambda values: linalg.cho_solve(factorization, values, check_finite=False)
            if direct_solve is not None:
                residual = probes.copy()
                transpose = scaled.T.tocsr()
                for iteration in range(6):
                    if dual:
                        residual -= transpose @ direct_solve(scaled @ residual)
                    else:
                        residual = ridge * direct_solve(residual)
                if not dual:
                    for iteration in range(2):
                        residual -= direct_solve(transpose @ (scaled @ residual))
                normal_error = np.linalg.norm(scaled @ residual, axis=0)
                report('calibration direct', dimension, gram_nonzero, 'dual' if dual else 'primal', normal_error.tolist())
                if np.max(normal_error) > 2e-8:
                    residual = None
        except (RuntimeError, MemoryError, linalg.LinAlgError):
            residual = None
        del gram
    if residual is None:
        residual = np.empty_like(probes)
        transpose = scaled.T.tocsr()
        timing_start = time.monotonic()
        for iteration in range(3):
            transpose @ (scaled @ probes[:, 0])
        iteration_time = max((time.monotonic() - timing_start) / 3 * 1.3, 2e-5)
        projection_deadline = min(START + 80, time.monotonic() + 40)
        for probe in range(probes.shape[1]):
            remaining_time = max(0.0, projection_deadline - time.monotonic())
            iteration_limit = max(1, int(remaining_time / ((probes.shape[1] - probe) * iteration_time)))
            iteration_limit = min(iteration_limit, 12000, max(1500, parameter_count * 3))
            timing_start = time.monotonic()
            fitted = splinalg.lsmr(transpose, probes[:, probe], atol=1e-13, btol=1e-13, conlim=1e12, maxiter=iteration_limit)
            if fitted[2] > 0:
                iteration_time = max(iteration_time, (time.monotonic() - timing_start) / fitted[2] * 1.1)
            residual[:, probe] = probes[:, probe] - transpose @ fitted[0]
            report('calibration iterative', probe, fitted[1:5])
    distances = np.linalg.norm(scaled_queries @ residual, axis=1) / np.maximum(query_norms, 1e-300)
    tolerance = 3e-6
    result = structural & (distances < tolerance)
    report('calibration ranks', int(np.sum(structural)), int(np.sum(result)), 'queries', len(result))
    return result


def fit_rates(matrix, shots, plus, signs, deadline):
    parameter_count = matrix.shape[1]
    if not parameter_count:
        return np.empty(0)
    nonzero = (np.diff(matrix.indptr) > 0) & (shots > 0)
    matrix = matrix[nonzero].tocsr()
    shots = shots[nonzero].astype(float)
    plus = np.where(signs[nonzero] > 0, plus[nonzero], shots - plus[nonzero]).astype(float)
    minus = shots - plus
    if not len(shots):
        return np.zeros(parameter_count)
    contrast = (plus - minus) / shots
    observed = np.clip(contrast, 0.02, 1 - 0.5 / (shots + 1))
    target = -np.log(observed)
    weight = shots * observed ** 2 / np.maximum(1 - observed ** 2, 1e-12)
    corrected = target - (1 - observed ** 2) / (2 * shots * observed ** 2)
    corrected = np.maximum(corrected, 0)
    squared = matrix.multiply(matrix)
    diagonal = np.asarray(squared.T @ weight).ravel()
    scale = np.sqrt(np.maximum(diagonal, 1))
    design = matrix.multiply(1 / scale).tocsr()
    transpose = design.T.tocsr()
    row_sums = np.asarray(matrix.sum(axis=1)).ravel()
    initial_rate = max(1e-5, float(np.median(target / np.maximum(row_sums, 1))))
    initial = np.full(parameter_count, initial_rate) * scale
    bounds = [(0.0, None)] * parameter_count
    best = initial.copy()
    best_value = np.inf
    evaluations = 0
    quadratic_evaluations = 0
    saturated = -np.sum(xlogy(plus, plus / shots) + xlogy(minus, minus / shots))
    log_two = np.log(2.0)

    def quadratic(values):
        nonlocal best, best_value, quadratic_evaluations
        quadratic_evaluations += 1
        if quadratic_evaluations % 10 == 0 and time.monotonic() > deadline:
            raise TimeoutError
        difference = design @ values - corrected
        gradient_rows = weight * difference
        value = 0.5 * np.dot(difference, gradient_rows)
        if value < best_value:
            best_value = value
            best = values.copy()
        return value, transpose @ gradient_rows

    try:
        preliminary = optimize.minimize(quadratic, initial, method='L-BFGS-B', jac=True, bounds=bounds, options={'maxiter': 150, 'ftol': 1e-9, 'gtol': 1e-5, 'maxcor': 15})
        initial = preliminary.x
        report('linear fit', preliminary.nit, preliminary.fun)
    except TimeoutError:
        return best / scale
    best = initial.copy()
    best_value = np.inf

    def likelihood(values):
        nonlocal best, best_value, evaluations
        evaluations += 1
        if evaluations % 10 == 0 and time.monotonic() > deadline:
            raise TimeoutError
        attenuation = np.maximum(design @ values, 1e-14)
        mean = np.exp(-attenuation)
        one_minus_mean = -np.expm1(-attenuation)
        value = -np.dot(plus, np.log1p(mean) - log_two) - np.dot(minus, np.log(one_minus_mean) - log_two) - saturated
        gradient_rows = mean * (plus / (1 + mean) - minus / one_minus_mean)
        if value < best_value:
            best = values.copy()
            best_value = value
        return value, transpose @ gradient_rows

    try:
        result = optimize.minimize(likelihood, initial, method='L-BFGS-B', jac=True, bounds=bounds, options={'maxiter': 4000, 'ftol': 2e-11, 'gtol': 2e-6, 'maxcor': 40, 'maxls': 30})
        best = result.x
        report('likelihood fit', result.nit, result.fun, result.message)
    except TimeoutError:
        report('likelihood deadline', evaluations)
    return best / scale


def solve(input_path, output_path):
    global START
    START = time.monotonic()
    with np.load(input_path, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    model = Model(data)
    report('parameters', model.parameter_count)
    training, holdout, training_signs, holdout_signs = model.experiments(data)
    queries = model.queries(data)
    report('design', training.shape, training.nnz, 'holdout', holdout.shape, 'queries', queries.shape)
    structural = model.structural(queries)
    training, shots, plus = compress_experiments(training, data['train_shots'], data['train_plus'], training_signs)
    training, holdout, queries, consistent = compress_parameters(training, holdout, queries)
    calibration = calibration_identifiability(training, queries, structural & consistent)
    rates = fit_rates(training, shots, plus, np.ones(len(shots)), START + 111)
    query_estimate = np.nan_to_num(np.asarray(queries @ rates).ravel(), nan=0.0, posinf=0.0, neginf=0.0)
    holdout_mean = np.nan_to_num(holdout_signs * np.exp(-np.clip(np.asarray(holdout @ rates).ravel(), 0, 745)), nan=0.0)
    np.savez(output_path, structural_identifiable=structural.astype(float), calibration_identifiable=calibration.astype(float), query_log_estimate=query_estimate, holdout_mean=holdout_mean)
    report('saved', output_path)


if __name__ == '__main__':
    solve(sys.argv[1], sys.argv[2])
