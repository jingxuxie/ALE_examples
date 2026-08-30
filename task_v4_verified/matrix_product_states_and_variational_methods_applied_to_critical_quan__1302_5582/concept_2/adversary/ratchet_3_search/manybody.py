import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]
sys.dont_write_bytecode = True
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
sys.path.insert(0, str(CONCEPT / 'adversary' / 'fourpoint_search'))

import itertools
import math
import numpy as np
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg

from fourpoint import ExactTargets, TensorContractions, trusted_physics, write_json


def validate_sites(positions):
    if len(positions) not in (2, 4, 6) or any(int(site) != site for site in positions):
        raise ValueError('Expected two, four, or six integer sites')
    positions = tuple(map(int, positions))
    if any(right <= left for left, right in zip(positions, positions[1:])):
        raise ValueError('Spin sites must be strictly increasing')
    return positions


def determinant(positions, size=None):
    positions = validate_sites(positions)
    rows = np.concatenate([np.arange(first + 1, second + 1) for first, second in zip(positions[::2], positions[1::2])])
    columns = rows - 1
    differences = rows[:, None] - columns[None, :] - .5
    if size is None:
        matrix = 1 / (np.pi * differences)
    else:
        if size % 2 or size < 4 or positions[0] < 0 or positions[-1] >= size:
            raise ValueError('Expected ordered sites in an even periodic chain')
        matrix = 1 / (size * np.sin(np.pi * differences / size))
    sign, logarithm = np.linalg.slogdet(matrix)
    return float(sign * np.exp(logarithm))


def stable_six(positions, targets=None, size=None):
    positions = validate_sites(positions)
    if len(positions) != 6:
        raise ValueError('Six sites required')
    intervals = list(zip(positions[::2], positions[1::2]))
    if targets is None:
        targets = ExactTargets(positions[-1] - positions[0])
    means = [targets.pair(second - first) if size is None else determinant((first, second), size) for first, second in intervals]
    enhancements = []
    for left_index, right_index in ((0, 1), (0, 2), (1, 2)):
        first, second = intervals[left_index]
        third, fourth = intervals[right_index]
        if size is None:
            enhancement = targets.evaluate((first, second, third, fourth))['connected_ratio']
        else:
            distances = np.arange(third + 1, fourth + 1)[None, :] - np.arange(first + 1, second + 1)[:, None]
            logarithm = np.sum(-np.log1p(-np.sin(np.pi / (2 * size))**2 / np.sin(np.pi * distances / size)**2), dtype=np.longdouble)
            enhancement = float(np.expm1(logarithm))
        enhancements.append(enhancement)
    first_cross, outer_cross, last_cross = enhancements
    product = math.prod(means)
    cumulant = product * (first_cross * outer_cross + first_cross * last_cross + outer_cross * last_cross + first_cross * outer_cross * last_cross)
    raw = product * math.prod(1 + enhancement for enhancement in enhancements)
    return {'raw': raw, 'third_composite_cumulant': cumulant, 'pair_means': means,
            'cross_enhancements_12_13_23': enhancements, 'pair_product': product}


def high_precision_six(positions, digits=70):
    import mpmath as mp
    positions = validate_sites(positions)
    with mp.workdps(digits):
        intervals = list(zip(positions[::2], positions[1::2]))
        means = []
        for first, second in intervals:
            length = second - first
            logarithm = length * mp.log(2 / mp.pi) - mp.fsum((length - offset) * mp.log1p(-mp.mpf(1) / (4 * offset**2)) for offset in range(1, length))
            means.append(mp.exp(logarithm))
        enhancements = []
        for left_index, right_index in ((0, 1), (0, 2), (1, 2)):
            first, second = intervals[left_index]
            third, fourth = intervals[right_index]
            logarithm = mp.fsum(-mp.log1p(-mp.mpf(1) / (4 * (right_site - left_site)**2))
                               for left_site in range(first + 1, second + 1) for right_site in range(third + 1, fourth + 1))
            enhancements.append(mp.expm1(logarithm))
        first_cross, outer_cross, last_cross = enhancements
        product = mp.fprod(means)
        cumulant = product * (first_cross * outer_cross + first_cross * last_cross + outer_cross * last_cross + first_cross * outer_cross * last_cross)
        raw = product * mp.fprod(1 + enhancement for enhancement in enhancements)
        return {'raw': str(raw), 'third_composite_cumulant': str(cumulant), 'digits': digits}


