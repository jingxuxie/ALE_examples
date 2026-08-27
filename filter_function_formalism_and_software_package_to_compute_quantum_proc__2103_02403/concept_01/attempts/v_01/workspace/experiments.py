import copy
import csv
import json
import resource
import time
from pathlib import Path

import numpy as np
from scipy.linalg import expm

from pipeline.physics import (basis_transform, ideal_channel, load_case, make_pulse,
                              observables, spectral_density)
from pipeline.predictor import predict


ROOT = Path(__file__).resolve().parent.parent
ROWS = []


def reference(case_id):
    path = ROOT / 'artifacts' / f'{case_id}_refined' / 'process.npz'
    if not path.exists():
        path = ROOT / 'artifacts' / f'{case_id}_selected' / 'process.npz'
    return dict(np.load(path)), str(path.parent.relative_to(ROOT))


def save(row_id, case, arrays, channel, quadratic, elapsed, method, target=None,
         reference_artifact='', **extra):
    destination = ROOT / 'experiments' / row_id
    destination.mkdir(parents=True, exist_ok=True)
    np.savez(destination / 'process.npz', channel=channel, k2=quadratic)
    metrics = observables(channel, arrays)
    ideal = ideal_channel(arrays)
    metrics.update(case_id=case['case_id'], mode=method, seconds=elapsed,
                   peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                   k2_norm=float(np.linalg.norm(quadratic)), diagnostics=dict(method=method))
    (destination / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    error = ideal.conj().T @ channel
    row = dict(row_id=row_id, case_id=case['case_id'], variant=method,
               artifact=str(destination.relative_to(ROOT)), reference_artifact=reference_artifact,
               **{key: value for key, value in metrics.items() if key not in ('case_id', 'mode', 'diagnostics')},
               coherent_probe=float((error[1, 0] - error[0, 1].conj()).imag / 2), **extra)
    if target is not None:
        row.update(relative_channel_error=float(np.linalg.norm(channel - target['channel'])
                   / max(np.linalg.norm(target['channel'] - ideal), 1e-8)),
                   relative_k2_error=float(np.linalg.norm(quadratic - target['k2'])
                   / max(np.linalg.norm(target['k2']), 1e-8)))
    ROWS.append(row)
    print(json.dumps(row), flush=True)


def closure_experiments():
    for case_id in ['driven_static', 'memory_ou', 'switching_echo',
                    'leakage_static', 'broadband_entangler']:
        case, arrays = load_case(ROOT / 'input' / 'cases' / f'{case_id}.json')
        target, target_path = reference(case_id)
        ideal = ideal_channel(arrays)
        for variant in ['corrected_cumulant', 'symmetric_cumulant']:
            started = time.perf_counter()
            quadratic = target['k2'].copy()
            if variant == 'symmetric_cumulant':
                quadratic = (quadratic + quadratic.conj().T) / 2
            channel = ideal @ expm(quadratic)
            save(f'{case_id}_{variant}', case, arrays, channel, quadratic,
                 time.perf_counter() - started, variant, target, target_path)


def amplitude_experiments():
    case, arrays = load_case(ROOT / 'input' / 'cases' / 'driven_static.json')
    for scale in [0.125, 0.25, 0.5, 1.0]:
        scaled = copy.deepcopy(case)
        scaled['noise']['sigma'] = (np.asarray(case['noise']['sigma']) * scale).tolist()
        label = f'driven_scale_{scale:g}'.replace('.', 'p')
        started = time.perf_counter()
        channel, quadratic, diagnostics = predict(scaled, arrays, 'refined')
        save(label + '_exact', scaled, arrays, channel, quadratic, time.perf_counter() - started,
             'scaled_gaussian_quadrature', sigma_scale=scale)
        target = dict(channel=channel, k2=quadratic)
        started = time.perf_counter()
        approximate = ideal_channel(arrays) @ expm(quadratic)
        save(label + '_cumulant', scaled, arrays, approximate, quadratic,
             time.perf_counter() - started, 'scaled_corrected_cumulant', target,
             f'experiments/{label}_exact', sigma_scale=scale)
        (ROOT / 'experiments' / (label + '_exact') / 'noise.json').write_text(
            json.dumps(scaled['noise'], indent=2) + '\n')


def noise_law_experiment():
    case, arrays = load_case(ROOT / 'input' / 'cases' / 'switching_echo.json')
    target, target_path = reference(case['case_id'])
    gaussian = copy.deepcopy(case)
    gaussian['noise']['kind'] = 'ou'
    gaussian['noise']['rates'] = (2 * np.asarray(case['noise']['rates'])).tolist()
    started = time.perf_counter()
    channel, quadratic, diagnostics = predict(gaussian, arrays, 'refined')
    save('switching_same_covariance_gaussian', gaussian, arrays, channel, quadratic,
         time.perf_counter() - started, 'gaussian_same_covariance', target, target_path)


def response_experiments():
    rows = []
    for case_id in ['driven_static', 'memory_ou', 'switching_echo', 'white_gate', 'leakage_static']:
        case, arrays = load_case(ROOT / 'input' / 'cases' / f'{case_id}.json')
        target, target_path = reference(case_id)
        estimates = []
        channels = []
        ideal = ideal_channel(arrays)
        for scale in [0.04, 0.02]:
            scaled = copy.deepcopy(case)
            scaled['noise']['sigma'] = (np.asarray(case['noise']['sigma']) * scale).tolist()
            channel, quadratic, diagnostics = predict(scaled, arrays, 'refined')
            channels.append(channel)
            estimates.append((ideal.conj().T @ channel - np.eye(len(ideal))) / scale ** 2)
        extrapolated = (4 * estimates[1] - estimates[0]) / 3
        destination = ROOT / 'validation' / f'{case_id}_finite_difference.npz'
        np.savez(destination, scales=[0.04, 0.02], channels=channels,
                 estimates=estimates, extrapolated=extrapolated, target=target['k2'])
        rows.append(dict(row_id=f'{case_id}_response', case_id=case_id,
                         relative_error=float(np.linalg.norm(extrapolated - target['k2'])
                                              / np.linalg.norm(target['k2'])),
                         unextrapolated_error=float(np.linalg.norm(estimates[1] - target['k2'])
                                                    / np.linalg.norm(target['k2'])),
                         artifact=str(destination.relative_to(ROOT)), reference_artifact=target_path))
    write_csv(ROOT / 'validation' / 'response.csv', rows)


def spectral_and_partition_experiments():
    import filter_functions as ff

    case, arrays = load_case(ROOT / 'input' / 'cases' / 'calibration_static.json')
    target, target_path = reference(case['case_id'])
    for variant, lower, two_sided in [('positive_dense', 1e-3, False),
                                      ('two_sided_same_cutoff', 1e-3, True),
                                      ('two_sided_low_cutoff', 1e-7, True)]:
        started = time.perf_counter()
        omega = np.geomspace(lower, 40, 4096)
        pulse = make_pulse(arrays)
        spectrum = spectral_density(case['noise'], omega)
        cumulant = ff.numeric.calculate_cumulant_function(
            pulse, spectrum, omega, second_order=False).sum(axis=(0, 1))
        if two_sided:
            negative = -omega[::-1]
            cumulant += ff.numeric.calculate_cumulant_function(
                pulse, spectral_density(case['noise'], negative), negative,
                second_order=False).sum(axis=(0, 1))
        transform = basis_transform(pulse.basis)
        quadratic = transform @ cumulant @ transform.conj().T
        save('static_spectrum_' + variant, case, arrays, ideal_channel(arrays) @ expm(quadratic),
             quadratic, time.perf_counter() - started, variant, target, target_path,
             response_ratio=float(np.linalg.norm(quadratic) / np.linalg.norm(target['k2'])))
    case, arrays = load_case(ROOT / 'input' / 'cases' / 'driven_static.json')
    arrays['blocks'] = np.array([0, len(arrays['dt'])])
    target, target_path = reference(case['case_id'])
    for mode in ['baseline', 'selected']:
        started = time.perf_counter()
        channel, quadratic, diagnostics = predict(case, arrays, mode)
        save('driven_repartition_' + mode, case, arrays, channel, quadratic,
             time.perf_counter() - started, 'repartition_' + mode, target, target_path)
    control = np.array([[0.3, 0.2 + 0.7j], [0.2 - 0.7j, -0.4]])
    propagator = expm(-0.43j * control)
    basis = ff.Basis.ggm(2)
    transform = basis_transform(basis)
    vendor = transform @ ff.superoperator.liouville_representation(propagator, basis) @ transform.conj().T
    residual = float(np.linalg.norm(vendor - np.kron(propagator.conj(), propagator)))
    (ROOT / 'validation' / 'vendor_representation.json').write_text(json.dumps(
        dict(frobenius_error=residual, passed=residual < 1e-12,
             test='Complex unitary: vendor basis representation versus column-vectorized conjugation'), indent=2) + '\n')


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    (ROOT / 'validation').mkdir(exist_ok=True)
    closure_experiments()
    amplitude_experiments()
    noise_law_experiment()
    response_experiments()
    spectral_and_partition_experiments()
    write_csv(ROOT / 'experiments.csv', ROWS)


if __name__ == '__main__':
    main()
