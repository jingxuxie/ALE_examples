import argparse
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--concept', type=Path, required=True)
    parser.add_argument('--generation', type=int, default=1)
    parser.add_argument('--attempt')
    parser.add_argument('--wait-seconds', type=int, default=5400)
    args = parser.parse_args()
    concept = args.concept.resolve()
    attempt = args.attempt or f'v_{args.generation}'
    metadata_path = concept / 'attempts' / f'{attempt}.run.json'
    deadline = time.monotonic() + args.wait_seconds
    while time.monotonic() < deadline:
        try:
            metadata = json.loads(metadata_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            metadata = {}
        if 'finished_utc' in metadata:
            break
        time.sleep(10)
    else:
        raise TimeoutError('fresh attempt did not finish within watcher window')
    if not metadata.get('participant_unchanged') or not metadata.get('evaluator_unchanged'):
        raise RuntimeError('frozen participant or evaluator changed during the attempt')
    environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    command = ['python3', str(concept / 'evaluator' / 'evaluate.py'), '--submission',
               str(concept / 'attempts' / attempt), '--output', str(concept / 'attempts' / f'{attempt}.score.json')]
    with (concept / 'attempts' / f'{attempt}.evaluation.log').open('wb') as log:
        completed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   env=environment, timeout=1500)
    print(json.dumps({'concept': concept.name, 'attempt': attempt, 'evaluator_returncode': completed.returncode}), flush=True)


if __name__ == '__main__':
    main()