def binary_powers(transfer, maximum):
    powers = [transfer]
    for bit in range(1, max(1, int(maximum).bit_length())):
        powers.append(powers[-1] @ powers[-1])
    return powers


def matrix_power(powers, exponent):
    result = np.eye(powers[0].shape[0], dtype=powers[0].dtype)
    for bit, power in enumerate(powers):
        if exponent & (1 << bit):
            result = power @ result
    return result


class SixContractions:
    def __init__(self, tensor, lengths, gaps):
        self.tensor = np.asarray(tensor)
        self.direct = TensorContractions(tensor)
        self.dimension = tensor.shape[1]
        half = self.dimension // 2
        rows, columns = np.indices((self.dimension, self.dimension))
        even_indices = np.flatnonzero(((rows < half) == (columns < half)).reshape(-1))
        odd_indices = np.flatnonzero(((rows < half) != (columns < half)).reshape(-1))
        full = trusted_physics.transfer_matrix(tensor)
        insertion = np.kron(tensor[0], tensor[1].conj()) + np.kron(tensor[1], tensor[0].conj())
        self.transfer = full[np.ix_(even_indices, even_indices)]
        odd_transfer = full[np.ix_(odd_indices, odd_indices)]
        even_from_odd = insertion[np.ix_(even_indices, odd_indices)]
        odd_from_even = insertion[np.ix_(odd_indices, even_indices)]
        self.powers = binary_powers(self.transfer, 4 * max(lengths) + 2 * max(gaps) + 8)
        odd_powers = binary_powers(odd_transfer, max(lengths))
        self.identity = np.eye(self.dimension).reshape(-1)[even_indices]
        self.density = self.direct.density.reshape(-1)[even_indices]
        self.maps = {}
        self.centered_maps = {}
        self.left = {}
        self.right = {}
        self.left_raw = {}
        self.right_raw = {}
        self.means = {}
        for length in lengths:
            insertion_map = even_from_odd @ matrix_power(odd_powers, length - 1) @ odd_from_even
            mean = np.vdot(self.density, insertion_map @ self.identity)
            if abs(mean.imag) > 1e-10:
                raise ValueError('Non-real interval mean')
            mean = float(mean.real)
            self.maps[length] = insertion_map
            self.means[length] = mean
            self.centered_maps[length] = insertion_map - mean * matrix_power(self.powers, length + 1)
            self.left_raw[length] = self.density.conj() @ insertion_map
            self.right_raw[length] = insertion_map @ self.identity
            self.left[length] = self.left_raw[length] - mean * self.density.conj()
            self.right[length] = self.right_raw[length] - mean * self.identity
        self.left_labels = [(length, gap) for length in lengths for gap in gaps]
        self.right_labels = [(length, gap) for length in lengths for gap in gaps]
        gap_powers = {gap: matrix_power(self.powers, gap - 1) for gap in gaps}
        self.left_rows = np.stack([self.left[length] @ gap_powers[gap] for length, gap in self.left_labels])
        self.left_raw_rows = np.stack([self.left_raw[length] @ gap_powers[gap] for length, gap in self.left_labels])
        self.right_columns = np.stack([gap_powers[gap] @ self.right[length] for length, gap in self.right_labels], axis=1)
        self.right_raw_columns = np.stack([gap_powers[gap] @ self.right_raw[length] for length, gap in self.right_labels], axis=1)

    def batch(self, middle_length):
        connected = self.left_rows @ self.centered_maps[middle_length] @ self.right_columns
        raw = self.left_raw_rows @ self.maps[middle_length] @ self.right_raw_columns
        if max(np.max(np.abs(connected.imag)), np.max(np.abs(raw.imag))) > 1e-9:
            raise ValueError('Non-real many-body contraction')
        return raw.real, connected.real

    def direct_moment(self, positions):
        positions = validate_sites(positions)
        environment = self.direct.identity.copy()
        selected = set(positions)
        for site in range(positions[-1], positions[0] - 1, -1):
            environment = self.direct.apply(environment, site in selected)
        result = np.trace(self.direct.density @ environment)
        if abs(result.imag) > 1e-10:
            raise ValueError('Non-real sequential moment')
        return float(result.real)

    def direct_six(self, positions):
        intervals = [tuple(pair) for pair in zip(positions[::2], positions[1::2])]
        means = [self.direct_moment(pair) for pair in intervals]
        fours = [self.direct_moment(intervals[first] + intervals[second]) for first, second in ((0, 1), (0, 2), (1, 2))]
        raw = self.direct_moment(positions)
        cumulant = raw - fours[0] * means[2] - fours[1] * means[1] - fours[2] * means[0] + 2 * math.prod(means)
        return {'raw': raw, 'third_composite_cumulant': cumulant, 'pair_means': means, 'four_moments_12_13_23': fours}


