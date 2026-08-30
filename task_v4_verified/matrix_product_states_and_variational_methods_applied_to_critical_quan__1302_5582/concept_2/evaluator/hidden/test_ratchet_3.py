import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import hashlib
import itertools
import json
import math
import shutil
import subprocess
import time
import types

import numpy as np
import scipy.linalg as sla
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import eigsh

import trusted_physics as physics

CONCEPT = Path(__file__).resolve().parents[2]
AUDIT = CONCEPT / 'adversary' / 'ratchet_3'
ARCHIVE = CONCEPT / 'generations' / 'generation_2'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def load_source(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_text(), str(path), 'exec'), module.__dict__)
    return module


def close(actual, expected, tolerance, name):
    difference = float(np.max(np.abs(np.asarray(actual) - np.asarray(expected))))
    assert difference <= tolerance, (name, difference, tolerance)
    return difference


def determinant(sites, size=None):
    rows = np.concatenate([np.arange(left + 1, right + 1) for left, right in zip(sites[::2], sites[1::2])])
    differences = rows[:, None] - (rows - 1)[None, :] - .5
    matrix = 1 / (np.pi * differences) if size is None else 1 / (size * np.sin(np.pi * differences / size))
    sign, logarithm = np.linalg.slogdet(matrix)
    return float(sign * np.exp(logarithm))


def literal_cumulant(sites, moment):
    intervals = tuple(zip(sites[::2], sites[1::2]))
    means = [moment(interval) for interval in intervals]
    lower = [moment(intervals[first] + intervals[second]) for first, second in ((0, 1), (0, 2), (1, 2))]
    raw = moment(tuple(sites))
    value = math.fsum((raw, -lower[0] * means[2], -lower[1] * means[1], -lower[2] * means[0], 2 * math.prod(means)))
    return raw, means, lower, value


class SpectralReference:
    def __init__(self, tensor):
        dimension = tensor.shape[1]
        transfer = sum(np.kron(matrix, matrix.conj()) for matrix in tensor)
        spectrum, left_vectors, right_vectors = sla.eig(transfer, left=True, right=True)
        index = int(np.argmax(np.abs(spectrum)))
        eigenvalue = float(spectrum[index].real)
        left = left_vectors[:, index].reshape(dimension, dimension)
        right = right_vectors[:, index].reshape(dimension, dimension)
        left /= np.trace(left)
        right /= np.trace(right)
        left = (left + left.conj().T) / 2
        right = (right + right.conj().T) / 2
        right /= np.trace(left @ right)
        self.left = left.reshape(-1)
        self.right = right.reshape(-1)
        transfer /= eigenvalue
        self.insertion = (np.kron(tensor[0], tensor[1].conj()) + np.kron(tensor[1], tensor[0].conj())) / eigenvalue
        self.powers = [transfer]
        for unused_bit in range(8):
            self.powers.append(self.powers[-1] @ self.powers[-1])
        self.cache = {}

    def moment(self, sites):
        sites = tuple(site - sites[0] for site in sites)
        if sites not in self.cache:
            vector = self.right.copy()
            previous = None
            for site in reversed(sites):
                if previous is not None:
                    exponent = previous - site - 1
                    for bit, power in enumerate(self.powers):
                        if exponent & (1 << bit):
                            vector = power @ vector
                vector = self.insertion @ vector
                previous = site
            value = np.vdot(self.left, vector)
            assert abs(value.imag) < 1e-10
            self.cache[sites] = float(value.real)
        return self.cache[sites]


