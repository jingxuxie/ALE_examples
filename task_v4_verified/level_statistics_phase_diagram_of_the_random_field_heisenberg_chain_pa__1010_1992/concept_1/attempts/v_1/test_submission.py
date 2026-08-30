import argparse
import json
import math
import os
from pathlib import Path
import resource
import selectors
import subprocess
import sys
import time


def limits():
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    resource.setrlimit(resource.RLIMIT_AS, (2048 * 1024**2, 2048 * 1024**2))


def read_line(process, timeout):
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    if not selector.select(timeout):
        process.kill()
        raise TimeoutError('Submission did not respond in time')
    selector.close()
    line = process.stdout.readline()
    if not line:
        raise RuntimeError(process.stderr.read().decode())
    return line


def score(records, result):
    predictions = result['predictions']
    assert len(predictions) == len(records)
    lookup = {prediction['id']: prediction['f'] for prediction in predictions}
    assert len(lookup) == len(records)
    assert all(isinstance(value, (float, int)) and math.isfinite(value) and 0 <= value <= 1
               for value in lookup.values())
    errors = [(record, (record['f'] - lookup[record['id']]) ** 2) for record in records]
    metrics = {'overall_rmse': math.sqrt(sum(error for record, error in errors) / len(errors))}
    for attribute in ('family', 'L'):
        metrics['by_' + attribute] = {}
        for value in sorted({record[attribute] for record in records}):
            selected = [error for record, error in errors if record[attribute] == value]
            metrics['by_' + attribute][value] = math.sqrt(sum(selected) / len(selected))
    metrics['worst_family_rmse'] = max(metrics['by_family'].values())
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='../../participant/input/validation.jsonl')
    parser.add_argument('--repeats', default=5, type=int)
    parser.add_argument('--report', default='validation_report.json')
    parser.add_argument('--plain', action='store_true')
    args = parser.parse_args()
    records = [json.loads(line) for line in Path(args.data).read_text().splitlines()]
    payload = {'cases': [{key: record[key] for key in ('id', 'L', 'fields')} for record in records]}
    encoded = (json.dumps(payload) + '\n').encode()
    runs = []
    for repeat in range(args.repeats):
        launched = time.perf_counter()
        command = [sys.executable, 'predict.py']
        if not args.plain:
            command.append('--diagnostics')
        process = subprocess.Popen(command,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, preexec_fn=limits)
        assert read_line(process, 60).strip() == b'READY'
        ready = time.perf_counter()
        process.stdin.write(encoded)
        process.stdin.flush()
        result = json.loads(read_line(process, 3))
        responded = time.perf_counter()
        process.wait(timeout=10)
        exited = time.perf_counter()
        diagnostics = process.stderr.read().decode()
        assert process.returncode == 0, diagnostics
        metrics = score(records, result)
        metrics.update(startup_seconds=ready - launched, wall_seconds=responded - ready,
                       exit_seconds=exited - ready,
                       diagnostics=json.loads(diagnostics) if diagnostics else None)
        metrics['passes'] = (metrics['overall_rmse'] <= 0.035
                             and metrics['worst_family_rmse'] <= 0.050
                             and metrics['wall_seconds'] < 3
                             and metrics['startup_seconds'] < 60)
        runs.append(metrics)
        print(json.dumps(metrics), flush=True)
    report = {'response_clock': 'Complete flushed response; exit_seconds is a separate diagnostic',
              'runs': runs}
    Path(args.report).write_text(json.dumps(report, indent=2) + '\n')
    assert all(run['passes'] for run in runs), 'One or more resource/accuracy checks failed'


if __name__ == '__main__':
    main()