def validate_ed():
    records = []
    for size in (6, 8, 10, 12):
        labels = np.arange(2**size, dtype=np.int64)
        magnetization = sum(1 - 2 * ((labels >> site) & 1) for site in range(size))
        rows, columns, values = [labels], [labels], [-magnetization.astype(float)]
        for site in range(size):
            rows.append(labels)
            columns.append(labels ^ ((1 << site) | (1 << ((site + 1) % size))))
            values.append(-np.ones(len(labels)))
        hamiltonian = sparse.coo_matrix((np.concatenate(values), (np.concatenate(rows), np.concatenate(columns))), shape=(len(labels), len(labels))).tocsr()
        energies, vectors = sparse_linalg.eigsh(hamiltonian, k=1, which='SA', tol=2e-14, v0=np.ones(len(labels)), maxiter=10000)
        ground = vectors[:, 0]
        residual = float(np.linalg.norm(hamiltonian @ ground - energies[0] * ground))
        parity = np.prod([1 - 2 * ((labels >> site) & 1) for site in range(size)], axis=0)
        parity_mean = float(np.dot(ground**2, parity))
        moments = {}

        def moment(positions):
            mask = sum(1 << site for site in positions)
            if mask not in moments:
                moments[mask] = float(np.dot(ground, ground[labels ^ mask]))
            return moments[mask]

        maxima = {'raw_vs_determinant': 0.0, 'raw_vs_stable_product': 0.0, 'connected_vs_stable_product': 0.0}
        count = 0
        worst = None
        for positions in itertools.combinations(range(size), 6):
            observed = moment(positions)
            direct = determinant(positions, size)
            stable = stable_six(positions, size=size)
            pairs = list(zip(positions[::2], positions[1::2]))
            means = [moment(pair) for pair in pairs]
            cumulant = observed - moment(pairs[0] + pairs[1]) * means[2] - moment(pairs[0] + pairs[2]) * means[1] - moment(pairs[1] + pairs[2]) * means[0] + 2 * math.prod(means)
            differences = {'raw_vs_determinant': abs(observed - direct), 'raw_vs_stable_product': abs(observed - stable['raw']), 'connected_vs_stable_product': abs(cumulant - stable['third_composite_cumulant'])}
            if differences['connected_vs_stable_product'] > maxima['connected_vs_stable_product']:
                worst = {'positions': positions, 'ed_cumulant': cumulant, 'stable_cumulant': stable['third_composite_cumulant']}
            maxima = {key: max(maxima[key], differences[key]) for key in maxima}
            count += 1
        record = {'size': size, 'sextuples_checked': count, 'energy': float(energies[0]), 'eigen_residual': residual, 'parity': parity_mean, 'maximum_absolute_differences': maxima, 'worst_connected': worst}
        records.append(record)
        if max(maxima.values()) > 2e-11 or residual > 2e-10 or abs(parity_mean - 1) > 1e-10:
            raise RuntimeError('Independent spin ED did not certify six-spin target')
    generator = np.random.default_rng(449)
    infinite = []
    targets = ExactTargets(256)
    for sample in range(30):
        spacings = generator.integers(1, 24, size=5)
        positions = tuple(map(int, np.r_[0, np.cumsum(spacings)]))
        direct = determinant(positions)
        stable = stable_six(positions, targets)
        infinite.append({'positions': positions, 'absolute_difference': abs(direct - stable['raw'])})
    if max(record['absolute_difference'] for record in infinite) > 1e-11:
        raise RuntimeError('Six-spin product disagrees with independent dense determinant')
    result = {'finite_spin_ed': records, 'infinite_dense_determinants': infinite}
    write_json(ROOT / 'six_ed_certificates.json', result)
    return result
