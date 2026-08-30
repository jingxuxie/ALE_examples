import argparse
import importlib.util
import json
import os
import stat
from pathlib import Path
import time

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import numpy as np


ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('frozen_physics', ROOT / 'hidden' / 'model.py')
physics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(physics)
CONTRACT = json.loads((ROOT / 'hidden' / 'contract.json').read_text())


def score_metrics(metrics, robust=False):
    chern = int(round(metrics['chern']))
    interval = CONTRACT['robust_signed_plateau_mean_interval' if robust else 'signed_plateau_mean_interval']
    signed_mean = chern * metrics['plateau_mean']
    checks = {
        'topological_band': abs(chern) == 1 and abs(metrics['chern'] - chern) < 1e-8,
        'full_response': abs(metrics['full'] - chern) <= CONTRACT['robust_chern_tolerance' if robust else 'full_to_chern_tolerance'],
        'gap': metrics['gap_lower_bound'] >= CONTRACT['robust_gap_minimum' if robust else 'certified_gap_minimum'],
        'norm': metrics['norm_upper_bound'] <= CONTRACT['hamiltonian_norm_maximum'],
        'resolved_flux': metrics['max_flux'] <= CONTRACT['max_plaquette_flux'],
        'resolved_overlap': metrics['min_overlap'] >= CONTRACT['minimum_neighbor_overlap'],
        'plateau': metrics['plateau_spread'] <= CONTRACT['robust_plateau_spread_maximum' if robust else 'nominal_plateau_spread_maximum'],
        'nonzero_plateau': interval[0] <= signed_mean <= interval[1],
        'omitted_response': metrics['omitted_response'] >= CONTRACT['omitted_response_minimum'],
        'hybridization': metrics['retained_optical_min'] >= CONTRACT['robust_optical_minimum' if robust else 'retained_optical_minimum']
    }
    return checks


