import argparse
import concurrent.futures
import json
import os
import pathlib
import subprocess
import sys
import time


ROOT = pathlib.Path(__file__).resolve().parents[1]


def evaluate(concept, phase, split):
    pilot = ROOT / 'pilots' / concept
    submission = pilot / 'attempt' if phase == 'initial' else pilot / phase / 'attempt'
    evidence = ROOT / 'authoring/tournament' / phase
    evidence.mkdir(parents=True, exist_ok=True)
    report_path = evidence / f'{concept}_{split}_score.json'
    log_path = evidence / f'{concept}_{split}_evaluation.log'
    command = [sys.executable, str(pilot / 'private/evaluator.py'), '--submission', str(submission), '--split', split, '--output', str(report_path)]
    environment = os.environ.copy()
    for key in ['PYTHONPATH', 'PYTHONHOME']:
        environment.pop(key, None)
    environment.update({'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'PYTHONNOUSERSITE': '1'})
    started = time.monotonic()
    with log_path.open('w') as output:
        process = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, env=environment, timeout=7200)
    if process.returncode != 0 or not report_path.exists():
        result = {'concept': concept, 'phase': phase, 'split': split, 'infrastructure_error': True, 'returncode': process.returncode, 'log': str(log_path)}
    else:
        report = json.loads(report_path.read_text())
        result = {'concept': concept, 'phase': phase, 'split': split, 'core_score': report['core_score'], 'worst_family_score': report['worst_family_score'], 'family_scores': report['family_scores'], 'report': str(report_path), 'seconds': time.monotonic() - started}
    print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--concepts', nargs='+', required=True)
    parser.add_argument('--phase', default='initial')
    parser.add_argument('--split', choices=['test', 'challenge', 'confirmation'], default='test')
    arguments = parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(arguments.concepts)) as executor:
        futures = [executor.submit(evaluate, concept, arguments.phase, arguments.split) for concept in arguments.concepts]
        rows = [future.result() for future in futures]
    (ROOT / 'authoring/tournament' / arguments.phase / f'scoreboard_{arguments.split}.json').write_text(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
