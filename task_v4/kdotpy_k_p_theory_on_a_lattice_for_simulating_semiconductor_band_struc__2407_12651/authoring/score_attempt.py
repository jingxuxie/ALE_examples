import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob('*')) if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--concept', type=int, required=True)
    parser.add_argument('--generation', type=int, default=1)
    options = parser.parse_args()
    concept = ROOT / ('concept_' + str(options.concept))
    name = 'v_' + str(options.generation)
    evidence = concept / 'attempts' / (name + '_evidence')
    launch = json.loads((evidence / 'launch.json').read_text())
    if 'end_epoch' not in launch:
        raise RuntimeError('fresh attempt is still active')
    if not launch.get('participant_unchanged'):
        raise RuntimeError('participant integrity changed during attempt')
    source = concept / 'attempts' / name
    before = hashes(source)
    snapshot = evidence / 'submission_snapshot'
    if snapshot.exists():
        raise RuntimeError('submission snapshot already exists; do not overwrite evidence')
    shutil.copytree(source, snapshot, symlinks=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    after = hashes(source)
    if before != after:
        raise RuntimeError('submission changed while snapshotting')
    raw = evidence / 'raw_evaluation.json'
    flag = '--submission-dir' if options.concept == 3 else '--submission'
    command = ['/usr/bin/python3', str(concept / 'evaluator' / 'evaluate.py'), flag, str(snapshot), '--output', str(raw)]
    started = time.monotonic()
    environment = os.environ.copy()
    environment.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    evaluation_cpus = sorted(os.sched_getaffinity(0))[-4:]
    def evaluation_affinity():
        os.sched_setaffinity(0, evaluation_cpus)
    with (evidence / 'evaluator.log').open('wb') as log:
        process = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT,
                                 timeout=900, preexec_fn=evaluation_affinity)
    if not raw.exists():
        report = {'core_score': 0., 'worst_family_score': 0., 'passed': False, 'valid': False,
                  'reason': 'evaluator could not read or execute the submitted artifact',
                  'evaluator_return_code': process.returncode}
    else:
        report = json.loads(raw.read_text())
    if options.concept == 3:
        accepted = bool(report.get('accepted', False))
        report.update(core_score=float(report.get('score', 0.)),
                      worst_family_score=float(report.get('score', 0.)), passed=accepted, valid=accepted)
        report['reason'] = ('valid continuum-certified topological design' if accepted else
                            report.get('error', report.get('evaluator_error', 'topology, robust flatness, or spectral gap condition failed')))
    report['runtime_seconds'] = report.get('runtime_seconds', report.get('elapsed_seconds', time.monotonic() - started))
    report['resource_score'] = report.get('resource_score', 1. if process.returncode == 0 else 0.)
    report['model'] = launch['model']
    report['fresh_agent_elapsed_seconds'] = launch['elapsed_seconds']
    report['fresh_agent_timed_out'] = launch['timed_out']
    report['submission_hashes'] = before
    report['evaluation_finished_epoch'] = time.time()
    report['evaluation_cpu_affinity'] = evaluation_cpus
    report['raw_evaluation'] = str(raw.relative_to(concept))
    (evidence / 'evaluation.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({key: report.get(key) for key in ('core_score', 'worst_family_score', 'passed', 'valid',
                                                     'reason', 'runtime_seconds', 'fresh_agent_elapsed_seconds')}, indent=2))


if __name__ == '__main__':
    main()
