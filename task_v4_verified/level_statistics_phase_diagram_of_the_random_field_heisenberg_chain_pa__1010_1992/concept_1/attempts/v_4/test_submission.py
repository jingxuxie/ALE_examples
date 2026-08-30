import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import numpy as np
from data_io import read, metrics


def restrict():
    available = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, available[:4])
    resource.setrlimit(resource.RLIMIT_AS, (2048 * 1024 ** 2, 2048 * 1024 ** 2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--cases')
    args = parser.parse_args()
    original = read(args.cases) if args.cases else read(Path(os.environ['SRC']) / 'input' / 'validation.jsonl')
    selected = original if args.cases else original + original
    cases = [dict(case, id=f'case_{index:05d}') for index, case in enumerate(selected)]
    payload = json.dumps({'cases': [{'id': case['id'], 'L': 14, 'fields': case['fields']} for case in cases]}) + '\n'
    results = []
    for repeat in range(args.runs):
        started = time.monotonic()
        environment = dict(os.environ, PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
        process = subprocess.Popen([sys.executable, 'predict.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, env=environment, preexec_fn=restrict)
        ready = process.stdout.readline()
        assert ready == 'READY\n', (ready, process.stderr.read())
        startup = time.monotonic() - started
        assert startup <= 60, startup
        started = time.monotonic()
        try:
            stdout, stderr = process.communicate(payload, timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        inference = time.monotonic() - started
        assert inference <= 3, inference
        assert process.returncode == 0, stderr
        assert stdout.count('\n') == 1
        output = json.loads(stdout)
        assert set(output) == {'predictions'}
        estimates = {prediction['id']: prediction['f'] for prediction in output['predictions']}
        assert all(set(prediction) == {'id', 'f'} for prediction in output['predictions'])
        assert len(estimates) == len(cases) == len(output['predictions'])
        assert set(estimates) == {case['id'] for case in cases}
        assert all(isinstance(value, (float, int)) and not isinstance(value, bool)
                   and np.isfinite(value) and 0 <= value <= 1 for value in estimates.values())
        result = dict(startup_seconds=startup, inference_seconds=inference,
                      metrics=metrics(cases, np.array([estimates[case['id']] for case in cases])), stderr=stderr)
        print(json.dumps(result), flush=True)
        results.append(result)
    Path('runtime_test.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
