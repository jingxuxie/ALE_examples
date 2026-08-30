import argparse
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
import time

ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / 'evaluator/hidden'
sys.path.insert(0,str(HIDDEN))
from generate import serialize
from oracle import check

FLAGS = ['-O2','-fno-fast-math','-ffp-contract=off','-ffixed-line-length-none','-std=legacy']
SOURCES = ['kinematics.f','phaseee.f','eerad3lib.f']


def isolated_command(directory, command, trusted=False):
    if shutil.which('bwrap') is None:
        raise RuntimeError('environment_error: bubblewrap is required; no unsandboxed fallback')
    arguments = ['bwrap','--unshare-all','--die-with-parent','--new-session']
    for path in ['/usr','/bin','/lib','/lib64','/etc/alternatives','/etc/ld.so.cache']:
        arguments += ['--ro-bind',path,path]
    if trusted:
        arguments += ['--ro-bind',str(ROOT/'evaluator/trusted_runner.py'),'/trusted_runner.py']
    return arguments + ['--proc','/proc','--dev','/dev','--tmpfs','/tmp',
        '--bind',str(directory),'/work','--chdir','/work','--clearenv',
        '--setenv','PATH','/usr/bin:/bin','--setenv','LANG','C',
        '--setenv','OMP_NUM_THREADS','1','--'] + command


def limits(cpu=None):
    if cpu is not None:
        os.sched_setaffinity(0, {cpu})
    resource.setrlimit(resource.RLIMIT_CPU,(35,35))
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def build(artifact,directory):
    artifact = Path(artifact).resolve()
    for filename in SOURCES:
        source = artifact / filename
        if not source.is_file() or source.is_symlink() or source.stat().st_size > 512*1024:
            raise ValueError('Missing, symlinked, or oversized source: '+filename)
        shutil.copyfile(source,Path(directory)/filename)
    shutil.copyfile(HIDDEN/'driver.f90',Path(directory)/'driver.f90')
    result = subprocess.run(isolated_command(directory,['gfortran',*FLAGS,*SOURCES,'driver.f90','-o','runner']),cwd=directory,
        capture_output=True,text=True,timeout=45,preexec_fn=limits)
    if result.returncode:
        if 'bwrap:' in result.stderr:
            raise RuntimeError('environment_error: isolated compiler could not initialize: '+result.stderr[-1000:])
        raise RuntimeError('compile_failure: '+result.stderr[-1500:])
    return Path(directory)/'runner'


def run(executable,cases,repeats=300,cpu=None,timing_audit=None):
    result = subprocess.run(isolated_command(executable.parent,['/usr/bin/python3','-I','/trusted_runner.py'],trusted=True),input=serialize(cases,repeats),cwd=executable.parent,
        capture_output=True,text=True,timeout=40,preexec_fn=partial(limits, cpu),
        env={'PATH':'/usr/bin:/bin','LANG':'C','OMP_NUM_THREADS':'1'})
    if result.returncode:
        if 'bwrap:' in result.stderr:
            raise RuntimeError('environment_error: isolated runner could not initialize: '+result.stderr[-1000:])
        raise RuntimeError('execution_failure: '+str(result.returncode)+' '+result.stderr[-500:])
    trusted = json.loads(result.stdout)
    if trusted['returncode']:
        raise RuntimeError('execution_failure: '+str(trusted['returncode'])+' '+trusted['stderr'])
    lines = trusted['stdout'].splitlines()
    if len(lines) != len(cases)+1 or not lines[-1].startswith('TIME '):
        raise ValueError('Malformed output record count or timing trailer')
    records = [[float(token) for token in line.split()] for line in lines[:-1]]
    native_duration = float(lines[-1].split()[1])
    duration = float(trusted['cpu_seconds'])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid CPU time')
    if timing_audit is not None:
        timing_audit.update(trusted_cpu_seconds=duration, untrusted_native_cpu_seconds=native_duration)
    return records,duration


def measure(executable,cases,repeats,trials=3):
    timings = []
    records = None
    for trial in range(trials):
        records,duration = run(executable,cases,repeats)
        timings.append(duration)
    return records,statistics.median(timings),timings