def exact_and_ed_certificates():
    records = []
    for sites in physics.THREE_INTERVAL_SEXTUPLES:
        raw, means, lower, expected = literal_cumulant(sites, determinant)
        actual = physics.exact_three_interval_cumulant(sites)
        difference = close(actual, expected, 4e-14, '252 exact determinants')
        records.append({'sites': sites, 'stable_target': actual, 'dense_cauchy_cumulant': expected, 'absolute_difference': difference})
    assert min(record['stable_target'] for record in records) >= 1e-6
    write_json(AUDIT / 'exact_252_certificates.json', records)
    finite = []
    for size in (6, 8, 10, 12):
        labels = np.arange(2**size, dtype=np.int64)
        magnetization = sum(1 - 2 * ((labels >> site) & 1) for site in range(size))
        rows, columns, values = [labels], [labels], [-magnetization.astype(float)]
        for site in range(size):
            rows.append(labels)
            columns.append(labels ^ ((1 << site) | (1 << ((site + 1) % size))))
            values.append(-np.ones(len(labels)))
        hamiltonian = coo_matrix((np.concatenate(values), (np.concatenate(rows), np.concatenate(columns))), shape=(len(labels), len(labels))).tocsr()
        energies, vectors = eigsh(hamiltonian, k=1, which='SA', tol=2e-14, v0=np.ones(len(labels)), maxiter=10000)
        ground = vectors[:, 0]
        residual = float(np.linalg.norm(hamiltonian @ ground - energies[0] * ground))
        parity = np.prod([1 - 2 * ((labels >> site) & 1) for site in range(size)], axis=0)
        parity_mean = float(np.dot(ground**2, parity))
        moment_cache = {}

        def moment(sites):
            mask = sum(1 << site for site in sites)
            if mask not in moment_cache:
                moment_cache[mask] = float(np.dot(ground, ground[labels ^ mask]))
            return moment_cache[mask]

        maximum_raw = maximum_connected = 0.0
        count = 0
        for sites in itertools.combinations(range(size), 6):
            observed = literal_cumulant(sites, moment)
            expected = literal_cumulant(sites, lambda positions: determinant(positions, size))
            maximum_raw = max(maximum_raw, close(observed[0], expected[0], 2e-11, 'finite spin raw six'))
            maximum_connected = max(maximum_connected, close(observed[3], expected[3], 2e-11, 'finite spin K3'))
            count += 1
        assert residual < 2e-10 and abs(parity_mean - 1) < 1e-10
        finite.append({'size': size, 'sextuples': count, 'energy': float(energies[0]), 'eigen_residual': residual,
                       'parity': parity_mean, 'maximum_raw_difference': maximum_raw, 'maximum_cumulant_difference': maximum_connected})
    write_json(AUDIT / 'ed_certificates.json', finite)
    return {'exact_targets': len(records), 'maximum_exact_absolute_difference': max(record['absolute_difference'] for record in records),
            'minimum_exact_target': min(record['stable_target'] for record in records), 'finite_ed_sextuples': sum(record['sextuples'] for record in finite)}


def contraction_certificates(tensor, baseline):
    reference = SpectralReference(tensor)
    records = []
    for index, sites in enumerate(physics.THREE_INTERVAL_SEXTUPLES):
        raw, means, lower, cumulant = literal_cumulant(sites, reference.moment)
        differences = {key: close(actual, expected, 3e-11, key) for key, actual, expected in (
            ('raw', baseline['three_interval_six_spin_correlations'][index], raw),
            ('means', baseline['three_interval_means'][index], means),
            ('lower', baseline['three_interval_four_spin_correlations'][index], lower),
            ('cumulant', baseline['three_interval_cumulants'][index], cumulant))}
        records.append({'sites': sites, 'absolute_differences': differences})
    write_json(AUDIT / 'independent_252_contractions.json', records)
    generator = np.random.default_rng(82826)
    raw = generator.normal(size=(8, 4)) + 1j * generator.normal(size=(8, 4))
    orthogonal, unused_triangular = np.linalg.qr(raw)
    rows = orthogonal.conj().T
    complex_tensor = np.stack((rows[:, :4], rows[:, 4:]))
    density = physics.stationary(complex_tensor)[0]
    sites = ((0, 1, 3, 4, 6, 8), (0, 2, 4, 8, 9, 13), (0, 16, 48, 64, 96, 112))
    observed = physics.three_interval_observables(complex_tensor, density, sites)[3]
    complex_reference = SpectralReference(complex_tensor)
    expected = [literal_cumulant(positions, complex_reference.moment)[3] for positions in sites]
    complex_difference = close(observed, expected, 2e-12, 'general complex full-tensor contraction')
    return {'sextuples': len(records), 'maximum_absolute_difference': max(max(record['absolute_differences'].values()) for record in records),
            'general_complex_difference': complex_difference, 'general_complex_sites': sites}


