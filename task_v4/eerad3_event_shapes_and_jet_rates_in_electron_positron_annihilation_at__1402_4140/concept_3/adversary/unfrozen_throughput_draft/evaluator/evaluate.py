import argparse
import base64
from functools import partial
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import statistics
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / 'evaluator/hidden'
sys.path.insert(0, str(HIDDEN))
from binary_protocol import decode, serialize
from oracle import check

FLAGS = ['-O2', '-fno-fast-math', '-ffp-contract=off', '-ffixed-line-length-none', '-std=legacy']
SOURCES = ['kinematics.f', 'phaseee.f', 'eerad3lib.f']


class InvalidSubmissionError(ValueError):
    pass


class MeasurementError(RuntimeError):
    pass


def exception_result(error):
    if isinstance(error, InvalidSubmissionError):
        category = 'invalid_submission'
    elif isinstance(error, (MeasurementError, subprocess.TimeoutExpired)):
        category = 'measurement_error'
    else:
        category = 'environment_error'
    return {'core_score': 0.0, 'worst_family_score': 0.0, 'runtime_score': 0.0,
            'passed': False, 'valid': False, 'error_kind': category,
            'measurement_invalid': category in ['measurement_error', 'environment_error'],
            'reason': type(error).__name__ + ': ' + str(error)}


def isolated_command(directory, command, trusted=False):
    if shutil.which('bwrap') is None:
        raise RuntimeError('environment_error: bubblewrap required; no unsandboxed fallback')
    arguments = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session']
    for path in ['/usr', '/bin', '/lib', '/lib64', '/etc/alternatives', '/etc/ld.so.cache']:
        arguments += ['--ro-bind', path, path]
    if trusted:
        arguments += ['--ro-bind', str(ROOT / 'evaluator/trusted_runner.py'), '/trusted_runner.py']
    return arguments + ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
                        '--ro-bind' if trusted else '--bind', str(directory), '/work', '--chdir', '/tmp',
                        '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'LANG', 'C',
                        '--setenv', 'OMP_NUM_THREADS', '1', '--'] + command


def limits(cpu=None):
    if cpu is not None:
        os.sched_setaffinity(0, {cpu})
    resource.setrlimit(resource.RLIMIT_CPU, (35, 35))
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2, 32 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def build(artifact, directory):
    artifact, directory = Path(artifact).resolve(), Path(directory)
    for filename in SOURCES:
        source = artifact / filename
        if not source.is_file() or source.is_symlink() or source.stat().st_size > 512 * 1024:
            raise InvalidSubmissionError('Missing, symlinked, or oversized source: ' + filename)
        shutil.copyfile(source, directory / filename)
    shutil.copyfile(HIDDEN / 'driver.f90', directory / 'driver.f90')
    command = ['gfortran', '-fPIC', '-shared', '-Wl,-z,defs', *FLAGS,
               *['/work/' + name for name in SOURCES], '/work/driver.f90', '-o', '/work/runner.so']
    result = subprocess.run(isolated_command(directory, command), capture_output=True, text=True,
                            timeout=45, preexec_fn=limits)
    if result.returncode:
        if 'bwrap:' in result.stderr:
            raise RuntimeError('environment_error: isolated compiler could not initialize: ' + result.stderr[-2000:])
        raise InvalidSubmissionError('compile_failure: ' + result.stderr[-2000:])
    return directory / 'runner.so'


def run(executable, cases, cpu=None, timing_audit=None):
    command = ['/usr/bin/python3', '-I', '/trusted_runner.py']
    result = subprocess.run(isolated_command(executable.parent, command, trusted=True), input=serialize(cases),
                            capture_output=True, timeout=60, preexec_fn=partial(limits, cpu))
    if result.returncode:
        diagnostic = result.stderr[-2000:].decode(errors='replace')
        if 'bwrap:' in diagnostic:
            raise RuntimeError('environment_error: isolated runner could not initialize: ' + diagnostic)
        try:
            native = json.loads(result.stdout)
        except (ValueError, UnicodeError):
            raise MeasurementError('Trusted supervisor did not complete: ' + diagnostic)
        raise InvalidSubmissionError('execution_failure: ' + str(native['returncode']) + ' ' + native['stderr'])
    trusted = json.loads(result.stdout)
    if trusted['returncode']:
        raise InvalidSubmissionError('execution_failure: ' + trusted['stderr'])
    duration = float(trusted['cpu_seconds'])
    if not math.isfinite(duration) or duration <= 0:
        raise MeasurementError('Invalid trusted CPU accounting')
    if abs(duration - trusted['user_seconds'] - trusted['system_seconds']) > 1e-9:
        raise MeasurementError('Trusted user/system CPU accounting inconsistent')
    full_duration = float(trusted['full_child_cpu_seconds'])
    setup_duration = float(trusted['trusted_setup_cpu_seconds'])
    if (not math.isfinite(full_duration) or not math.isfinite(setup_duration) or setup_duration < 0
            or abs(full_duration - setup_duration - duration) > 1e-9):
        raise MeasurementError('Trusted full/setup/native CPU accounting inconsistent')
    if timing_audit is not None:
        timing_audit.update(native_cpu_seconds=duration, user_seconds=trusted['user_seconds'], system_seconds=trusted['system_seconds'],
                            full_child_cpu_seconds=trusted['full_child_cpu_seconds'],
                            trusted_setup_cpu_seconds=trusted['trusted_setup_cpu_seconds'],
                            wall_seconds=trusted['wall_seconds'], input_transport=trusted['input_transport'],
                            minor_faults=trusted['minor_faults'], major_faults=trusted['major_faults'],
                            voluntary_context_switches=trusted['voluntary_context_switches'],
                            involuntary_context_switches=trusted['involuntary_context_switches'])
    try:
        records = decode(base64.b64decode(trusted['stdout_b64'], validate=True), len(cases))
    except ValueError as error:
        raise InvalidSubmissionError(str(error)) from error
    return records, duration