def measure_paired(executable, baseline, cases, target):
    import numpy as np
    cpu = min(os.sched_getaffinity(0))
    repeats = target['timing_repeats']
    minimum = target['minimum_baseline_cpu_seconds']
    for calibration in range(4):
        unused, duration = run(baseline, cases, repeats, cpu)
        if duration >= minimum:
            break
        repeats = max(repeats + 1, math.ceil(repeats * minimum * 1.15 / duration))
        if repeats > target['maximum_timing_repeats']:
            raise RuntimeError('environment_error: baseline timing cannot reach minimum duration')
    else:
        raise RuntimeError('environment_error: baseline timing calibration did not stabilize')
    warm_records, unused = run(executable, cases, 1, cpu)
    pairs, records = [], None
    for trial in range(target['timing_pairs']):
        order = ['baseline', 'candidate'] if trial % 2 == 0 else ['candidate', 'baseline']
        pair = {'order': order}
        for name in order:
            audit = {}
            current, duration = run(baseline if name == 'baseline' else executable,
                                    cases, repeats, cpu, audit)
            pair[name] = duration
            pair[name + '_audit'] = audit
            if name == 'candidate':
                if not np.array_equal(current, warm_records, equal_nan=True):
                    raise ValueError('Candidate results change across identical repeated executions')
                records = current
        if pair['baseline'] < minimum:
            raise RuntimeError('environment_error: paired baseline trial below minimum CPU duration; rerun evaluation')
        pair['ratio'] = pair['candidate'] / pair['baseline']
        pairs.append(pair)
    baseline_trials = [pair['baseline'] for pair in pairs]
    candidate_trials = [pair['candidate'] for pair in pairs]
    return records, {'candidate_cpu_seconds': statistics.median(candidate_trials),
                     'baseline_cpu_seconds': statistics.median(baseline_trials),
                     'candidate_trials': candidate_trials, 'baseline_trials': baseline_trials,
                     'runtime_ratio': statistics.median(pair['ratio'] for pair in pairs),
                     'paired_trials': pairs, 'timing_cpu': cpu, 'effective_timing_repeats': repeats,
                     'timing_method': 'median of five alternating same-CPU trusted whole-process CPU ratios',
                     'cpu_accounting': 'read-only in-namespace subreaper; waitpid and RUSAGE_CHILDREN; native CPU_TIME ignored'}


def evaluate(artifact):
    target = json.loads((HIDDEN/'target.json').read_text())
    for filename,key in [('cases.json','case_sha256'),('references.json','reference_sha256')]:
        if hashlib.sha256((HIDDEN/filename).read_bytes()).hexdigest() != target[key]:
            raise RuntimeError('environment_error: frozen evaluation data hash mismatch')
    for filename, expected in target.get('required_sha256', {}).items():
        if hashlib.sha256((ROOT/filename).read_bytes()).hexdigest() != expected:
            raise RuntimeError('environment_error: fixed evaluator input hash mismatch: ' + filename)
    cases = json.loads((HIDDEN/'cases.json').read_text())
    references = json.loads((HIDDEN/'references.json').read_text())
    if len(cases) != len(references) or len({case['id'] for case in cases}) != len(cases):
        raise RuntimeError('environment_error: invalid case/reference count or duplicate IDs')
    with tempfile.TemporaryDirectory(prefix='eerad3-eval-') as directory:
        candidate_dir = Path(directory)/'candidate'
        baseline_dir = Path(directory)/'baseline'
        candidate_dir.mkdir()
        baseline_dir.mkdir()
        executable = build(artifact,candidate_dir)
        baseline = build(HIDDEN/'pristine',baseline_dir)
        if target.get('timing_pairs'):
            records, timing = measure_paired(executable, baseline, cases, target)
        else:
            baseline_records,baseline_time,baseline_trials = measure(baseline,cases,target['timing_repeats'])
            records,candidate_time,candidate_trials = measure(executable,cases,target['timing_repeats'])
            timing = {'candidate_cpu_seconds': candidate_time, 'baseline_cpu_seconds': baseline_time,
                      'candidate_trials': candidate_trials, 'baseline_trials': baseline_trials,
                      'runtime_ratio': candidate_time / baseline_time}
    families = {}
    failures = []
    record_by_id = {}
    for case,reference,record in zip(cases,references,records):
        errors = check(case,reference,record,target)
        record_by_id[case['id']] = record
        if case.get('parent') and not errors:
            import numpy as np
            original = np.array(record_by_id[case['parent']][25:37]).reshape((4,3),order='F').T
            transformed = original.copy()
            transformed[:,:3] = transformed[:,:3]@np.array(case['transform']).T
            transformed *= case['scale_factor']
            actual = np.array(record[25:37]).reshape((4,3),order='F').T
            actual = actual[np.array(case['slots'])-1]
            if np.max(np.abs(actual-transformed))/sum(vector[3] for vector in case['p']) > target['momentum_atol']:
                errors.append('metamorphic_covariance')
        families.setdefault(case['family'],[]).append(not errors)
        if errors:
            failures.append({'id':case['id'],'checks':errors})
    family_scores = {family:sum(results)/len(results) for family,results in families.items()}
    core = sum(family_scores.values())/len(family_scores)
    worst = min(family_scores.values())
    ratio = timing['runtime_ratio']
    runtime = min(1.,target['runtime_ratio_limit']/ratio)
    passed = not failures and ratio <= target['runtime_ratio_limit']
    reason = 'all physical, oracle, metamorphic and resource checks passed' if passed else (
        f'{len(failures)} cases fail numerical/physical checks' if failures else 'runtime budget exceeded')
    return {'core_score':core,'worst_family_score':worst,'runtime_score':runtime,'passed':passed,'reason':reason,
        'family_scores':family_scores,'failures':failures[:24],'failed_case_count':len(failures),
        **timing, 'runtime_ratio_limit':target['runtime_ratio_limit'],
        'target_sha256':hashlib.sha256((HIDDEN/'target.json').read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.artifact)
    except Exception as error:
        result = {'core_score':0.,'worst_family_score':0.,'runtime_score':0.,'passed':False,
                  'reason':type(error).__name__+': '+str(error)}
    text = json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:
        args.output.write_text(text)
    print(text,end='')


if __name__ == '__main__':
    main()