def evaluate(path):
    started = time.monotonic()
    if path.is_dir():
        path = path / 'witness.json'
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as handle:
        information = os.fstat(handle.fileno())
        if not stat.S_ISREG(information.st_mode) or information.st_nlink != 1 or information.st_size > 100000:
            raise ValueError('witness must be a bounded regular file without hardlinks')
        payload = json.loads(handle.read(100001))
    raw = payload['parameters']
    if not isinstance(raw, list) or len(raw) != 25 or any(type(value) not in (int, float) for value in raw):
        raise ValueError('parameters must be a list of 25 real numbers')
    parameters = np.array(raw, float)
    if not np.isfinite(parameters).all() or np.any(parameters < physics.LOWER) or np.any(parameters > physics.UPPER):
        raise ValueError('nonfinite or out-of-bounds coefficients')
    nominal = [physics.diagnose(parameters, size, tuple(offset))
               for size, offset in zip(CONTRACT['nominal_meshes'], CONTRACT['mesh_offsets'])]
    fine = nominal[-1]
    checks = score_metrics(fine)
    mesh_error = max(abs(nominal[-2]['full'] - fine['full']),
                     float(np.max(np.abs(np.array(nominal[-2]['windows']) - fine['windows']))))
    checks['quadrature'] = mesh_error <= CONTRACT['fine_mesh_response_tolerance']
    checks['coarse_topology'] = all(abs(item['chern'] - fine['chern']) < 1e-8 for item in nominal)
    perturbations = []
    for coordinate in range(21):
        for sign in (-1, 1):
            values = parameters.copy()
            values[coordinate] += sign * CONTRACT.get('perturbation_radius', .002)
            metrics = physics.diagnose(values, CONTRACT['robust_mesh'], (.193, .371))
            conditions = score_metrics(metrics, robust=True)
            conditions['same_topology'] = abs(metrics['chern'] - fine['chern']) < 1e-8
            perturbations.append({'coordinate': coordinate, 'sign': sign,
                                  'metrics': metrics, 'checks': conditions})
    family_scores = {
        'nominal': sum(checks.values()) / len(checks),
        'offset_robustness': np.mean([all(item['checks'].values()) for item in perturbations[:18]]).item(),
        'dispersion_robustness': np.mean([all(item['checks'].values()) for item in perturbations[18:26]]).item(),
        'coupling_robustness': np.mean([all(item['checks'].values()) for item in perturbations[26:]]).item()
    }
    correlated = []
    if CONTRACT.get('correlated_probe_count', 0):
        displacements = np.load(ROOT / 'hidden' / 'correlated_displacements.npy', allow_pickle=False)
        expected_shape = (CONTRACT['correlated_probe_count'], 25)
        if displacements.shape != expected_shape or not np.isfinite(displacements).all():
            raise RuntimeError('invalid private perturbation set')
        if np.max(np.abs(displacements)) > CONTRACT['perturbation_radius'] or np.any(displacements[:, 21:] != 0):
            raise RuntimeError('private perturbation outside public domain')
        for index, displacement in enumerate(displacements):
            metrics = physics.diagnose(parameters + displacement, CONTRACT['robust_mesh'], (.193, .371))
            conditions = score_metrics(metrics, robust=True)
            conditions['same_topology'] = abs(metrics['chern'] - fine['chern']) < 1e-8
            correlated.append({'probe': index, 'metrics': metrics, 'checks': conditions})
        family_scores['simultaneous_robustness'] = float(np.mean([all(item['checks'].values()) for item in correlated]))
    corners = []
    if CONTRACT.get('corner_probe_count', 0):
        displacements = np.load(ROOT / 'hidden' / 'corner_displacements.npy', allow_pickle=False)
        labels = json.loads((ROOT / 'hidden' / 'corner_families.json').read_text())
        expected_shape = (CONTRACT['corner_probe_count'], 25)
        if displacements.shape != expected_shape or not np.isfinite(displacements).all() or len(labels) != len(displacements):
            raise RuntimeError('invalid private corner set')
        radius = CONTRACT['perturbation_radius']
        if np.any(~np.isin(displacements, [-radius, 0., radius])) or np.any(displacements[:, 21:] != 0):
            raise RuntimeError('private corner outside public domain')
        for index, (displacement, family) in enumerate(zip(displacements, labels)):
            metrics = physics.diagnose(parameters + displacement, CONTRACT['robust_mesh'], (.193, .371))
            conditions = score_metrics(metrics, robust=True)
            conditions['same_topology'] = abs(metrics['chern'] - fine['chern']) < 1e-8
            corners.append({'probe': index, 'family': family, 'metrics': metrics, 'checks': conditions})
        for family, definition in CONTRACT['corner_families'].items():
            records = [item for item in corners if item['family'] == family]
            if len(records) != definition['count']:
                raise RuntimeError('private corner family count mismatch')
            family_scores['corner_' + family] = float(np.mean([all(item['checks'].values()) for item in records]))
    passed = (all(checks.values()) and all(all(item['checks'].values()) for item in perturbations)
              and all(all(item['checks'].values()) for item in correlated)
              and all(all(item['checks'].values()) for item in corners))
    failures = [name for name, value in checks.items() if not value]
    if any(not all(item['checks'].values()) for item in perturbations):
        failures.append('perturbation_audit')
    if any(not all(item['checks'].values()) for item in correlated):
        failures.append('simultaneous_perturbation_audit')
    if any(not all(item['checks'].values()) for item in corners):
        failures.append('corner_perturbation_audit')
    elapsed = time.monotonic() - started
    if elapsed > CONTRACT['checker_timeout_seconds']:
        passed = False
        failures.append('checker_resource_limit')
    return {
        'core_score': 100 * float(np.mean(list(family_scores.values()))),
        'worst_family_score': 100 * min(family_scores.values()),
        'runtime_seconds': elapsed, 'resource_score': min(1., CONTRACT['checker_timeout_seconds'] / max(elapsed, 1e-6)),
        'passed': bool(passed), 'valid': bool(passed),
        'reason': 'valid false-convergence witness' if passed else 'failed: ' + ', '.join(failures),
        'family_scores': family_scores, 'checks': checks, 'nominal': nominal,
        'mesh_error': mesh_error, 'perturbations': perturbations, 'correlated_perturbations': correlated,
        'corner_perturbations': corners
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', required=True)
    parser.add_argument('--output')
    options = parser.parse_args()
    try:
        result = evaluate(Path(options.submission))
    except Exception as error:
        result = {'core_score': 0., 'worst_family_score': 0., 'runtime_seconds': 0.,
                  'resource_score': 0., 'passed': False, 'valid': False,
                  'reason': type(error).__name__ + ': ' + str(error)}
    serialized = json.dumps(result, indent=2, allow_nan=False)
    if options.output:
        Path(options.output).write_text(serialized)
    print(serialized)


if __name__ == '__main__':
    main()
