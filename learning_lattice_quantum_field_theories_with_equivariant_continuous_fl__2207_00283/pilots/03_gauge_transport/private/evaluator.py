import argparse
import json
import math
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
OUTPUTS = ('vector', 'divergence', 'state', 'log_density', 'weight_gradient', 'initial_gradient')


def execute(submission, input_path, timeout):
    with tempfile.TemporaryDirectory(prefix='gauge-eval-') as temporary:
        work = Path(temporary)
        (work / 'input.npz').write_bytes(input_path.read_bytes())
        participant = PILOT / 'participant'
        aliases = []
        for source in (participant, submission):
            paths = {str(source)}
            if str(source).startswith('/srv/home/'):
                paths.add(str(source).replace('/srv/home/', '/home/', 1))
            elif str(source).startswith('/home/'):
                paths.add('/srv' + str(source))
            for target in sorted(paths):
                aliases.extend(('--ro-bind', str(source), target))
        command = ['bwrap', '--die-with-parent', '--unshare-all', '--new-session',
                   '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib',
                   '--ro-bind', '/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev',
                   '--tmpfs', '/tmp', '--ro-bind', str(participant), '/task',
                   '--ro-bind', str(submission), '/submission', '--bind', str(work), '/work',
                   *aliases,
                   '--chdir', '/submission', '--clearenv',
                   '--setenv', 'PATH', '/task/input/runtime/bin:/usr/bin:/bin',
                   '--setenv', 'HOME', '/tmp', '--setenv', 'PYTHONPATH', '/submission:/task/workspace',
                   '--setenv', 'JAX_ENABLE_X64', 'true', '--setenv', 'JAX_PLATFORMS', 'cpu',
                   '--setenv', 'OMP_NUM_THREADS', '8', '--setenv', 'OPENBLAS_NUM_THREADS', '2',
                   '--', '/usr/bin/time', '-f', '%M', '-o', '/work/peak_rss_kib.txt',
                   '/task/input/runtime/bin/python3.12', '/submission/solve.py',
                   '/work/input.npz', '/work/output.npz']
        started = time.monotonic()
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        elapsed = time.monotonic() - started
        metadata = {'seconds': elapsed, 'returncode': process.returncode, 'timeout': timed_out,
                    'stderr_tail': stderr.decode(errors='replace')[-2500:],
                    'stdout_tail': stdout.decode(errors='replace')[-1000:]}
        if (work / 'peak_rss_kib.txt').exists():
            lines = (work / 'peak_rss_kib.txt').read_text().strip().splitlines()
            if lines and lines[-1].isdigit():
                metadata['peak_rss_kib'] = int(lines[-1])
        result = {}
        if (work / 'output.npz').exists() and not timed_out and (work / 'output.npz').stat().st_size < 256 * 1024**2:
            try:
                with np.load(work / 'output.npz', allow_pickle=False) as archive:
                    result = {name: archive[name] for name in archive.files}
            except Exception as error:
                metadata['output_error'] = str(error)
        return result, metadata


def evaluate(submission, pool='initial', reference_check=False, timeout=240):
    folder = HERE / ('challenge_pool' if pool == 'challenge' else f'reference/{pool}')
    manifest = json.loads((folder / 'manifest.json').read_text())
    records, family_values, component_values = [], {}, {}
    for item in manifest:
        with np.load(folder / item['reference'], allow_pickle=False) as archive:
            reference = dict(archive)
        if reference_check:
            result, execution = reference, {'seconds': item['reference_seconds'], 'reference_replay': True}
        else:
            result, execution = execute(submission, folder / item['input'], timeout)
        scores, errors = {}, {}
        for name in OUTPUTS:
            value = result.get(name)
            target = reference[name]
            if value is None or value.shape != target.shape or not np.all(np.isfinite(value)):
                errors[name], scores[name] = None, 0.0
            else:
                error = float(np.sqrt(np.mean(np.abs(value - target)**2)))
                relative = error / item['weak_error'][name]
                errors[name] = relative
                scores[name] = 1.0 / (1.0 + 9.0 * math.sqrt(relative))
            component_values.setdefault(name, []).append(scores[name])
            family_values.setdefault(item['family'], []).append(scores[name])
        records.append({'id': item['id'], 'family': item['family'], 'scores': scores,
                        'normalized_errors': errors, 'mean_core': float(np.mean(list(scores.values()))),
                        'execution': execution})
        print(json.dumps({'id': item['id'], 'scores': scores, 'execution': execution}), flush=True)
    family_scores = {name: float(np.mean(values)) for name, values in family_values.items()}
    components = {name: float(np.mean(values)) for name, values in component_values.items()}
    return {'mean_core': float(np.mean([row['mean_core'] for row in records])),
            'worst_family': min(family_scores.values()), 'family_scores': family_scores,
            'component_scores': components, 'worst_component': min(components.values()),
            'pool': pool, 'reference_check': reference_check, 'cases': records,
            'score_definition': '1/(1+9*sqrt(RMS_error/RMS_identity_error)), equally weighted outputs/cases',
            'submission': str(submission) if submission else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--pool', default='initial')
    parser.add_argument('--reference-check', action='store_true')
    parser.add_argument('--timeout', type=float, default=240)
    options = parser.parse_args()
    if options.submission is None and not options.reference_check:
        parser.error('--submission is required without --reference-check')
    if options.submission:
        options.submission = options.submission.resolve()
    result = evaluate(options.submission, options.pool, options.reference_check, options.timeout)
    options.report.parent.mkdir(parents=True, exist_ok=True)
    options.report.write_text(json.dumps(result, indent=2))
    print(json.dumps({name: result[name] for name in ('mean_core', 'worst_family', 'component_scores')}), flush=True)
