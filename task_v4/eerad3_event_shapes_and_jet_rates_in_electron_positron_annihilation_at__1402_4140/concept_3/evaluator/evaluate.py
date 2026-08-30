import argparse
import base64
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
import time

ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / 'evaluator/hidden'
sys.path.insert(0,str(HIDDEN))
from generate import serialize
from oracle import check

FLAGS = ['-O2','-fno-fast-math','-ffp-contract=off','-ffixed-line-length-none','-std=legacy']
SOURCES = ['kinematics.f','phaseee.f','eerad3lib.f']


def isolated_command(directory, command, compile_phase=False):
    if shutil.which('bwrap') is None:
        raise RuntimeError('environment_error: bubblewrap is required; no unsandboxed fallback')
    arguments = ['bwrap','--unshare-all','--die-with-parent','--new-session']
    for path in ['/usr','/bin','/lib','/lib64','/etc/alternatives','/etc/ld.so.cache']:
        arguments += ['--ro-bind',path,path]
    return arguments + ['--proc','/proc','--dev','/dev','--tmpfs','/tmp',
        '--bind' if compile_phase else '--ro-bind',str(directory),'/work',
        '--ro-bind',str(ROOT/'evaluator/trusted_runner.py'),'/trusted_runner.py',
        '--chdir','/work','--clearenv',
        '--setenv','PATH','/usr/bin:/bin','--setenv','LANG','C',
        '--setenv','OMP_NUM_THREADS','1','--'] + command


def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(35,35))
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def build(artifact,directory):
    artifact = Path(artifact)
    if artifact.is_symlink():
        raise ValueError('Symlinked artifact directory')
    artifact = artifact.resolve()
    for filename in SOURCES:
        source = artifact / filename
        if not source.is_file() or source.is_symlink() or source.stat().st_size > 512*1024:
            raise ValueError('Missing, symlinked, or oversized source: '+filename)
        shutil.copyfile(source,Path(directory)/filename)
    shutil.copyfile(HIDDEN/'driver.f90',Path(directory)/'driver.f90')
    result = subprocess.run(isolated_command(directory,['gfortran',*FLAGS,*SOURCES,'driver.f90','-o','runner'],compile_phase=True),cwd=directory,
        capture_output=True,text=True,timeout=45,preexec_fn=limits)
    if result.returncode:
        if 'bwrap:' in result.stderr:
            raise RuntimeError('environment_error: isolated compiler could not initialize: '+result.stderr[-1000:])
        raise RuntimeError('compile_failure: '+result.stderr[-1500:])
    return Path(directory)/'runner'


def run(executable,cases,repeats=300):
    try:
        result = subprocess.run(isolated_command(executable.parent,['/usr/bin/python3','-I','/trusted_runner.py']),input=serialize(cases,repeats),cwd=executable.parent,
            capture_output=True,text=True,timeout=90,preexec_fn=limits,
            env={'PATH':'/usr/bin:/bin','LANG':'C','OMP_NUM_THREADS':'1'})
    except subprocess.TimeoutExpired as error:
        raise RuntimeError('measurement_error: trusted supervisor startup/transport exceeded the outer watchdog') from error
    if result.returncode:
        if 'bwrap:' in result.stderr:
            raise RuntimeError('environment_error: isolated runner could not initialize: '+result.stderr[-1000:])
        raise RuntimeError('execution_failure: '+str(result.returncode)+' '+result.stderr[-500:])
    try:
        accounting = json.loads(result.stdout)
    except (ValueError, TypeError) as error:
        raise RuntimeError('measurement_error: trusted supervisor returned no valid report') from error
    if 'wrapper_error' in accounting:
        raise RuntimeError(accounting['wrapper_error'])
    if accounting.get('returncode') != 0 or accounting.get('descendant_failures'):
        raise RuntimeError('execution_failure: native process or descendant failed: '+str(accounting))
    try:
        stdout = base64.b64decode(accounting.pop('stdout_b64'),validate=True).decode('ascii')
    except (ValueError, KeyError, UnicodeError) as error:
        raise ValueError('Malformed native output encoding') from error
    lines = stdout.splitlines()
    if len(lines) != len(cases)+1 or not lines[-1].startswith('TIME '):
        raise ValueError('Malformed output record count or timing trailer')
    records = [[float(token) for token in line.split()] for line in lines[:-1]]
    if any(len(record) != 84 for record in records):
        raise ValueError('Malformed native numerical record width')
    duration = accounting.get('cpu_seconds')
    if not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration <= 0:
        raise RuntimeError('measurement_error: invalid trusted child CPU time')
    if abs(duration-accounting['user_seconds']-accounting['system_seconds']) > 1e-10:
        raise RuntimeError('measurement_error: inconsistent trusted CPU accounting')
    run.last_accounting = accounting
    return records,duration