def normalized_gauge_certificates(tensor, baseline):
    dimension = tensor.shape[1]
    half = dimension // 2
    density = physics.stationary(tensor)[0]
    generator = np.random.default_rng(631)
    unitary = np.zeros((dimension, dimension), dtype=complex)
    for offset in (0, half):
        raw = generator.normal(size=(half, half)) + 1j * generator.normal(size=(half, half))
        orthogonal, unused_triangular = np.linalg.qr(raw)
        unitary[offset:offset + half, offset:offset + half] = orthogonal
    complex_tensor = unitary @ tensor @ unitary.conj().T
    complex_metrics = physics.metrics(complex_tensor)
    complex_error = close(complex_metrics['three_interval_cumulants'], baseline['three_interval_cumulants'], 2e-11, 'complex gauge K3')
    rescaled = tensor * (1 + 5e-10)
    rescaled_metrics = physics.metrics(rescaled)
    scale_error = close(rescaled_metrics['three_interval_cumulants'], baseline['three_interval_cumulants'], 2e-11, 'uniform rescaling K3')
    rows, columns = np.indices((dimension, dimension))
    indices = np.flatnonzero(((rows < half) == (columns < half)).reshape(-1))
    even_transfer = physics.transfer_matrix(tensor)[np.ix_(indices, indices)]
    spectrum, vectors = sla.eig(even_transfer)
    candidates = [index for index in range(len(spectrum)) if abs(spectrum[index] - 1) > 1e-7 and abs(spectrum[index].imag) < 1e-8]
    selected = max(candidates, key=lambda index: spectrum[index].real)
    hermitian = np.zeros(dimension**2, dtype=complex)
    hermitian[indices] = vectors[:, selected]
    hermitian = hermitian.reshape(dimension, dimension)
    hermitian = (hermitian + hermitian.conj().T) / 2
    hermitian -= np.trace(density @ hermitian) * np.eye(dimension)
    hermitian /= np.linalg.norm(hermitian)
    amplitude = 1e-3
    for unused_trial in range(30):
        gauge = sla.expm(amplitude * hermitian)
        gauged = gauge @ tensor @ sla.inv(gauge)
        defect = float(np.linalg.norm(physics.apply_transfer(gauged, np.eye(dimension)) - np.eye(dimension)))
        if defect <= 1.5e-8:
            break
        amplitude /= 2
    assert 1e-10 < defect <= 2e-8
    gauged_metrics = physics.metrics(gauged)
    gauge_error = close(gauged_metrics['three_interval_cumulants'], baseline['three_interval_cumulants'], 2e-11, 'near-canonical nonunitary gauge K3')
    left = physics.stationary(gauged)[0]
    normalized, left, right, eigenvalue, residual = physics.observable_boundaries(gauged, left)
    chosen = ((0, 16, 112, 128, 224, 240),)
    physical = physics.three_interval_observables(normalized, left, chosen, right_boundary=right)[3][0]
    naive = physics.three_interval_observables(normalized, left, chosen, right_boundary=np.eye(dimension))[3][0]
    eigenvalues, eigenvectors = sla.eigh(right)
    assert min(eigenvalues) > 0
    root = (eigenvectors * np.sqrt(eigenvalues)) @ eigenvectors.conj().T
    inverse = (eigenvectors * (1 / np.sqrt(eigenvalues))) @ eigenvectors.conj().T
    recanonicalized = inverse @ normalized @ root
    recanonicalized_metrics = physics.metrics(recanonicalized)
    assert recanonicalized_metrics['canonical_defect'] < 2e-12
    recanonicalized_error = close(recanonicalized_metrics['three_interval_cumulants'], baseline['three_interval_cumulants'], 2e-11, 'exact recanonicalization K3')
    families = ('energy_excess', 'order_correlations', 'density_connected_correlations', 'y_correlations', 'composite_order_covariances')
    regressions = {name: {key: close(values[key], baseline[key], 3e-10, name + ':' + key) for key in families}
                   for name, values in (('scale', rescaled_metrics), ('nonunitary', gauged_metrics), ('complex', complex_metrics), ('recanonicalized', recanonicalized_metrics))}
    result = {'complex_gauge_K3_max_absolute_difference': complex_error, 'uniform_scale_K3_max_absolute_difference': scale_error,
              'uniform_scale_canonical_defect': rescaled_metrics['canonical_defect'], 'uniform_scale_eigenvalue_error': rescaled_metrics['fixed_point_eigenvalue_error'],
              'nonunitary_gauge_amplitude': amplitude, 'nonunitary_canonical_defect': defect, 'nonunitary_K3_max_absolute_difference': gauge_error,
              'nonunitary_right_identity_defect': float(np.linalg.norm(right - np.eye(dimension))), 'right_fixed_point_residual': residual,
              'physical_selected_K3': float(physical), 'eigenvalue_only_identity_boundary_K3': float(naive), 'identity_boundary_bias': float(abs(physical - naive)),
              'recanonicalized_canonical_defect': recanonicalized_metrics['canonical_defect'], 'recanonicalized_K3_max_absolute_difference': recanonicalized_error,
              'all_v3_families_invariance': regressions}
    write_json(AUDIT / 'normalization_gauge_certificates.json', result)
    return result


