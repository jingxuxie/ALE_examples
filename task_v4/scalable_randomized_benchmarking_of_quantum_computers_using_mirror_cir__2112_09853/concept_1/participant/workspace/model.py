import itertools
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import minimize_scalar


LOCAL_PERMUTATIONS = list(itertools.permutations((1, 2, 3)))
EDGES = [(0, 1), (0, 3), (1, 2), (1, 0), (2, 3), (2, 1), (3, 0), (3, 2)]
DEPTHS = np.arange(0, 258, 2)
BIAS_TARGET = 0.0235


def embed(digit, site):
    return ((digit & 1) << site) | (((digit >> 1) & 1) << (site + 4))


def native_ensemble():
    labels = np.arange(256, dtype=np.int64)
    permutations = []
    inverse = []
    supports = []
    for site in range(4):
        digit = ((labels >> site) & 1) | (((labels >> (site + 4)) & 1) << 1)
        remainder = labels ^ (digit % 2 << site) ^ (digit // 2 << (site + 4))
        for class_index, local in enumerate(LOCAL_PERMUTATIONS):
            lookup = np.array([0] + list(local))
            transformed = lookup[digit]
            permutations.append(remainder | ((transformed & 1) << site)
                                | ((transformed >> 1) << (site + 4)))
            reversed_local = tuple(local.index(value) + 1 for value in (1, 2, 3))
            inverse.append(site * 6 + LOCAL_PERMUTATIONS.index(reversed_local))
            supports.append([embed(value, site) for value in (1, 2, 3)])
    for edge_index, (control, target) in enumerate(EDGES):
        transformed = labels.copy()
        transformed ^= ((labels >> control) & 1) << target
        transformed ^= ((labels >> (target + 4)) & 1) << (control + 4)
        permutations.append(transformed)
        inverse.append(24 + edge_index)
        supports.append([embed(value % 4, control) | embed(value // 4, target)
                         for value in range(1, 16)])
    weights = np.array([1] * 24 + [2] * 8, dtype=np.int64)
    return np.array(permutations), np.array(inverse), supports, weights


PERMUTATIONS, INVERSE, SUPPORTS, WEIGHTS = native_ensemble()


def baseline():
    return {'single': [[[20, 20, 20] for class_index in range(6)] for site in range(4)],
            'cx': [[4] * 15 for edge in EDGES]}


def rows_of(artifact):
    if not isinstance(artifact, dict) or set(artifact) != {'single', 'cx'}:
        raise ValueError('Expected exactly the keys single and cx.')
    single = artifact['single']
    cnot = artifact['cx']
    if not isinstance(single, list) or len(single) != 4:
        raise ValueError('single must have shape [4,6,3].')
    rows = []
    for block in single:
        if not isinstance(block, list) or len(block) != 6:
            raise ValueError('single must have shape [4,6,3].')
        for row in block:
            if not isinstance(row, list) or len(row) != 3:
                raise ValueError('single must have shape [4,6,3].')
            rows.append(row)
    if not isinstance(cnot, list) or len(cnot) != 8:
        raise ValueError('cx must have shape [8,15].')
    for row in cnot:
        if not isinstance(row, list) or len(row) != 15:
            raise ValueError('cx must have shape [8,15].')
        rows.append(row)
    for index, row in enumerate(rows):
        lower, upper = (2, 42) if index < 24 else (1, 21)
        if any(type(value) is not int or not lower <= value <= upper for value in row):
            raise ValueError(f'Row {index} must contain JSON integers in [{lower},{upper}].')
        if sum(row) != 60:
            raise ValueError(f'Row {index} does not sum to 60.')
    return rows


def count_matrix(artifact):
    counts = np.zeros((32, 256), dtype=np.int64)
    for index, row in enumerate(rows_of(artifact)):
        counts[index, SUPPORTS[index]] = row
    return counts


BASELINE_COUNTS = count_matrix(baseline())
BASELINE_MARGINALS = WEIGHTS @ BASELINE_COUNTS
BASELINE_SINGLE_MARGINALS = np.sum(BASELINE_COUNTS[:24], axis=0)
BASELINE_CNOT_MARGINALS = np.sum(BASELINE_COUNTS[24:], axis=0)


def check_constraints(artifact):
    counts = count_matrix(artifact)
    marginals = WEIGHTS @ counts
    if not np.array_equal(marginals, BASELINE_MARGINALS):
        difference = int(np.max(np.abs(marginals - BASELINE_MARGINALS)))
        raise ValueError(f'Ensemble-average channel mismatch; max weighted count difference {difference}.')
    single_marginals = np.sum(counts[:24], axis=0)
    cnot_marginals = np.sum(counts[24:], axis=0)
    for family, observed, expected in (
            ('single-qubit', single_marginals, BASELINE_SINGLE_MARGINALS),
            ('CNOT', cnot_marginals, BASELINE_CNOT_MARGINALS)):
        if not np.array_equal(observed, expected):
            difference = int(np.max(np.abs(observed - expected)))
            raise ValueError(f'Family-resolved average-channel mismatch for {family}; '
                             f'max unweighted count difference {difference}.')
    class_overlaps = np.sum(counts[INVERSE]
                            * np.take_along_axis(counts, PERMUTATIONS, axis=1), axis=1)
    overlap = int(WEIGHTS @ class_overlaps)
    if overlap != 32640:
        raise ValueError(f'Inverse-pair overlap {overlap}, required 32640.')
    single_overlap = int(np.sum(class_overlaps[:24]))
    cnot_overlap = int(np.sum(class_overlaps[24:]))
    if single_overlap != 28800 or cnot_overlap != 1920:
        raise ValueError(f'Family-resolved inverse-pair overlaps are {single_overlap}, {cnot_overlap}; '
                         'required 28800 for single-qubit classes and 1920 for CNOT classes.')
    return counts


def pauli_characters():
    labels = np.arange(256, dtype=np.int64)
    parity = ((labels[:, None] & 15) & (labels[None, :] >> 4))
    parity ^= ((labels[:, None] >> 4) & (labels[None, :] & 15))
    lookup = np.array([1 - 2 * (int(value).bit_count() % 2) for value in range(16)])
    return lookup[parity]


CHARACTERS = pauli_characters()


def exact_curve(counts):
    eigenvalues = 0.98 + counts @ CHARACTERS / 3000.0
    transformed = np.take_along_axis(eigenvalues, PERMUTATIONS, axis=1)
    weights = (WEIGHTS[:, None] / 40.0) * eigenvalues[INVERSE] * transformed
    permutation = PERMUTATIONS[:, 1:] - 1
    vector = np.ones(255)
    signal = [1.0]
    for halfdepth in range(128):
        vector = np.sum(weights[:, 1:] * vector[permutation], axis=0)
        signal.append(float(vector.mean()))
    return np.array(signal)


def fit_curve(signal):
    grid = np.linspace(0.005, 0.04, 4097)
    curves = np.exp(-grid[:, None] * DEPTHS)
    amplitudes = (curves @ signal) / np.sum(curves ** 2, axis=1)
    losses = np.sum((amplitudes[:, None] * curves - signal) ** 2, axis=1)

    def objective(decay):
        shape = np.exp(-decay * DEPTHS)
        amplitude = float(np.dot(shape, signal) / np.dot(shape, shape))
        return float(np.sum((amplitude * shape - signal) ** 2))

    candidates = [(float(losses[0]), float(grid[0])), (float(losses[-1]), float(grid[-1]))]
    minima = np.flatnonzero((losses[1:-1] <= losses[:-2]) & (losses[1:-1] <= losses[2:])) + 1
    for index in minima:
        result = minimize_scalar(objective, bounds=(grid[index - 1], grid[index + 1]),
                                 method='bounded', options={'xatol': 1e-12})
        candidates.append((float(result.fun), float(result.x)))
    loss, decay = min(candidates)
    shape = np.exp(-decay * DEPTHS)
    amplitude = float(np.dot(shape, signal) / np.dot(shape, shape))
    inferred = float((255 / 256) * (-np.expm1(-decay)))
    return {'fitted_infidelity': inferred, 'relative_bias': 1 - inferred / 0.02,
            'amplitude': amplitude, 'decay': decay, 'sum_squared_error': loss,
            'max_residual': float(np.max(np.abs(amplitude * shape - signal)))}


def evaluate(artifact):
    started = time.monotonic()
    result = {'core_score': 0.0, 'worst_family_score': 0.0, 'passed': False,
              'valid': False, 'admissible': False, 'true_infidelity': 0.02}
    try:
        counts = check_constraints(artifact)
        result['admissible'] = True
        signal = exact_curve(counts)
        metrics = fit_curve(signal)
        result.update(metrics)
        result['depth_2_polarization'] = float(signal[1])
        result['depth_256_polarization'] = float(signal[-1])
        result['core_score'] = float(100 * max(0, metrics['relative_bias']) / BIAS_TARGET)
        result['worst_family_score'] = result['core_score']
        failures = []
        if metrics['relative_bias'] < BIAS_TARGET - 1e-10:
            failures.append(f'relative bias is below {BIAS_TARGET}')
        if metrics['max_residual'] > 0.004 + 1e-10:
            failures.append('maximum exponential-fit residual exceeds 0.004')
        if signal[-1] < 0.005 - 1e-10:
            failures.append('depth-256 polarization is below 0.005')
        result['passed'] = not failures
        result['valid'] = not failures
        result['reason'] = '; '.join(failures) if failures else 'Valid calibration-matched falsification witness.'
    except (ValueError, TypeError, OverflowError) as error:
        result['reason'] = str(error)
    result['runtime_seconds'] = time.monotonic() - started
    result['resource_score'] = 1.0 if result['runtime_seconds'] <= 30 else 0.0
    return result


def load_artifact(path):
    path = Path(path)
    if path.stat().st_size > 65536:
        raise ValueError('Artifact exceeds 64 KiB.')

    def unique_keys(pairs):
        mapping = {}
        for key, value in pairs:
            if key in mapping:
                raise ValueError('Duplicate JSON key.')
            mapping[key] = value
        return mapping

    return json.loads(path.read_text(), object_pairs_hook=unique_keys)
