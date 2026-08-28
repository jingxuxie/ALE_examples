import argparse
import csv
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
HIDDEN = Path(__file__).parent / 'hidden'


def load_npz(filename):
    with np.load(filename, allow_pickle=False) as arrays:
        return {key: arrays[key] for key in arrays.files}


def run_command(command, directory, timeout=60):
    directory.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')

    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
        resource.setrlimit(resource.RLIMIT_CPU, (timeout + 1, timeout + 2))

    started = time.monotonic()
    with (directory / 'stdout.log').open('w') as stdout, (directory / 'stderr.log').open('w') as stderr:
        process = subprocess.Popen(['/usr/bin/time', '-f', '%M', '-o', str(directory / 'memory.txt')] + command,
                                    stdout=stdout, stderr=stderr, env=environment,
                                    start_new_session=True, preexec_fn=limit)
        expired = False
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            returncode = -9
    memory = directory / 'memory.txt'
    try:
        peak_mib = float(memory.read_text().strip().splitlines()[-1]) / 1024
    except (OSError, ValueError, IndexError):
        peak_mib = None
    return {'wall_seconds': time.monotonic() - started, 'peak_mib': peak_mib,
            'returncode': returncode, 'timeout': expired}


def physical_error(result, oracle, case_arrays, process=False):
    times = case_arrays['times']
    dimension = len(case_arrays['H0'])
    if result['states'].shape != (len(times), dimension, dimension):
        raise ValueError('incorrect state shape')
    if not np.allclose(times, result['times'], rtol=0, atol=1e-11):
        raise ValueError('incorrect times')
    for value in result.values():
        if not np.isfinite(value).all():
            raise ValueError('nonfinite output')
    errors = {'state_max': float(np.max(np.linalg.norm(result['states'] - oracle['states'], axis=(1, 2))))}
    predictions = np.einsum('oij,tji->to', case_arrays['e_ops'], result['states'])
    if result['expectations'].shape != predictions.shape:
        raise ValueError('incorrect expectations shape')
    errors['observable_consistency'] = float(np.max(np.abs(predictions - result['expectations'])))
    errors['initial'] = float(np.linalg.norm(result['states'][0] - case_arrays['rho0']))
    errors['trace'] = float(np.max(np.abs(np.trace(result['states'], axis1=1, axis2=2) - 1)))
    errors['hermiticity'] = float(np.max(np.linalg.norm(result['states'] - result['states'].conj().transpose(0, 2, 1), axis=(1, 2))))
    if process:
        for name in ['channel', 'choi']:
            if result[name].shape != (dimension ** 2, dimension ** 2):
                raise ValueError('incorrect ' + name + ' shape')
            errors[name] = float(np.linalg.norm(result[name] - oracle[name]) / dimension)
        predicted_final = (result['channel'] @ case_arrays['rho0'].reshape(-1, order='F')).reshape(dimension, dimension, order='F')
        errors['channel_state_consistency'] = float(np.linalg.norm(predicted_final - result['states'][-1]))
    return max(errors.values()), errors


def read_rows(filename):
    with Path(filename).open() as stream:
        return {row['row_id']: row for row in csv.DictReader(stream)}


def evidence_check(submission, destination):
    reasons = []
    regeneration = destination / 'public_rerun'
    resources = run_command(['bash', str(submission / 'run.sh'), 'campaign',
                             str(ROOT / 'participant/v_01/input'), str(regeneration)],
                            destination / 'public_resources', timeout=150)
    if resources['returncode'] != 0:
        return {'score': 0.0, 'issues': ['campaign regeneration failed'], 'resources': resources}
    checks = []
    for table in ['results.csv', 'ablation.csv', 'scaling.csv']:
        try:
            supplied = read_rows(submission / table)
            rerun = read_rows(regeneration / table)
            checks.append(set(supplied) == set(rerun))
            for identifier, fresh in rerun.items():
                old = supplied[identifier]
                for metric in ['final_expectation', 'final_purity', 'trace_error', 'hermiticity_error', 'minimum_eigenvalue']:
                    checks.append(bool(np.isclose(float(old[metric]), float(fresh[metric]), atol=2e-6, rtol=1e-5)))
                if 'distance_to_refined' in fresh:
                    checks.append(bool(np.isclose(float(old['distance_to_refined']), float(fresh['distance_to_refined']), atol=2e-6, rtol=2e-4)))
                checks.append(float(old['wall_seconds']) > 0 and float(old['peak_mib']) > 0)
                raw_path = regeneration / 'runs' / fresh['case'] / fresh['configuration'] / 'result.npz'
                raw = load_npz(raw_path)
                arrays_name = fresh['case'].split('_size_')[0]
                saved_input = raw_path.parent / 'input.npz'
                case = load_npz(saved_input if saved_input.exists() else ROOT / 'participant/v_01/input' / (arrays_name + '.npz'))
                dimension = int(fresh['dimension'])
                observable = case['e_ops'][0, :dimension, :dimension]
                value = np.trace(observable @ raw['states'][-1]).real
                checks.append(bool(np.isclose(value, float(fresh['final_expectation']), atol=1e-7, rtol=1e-7)))
                checks.append(bool(np.isclose(np.trace(raw['states'][-1] @ raw['states'][-1]).real,
                                              float(fresh['final_purity']), atol=1e-7, rtol=1e-7)))
                old_raw_path = submission / raw_path.relative_to(regeneration)
                old_raw = load_npz(old_raw_path)
                checks.append(bool(np.max(np.abs(old_raw['states'] - raw['states'])) < 2e-5))
            checks.append(len(rerun) >= (3 if table == 'scaling.csv' else 12))
        except Exception as error:
            checks.append(False)
            reasons.append(table + ': ' + str(error))
    try:
        results = read_rows(regeneration / 'results.csv')
        differences = []
        for row in results.values():
            if row['configuration'] == 'production':
                ablated = results[row['case'] + '/ablation']
                differences.append(abs(float(row['final_expectation']) - float(ablated['final_expectation'])))
                checks.append(row['config_digest'] != ablated['config_digest'])
        checks.append(max(differences) > 1e-5)
        claims = json.loads((submission / 'claims.json').read_text())
        checks.append(len(claims) >= 2)
        for claim in claims:
            table = read_rows(regeneration / claim['table'])
            left, right = float(table[claim['left']][claim['metric']]), float(table[claim['right']][claim['metric']])
            supported = left <= right + 1e-8 if claim['relation'] == 'le' else left > right
            checks.append(supported)
        sources = json.loads((submission / 'figures/sources.json').read_text())
        for name in ['primary_result.png', 'robustness_or_scaling.png']:
            from PIL import Image
            Image.open(submission / 'figures' / name).verify()
            source = sources[name]
            table = read_rows(regeneration / source['table'])
            checks.append(all(identifier in table and source['metric'] in table[identifier] for identifier in source['rows']))
        checks.append(len((submission / 'report.md').read_text().split()) >= 150)
    except Exception as error:
        checks.append(False)
        reasons.append('evidence: ' + str(error))
    return {'score': sum(checks) / max(1, len(checks)), 'checks': len(checks),
            'failed_checks': len(checks) - sum(checks), 'issues': reasons, 'resources': resources}


