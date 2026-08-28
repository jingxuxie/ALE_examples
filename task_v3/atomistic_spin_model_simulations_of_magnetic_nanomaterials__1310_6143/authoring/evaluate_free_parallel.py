import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'pilots' / 'free_energy'
sys.path.insert(0, str(PILOT / 'private'))
import evaluator as grader


def evaluate_case(arguments):
    entry, submission = arguments
    case_path = PILOT / entry['path']
    assert hashlib.sha256(case_path.read_bytes()).hexdigest() == entry['sha256']
    case = json.loads(case_path.read_text())
    reference = json.loads((PILOT / 'private' / 'reference' / 'results' / (entry['id'] + '.json')).read_text())
    item = dict(id=entry['id'], family=entry['family'], score=0.0, runtime_seconds=0.0)
    start = time.monotonic()
    try:
        prediction, elapsed = grader.run_submission(Path(submission).resolve(), case_path, case)
        item['score'], item['components'] = grader.score(case, reference, prediction)
        item.update(runtime_seconds=elapsed, status='ok')
    except Exception as error:
        item.update(runtime_seconds=time.monotonic() - start, status='failed', error=str(error))
    return item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', default='initial', choices=['initial', 'challenge'])
    parser.add_argument('--jobs', type=int, default=6)
    parser.add_argument('--wait-for-attempt', action='store_true')
    arguments = parser.parse_args()
    if arguments.wait_for_attempt:
        metadata = ROOT / 'authoring' / 'runs' / 'initial' / 'free_energy.json'
        while not metadata.exists() or json.loads(metadata.read_text())['status'] == 'running':
            time.sleep(5)
    manifest = json.loads((PILOT / 'private' / 'challenge_pool' / 'manifest.json').read_text())
    entries = manifest[arguments.split]
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=arguments.jobs, mp_context=multiprocessing.get_context('spawn')) as pool:
        results = list(pool.map(evaluate_case, [(entry, str(PILOT / 'attempt')) for entry in entries]))
    report = grader.summarize(results, arguments.split)
    report.update(parallel_wall_seconds=time.monotonic() - started, parallel_jobs=arguments.jobs,
        evaluator_sha256=hashlib.sha256((PILOT / 'private' / 'evaluator.py').read_bytes()).hexdigest(),
        protocol='Unmodified frozen per-case executor/scorer; independent cases evaluated concurrently.')
    destination = ROOT / 'authoring' / 'runs' / 'initial' / ('free_energy.' + arguments.split + '.parallel.scores.json')
    destination.write_text(json.dumps(report, indent=2))
    print(json.dumps({key: report[key] for key in ['mean_score', 'worst_family_score', 'family_scores', 'parallel_wall_seconds']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