def measure(executable,cases,repeats,trials=3):
    timings = []
    accounting = []
    record_trials = []
    records = None
    for trial in range(trials):
        records,duration = run(executable,cases,repeats)
        timings.append(duration)
        accounting.append(run.last_accounting)
        record_trials.append(records)
    measure.last_accounting = accounting
    measure.last_record_trials = record_trials
    return records,statistics.median(timings),timings


def evaluate(artifact):
    target = json.loads((HIDDEN/'target.json').read_text())
    for filename,key in [('cases.json','case_sha256'),('references.json','reference_sha256')]:
        if hashlib.sha256((HIDDEN/filename).read_bytes()).hexdigest() != target[key]:
            raise RuntimeError('environment_error: frozen evaluation data hash mismatch')
    cases = json.loads((HIDDEN/'cases.json').read_text())
    references = json.loads((HIDDEN/'references.json').read_text())
    with tempfile.TemporaryDirectory(prefix='eerad3-eval-') as directory:
        candidate_dir = Path(directory)/'candidate'
        baseline_dir = Path(directory)/'baseline'
        candidate_dir.mkdir()
        baseline_dir.mkdir()
        executable = build(artifact,candidate_dir)
        try:
            baseline = build(HIDDEN/'pristine',baseline_dir)
        except Exception as error:
            raise RuntimeError('environment_error: pristine baseline build failed: '+str(error)) from error
        try:
            baseline_records,baseline_time,baseline_trials = measure(baseline,cases,target['timing_repeats'])
        except Exception as error:
            raise RuntimeError('measurement_error: pristine baseline measurement failed: '+str(error)) from error
        baseline_accounting = measure.last_accounting
        records,candidate_time,candidate_trials = measure(executable,cases,target['timing_repeats'])
        candidate_accounting = measure.last_accounting
        candidate_record_trials = measure.last_record_trials
    families = {}
    failures = []
    case_index_by_id = {case['id']:index for index,case in enumerate(cases)}
    for case_index,(case,reference,record) in enumerate(zip(cases,references,records)):
        errors = []
        for trial_records in candidate_record_trials:
            record = trial_records[case_index]
            trial_errors = check(case,reference,record,target)
            if case.get('parent') and not trial_errors:
                import numpy as np
                original = np.array(trial_records[case_index_by_id[case['parent']]][25:37]).reshape((4,3),order='F').T
                transformed = original.copy()
                transformed[:,:3] = transformed[:,:3]@np.array(case['transform']).T
                transformed *= case['scale_factor']
                actual = np.array(record[25:37]).reshape((4,3),order='F').T
                actual = actual[np.array(case['slots'])-1]
                if np.max(np.abs(actual-transformed))/sum(vector[3] for vector in case['p']) > target['momentum_atol']:
                    trial_errors.append('metamorphic_covariance')
            errors = sorted(set(errors + trial_errors))
        families.setdefault(case['family'],[]).append(not errors)
        if errors:
            failures.append({'id':case['id'],'checks':errors})
    family_scores = {family:sum(results)/len(results) for family,results in families.items()}
    core = sum(family_scores.values())/len(family_scores)
    worst = min(family_scores.values())
    ratio = candidate_time/baseline_time
    runtime = min(1.,target['runtime_ratio_limit']/ratio)
    passed = not failures and ratio <= target['runtime_ratio_limit']
    reason = 'all physical, oracle, metamorphic and resource checks passed' if passed else (
        f'{len(failures)} cases fail numerical/physical checks' if failures else 'runtime budget exceeded')
    return {'core_score':core,'worst_family_score':worst,'runtime_score':runtime,'passed':passed,'valid':True,'reason':reason,
        'family_scores':family_scores,'failures':failures[:24],'failed_case_count':len(failures),
        'candidate_cpu_seconds':candidate_time,'baseline_cpu_seconds':baseline_time,'runtime_ratio':ratio,
        'runtime_ratio_limit':target['runtime_ratio_limit'],'candidate_trials':candidate_trials,
        'baseline_trials':baseline_trials,'candidate_accounting':candidate_accounting,
        'baseline_accounting':baseline_accounting,'resource_metric':'full native child user+system CPU, including startup and descendants',
        'audit_revision':'generation_1_trusted_cpu_v1','target_sha256':hashlib.sha256((HIDDEN/'target.json').read_bytes()).hexdigest()}


def exception_result(error):
    reason = type(error).__name__+': '+str(error)
    if 'environment_error:' in reason:
        category = 'environment_error'
    elif 'measurement_error:' in reason:
        category = 'measurement_error'
    elif isinstance(error,(ValueError,subprocess.TimeoutExpired)) or any(
            label in reason for label in ['compile_failure:','execution_failure:']):
        category = 'invalid_submission'
    else:
        category = 'environment_error'
    return {'core_score':0.,'worst_family_score':0.,'runtime_score':0.,'passed':False,'valid':False,
            'reason':reason,'error_type':category,'infrastructure_error':category != 'invalid_submission'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.artifact)
    except Exception as error:
        result = exception_result(error)
    text = json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:
        args.output.write_text(text)
    print(text,end='')


if __name__ == '__main__':
    main()
