import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

import numpy as np
from scipy.linalg import qr, svd

AUDIT = Path(__file__).resolve().parent
REFERENCE = AUDIT.parent
ROOT = REFERENCE.parent.parent
FROZEN = ROOT.parent / 'private/runs/pilot/submissions/concept_02_gateset.py'
sys.path.insert(0, str(REFERENCE))
sys.path.insert(0, str(ROOT / 'private'))

from evaluator import run_case
from generate import build_case, pack_experiments, pack_queries, physical_rates, save_npz, topology
from metrics import WEIGHTS, losses, score_components
from solver import Model, membership, row_basis
from weak_baseline import solve as weak_solve


CASES = [
    ('sector_x', 'calibration_sectors', 20, 9050101),
    ('sector_y', 'calibration_sectors', 20, 9050103),
    ('sector_xyz', 'calibration_sectors', 24, 9050111),
    ('crosstalk_anisotropy', 'connected_crosstalk', 20, 9050201),
    ('crosstalk_extra_pairs', 'connected_crosstalk', 24, 9050203),
    ('compiled_asymmetric_spam', 'connected_crosstalk', 20, 9050209),
    ('shots_short_anchors', 'shot_imbalance', 20, 9050301),
    ('shots_long_anchors', 'shot_imbalance', 24, 9050307),
    ('shots_gate_imbalance', 'shot_imbalance', 24, 9050311),
]


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_hashes():
    files = [FROZEN, ROOT / 'private/evaluator.py', ROOT.parent / 'private/evaluation_sandbox.py']
    for name in ('solver.py', 'generate.py', 'metrics.py', 'weak_baseline.py', 'test_reference.py'):
        files.append(REFERENCE / name)
    for directory in (ROOT / 'participant', REFERENCE / 'core', ROOT / 'private/challenge_pool'):
        files.extend(path for path in directory.rglob('*') if path.is_file())
    return {str(path.resolve()): file_hash(path) for path in sorted(set(files))}


def unpack_experiments(data, prefix):
    return [(data[prefix + '_gates'][begin:end].tolist(), observable.copy())
            for begin, end, observable in zip(data[prefix + '_ptr'][:-1], data[prefix + '_ptr'][1:],
                                              data[prefix + '_observable'])]


def repack_gates(data, operations):
    pointers, flat = [0], []
    for gate in operations:
        flat.extend(gate)
        pointers.append(len(flat))
    data['gate_ptr'] = np.array(pointers, dtype=np.int32)
    data['gate_ops'] = np.array(flat, dtype=np.int16)


def rotate_sector(data, sector):
    old = Model(data)
    operations = []
    for gate in old.operations:
        active = sorted({int(site) for opcode, first, second in gate
                         for site in ([first] if opcode < 3 else [first, second])})
        before, after = [], []
        for site in active:
            if sector[site] == 1:
                before.append((1, site, -1))
                after.append((1, site, -1))
            elif sector[site] == 2:
                before.extend([(2, site, -1)] * 3 + [(1, site, -1)])
                after.extend([(1, site, -1), (2, site, -1)])
        operations.append(before + [tuple(operation) for operation in gate] + after)
    repack_gates(data, operations)
    for prefix in ('train', 'holdout'):
        original = data[prefix + '_observable'].copy()
        rotated = original.copy()
        for site, axis in enumerate(sector):
            mapping = np.array([0, 3, 2, 1]) if axis == 1 else np.array([0, 3, 1, 2])
            if axis != 3:
                rotated[:, site] = mapping[original[:, site]]
        data[prefix + '_observable'] = rotated


