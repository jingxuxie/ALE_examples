import argparse
import functools
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'private'))
sys.path.insert(0, str(ROOT / 'private/reference'))

from evaluation_sandbox import restrict_solver
from metrics import WEIGHTS, losses, score_components


def limit_process(submission_directory, staged_workdir):
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 ** 2, 16 * 1024 ** 2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    restrict_solver(submission_directory, staged_workdir, seconds=120, gibibytes=3)


def load_output(path, query_count, heldout_count):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024 ** 2:
        raise ValueError('Missing, nonregular, or oversized output')
    expected = {'structural_identifiable': query_count, 'calibration_identifiable': query_count,
                'query_log_estimate': query_count, 'holdout_mean': heldout_count}
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if sorted(member.filename for member in members) != sorted(key + '.npy' for key in expected):
            raise ValueError('Output must contain exactly the four documented arrays')
        if sum(member.file_size for member in members) > 16 * 1024 ** 2:
            raise ValueError('Uncompressed output too large')
        for key, length in expected.items():
            with archive.open(key + '.npy') as stream:
                version = np.lib.format.read_magic(stream)
                if version == (1, 0):
                    shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
                elif version == (2, 0):
                    shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
                else:
                    raise ValueError('Unsupported NPY version')
                if shape != (length,) or dtype.hasobject or dtype.kind not in 'fiub':
                    raise ValueError('Invalid shape or dtype for ' + key)
    with np.load(path, allow_pickle=False) as archive:
        output = {key: np.asarray(archive[key], dtype=float) for key in expected}
    for key, values in output.items():
        if not np.all(np.isfinite(values)):
            raise ValueError('Nonfinite output: ' + key)
        if key.endswith('identifiable') and np.any((values < 0) | (values > 1)):
            raise ValueError('Identification probabilities must be in [0,1]')
        if key == 'holdout_mean' and np.any(np.abs(values) > 1):
            raise ValueError('Means must be in [-1,1]')
    return output


def run_case(source_submission, input_path, query_count, heldout_count, telemetry=None):
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='gateset-eval-') as temporary:
        staged_workdir = Path(temporary)
        submission = staged_workdir / 'submission' / 'solver.py'
        submission.parent.mkdir()
        shutil.copyfile(source_submission, submission)
        shutil.copyfile(input_path, staged_workdir / 'input.npz')
        environment = {'PATH': '/usr/bin:/bin', 'HOME': str(staged_workdir),
                       'TMPDIR': str(staged_workdir), 'LC_ALL': 'C.UTF-8',
                       'NUMBA_CACHE_DIR': str(staged_workdir / 'cache'),
                       'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
                       'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1',
                       'PYTHONHASHSEED': '0'}
        with (staged_workdir / 'stdout.log').open('wb') as stdout, \
                (staged_workdir / 'stderr.log').open('wb') as stderr:
            command = ['/usr/bin/python3', '-I', '-B', str(submission), 'input.npz', 'output.npz']
            if telemetry is not None:
                command = ['/usr/bin/time', '-f', '%M', '-o', 'peak_rss.txt'] + command
            process = subprocess.Popen(
                command,
                cwd=staged_workdir, env=environment, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, close_fds=True, start_new_session=True,
                preexec_fn=functools.partial(limit_process, submission.parent, staged_workdir))
            try:
                process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise TimeoutError('Exceeded 120 seconds')
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        if process.returncode:
            diagnostic = (staged_workdir / 'stderr.log').read_bytes()[:3000].decode('utf-8', 'replace')
            raise RuntimeError(f'Exit code {process.returncode}: {diagnostic}')
        output = load_output(staged_workdir / 'output.npz', query_count, heldout_count)
        if telemetry is not None:
            profile = staged_workdir / 'peak_rss.txt'
            if profile.is_symlink() or not profile.is_file() or profile.stat().st_size > 64:
                raise ValueError('Missing or invalid runtime memory profile')
            text = profile.read_text().strip()
            if not text.isdigit():
                raise ValueError('Invalid peak memory measurement')
            telemetry['peak_memory_mib'] = int(text) / 1024
    return output, time.monotonic() - started