def grade(cases, references, records, target):
    failures, record_by_id = {}, {}
    for case, reference, record in zip(cases, references, records):
        errors = check(case, reference, record, target)
        record_by_id[case['id']] = record
        if case.get('parent') and not errors:
            original = np.array(record_by_id[case['parent']][25:37]).reshape((4, 3), order='F').T
            transformed = original.copy()
            transformed[:, :3] = transformed[:, :3] @ np.array(case['transform']).T
            transformed *= case['scale_factor']
            actual = record[25:37].reshape((4, 3), order='F').T[np.array(case['slots']) - 1]
            if np.max(np.abs(actual - transformed)) / sum(vector[3] for vector in case['p']) > target['momentum_atol']:
                errors.append('metamorphic_covariance')
        if errors:
            failures[case['id']] = errors
    return failures


def evaluate(artifact, calibration=False):
    target = json.loads((HIDDEN / 'target.json').read_text())
    if target.get('measurement') != 'unique_binary_one_pass':
        raise RuntimeError('Use the preserved snapshot evaluator for a superseded target')
    if target['runtime_ratio_limit'] is None and not calibration:
        raise RuntimeError('Production target not yet calibrated and committed; fresh evaluation prohibited')
    for filename, key in [('cases.json', 'case_sha256'), ('references.json', 'reference_sha256')]:
        if hashlib.sha256((HIDDEN / filename).read_bytes()).hexdigest() != target[key]:
            raise RuntimeError('environment_error: evaluation data hash mismatch')
    for filename, expected in target['required_sha256'].items():
        if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != expected:
            raise RuntimeError('environment_error: protected input changed: ' + filename)
    cases = json.loads((HIDDEN / 'cases.json').read_text())
    references = json.loads((HIDDEN / 'references.json').read_text())
    if len(cases) != len(references) or len(cases) != target['case_count']:
        raise RuntimeError('environment_error: incorrect case/reference count')
    signatures = {json.dumps(case['p'], separators=(',', ':')) for case in cases}
    if len(signatures) != len(cases) or len({case['id'] for case in cases}) != len(cases):
        raise RuntimeError('environment_error: repeated native momentum input or ID')
    cpu = min(os.sched_getaffinity(0))
    pairs, failures = [], {}
    with tempfile.TemporaryDirectory(prefix='eerad3-unique-') as temporary:
        candidate_dir, baseline_dir = Path(temporary) / 'candidate', Path(temporary) / 'baseline'
        candidate_dir.mkdir()
        baseline_dir.mkdir()
        candidate, baseline = build(artifact, candidate_dir), build(HIDDEN / 'pristine', baseline_dir)
        for trial in range(target['timing_pairs']):
            order = ['baseline', 'candidate'] if trial % 2 == 0 else ['candidate', 'baseline']
            pair = {'order': order}
            for name in order:
                audit = {}
                records, duration = run(baseline if name == 'baseline' else candidate, cases, cpu, audit)
                current = grade(cases, references, records, target)
                pair[name] = duration
                pair[name + '_accounting'] = audit
                pair[name + '_checked_records'] = len(records)
                pair[name + '_failed_case_count'] = len(current)
                if name == 'candidate':
                    for identifier, errors in current.items():
                        failures.setdefault(identifier, set()).update(errors)
            pair['ratio'] = pair['candidate'] / pair['baseline']
            pairs.append(pair)
    families = {}
    for case in cases:
        families.setdefault(case['family'], []).append(case['id'] not in failures)
    scores = {family: sum(values) / len(values) for family, values in families.items()}
    ratio = statistics.median(pair['ratio'] for pair in pairs)
    limit = target['runtime_ratio_limit']
    passed = not failures and limit is not None and ratio <= limit
    reason = ('all unique-event numerical and trusted CPU gates passed' if passed else
              'numerical gates failed' if failures else 'calibration only; target not fixed' if limit is None else 'runtime budget exceeded')
    return {'passed': passed, 'valid': True, 'quality_passed': not failures, 'reason': reason,
            'core_score': sum(scores.values()) / len(scores), 'worst_family_score': min(scores.values()),
            'family_scores': scores, 'failed_case_count': len(failures),
            'failures': [{'id': identifier, 'checks': sorted(errors)} for identifier, errors in failures.items()][:24],
            'runtime_ratio': ratio, 'runtime_ratio_limit': limit,
            'runtime_score': min(1.0, limit / ratio) if limit is not None else None,
            'candidate_cpu_seconds': statistics.median(pair['candidate'] for pair in pairs),
            'baseline_cpu_seconds': statistics.median(pair['baseline'] for pair in pairs),
            'paired_trials': pairs, 'timing_cpu': cpu, 'native_events_per_process': len(cases),
            'native_passes_per_process': 1, 'all_trial_records_checked': True,
            'measurement': 'unique_binary_one_pass', 'target_sha256': hashlib.sha256((HIDDEN / 'target.json').read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.artifact)
    except Exception as error:
        result = exception_result(error)
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
