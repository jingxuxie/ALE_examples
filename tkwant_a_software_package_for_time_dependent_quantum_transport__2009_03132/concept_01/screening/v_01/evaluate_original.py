import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import time
import numpy as np


HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parent
PUBLIC = CONCEPT / 'participant' / 'v_01' / 'input'
FIELDS = ['initial_charge', 'final_charge', 'peak_current', 'transported_charge', 'max_density_change']


def rms(values):
    return float(np.sqrt(np.mean(np.asarray(values) ** 2)))


def summary(trace):
    density, current, times = trace['density'], trace['current'], trace['times']
    return dict(initial_charge=float(np.sum(density[0])), final_charge=float(np.sum(density[-1])),
                peak_current=float(np.max(abs(current))), transported_charge=float(np.trapz(current[:, 0], times)),
                max_density_change=float(np.max(abs(density - density[0]))))


def read_csv(path):
    with open(path) as handle:
        return list(csv.DictReader(handle))


def limit_memory():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))


def launch(submission, suite, output, config, limit=240):
    output.mkdir(parents=True, exist_ok=True)
    command = ['bwrap', '--die-with-parent', '--unshare-all', '--new-session', '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp']
    for directory in ['/usr', '/bin', '/lib', '/lib64', '/etc']:
        if Path(directory).exists():
            command.extend(['--ro-bind', directory, directory])
    command.extend(['--ro-bind', str(submission), '/submission', '--ro-bind', str(suite), '/cases.json',
                    '--bind', str(output), '/output', '--chdir', '/submission',
                    '--setenv', 'HOME', '/tmp', '--setenv', 'OPENBLAS_NUM_THREADS', '1', '--setenv', 'OMP_NUM_THREADS', '1',
                    '--setenv', 'MKL_NUM_THREADS', '1', '--setenv', 'NUMBA_CACHE_DIR', '/output/.numba',
                    '--setenv', 'PYTHONDONTWRITEBYTECODE', '1', '--setenv', 'PYTHONPATH', '',
                    '/usr/bin/time', '-f', '%e %M %U %S', '-o', '/output/process_resources.txt',
                    '/bin/bash', '/submission/run.sh', '--cases', '/cases.json', '--output', '/output', '--config', config])
    started = time.monotonic()
    with open(output / 'stdout.log', 'w') as stdout, open(output / 'stderr.log', 'w') as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, preexec_fn=limit_memory, start_new_session=True)
        try:
            returncode = process.wait(timeout=limit)
            timed_out = False
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            returncode = -9
            timed_out = True
    elapsed = time.monotonic() - started
    result = dict(returncode=returncode, wall_seconds=elapsed, timeout=timed_out)
    resource_path = output / 'process_resources.txt'
    if resource_path.exists():
        tokens = resource_path.read_text().strip().splitlines()[-1].split()
        if len(tokens) == 4:
            result.update(measured_seconds=float(tokens[0]), peak_rss_mb=float(tokens[1]) / 1024,
                          user_seconds=float(tokens[2]), system_seconds=float(tokens[3]))
    (output / 'process.json').write_text(json.dumps(result, indent=2))
    return result


def score_case(case, predicted_path, truth_path):
    try:
        predicted = np.load(predicted_path)
        truth = np.load(truth_path)
        for key in ['times', 'density', 'current']:
            if predicted[key].shape != truth[key].shape or not np.all(np.isfinite(predicted[key])):
                raise ValueError('bad shape or nonfinite ' + key)
        if np.max(abs(predicted['times'] - truth['times'])) > 1e-10:
            raise ValueError('wrong observation times')
        initial_error = rms(predicted['density'][0] - truth['density'][0])
        density_error = rms((predicted['density'] - predicted['density'][0]) - (truth['density'] - truth['density'][0]))
        current_error = rms(predicted['current'] - truth['current'])
        density_scale = .01 + rms(truth['density'] - truth['density'][0])
        current_scale = .01 + rms(truth['current'])
        errors = [initial_error / .10, density_error / density_scale, current_error / current_scale]
        qualities = [1 / (1 + (error / .035) ** 1.2) for error in errors]
        quality = .2 * qualities[0] + .4 * qualities[1] + .4 * qualities[2]
        worst_absolute = max(float(np.max(abs(predicted['density'] - truth['density']))), float(np.max(abs(predicted['current'] - truth['current']))))
        pauli_violation = max(0., float(-np.min(predicted['density'])), float(np.max(predicted['density']) - 1))
        quality *= 1 / (1 + pauli_violation / .005)
        return dict(family=case['family'], score=quality, initial_density_rmse=initial_error,
                    delta_density_rmse=density_error, current_rmse=current_error, worst_absolute_error=worst_absolute,
                    normalized_errors=errors, pauli_violation=pauli_violation)
    except Exception as error:
        return dict(family=case['family'], score=0., error=repr(error))


