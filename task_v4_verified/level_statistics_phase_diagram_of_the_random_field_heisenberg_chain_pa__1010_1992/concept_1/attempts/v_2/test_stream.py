import argparse
import json
import os
from pathlib import Path
import resource
import selectors
import subprocess
import sys
import time


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2048 * 1024 ** 2, 2048 * 1024 ** 2))
    available = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, available[:4])


def read_line(process, timeout):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        if not selector.select(timeout):
            process.kill()
            raise TimeoutError('Prediction process exceeded time limit')
    return process.stdout.readline()


def metrics(cases, output):
    assert set(output) == {'predictions'}
    assert all(set(entry) == {'id', 'f'} for entry in output['predictions'])
    predictions = {entry['id']: entry['f'] for entry in output['predictions']}
    assert len(predictions) == len(cases) == len(output['predictions'])
    assert all(0 <= value <= 1 for value in predictions.values())
    errors = [(case, (predictions[case['id']] - case['f']) ** 2) for case in cases]
    result = {'overall_rmse': (sum(error for case, error in errors) / len(errors)) ** 0.5}
    for field in ('family', 'L'):
        result['by_' + field] = {}
        for group in sorted({case[field] for case in cases}):
            selected = [error for case, error in errors if case[field] == group]
            result['by_' + field][str(group)] = (sum(selected) / len(selected)) ** 0.5
    result['worst_family_rmse'] = max(result['by_family'].values())
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='../../participant/input/validation.jsonl')
    parser.add_argument('--output', default='validation_result.json')
    parser.add_argument('--repeat', type=int, default=1)
    arguments = parser.parse_args()
    cases = [json.loads(line) for line in Path(arguments.data).read_text().splitlines()]
    payload = json.dumps({'cases': [{key: case[key] for key in ('id', 'L', 'fields')} for case in cases]}) + '\n'
    results = []
    for repeat in range(arguments.repeat):
        started = time.monotonic()
        process = subprocess.Popen([sys.executable, 'predict.py'], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, preexec_fn=limits)
        ready = read_line(process, 60)
        if ready != 'READY\n':
            raise RuntimeError((ready, process.stderr.read()))
        startup_seconds = time.monotonic() - started
        started = time.monotonic()
        process.stdin.write(payload)
        process.stdin.flush()
        output = json.loads(read_line(process, 3))
        elapsed = time.monotonic() - started
        process.wait(timeout=max(0.01, 3 - elapsed))
        assert process.stdout.read() == ''
        result = metrics(cases, output)
        result.update(startup_seconds=startup_seconds, response_seconds=elapsed,
                      total_inference_seconds=time.monotonic() - started, exit_code=process.returncode)
        result['passed'] = (result['overall_rmse'] <= 0.035 and result['worst_family_rmse'] <= 0.050
                            and result['total_inference_seconds'] <= 3 and process.returncode == 0)
        print(json.dumps(result, indent=2), flush=True)
        results.append(result)
        Path(arguments.output).write_text(json.dumps(results, indent=2) + '\n')
        Path(arguments.output).with_suffix('.predictions.json').write_text(json.dumps(output) + '\n')


if __name__ == '__main__':
    main()
