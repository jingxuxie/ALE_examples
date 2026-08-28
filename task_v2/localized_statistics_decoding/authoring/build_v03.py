import json
from pathlib import Path
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'solution/v_03'))
from core import BpOsdDecoder, legacy_correction, make_decoders, recover


def row_masks(matrix):
    return [sum(1 << int(column) for column in np.flatnonzero(row)) for row in matrix]


def insert(basis, vector):
    while vector:
        pivot = vector.bit_length() - 1
        if pivot not in basis:
            basis[pivot] = vector
            return True
        vector ^= basis[pivot]
    return False


def nullspace(matrix):
    rows = row_masks(matrix)
    pivots = []
    row = 0
    for column in range(matrix.shape[1]):
        choices = [index for index in range(row, len(rows)) if (rows[index] >> column) & 1]
        if not choices:
            continue
        pivot = choices[0]
        rows[row], rows[pivot] = rows[pivot], rows[row]
        for other in range(len(rows)):
            if other != row and (rows[other] >> column) & 1:
                rows[other] ^= rows[row]
        pivots.append(column)
        row += 1
    output = []
    for column in range(matrix.shape[1]):
        if column in pivots:
            continue
        vector = 1 << column
        for pivot_row, pivot_column in enumerate(pivots):
            if (rows[pivot_row] >> column) & 1:
                vector |= 1 << pivot_column
        output.append(vector)
    return output


def quotient(matrix, stabilizers):
    basis = {}
    for vector in row_masks(stabilizers):
        insert(basis, vector)
    output = []
    for vector in nullspace(matrix):
        if insert(basis, vector):
            output.append([(vector >> index) & 1 for index in range(matrix.shape[1])])
    return np.asarray(output, dtype=np.uint8)


def code(length, width):
    shift_x = np.kron(np.roll(np.eye(length, dtype=np.uint8), 1, axis=1), np.eye(width, dtype=np.uint8))
    shift_y = np.kron(np.eye(length, dtype=np.uint8), np.roll(np.eye(width, dtype=np.uint8), 1, axis=1))
    matrix_a = (np.linalg.matrix_power(shift_x, 3) + shift_y + shift_y @ shift_y) % 2
    matrix_b = (np.linalg.matrix_power(shift_y, 3) + shift_x + shift_x @ shift_x) % 2
    checks_x = np.column_stack([matrix_a, matrix_b]).astype(np.uint8)
    checks_z = np.column_stack([matrix_b.T, matrix_a.T]).astype(np.uint8)
    if np.any((checks_x @ checks_z.T) % 2):
        raise AssertionError('Noncommuting checks')
    logical_z = quotient(checks_x, checks_z)
    logical_x = quotient(checks_z, checks_x)
    zeros = np.zeros_like(checks_x)
    matrix = np.block([[checks_z, checks_z, zeros], [zeros, checks_x, checks_x]]).astype(np.uint8)
    logical_zeros = np.zeros_like(logical_x)
    logical = np.block([[logical_z, logical_z, logical_zeros], [logical_zeros, logical_x, logical_x]]).astype(np.uint8)
    return matrix, logical, checks_x.shape[1], len(logical_x)


def build_case(name, length, width, base_rates, count, seed):
    random = np.random.default_rng(seed)
    matrix, logical, physical_qubits, logical_qubits = code(length, width)
    prior = np.repeat(base_rates, physical_qubits) * np.exp(random.normal(0, 0.25, 3 * physical_qubits))
    prior = np.clip(prior, 0.001, 0.15)
    columns = random.permutation(matrix.shape[1])
    rows = random.permutation(matrix.shape[0])
    matrix = matrix[rows][:, columns]
    logical = logical[:, columns]
    prior = prior[columns]
    frontend = BpOsdDecoder(matrix, error_channel=prior.tolist(), max_iter=100,
                            bp_method='minimum_sum', ms_scaling_factor=0.625,
                            schedule='parallel', osd_method='OSD_0', osd_order=0, omp_thread_count=1)
    decoders = make_decoders(matrix, prior)
    syndromes = []
    reliabilities = []
    targets = []
    true_errors = []
    legacy_costs = []
    reference_costs = []
    draws = 0
    baseline_failures = 0
    started = time.monotonic()
    weights = np.log((1 - prior) / prior)
    while len(syndromes) < count and draws < 50000:
        draws += 1
        error = (random.random(matrix.shape[1]) < prior).astype(np.uint8)
        syndrome = (matrix @ error) % 2
        target = (logical @ error) % 2
        frontend.decode(syndrome)
        reliability = np.asarray(frontend.log_prob_ratios).copy()
        legacy = legacy_correction(matrix, syndrome, reliability)
        if np.array_equal((logical @ legacy) % 2, target):
            continue
        baseline_failures += 1
        repaired = recover(matrix, syndrome, prior, reliability, decoders)
        if not np.array_equal((logical @ repaired) % 2, target):
            continue
        legacy_cost = float(weights @ legacy)
        repaired_cost = float(weights @ repaired)
        if legacy_cost - repaired_cost < 0.5:
            continue
        syndromes.append(syndrome)
        reliabilities.append(reliability)
        targets.append(target)
        true_errors.append(error)
        legacy_costs.append(legacy_cost)
        reference_costs.append(repaired_cost)
        if len(syndromes) % 8 == 0:
            print(json.dumps({'case': name, 'accepted': len(syndromes), 'draws': draws,
                              'seconds': round(time.monotonic() - started, 2)}), flush=True)
    if len(syndromes) != count:
        raise RuntimeError(f'Could not curate {name}: {len(syndromes)} / {count}')
    data = {'H': matrix, 'L': logical, 'prior': prior, 'syndrome': np.asarray(syndromes, dtype=np.uint8),
            'soft_llr': np.asarray(reliabilities)}
    labels = {'logical_target': np.asarray(targets, dtype=np.uint8)}
    provenance = {'id': name, 'physical_qubits': physical_qubits, 'logical_qubits': logical_qubits,
                  'mechanisms': matrix.shape[1], 'detectors': matrix.shape[0], 'frames': count,
                  'draws': draws, 'legacy_failures_seen': baseline_failures,
                  'seconds': round(time.monotonic() - started, 3),
                  'mean_legacy_cost': float(np.mean(legacy_costs)),
                  'mean_reference_cost': float(np.mean(reference_costs)),
                  'corpus': 'legacy-failed, lower-cost reference-recoverable independent-mechanism replay'}
    return data, labels, np.asarray(true_errors), provenance


def main():
    cases = [
        ('validation_small', 6, 6, [0.012, 0.024, 0.012], 20, 88321, False),
        ('validation_large', 12, 6, [0.014, 0.032, 0.014], 20, 719233, False),
        ('heldout_bias', 12, 6, [0.025, 0.060, 0.020], 24, 912701, True),
        ('heldout_geometry', 9, 6, [0.027, 0.046, 0.027], 24, 562017, True),
        ('heldout_scale', 12, 12, [0.027, 0.036, 0.027], 24, 371917, True),
    ]
    manifest = []
    for name, length, width, rates, count, seed, hidden in cases:
        data, labels, errors, record = build_case(name, length, width, rates, count, seed)
        destination = ROOT / ('evaluator/v_03/hidden' if hidden else 'participant/v_03/input')
        np.savez_compressed(destination / f'{name}.npz', **data)
        np.savez_compressed(destination / f'{name}_labels.npz', **labels)
        np.savez_compressed(ROOT / 'authoring' / f'{name}_physical_replays.npz', error=errors)
        manifest.append(record)
        print(json.dumps(record), flush=True)
    (ROOT / 'authoring/v03_curation_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
