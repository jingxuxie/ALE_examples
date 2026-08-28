import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / 'participant' / 'v_01'
WORKSPACE = PUBLIC / 'workspace'
sys.path[:0] = [str(ROOT / 'solution'), str(WORKSPACE), str(WORKSPACE / 'deps'), str(WORKSPACE / 'vendor')]
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MPLCONFIGDIR'] = '/tmp/ale_filter_qualification_mpl'

import numpy as np
from scipy.linalg import expm

from pipeline.physics import ideal_channel, load_case, observables, time_noise
from quadratic import quadratic_response
from reference_dynamics import solve_exact


def serializable(value):
    if isinstance(value, np.ndarray):
        return {'shape': list(value.shape), 'norm': float(np.linalg.norm(value))}
    if isinstance(value, dict):
        return {key: serializable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [serializable(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', nargs='*')
    parser.add_argument('--resume', action='store_true')
    arguments = parser.parse_args()
    target_directory = ROOT / 'evaluator' / 'hidden' / 'targets'
    target_directory.mkdir(exist_ok=True)
    validation_directory = ROOT / 'screening' / 'reference_validation'
    validation_directory.mkdir(exist_ok=True)
    hidden_manifest = json.loads((ROOT / 'evaluator' / 'hidden' / 'manifest.json').read_text())
    public_manifest = json.loads((PUBLIC / 'input' / 'manifest.json').read_text())
    records = [(case, ROOT / 'evaluator' / 'hidden' / 'cases', True) for case in hidden_manifest]
    records += [(case, PUBLIC / 'input' / 'cases', False) for case in public_manifest]
    for entry, directory, hidden in records:
        name = entry['case_id']
        if arguments.only and name not in arguments.only:
            continue
        report_path = validation_directory / f'{name}.json'
        if arguments.resume and report_path.exists():
            continue
        case, arrays = load_case(directory / entry['file'])
        law = dict(case['noise'])
        if law['kind'] == 'broadband':
            law['kind'] = 'ou'
        noise = time_noise(arrays)
        started = time.perf_counter()
        generator = quadratic_response(arrays['dt'], arrays['H'], noise, case['noise'])
        if isinstance(generator, tuple):
            generator, response_diagnostics = generator
        else:
            response_diagnostics = {}
        response_seconds = time.perf_counter() - started
        tolerance = 2e-5 if case['noise']['kind'] == 'broadband' else 2e-10
        channel, diagnostics = solve_exact(arrays['dt'], arrays['H'], noise, law, tolerance=tolerance)
        ideal = ideal_channel(arrays)
        approximation = ideal @ expm(generator)
        channel_scale = max(float(np.linalg.norm(channel - ideal)), 1e-8)
        approximation_error = float(np.linalg.norm(approximation - channel) / channel_scale)
        report = dict(case_id=name, family=entry['family'], hidden=hidden,
                      response_seconds=response_seconds, response_diagnostics=response_diagnostics,
                      exact_diagnostics=diagnostics, response_norm=float(np.linalg.norm(generator)),
                      error_channel_norm=channel_scale, exp_k2_relative_error=approximation_error,
                      observables=observables(channel, arrays))
        if case['noise']['kind'] != 'broadband':
            finite_difference = []
            for scale in (0.04, 0.02):
                small_law = dict(law, sigma=(np.asarray(law['sigma']) * scale).tolist())
                small_channel, small_diagnostics = solve_exact(arrays['dt'], arrays['H'], noise,
                                                               small_law, tolerance=3e-9)
                correction = small_channel - ideal
                finite_difference.append(ideal.conj().T @ correction / scale ** 2)
            extrapolated = (4 * finite_difference[1] - finite_difference[0]) / 3
            report['response_crosscheck_relative_error'] = float(
                np.linalg.norm(extrapolated - generator) / max(np.linalg.norm(generator), 1e-8))
            if report['response_crosscheck_relative_error'] > 1e-4:
                raise RuntimeError(f'Independent response check failed: {name}: {report}')
        if not diagnostics['converged']:
            raise RuntimeError(f'Reference convergence failed: {name}: {diagnostics}')
        if report['observables']['tp_error'] > 1e-8 or report['observables']['choi_min'] < -1e-8:
            raise RuntimeError(f'Reference physicality failed: {name}')
        destination = target_directory if hidden else validation_directory
        np.savez_compressed(destination / f'{name}.npz', channel=channel, k2=generator)
        report_path.write_text(json.dumps(serializable(report), indent=2) + '\n')
        print(json.dumps({key: report[key] for key in ('case_id', 'response_seconds', 'exp_k2_relative_error')}), flush=True)
    reports = [json.loads(path.read_text()) for path in validation_directory.glob('*.json')]
    summary = {'status': 'passed' if len(reports) == len(records) else 'partial',
               'cases_qualified': len(reports), 'cases_expected': len(records), 'cases': reports}
    (ROOT / 'screening' / 'reference_validation.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