def add_distance_two_factors(data, random):
    qubits = int(data['n_qubits'])
    neighbors = [set() for _ in range(qubits)]
    existing = set()
    for channel, mask in zip(data['factor_channel'], data['factor_mask']):
        sites = tuple(np.flatnonzero(mask))
        if channel >= 0 and len(sites) == 2:
            existing.add(sites)
            first, second = sites
            neighbors[first].add(second)
            neighbors[second].add(first)
    candidates = sorted({tuple(sorted((first, second))) for middle in range(qubits)
                         for first in neighbors[middle] for second in neighbors[middle]
                         if first != second} - existing)
    selected = random.choice(len(candidates), min(qubits // 2, len(candidates)), replace=False)
    masks, channels = [], []
    for position in selected:
        mask = np.zeros(qubits, dtype=np.int8)
        mask[list(candidates[position])] = 1
        for channel in sorted(set(data['gate_noise']) - {-1}):
            masks.append(mask.copy())
            channels.append(channel)
    data['factor_mask'] = np.concatenate([data['factor_mask'], np.array(masks)])
    data['factor_channel'] = np.concatenate([data['factor_channel'], np.array(channels, dtype=np.int16)])
    return len(masks)


def compile_gates_and_asymmetric_spam(data):
    old = Model(data)
    operations = []
    for gate_index, gate in enumerate(old.operations):
        sequence = [tuple(operation) for operation in gate]
        if old.noise[gate_index] >= 0:
            dressed = []
            for opcode, first, second in sequence:
                dressed.extend([(opcode, first, second), (2, first, -1)])
            sequence = dressed
        operations.append(sequence)
    repack_gates(data, operations)
    keep = ~((data['factor_channel'] == -2) & (data['factor_mask'].sum(axis=1) == 2))
    data['factor_channel'] = data['factor_channel'][keep]
    data['factor_mask'] = data['factor_mask'][keep]


def random_observable(random, qubits, sector=None):
    weight = int(random.integers(1, 4))
    sites = random.choice(qubits, weight, replace=False)
    pauli = np.zeros(qubits, dtype=np.int8)
    pauli[sites] = random.integers(1, 4, weight) if sector is None else sector[sites]
    return pauli


def sector_controls(model, sector):
    clean = np.flatnonzero(model.noise < 0).tolist()
    if sector is None:
        return clean
    allowed = []
    for gate in clean:
        preserves = True
        for site in range(model.qubits):
            pauli = np.zeros(model.qubits, dtype=np.int8)
            pauli[site] = sector[site]
            changed, _ = model.backward(gate, pauli)
            if np.any((changed != 0) & (changed != sector)):
                preserves = False
                break
        if preserves:
            allowed.append(gate)
    return allowed


def new_queries(data, model, training, sector, random):
    noisy = np.flatnonzero(model.noise >= 0).tolist()
    channels = sorted(model.factors)
    queries = []
    for position in range(112):
        selected_sector = sector if position % 4 in (1, 2) else None
        pauli = random_observable(random, model.qubits, selected_sector)
        if position % 4 == 0:
            terms = [(int(random.choice(channels)), pauli, 1.0)]
        elif position % 4 == 1:
            gate = int(random.choice(noisy))
            current = pauli.copy()
            period = 0
            for repetition in range(1, 25):
                current, _ = model.backward(gate, current)
                if np.array_equal(current, pauli):
                    period = repetition
                    break
            if not period:
                raise AssertionError('Unexpected Clifford order beyond audit bound')
            _, _, components = model.trace([gate] * period, pauli, terms=True)
            terms = [term for term in components if term[0] >= 0]
        elif position % 4 == 2:
            sequence, observable = training[int(random.integers(len(training)))]
            _, _, terms = model.trace(sequence[:6], observable, terms=True)
        else:
            other = random_observable(random, model.qubits)
            channel = int(random.choice(noisy))
            channel = int(model.noise[channel])
            terms = [(channel, pauli, 1.0), (channel, other, -1.0)]
        queries.append(terms)
    random.shuffle(queries)
    pack_queries(data, queries)
    return np.array([sum(abs(coefficient) * max(1, np.count_nonzero(pauli))
                         for channel, pauli, coefficient in terms) for terms in queries])


def create_case(name, qubits, seed):
    restricted = name.startswith('sector_')
    family = 'restricted_components' if restricted else 'parallel_crosstalk'
    data, _, _ = build_case(seed, qubits, family, 4)
    random = np.random.default_rng(seed + 140921)
    sector = None
    changes = {}
    if restricted:
        axis = {'sector_x': 1, 'sector_y': 2}.get(name)
        sector = np.full(qubits, axis, dtype=np.int8) if axis else random.integers(1, 4, qubits, dtype=np.int8)
        rotate_sector(data, sector)
        changes['calibration_axes'] = sector.tolist()
    if name == 'crosstalk_extra_pairs':
        changes['added_gate_factors'] = add_distance_two_factors(data, random)
    if name == 'compiled_asymmetric_spam':
        compile_gates_and_asymmetric_spam(data)
        changes['gate_compilation'] = 'Each disjoint entangler followed by control-site S; preparation pairs removed'
    model = Model(data)
    rates = physical_rates(model, random, 4)
    if name == 'crosstalk_anisotropy':
        for position, channel in enumerate(model.channels):
            if channel >= 0:
                pair = np.count_nonzero(model.supports[position]) == 2
                axes = model.labels[position][model.labels[position] != 0]
                rates[position] *= 1.6 if pair and np.any(axes == 3) else 0.65
            elif channel == -1 and np.count_nonzero(model.supports[position]) == 2:
                rates[position] *= 2
        changes['rate_shift'] = 'Stronger anisotropic pair crosstalk and correlated readout; all rates remain positive'
    rooted = model.rooted_experiments()
    if sector is not None:
        rooted = [(sequence, pauli) for sequence, pauli in rooted
                  if np.all((pauli == 0) | (pauli == sector))]
    root_rows = np.array([model.trace(sequence, pauli)[0] for sequence, pauli in rooted])
    root_basis = row_basis(root_rows)
    _, _, pivots = qr(root_rows.T, mode='economic', pivoting=True, check_finite=False)
    training = unpack_experiments(data, 'train')
    training += [rooted[position] for position in pivots[:len(root_basis)]]
    random.shuffle(training)
    pack_experiments(data, 'train', training)
    noisy = np.flatnonzero(model.noise >= 0).tolist()
    clean = sector_controls(model, sector)
    heldout = []
    for _ in range(128):
        length = int(random.integers(3, 15))
        sequence = [int(random.choice(noisy if random.random() < 0.65 else clean)) for _ in range(length)]
        heldout.append((sequence, random_observable(random, qubits, sector)))
    pack_experiments(data, 'holdout', heldout)
    query_scale = new_queries(data, model, training, sector, random)
    calibration, signs = model.experiments('train')
    holdout_rows, holdout_signs = model.experiments('holdout')
    queries = model.queries()
    structural_basis = model.structural_basis()
    calibration_basis = row_basis(calibration)
    if not np.all(membership(holdout_rows, calibration_basis)):
        raise AssertionError('Audit held-out expectation is not calibration-identifiable')
    lengths = np.diff(data['train_ptr'])
    anchors = lengths <= 1
    shots = random.choice([512, 2048, 8192, 32768], len(training), p=[0.15, 0.25, 0.35, 0.25])
    shots[anchors] = np.maximum(shots[anchors], 8192)
    if name == 'shots_short_anchors':
        shots = random.choice([128, 256, 512, 2048], len(training))
        shots[anchors] = random.choice([65536, 131072, 262144], np.sum(anchors))
    elif name == 'shots_long_anchors':
        shots = random.choice([32768, 65536, 131072], len(training))
        shots[anchors] = 2048
    elif name == 'shots_gate_imbalance':
        for position, (sequence, observable) in enumerate(training):
            counts = np.bincount([int(model.noise[gate]) for gate in sequence if model.noise[gate] >= 0], minlength=2)
            shots[position] = 128 if counts[0] > counts[1] else 65536
        shots[anchors] = 32768
    true_training = signs * np.exp(-calibration @ rates)
    data['train_shots'] = shots.astype(np.int64)
    data['train_plus'] = random.binomial(shots, (1 + true_training) / 2).astype(np.int64)
    oracle = {'structural_identifiable': membership(queries, structural_basis).astype(np.int8),
              'calibration_identifiable': membership(queries, calibration_basis).astype(np.int8),
              'query_log': queries @ rates, 'query_scale': query_scale,
              'holdout_mean': holdout_signs * np.exp(-holdout_rows @ rates)}
    details = {'qubits': qubits, 'parameters': model.parameter_count, 'train_count': len(training),
               'structural_rank': len(structural_basis), 'calibration_rank': len(calibration_basis),
               'structural_queries': int(oracle['structural_identifiable'].sum()),
               'supported_queries': int(oracle['calibration_identifiable'].sum()),
               'shots_min': int(shots.min()), 'shots_max': int(shots.max()),
               'changes': changes, **topology(data)}
    return data, oracle, rates, details, calibration, holdout_rows, queries, calibration_basis


class IndependentTransfer:
    def __init__(self, data):
        self.data = data
        self.qubits = int(data['n_qubits'])
        self.parameters = {}
        self.parameter_count = 0
        for channel, mask in zip(data['factor_channel'], data['factor_mask']):
            sites = np.flatnonzero(mask).tolist()
            support = sum(1 << site for site in sites)
            choices = [()] if channel < 0 else itertools.product((1, 2, 3), repeat=len(sites))
            for axes in choices:
                error_x = sum(1 << site for site, axis in zip(sites, axes) if axis in (1, 2))
                error_z = sum(1 << site for site, axis in zip(sites, axes) if axis in (2, 3))
                self.parameters.setdefault(int(channel), []).append((self.parameter_count, support, error_x, error_z))
                self.parameter_count += 1

    def bits(self, pauli):
        coordinates_x = sum(1 << site for site, axis in enumerate(pauli) if axis in (1, 2))
        coordinates_z = sum(1 << site for site, axis in enumerate(pauli) if axis in (2, 3))
        return coordinates_x, coordinates_z

    def feature(self, channel, coordinates_x, coordinates_z):
        row = np.zeros(self.parameter_count)
        for position, support, error_x, error_z in self.parameters[channel]:
            if channel < 0:
                row[position] = bool(support & (coordinates_x | coordinates_z))
            else:
                row[position] = 2 * (((error_x & coordinates_z).bit_count() +
                                      (error_z & coordinates_x).bit_count()) % 2)
        return row

    def experiment(self, sequence, observable):
        coordinates_x, coordinates_z = self.bits(observable)
        row = self.feature(-1, coordinates_x, coordinates_z)
        phase = 0
        for gate in reversed(sequence):
            begin, end = self.data['gate_ptr'][gate:gate + 2]
            for opcode, first, second in self.data['gate_ops'][begin:end][::-1]:
                first, second = int(first), int(second)
                first_x, first_z = (coordinates_x >> first) & 1, (coordinates_z >> first) & 1
                if opcode == 1:
                    phase ^= first_x & first_z
                    changed = (first_x ^ first_z) << first
                    coordinates_x ^= changed
                    coordinates_z ^= changed
                elif opcode == 2:
                    phase ^= first_x & (1 ^ first_z)
                    coordinates_z ^= first_x << first
                else:
                    second_x, second_z = (coordinates_x >> second) & 1, (coordinates_z >> second) & 1
                    if opcode == 3:
                        phase ^= first_x & second_z & (second_x ^ first_z ^ 1)
                        coordinates_x ^= first_x << second
                        coordinates_z ^= second_z << first
                    elif opcode == 4:
                        phase ^= first_x & second_x & (first_z ^ second_z)
                        coordinates_z ^= (first_x << second) | (second_x << first)
                    elif opcode == 5:
                        coordinates_x ^= ((first_x ^ second_x) << first) | ((first_x ^ second_x) << second)
                        coordinates_z ^= ((first_z ^ second_z) << first) | ((first_z ^ second_z) << second)
            channel = int(self.data['gate_noise'][gate])
            if channel >= 0:
                row += self.feature(channel, coordinates_x, coordinates_z)
        row += self.feature(-2, coordinates_x, coordinates_z)
        return row, 1 - 2 * phase


def independent_checks(data, oracle, rates, calibration, heldout, queries, basis, seed):
    random = np.random.default_rng(seed + 2917)
    independent = IndependentTransfer(data)
    source_model = Model(data)
    maximum_error = 0.0
    for prefix, expected in (('train', calibration), ('holdout', heldout)):
        experiments = unpack_experiments(data, prefix)
        selected = random.choice(len(experiments), min(32, len(experiments)), replace=False)
        for position in selected:
            row, sign = independent.experiment(*experiments[position])
            maximum_error = max(maximum_error, float(np.max(np.abs(row - expected[position]))))
            if sign != source_model.trace(*experiments[position])[1]:
                raise AssertionError('Independent signed propagation disagreement')
    for position, (begin, end) in enumerate(zip(data['query_ptr'][:-1], data['query_ptr'][1:])):
        row = np.zeros(len(rates))
        for term in range(begin, end):
            coordinates_x, coordinates_z = independent.bits(data['query_pauli'][term])
            row += data['query_coeff'][term] * independent.feature(
                int(data['query_channel'][term]), coordinates_x, coordinates_z)
        maximum_error = max(maximum_error, float(np.max(np.abs(row - queries[position]))))
    if maximum_error > 1e-11:
        raise AssertionError('Independent transfer/embedding disagreement')
    candidate = random.normal(size=len(rates))
    null_direction = candidate - basis.T @ (basis @ candidate)
    null_direction *= float(rates.min()) / (3 * max(np.max(np.abs(null_direction)), 1e-30))
    mask = oracle['calibration_identifiable'].astype(bool)
    invariant_error = max(float(np.max(np.abs(calibration @ null_direction))),
                          float(np.max(np.abs(heldout @ null_direction))),
                          float(np.max(np.abs(queries[mask] @ null_direction))))
    if invariant_error > 1e-10 or not np.all(rates + null_direction > 0):
        raise AssertionError('Gauge/calibration-equivalent physical consistency failed')
    contrast = np.exp(-calibration @ rates)
    information = data['train_shots'] * contrast ** 2 / np.maximum(1 - contrast ** 2, 1e-12)
    _, singular, right = svd(calibration * np.sqrt(information[:, None]), full_matrices=False, check_finite=False)
    retain = singular > max(calibration.shape) * singular[0] * 2e-12
    prediction_jacobian = oracle['holdout_mean'][:, None] * heldout
    prediction_std = np.sqrt(np.sum(((prediction_jacobian @ right[retain].T) / singular[retain]) ** 2, axis=1))
    query_std = np.sqrt(np.sum(((queries[mask] @ right[retain].T) / singular[retain]) ** 2, axis=1)) / oracle['query_scale'][mask]
    return {'independent_rows_checked': 64, 'all_query_rows_checked': len(queries),
            'maximum_row_error': maximum_error, 'physical_null_orbit_error': invariant_error,
            'fisher_rank': int(retain.sum()), 'prediction_std_median': float(np.median(prediction_std)),
            'prediction_std_p95': float(np.quantile(prediction_std, 0.95)),
            'normalized_query_std_p95': float(np.quantile(query_std, 0.95)),
            'informative_holdouts': int(np.sum(np.abs(oracle['holdout_mean']) >= 0.1)),
            'median_absolute_holdout_mean': float(np.median(np.abs(oracle['holdout_mean'])))}


def run_one(name, family, qubits, seed):
    started = time.monotonic()
    data, oracle, rates, details, calibration, heldout, queries, basis = create_case(name, qubits, seed)
    consistency = independent_checks(data, oracle, rates, calibration, heldout, queries, basis, seed)
    case_directory = AUDIT / 'cases' / name
    save_npz(case_directory / 'input.npz', data)
    weak = weak_solve(data)
    weak_loss = losses(weak, oracle)
    reference_telemetry, frozen_telemetry = {}, {}
    reference, reference_runtime = run_case(REFERENCE / 'solver.py', case_directory / 'input.npz',
                                             len(queries), len(heldout), reference_telemetry)
    reference_loss = losses(reference, oracle)
    reference_components, reference_score = score_components(reference_loss, weak_loss, reference_loss)
    informative = np.abs(oracle['holdout_mean']) >= 0.1
    informative_weak_loss = float(np.mean((weak['holdout_mean'][informative] - oracle['holdout_mean'][informative]) ** 2))
    informative_reference_loss = float(np.mean((reference['holdout_mean'][informative] - oracle['holdout_mean'][informative]) ** 2))
    exact_identification = all(np.array_equal(reference[key], oracle[key])
                               for key in ('structural_identifiable', 'calibration_identifiable'))
    qualification = {
        'reference_score_over_0_9': reference_score > 0.9,
        'reference_identification_exact': exact_identification,
        'query_loss_improvement_at_least_10x': reference_loss['invariant_estimation'] <= weak_loss['invariant_estimation'] / 10,
        'prediction_loss_improvement_at_least_10x': reference_loss['heldout_prediction'] <= weak_loss['heldout_prediction'] / 10,
        'informative_prediction_improvement_at_least_10x': informative_reference_loss <= informative_weak_loss / 10,
        'absolute_prediction_rmse_below_0_02': reference_loss['heldout_prediction'] < 0.02 ** 2,
        'absolute_normalized_query_rmse_below_0_003': reference_loss['invariant_estimation'] < 0.003 ** 2,
        'at_least_24_supported_queries': details['supported_queries'] >= 24,
        'at_least_32_informative_holdouts': consistency['informative_holdouts'] >= 32,
        'prediction_fisher_std_p95_below_0_025': consistency['prediction_std_p95'] < 0.025,
        'query_fisher_std_p95_below_0_005': consistency['normalized_query_std_p95'] < 0.005,
        'fisher_rank_matches_calibration': consistency['fisher_rank'] == details['calibration_rank'],
        'independent_maps_exact': consistency['maximum_row_error'] == 0,
    }
    qualified = all(qualification.values())
    oracle['baseline_loss'] = np.array([weak_loss[key] for key in WEIGHTS])
    oracle['reference_loss'] = np.array([reference_loss[key] for key in WEIGHTS])
    save_npz(case_directory / 'oracle.npz', oracle)
    save_npz(case_directory / 'reference_output.npz', reference)
    frozen, frozen_runtime = run_case(FROZEN, case_directory / 'input.npz', len(queries), len(heldout), frozen_telemetry)
    save_npz(case_directory / 'frozen_output.npz', frozen)
    frozen_loss = losses(frozen, oracle)
    frozen_components, frozen_score = score_components(frozen_loss, weak_loss, reference_loss)
    differences = {key: int(np.count_nonzero(frozen[key] != oracle[key]))
                   for key in ('structural_identifiable', 'calibration_identifiable')}
    statistics = dict(case_id=name, family=family, seed=seed, domain='original_20_24',
                      **details, consistency=consistency, qualification=qualification, qualified=qualified,
                      baseline_losses=weak_loss, reference_losses=reference_loss, frozen_losses=frozen_loss,
                      reference_score=reference_score, frozen_score=frozen_score,
                      reference_components=reference_components, frozen_components=frozen_components,
                      identification_mismatches=differences, reference_runtime=reference_runtime,
                      frozen_runtime=frozen_runtime, reference_memory=reference_telemetry,
                      frozen_memory=frozen_telemetry, informative_reference_loss=informative_reference_loss,
                      informative_baseline_loss=informative_weak_loss,
                      same_scales={key: weak_loss[key] / 4 + 12 * reference_loss[key] for key in WEIGHTS},
                      input_sha256=file_hash(case_directory / 'input.npz'),
                      elapsed_seconds=time.monotonic() - started)
    (case_directory / 'result.json').write_text(json.dumps(statistics, indent=2, allow_nan=False) + '\n')
    return statistics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=[case[0] for case in CASES])
    parser.add_argument('--resume', action='store_true')
    arguments = parser.parse_args()
    staging = AUDIT / 'staging'
    staging.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(staging)
    os.environ['TMPDIR'] = str(staging)
    snapshot_path = AUDIT / 'preservation_before.json'
    current = protected_hashes()
    if snapshot_path.exists():
        if json.loads(snapshot_path.read_text()) != current:
            raise AssertionError('Protected artifacts changed before audit execution')
    else:
        snapshot_path.write_text(json.dumps(current, indent=2) + '\n')
    cases = [case for case in CASES if arguments.case is None or case[0] == arguments.case]
    records = []
    for case in cases:
        result_path = AUDIT / 'cases' / case[0] / 'result.json'
        if arguments.resume and result_path.exists():
            result = json.loads(result_path.read_text())
        else:
            print('START', case, flush=True)
            result = run_one(*case)
        records.append(result)
        print(json.dumps({key: result[key] for key in ('case_id', 'qualified', 'reference_score',
                                                       'frozen_score', 'identification_mismatches',
                                                       'reference_runtime', 'frozen_runtime')}), flush=True)
        (AUDIT / 'results.json').write_text(json.dumps({'cases': records}, indent=2, allow_nan=False) + '\n')
        if protected_hashes() != current:
            raise AssertionError('Protected artifacts changed during audit')
    (AUDIT / 'preservation_after.json').write_text(json.dumps(protected_hashes(), indent=2) + '\n')


if __name__ == '__main__':
    main()
