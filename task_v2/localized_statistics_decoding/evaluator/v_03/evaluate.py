import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np


HERE = Path(__file__).resolve().parent
PUBLIC = HERE.parents[1] / 'participant/v_03/input'


def grade(data, labels, prediction):
    frame_count, mechanism_count = data['syndrome'].shape[0], data['H'].shape[1]
    if prediction is None or prediction.ndim != 2 or prediction.shape[1] != mechanism_count:
        return {'score': 0.0, 'syndrome_fraction': 0.0, 'logical_recovery_fraction': 0.0,
                'complete_shape': False}
    available = min(frame_count, prediction.shape[0])
    prediction = prediction[:available]
    binary_rows = np.isin(prediction, [0, 1]).all(axis=1)
    correction = np.where(np.isfinite(prediction), prediction, 0).astype(np.uint8)
    valid = binary_rows & (((correction @ data['H'].T) % 2) == data['syndrome'][:available]).all(axis=1)
    recovered = valid & (((correction @ data['L'].T) % 2) == labels['logical_target'][:available]).all(axis=1)
    valid_fraction = float(valid.sum()) / frame_count
    recovery_fraction = float(recovered.sum()) / frame_count
    score = 0.15 * valid_fraction + 0.85 * min(1.0, recovery_fraction / 0.85)
    return {'score': round(score, 6), 'syndrome_fraction': round(valid_fraction, 6),
            'logical_recovery_fraction': round(recovery_fraction, 6),
            'complete_shape': prediction.shape == (frame_count, mechanism_count)}


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (65, 65))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if hasattr(os, 'sched_setaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def evaluate(submission):
    if not (submission / 'solve.py').is_file():
        return {'passed': False, 'score': 0.0, 'reason': 'Missing executable solve.py', 'cases': []}
    environment = dict(os.environ)
    environment.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', OMP_THREAD_LIMIT='1',
                       MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    results = []
    for path in sorted((HERE / 'hidden').glob('heldout_*.npz')):
        if path.stem.endswith('_labels'):
            continue
        data = np.load(path, allow_pickle=False)
        labels = np.load(path.with_name(path.stem + '_labels.npz'), allow_pickle=False)
        prediction = None
        timed_out = False
        error_message = ''
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix='recovery-evaluation-') as temporary:
            temporary = Path(temporary)
            input_path = temporary / 'batch.npz'
            output_path = temporary / 'prediction.npz'
            input_path.write_bytes(path.read_bytes())
            try:
                process = subprocess.Popen([sys.executable, str(submission / 'solve.py'),
                                            '--input', str(input_path), '--output', str(output_path)],
                                           cwd=submission, env=environment, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, preexec_fn=limits, start_new_session=True)
                try:
                    _, standard_error = process.communicate(timeout=60)
                    if process.returncode:
                        error_message = f'process_exit={process.returncode}: ' + standard_error.decode(errors='replace')[-1000:]
                except subprocess.TimeoutExpired:
                    timed_out = True
                    error_message = '60-second inference timeout'
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
            except Exception as error:
                error_message = f'{type(error).__name__}: {error}'
            try:
                if output_path.is_file() and output_path.stat().st_size < 64 * 1024 * 1024:
                    prediction = np.load(output_path, allow_pickle=False)['correction']
            except Exception as error:
                error_message += f'; invalid output: {type(error).__name__}: {error}'
        metrics = grade(data, labels, prediction)
        if timed_out:
            metrics['score'] = 0.0
        results.append({'id': path.stem, **metrics, 'timed_out': timed_out,
                        'seconds': round(time.monotonic() - started, 3), 'error': error_message})
    if len(results) != 3:
        raise ValueError('Expected three complete hidden batches')
    artifacts = {'diagnosis': (submission / 'diagnosis.md').is_file()}
    for name in ('validation_small', 'validation_large'):
        try:
            data = np.load(PUBLIC / f'{name}.npz', allow_pickle=False)
            labels = np.load(PUBLIC / f'{name}_labels.npz', allow_pickle=False)
            prediction = np.load(submission / f'{name}_predictions.npz', allow_pickle=False)['correction']
            metrics = grade(data, labels, prediction)
            artifacts[name] = metrics['syndrome_fraction'] == 1.0 and metrics['logical_recovery_fraction'] >= 0.85
        except Exception:
            artifacts[name] = False
    score = sum(result['score'] for result in results) / len(results)
    passed = all(result['syndrome_fraction'] == 1.0 and result['logical_recovery_fraction'] >= 0.85
                 and result['complete_shape'] and not result['timed_out'] for result in results) and all(artifacts.values())
    failed = [result['id'] for result in results if result['logical_recovery_fraction'] < 0.85 or result['timed_out']]
    reason = 'Logical recovery and deliverables pass' if passed else (
        'Logical recovery shortfall: ' + ', '.join(failed) if failed else 'Missing or inadequate public deliverables')
    return {'passed': bool(passed), 'score': round(score, 6), 'reason': reason, 'cases': results, 'artifacts': artifacts}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', required=True)
    arguments = parser.parse_args()
    try:
        result = evaluate(Path(arguments.submission).resolve())
    except Exception as error:
        result = {'passed': False, 'score': 0.0, 'reason': f'Evaluator error: {type(error).__name__}: {error}'}
    print(json.dumps(result, separators=(',', ':'), allow_nan=False))