def evaluate(submission, destination, evidence=True):
    submission, destination = Path(submission).resolve(), Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    calibration_path = HIDDEN / 'calibration.json'
    calibration = json.loads(calibration_path.read_text()) if calibration_path.exists() else {}
    families = {}
    for index, manifest in enumerate(sorted(HIDDEN.glob('*.json'))):
        if manifest.name == 'calibration.json':
            continue
        metadata = json.loads(manifest.read_text())
        case_id = metadata['id']
        case_directory = destination / ('case_' + str(index))
        case_directory.mkdir(parents=True, exist_ok=True)
        input_directory = case_directory / 'input'
        input_directory.mkdir(exist_ok=True)
        staged = dict(metadata, id='qualification_' + str(index), family='heldout_' + str(index), arrays='model.npz')
        (input_directory / 'case.json').write_text(json.dumps(staged))
        shutil.copyfile(HIDDEN / metadata['arrays'], input_directory / 'model.npz')
        output_directory = case_directory / 'output'
        metrics = run_command(['bash', str(submission / 'run.sh'), 'solve', str(input_directory / 'case.json'),
                               str(output_directory), '--config', 'production'], case_directory / 'resources')
        family = {'case': case_id, **metrics}
        try:
            if metrics['returncode'] != 0:
                raise RuntimeError('solver timeout' if metrics['timeout'] else 'solver process failed')
            result = load_npz(output_directory / 'result.npz')
            oracle = load_npz(HIDDEN / 'oracles' / (case_id + '.npz'))
            arrays = load_npz(HIDDEN / metadata['arrays'])
            error, components = physical_error(result, oracle, arrays, metadata.get('process', False))
            quality = float(1 / (1 + (error / 0.003) ** 0.65))
            family.update({'error': error, 'error_components': components, 'quality': quality,
                           'failure_classification': 'none' if quality >= 0.9 else 'core_scientific_error'})
        except Exception as error:
            family.update({'error': None, 'quality': 0.0, 'reason': str(error),
                           'failure_classification': 'resource_failure' if metrics['timeout'] else 'execution_or_contract_failure'})
        anchor = calibration.get(case_id, {'wall_seconds': metrics['wall_seconds'], 'peak_mib': metrics['peak_mib']})
        speed = min(1.0, (max(0.01, anchor['wall_seconds']) / max(0.01, metrics['wall_seconds'])) ** 0.3)
        memory = min(1.0, (max(1, anchor.get('peak_mib') or 1) / max(1, metrics['peak_mib'] or 1536)) ** 0.3)
        family['efficiency'] = (0.75 * speed + 0.25 * memory) * family['quality']
        if 'weak_error' in anchor:
            family['weak_baseline_error'] = anchor['weak_error']
        families[metadata['family']] = family
    qualities = [item['quality'] for item in families.values()]
    core = 0.7 * float(np.mean(qualities)) + 0.3 * min(qualities)
    evidence_result = evidence_check(submission, destination) if evidence else {'score': None, 'not_run': True}
    efficiency = float(np.mean([item['efficiency'] for item in families.values()]))
    overall = 0.82 * core + 0.10 * efficiency + 0.08 * (evidence_result['score'] or 0)
    classification = 'too_easy' if core >= 0.90 else 'moderate' if core >= 0.60 else 'potentially_hard'
    result = {'submission': str(submission), 'core_score': core, 'overall_score': overall,
              'minimum_family_score': min(qualities), 'mean_family_score': float(np.mean(qualities)),
              'efficiency_score': efficiency, 'per_family': families, 'evidence': evidence_result,
              'classification': classification,
              'solver_wall_seconds': sum(item['wall_seconds'] for item in families.values()),
              'peak_mib': max(item['peak_mib'] or 0 for item in families.values())}
    (destination / 'evaluation.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('submission')
    parser.add_argument('destination')
    parser.add_argument('--skip-evidence', action='store_true')
    arguments = parser.parse_args()
    result = evaluate(arguments.submission, arguments.destination, not arguments.skip_evidence)
    print(json.dumps({key: result[key] for key in ['core_score', 'overall_score', 'classification', 'solver_wall_seconds']}, indent=2))