def evidence(submission, output, replay=True):
    checks = []
    errors = []
    tables = {}
    case_sets = {
        'results.csv': ('development.json', ['production']),
        'ablation.csv': ('development.json', ['conservative', 'ablation']),
        'scaling.csv': ('controls.json', ['production']),
    }
    metadata_configs = {}
    for table, (suite, configurations) in case_sets.items():
        try:
            rows = read_csv(submission / table)
            indexed = {row['row_id']: row for row in rows}
            if len(indexed) != len(rows):
                raise ValueError('duplicate row IDs')
            tables[table] = indexed
            cases = json.loads((PUBLIC / suite).read_text())['cases']
            for case in cases:
                for config in configurations:
                    row = indexed[case['id'] + ':' + config]
                    run_name = 'scaling' if table == 'scaling.csv' else config
                    trace = np.load(submission / 'runs' / run_name / (case['id'] + '.npz'))
                    observed = summary(trace)
                    checks.append(all(math.isclose(float(row[field]), observed[field], rel_tol=1e-7, abs_tol=2e-8) for field in FIELDS))
                    metadata = json.loads((submission / 'runs' / run_name / (case['id'] + '.json')).read_text())
                    checks.append(math.isclose(float(row['runtime_s']), metadata['seconds'], rel_tol=1e-7, abs_tol=1e-7))
                    checks.append(math.isclose(float(row['peak_rss_mb']), metadata['peak_rss_mb'], rel_tol=1e-7, abs_tol=1e-7))
                    metadata_configs[(case['id'], config)] = metadata['config']
            if table == 'ablation.csv':
                checks.append(all(metadata_configs[(case['id'], 'production')] != metadata_configs[(case['id'], 'ablation')] for case in cases))
                checks.append(all(metadata_configs[(case['id'], 'production')] != metadata_configs[(case['id'], 'conservative')] for case in cases))
        except Exception as error:
            errors.append(table + ': ' + repr(error))
            checks.append(False)
    try:
        claims = json.loads((submission / 'claims.json').read_text())['claims']
        checks.append(len(claims) >= 3)
        cross_comparison = False
        resource_claim = False
        def cell(reference):
            return float(tables[reference['table']][reference['row_id']][reference['column']])
        for claim in claims:
            left = cell(claim['left'])
            right = cell(claim['right']) if 'right' in claim else float(claim['value'])
            if 'right' in claim and claim['left']['table'] != claim['right']['table']:
                cross_comparison = True
            if claim['left']['table'] == 'scaling.csv' and claim['left']['column'] in ['runtime_s', 'peak_rss_mb']:
                resource_claim = True
            operation = claim['comparison']
            if operation == 'le':
                valid = left <= right + 1e-9
            elif operation == 'ge':
                valid = left + 1e-9 >= right
            elif operation == 'abs_difference_le':
                valid = abs(left - right) <= claim['tolerance'] + 1e-9
            elif operation == 'relative_difference_le':
                valid = abs(left - right) / max(abs(left), abs(right), 1e-12) <= claim['tolerance'] + 1e-9
            else:
                valid = False
            checks.append(valid and len(claim.get('text', '')) > 20)
        checks.extend([cross_comparison, resource_claim])
    except Exception as error:
        errors.append('claims: ' + repr(error))
        checks.append(False)
    try:
        primary = read_csv(submission / 'figures' / 'primary_result.csv')
        checks.append(len(primary) > 40)
        trace_cache = {}
        for row in primary:
            key = row['case'], row['config']
            if key not in trace_cache:
                trace_cache[key] = np.load(submission / 'runs' / row['config'] / (row['case'] + '.npz'))
            trace = trace_cache[key]
            index = int(np.argmin(abs(trace['times'] - float(row['time']))))
            checks.append(abs(float(row['time']) - trace['times'][index]) < 1e-9 and abs(float(row['density_sum']) - np.sum(trace['density'][index])) < 1e-7 and abs(float(row['current_0']) - trace['current'][index, 0]) < 1e-7)
        for row in read_csv(submission / 'figures' / 'robustness_or_scaling.csv'):
            original = tables['scaling.csv'][row['row_id']]
            checks.append(all(abs(float(row[key]) - float(original[key])) < 1e-7 for key in ['runtime_s', 'peak_rss_mb']))
        for name in ['primary_result.png', 'robustness_or_scaling.png']:
            from PIL import Image
            with Image.open(submission / 'figures' / name) as image:
                checks.append(image.width >= 100 and image.height >= 100)
        checks.append(len((submission / 'report.md').read_text()) >= 500)
    except Exception as error:
        errors.append('figures/report: ' + repr(error))
        checks.append(False)
    reruns = {}
    if replay:
        public_cases = json.loads((PUBLIC / 'development.json').read_text())['cases']
        selected = [public_cases[1], public_cases[2]]
        replay_suite = output / 'replay_cases.json'
        replay_suite.write_text(json.dumps({'cases': selected}))
        for config in ['production', 'ablation']:
            run_directory = output / ('replay_' + config)
            reruns[config] = launch(submission, replay_suite, run_directory, config, limit=180)
            for case in selected:
                try:
                    original = np.load(submission / 'runs' / config / (case['id'] + '.npz'))
                    actual = np.load(run_directory / (case['id'] + '.npz'))
                    checks.append(all(np.allclose(actual[key], original[key], rtol=1e-7, atol=2e-8) for key in ['times', 'density', 'current']))
                except Exception as error:
                    errors.append('replay ' + config + ': ' + repr(error))
                    checks.append(False)
        try:
            distinct = any(np.max(abs(np.load(output / 'replay_production' / (case['id'] + '.npz'))['density'] - np.load(output / 'replay_ablation' / (case['id'] + '.npz'))['density'])) > 1e-9 for case in selected)
            checks.append(distinct)
        except Exception:
            checks.append(False)
    return dict(score=float(np.mean(checks)) if checks else 0., all_checks_pass=bool(checks) and all(checks), failures=errors, reruns=reruns, passed=int(sum(checks)), total=len(checks))