def evaluate(submission, pool):
    started = time.monotonic()
    directory = ROOT / 'private' / ('reference/core' if pool == 'core' else 'challenge_pool')
    manifest = json.loads((directory / 'manifest.json').read_text())
    cases = []
    for entry in manifest['cases']:
        case_started = time.monotonic()
        case_directory = directory / entry['case_id']
        result = {'case_id': entry['case_id'], 'family': entry['family']}
        for filename, hash_key in (('input.npz', 'input_sha256'), ('oracle.npz', 'oracle_sha256')):
            actual_hash = hashlib.sha256((case_directory / filename).read_bytes()).hexdigest()
            if actual_hash != entry[hash_key]:
                raise ValueError('Precomputed case integrity failure: ' + entry['case_id'])
        with np.load(case_directory / 'oracle.npz', allow_pickle=False) as archive:
            oracle = {key: archive[key] for key in archive.files}
        baseline = dict(zip(WEIGHTS, oracle['baseline_loss'].tolist()))
        reference = dict(zip(WEIGHTS, oracle['reference_loss'].tolist()))
        try:
            telemetry = {}
            output, runtime = run_case(submission, case_directory / 'input.npz',
                                       entry['queries'], entry['holdout_experiments'], telemetry)
            actual = losses(output, oracle)
            if not all(np.isfinite(value) for value in actual.values()):
                raise ValueError('Nonfinite loss from numerically extreme output')
            components, score = score_components(actual, baseline, reference)
            result.update(status='ok', score=score, components=components, losses=actual,
                          runtime=runtime, prediction_rmse=float(np.sqrt(actual['heldout_prediction'])),
                          **telemetry)
        except Exception as exception:
            result.update(status='error', error=f'{type(exception).__name__}: {exception}',
                          score=0.0, components={key: 0.0 for key in WEIGHTS},
                          runtime=time.monotonic() - case_started)
        result.update(baseline_losses=baseline, reference_losses=reference,
                      qubits=entry['qubits'], parameters=entry['parameters'],
                      structural_rank=entry['structural_rank'],
                      calibration_rank=entry['calibration_rank'])
        cases.append(result)
    families = {}
    for family in sorted({case['family'] for case in cases}):
        members = [case for case in cases if case['family'] == family]
        families[family] = {'mean': float(np.mean([case['score'] for case in members])),
                            'count': len(members),
                            'components': {key: float(np.mean([case['components'][key] for case in members]))
                                           for key in WEIGHTS},
                            'runtime': sum(case['runtime'] for case in members)}
    mean = float(np.mean([case['score'] for case in cases]))
    return {'schema_version': 1, 'pool': pool, 'submission': str(submission),
            'mean_core': mean if pool == 'core' else None,
            'mean_challenge': mean if pool == 'challenge' else None,
            'mean': mean, 'worst_family': min(family['mean'] for family in families.values()),
            'peak_memory_mib': max((case.get('peak_memory_mib', 0) for case in cases), default=0),
            'families': families, 'cases': cases, 'runtime': sum(case['runtime'] for case in cases),
            'wall_seconds': time.monotonic() - started, 'component_weights': WEIGHTS,
            'scoring': 'scale/(scale+loss), scale=weak_loss/4+12*reference_loss; no clipping',
            'limits': {'wall_seconds_per_case': 120, 'address_space_gib': 3,
                       'file_size_mib': 16, 'open_files': 64, 'threads': 1,
                       'filesystem': 'Landlock; staged solver/input and system runtime only'}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--pool', choices=('core', 'challenge'), default='core')
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    submission = arguments.submission.resolve(strict=True)
    if not submission.is_file() or submission.stat().st_size > 2 * 1024 ** 2:
        raise SystemExit('Submission must be a Python file smaller than 2 MiB')
    report = evaluate(submission, arguments.pool)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: report[key] for key in ('pool', 'mean_core', 'mean_challenge',
                                                  'worst_family', 'runtime')}))


if __name__ == '__main__':
    main()