def legacy_and_artifact_tests(tensor):
    legacy = load_source(CONCEPT / 'evaluator' / 'hidden' / 'test_validation.py', 'legacy_validation')
    os.environ['MPS_VALIDATION_DIR'] = str(AUDIT)
    legacy.main()
    ratchet = load_source(CONCEPT / 'evaluator' / 'hidden' / 'test_ratchet_2.py', 'legacy_ratchet')
    ratchet.AUDIT = AUDIT
    rejection = ratchet.malformed_cases(tensor)
    fixture = AUDIT / 'legacy_v3_fixture'
    for name in ('participant', 'evaluator'):
        shutil.copytree(ARCHIVE / name, fixture / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    champion = fixture / 'champions' / 'generation_2' / 'state.npz'
    champion.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fixture / 'participant' / 'baseline' / 'state.npz', champion)
    reference_folder = fixture / 'adversary' / 'fourpoint_search'
    reference_folder.mkdir(parents=True, exist_ok=True)
    for filename in ('fourpoint.py', 'champion_v2_recheck.json'):
        shutil.copyfile(CONCEPT / 'adversary' / 'fourpoint_search' / filename, reference_folder / filename)
    old = load_source(ARCHIVE / 'evaluator' / 'hidden' / 'trusted_physics.py', 'archived_v3_physics')
    ratchet.physics = old
    ratchet.CONCEPT = fixture
    ratchet.AUDIT = AUDIT / 'legacy_v3_reports'
    ratchet.main()
    return {'legacy_v2_passed': json.loads((AUDIT / 'legacy_validation.json').read_text())['passed'],
            'all_preserved_v3_tests_passed': json.loads((ratchet.AUDIT / 'validation.json').read_text())['passed'],
            'v4_artifact_rejection': rejection}


