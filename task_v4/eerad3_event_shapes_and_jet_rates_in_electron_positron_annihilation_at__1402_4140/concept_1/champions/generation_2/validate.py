import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

import numpy as np


ROOT = Path(__file__).resolve().parent


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def run_prediction(source, destination):
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.monotonic()
    subprocess.run([sys.executable, str(ROOT / 'predict.py'), str(source), str(destination)],
                   check=True, timeout=90, preexec_fn=limits, cwd=destination.parent)
    elapsed = time.monotonic() - start
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
    with np.load(destination) as result:
        assert result.files == ['log_weight']
        prediction = result['log_weight']
    assert prediction.dtype == np.float64
    assert prediction.ndim == 1 and np.isfinite(prediction).all()
    return prediction, cpu, elapsed


def metrics(prediction, label, family):
    assert prediction.shape == label.shape
    error = prediction - label
    return {
        'log_rmse': float(np.sqrt(np.mean(error**2))),
        'max_abs_log_error': float(np.max(np.abs(error))),
        'fraction_within_15_percent': float(np.mean(np.abs(np.expm1(error)) <= 0.15)),
        'family_log_rmse': {
            str(int(value)): float(np.sqrt(np.mean(error[family == value]**2)))
            for value in np.unique(family)
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('labelled', nargs='+', type=Path)
    parser.add_argument('--benchmark', type=int, default=0)
    arguments = parser.parse_args()
    arguments.labelled = [source.resolve() for source in arguments.labelled]
    with tempfile.TemporaryDirectory(prefix='validation_', dir=ROOT) as work:
        work = Path(work)
        for source in arguments.labelled:
            with np.load(source) as data:
                label, family = data['log_weight'], data['family']
            prediction, cpu, wall = run_prediction(source, work / 'prediction.npz')
            report = metrics(prediction, label, family)
            report.update(source=str(source), events=len(label), cpu_seconds=cpu, wall_seconds=wall)
            print(json.dumps(report, sort_keys=True), flush=True)
        if arguments.benchmark:
            with np.load(arguments.labelled[0]) as data:
                indices = np.arange(arguments.benchmark) % len(data['p'])
                np.random.default_rng(42).shuffle(indices)
                momentum = data['p'][indices].copy()
                label, family = data['log_weight'][indices], data['family'][indices]
                invariants = data['s'][indices]
            angle = np.random.default_rng(43).uniform(-np.pi, np.pi, len(momentum))
            cosine, sine = np.cos(angle)[:, None], np.sin(angle)[:, None]
            original_x, original_y = momentum[:, :, 0].copy(), momentum[:, :, 1].copy()
            momentum[:, :, 0] = cosine * original_x - sine * original_y
            momentum[:, :, 1] = sine * original_x + cosine * original_y
            for compressed in (False, True):
                source = work / 'query.npz'
                writer = np.savez_compressed if compressed else np.savez
                writer(source, p=momentum, s=invariants, family=family)
                prediction, cpu, wall = run_prediction(source, work / 'prediction.npz')
                report = metrics(prediction, label, family)
                report.update(events=len(label), compressed=compressed,
                              cpu_seconds=cpu, wall_seconds=wall)
                print(json.dumps(report, sort_keys=True), flush=True)
                assert report['log_rmse'] <= 0.05
                assert max(report['family_log_rmse'].values()) <= 0.08
                assert report['fraction_within_15_percent'] >= 0.95
                assert cpu <= 2.4


if __name__ == '__main__':
    main()