def evaluate(submission, output, include_evidence=True):
    submission, output = Path(submission).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    cases = json.loads((HERE / 'hidden' / 'cases.json').read_text())['cases']
    sanitized = []
    for index, case in enumerate(cases):
        item = dict(case, id='withheld_' + str(index))
        sanitized.append(item)
    suite = output / 'hidden_request.json'
    suite.write_text(json.dumps({'cases': sanitized}))
    run = launch(submission, suite, output / 'hidden_run', 'production')
    per_case = {}
    for case, sent in zip(cases, sanitized):
        per_case[case['id']] = score_case(case, output / 'hidden_run' / (sent['id'] + '.npz'), HERE / 'hidden' / 'gold' / (case['id'] + '.npz'))
    scores = [item['score'] for item in per_case.values()]
    core = .7 * float(np.mean(scores)) + .3 * min(scores)
    baseline_metadata = HERE / 'reference_resources.json'
    reference = json.loads(baseline_metadata.read_text()) if baseline_metadata.exists() else {'seconds': 90., 'peak_rss_mb': 300.}
    speed = 1 / (1 + run['wall_seconds'] / (3 * reference['seconds']))
    memory = 1 / (1 + run.get('peak_rss_mb', 2048) / (3 * reference['peak_rss_mb']))
    resource_score = .7 * speed + .3 * memory
    if run.get('peak_rss_mb', 0) > 2048:
        core *= 2048 / run['peak_rss_mb']
    evidence_result = evidence(submission, output, replay=True) if include_evidence else {'score': 0., 'skipped': True}
    overall = .9 * core + .07 * resource_score + .03 * evidence_result['score']
    classification = 'too_easy' if core >= .9 else ('moderate' if core >= .6 else 'potentially_hard')
    stderr = (output / 'hidden_run' / 'stderr.log').read_text()
    infrastructure = 'bwrap:' in stderr and not list((output / 'hidden_run').glob('*.npz'))
    if infrastructure:
        classification = 'invalid_infrastructure'
    result = dict(core_score=core, overall_score=overall, per_family={item['family']: item['score'] for item in per_case.values()},
                  per_case=per_case, resource_score=resource_score, resources=run, evidence=evidence_result,
                  classification=classification, infrastructure_failure=infrastructure,
                  submission=str(submission), evaluation_version='v_01', scoring_description='70% mean + 30% worst-family observable fidelity; overall 90% core, 7% measured resources, 3% coupled evidence')
    (output / 'evaluation.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('submission')
    parser.add_argument('--output', required=True)
    parser.add_argument('--skip-evidence', action='store_true')
    arguments = parser.parse_args()
    evaluate(arguments.submission, arguments.output, not arguments.skip_evidence)