def main():
    started = time.monotonic()
    AUDIT.mkdir(parents=True, exist_ok=True)
    os.environ['TMPDIR'] = str(AUDIT / 'tmp')
    (AUDIT / 'tmp').mkdir(exist_ok=True)
    contract = json.loads((CONCEPT / 'participant' / 'input' / 'contract.json').read_text())
    old_contract = json.loads((ARCHIVE / 'participant' / 'input' / 'contract.json').read_text())
    for key in old_contract:
        if key not in ('version', 'score', 'notes'):
            assert old_contract[key] == contract[key], key
    assert contract['version'] == physics.CONTRACT_VERSION == 'critical-vacuum-v4'
    assert contract['three_interval_channel']['maximum_relative_error'] == .1
    listed = json.loads((CONCEPT / 'participant' / 'input' / 'three_interval_sextuples.json').read_text())['sextuples']
    assert listed == [list(sites) for sites in physics.THREE_INTERVAL_SEXTUPLES]
    assert len(listed) == len({tuple(sites) for sites in listed}) == 252
    assert (CONCEPT / 'participant' / 'workspace' / 'physics.py').read_bytes() == (CONCEPT / 'evaluator' / 'hidden' / 'trusted_physics.py').read_bytes()
    assert {path.name for path in (CONCEPT / 'participant' / 'baseline').iterdir()} == {'README.md', 'state.npz'}
    state = CONCEPT / 'participant' / 'baseline' / 'state.npz'
    assert state.read_bytes() == (CONCEPT / 'champions' / 'generation_3' / 'state.npz').read_bytes()
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    official_run = subprocess.run([sys.executable, str(CONCEPT / 'evaluator' / 'evaluate.py'), '--submission', str(state.parent), '--output', str(AUDIT / 'baseline_score.json')], capture_output=True, text=True, env=environment, timeout=120, check=True)
    official = json.loads(official_run.stdout)
    assert official['valid'] and not official['passed'] and official['runtime_seconds'] < 120
    assert all(value == 1 for name, value in official['family_scores'].items() if name != 'three_interval')
    public_run = subprocess.run([sys.executable, str(CONCEPT / 'participant' / 'workspace' / 'check.py'), str(state)], capture_output=True, text=True, env=environment, timeout=120, check=True)
    public = json.loads(public_run.stdout)
    write_json(AUDIT / 'baseline_public_score.json', public)
    assert official['metrics'] == public['metrics']
    tensor = physics.load_tensor(state)
    values = official['metrics']
    report = {'contract_version': physics.CONTRACT_VERSION, 'all_v3_contract_criteria_preserved': True}
    for name, function in (('exact_and_ed', exact_and_ed_certificates), ('independent_contractions', lambda: contraction_certificates(tensor, values)),
                           ('normalization_and_gauges', lambda: normalized_gauge_certificates(tensor, values)), ('legacy_and_artifacts', lambda: legacy_and_artifact_tests(tensor))):
        report[name] = function()
        print(json.dumps({'completed': name, 'elapsed_seconds': time.monotonic() - started}), flush=True)
    old = load_source(ARCHIVE / 'evaluator' / 'hidden' / 'trusted_physics.py', 'archived_v3_regression')
    previous = old.metrics(tensor)
    report['v3_metric_regression'] = {key: close(values[key], previous[key], 3e-11, 'v3 regression ' + key)
        for key in ('energy_excess', 'order_correlations', 'density_connected_correlations', 'y_correlations', 'composite_order_covariances')}
    boundaries = dict(zip(('energy_excess', 'order_max_relative_error', 'density_max_relative_error', 'y_max_relative_error', 'composite_order_max_relative_error', 'three_interval_max_relative_error'), (5e-5, .025, .1, .1, .01, .1)))
    assert physics.score_metrics(boundaries)['passed']
    for key, limit in boundaries.items():
        outside = dict(boundaries)
        outside[key] = float(np.nextafter(limit, np.inf))
        assert not physics.score_metrics(outside)['passed'], key
    expected_files = {'TASK.md', 'baseline/README.md', 'baseline/state.npz', 'workspace/check.py', 'workspace/physics.py', 'input/contract.json', 'input/observables.md', 'input/fourpoint_quartets.json', 'input/three_interval_cumulant.md', 'input/three_interval_sextuples.json'}
    public_files = {str(path.relative_to(CONCEPT / 'participant')) for path in (CONCEPT / 'participant').rglob('*') if path.is_file()}
    assert public_files == expected_files, public_files ^ expected_files
    for folder in (CONCEPT / 'participant', CONCEPT / 'evaluator'):
        assert not list(folder.rglob('*.pyc')) and not list(folder.rglob('__pycache__'))
        assert not any(path.is_symlink() for path in folder.rglob('*'))
    report.update({'passed': True, 'baseline_valid': True, 'baseline_passed': False, 'baseline_core_score': official['core_score'],
                   'baseline_worst_family_score': official['worst_family_score'], 'baseline_three_interval_max_relative_error': values['three_interval_max_relative_error'],
                   'baseline_checker_seconds': official['runtime_seconds'], 'public_checker_seconds': public['runtime_seconds'],
                   'baseline_sha256': hashlib.sha256(state.read_bytes()).hexdigest(), 'public_trusted_source_sha256': hashlib.sha256((CONCEPT / 'participant' / 'workspace' / 'physics.py').read_bytes()).hexdigest(),
                   'public_regular_file_count': len(public_files), 'bytecode_and_symlink_free': True, 'score_boundary_tests': 7,
                   'passing_v4_tensor_known': False, 'fresh_agents_launched': False, 'total_validation_seconds': time.monotonic() - started})
    write_json(AUDIT / 'validation.json', report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
