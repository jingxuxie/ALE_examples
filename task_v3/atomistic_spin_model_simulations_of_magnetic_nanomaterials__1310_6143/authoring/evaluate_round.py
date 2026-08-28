import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def normalize(report):
    mean = next((report[key] for key in ['mean_core', 'mean_family_score', 'mean_score'] if key in report), None)
    worst = next((report[key] for key in ['worst_family', 'worst_family_score'] if key in report), None)
    families = report.get('families', report.get('family_scores', {}))
    return dict(mean_core=mean, worst_family=worst, families=families)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--round', required=True)
    parser.add_argument('--concepts', nargs='+', required=True)
    parser.add_argument('--split', default='initial')
    arguments = parser.parse_args()
    folder = ROOT / 'authoring' / 'runs' / arguments.round
    pending = set(arguments.concepts)
    running = {}
    completed = {}
    while pending or running:
        for concept in sorted(pending):
            metadata_path = folder / (concept + '.json')
            if not metadata_path.exists():
                continue
            metadata = json.loads(metadata_path.read_text())
            if metadata['status'] == 'running':
                continue
            pilot = ROOT / 'pilots' / concept
            if arguments.round != 'initial':
                pilot = pilot / arguments.round
            output = folder / (concept + '.' + arguments.split + '.scores.json')
            log = open(folder / (concept + '.' + arguments.split + '.evaluation.log'), 'w')
            command = [sys.executable, str(pilot / 'private' / 'evaluator.py'),
                '--submission', str(pilot / 'attempt'), '--output', str(output), '--split', arguments.split]
            environment = os.environ.copy()
            environment.update(PYTHONPATH=str(ROOT / 'authoring' / 'python_runtime'), PYTHONNOUSERSITE='1',
                OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', NUMBA_NUM_THREADS='1')
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=environment)
            running[concept] = (process, log, output, metadata)
            print('EVALUATING', concept, arguments.split, flush=True)
        pending.difference_update(running)
        for concept, (process, log, output, metadata) in list(running.items()):
            if process.poll() is None:
                continue
            log.close()
            result = dict(concept=concept, model=metadata['model'], model_status=metadata['status'],
                model_returncode=metadata['returncode'], model_seconds=metadata['elapsed_seconds'],
                evaluator_returncode=process.returncode, scores_path=str(output))
            if output.exists() and process.returncode == 0:
                result.update(normalize(json.loads(output.read_text())))
            else:
                result['infrastructure_or_submission_error'] = True
            completed[concept] = result
            del running[concept]
            (folder / (arguments.split + '.summary.json')).write_text(json.dumps(completed, indent=2))
            print('EVALUATED', concept, result.get('mean_core'), result.get('worst_family'), flush=True)
        if pending or running:
            time.sleep(5)


if __name__ == '__main__':
    main()
