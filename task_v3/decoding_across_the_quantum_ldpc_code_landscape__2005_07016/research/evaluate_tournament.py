import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ['01_local_recovery', '02_biased_pauli', '03_analog_memory', '04_circuit_compiler']
SCORES = ROOT / 'research/scores/tournament'
SCORES.mkdir(parents=True, exist_ok=True)


def evaluate_when_finished(concept):
    metadata_path = ROOT / 'research/runs/tournament' / (concept + '.metadata.json')
    started = time.monotonic()
    while True:
        try:
            metadata = json.loads(metadata_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            metadata = {}
        if 'returncode' in metadata:
            break
        if time.monotonic() - started > 4200:
            raise RuntimeError('No completed launcher metadata for ' + concept)
        time.sleep(10)
    pilot = ROOT / 'pilots' / concept
    submission = pilot / 'attempt'
    nested_entry = False
    if not (submission / 'solve.py').exists() and (submission / 'workspace/solve.py').exists():
        submission = submission / 'workspace'
        nested_entry = True
    report_path = SCORES / (concept + '.json')
    evaluator_report = pilot / 'private/reference/evaluations/tournament.json'
    log_path = SCORES / (concept + '.log')
    command = ['/usr/bin/python3', '-s', '-B', str(pilot / 'private/evaluator.py'), '--submission', str(submission), '--report', str(evaluator_report), '--split', 'pilot']
    if concept == '01_local_recovery':
        command += ['--save-predictions', str(SCORES / (concept + '_predictions'))]
    environment = dict(os.environ)
    environment.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    for variable in ['PYTHONPATH', 'PYTHONHOME']:
        environment.pop(variable, None)
    print(json.dumps(dict(event='evaluation_start', concept=concept, submission=str(submission), nested_entry=nested_entry)), flush=True)
    with log_path.open('w') as log:
        try:
            execution = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=environment, timeout=2400, stdin=subprocess.DEVNULL)
            returncode = execution.returncode
        except subprocess.TimeoutExpired:
            returncode = 124
    if returncode == 0 and evaluator_report.exists():
        shutil.copyfile(evaluator_report, report_path)
        report = json.loads(report_path.read_text())
        result = dict(concept=concept, mean_core=report.get('mean_core'), worst_family=report.get('worst_family'), evaluator_returncode=returncode, model_returncode=metadata['returncode'], model_elapsed_seconds=metadata['elapsed_seconds'], participant_unchanged=metadata['participant_unchanged'], nested_entry=nested_entry, report=str(report_path.relative_to(ROOT)))
    else:
        result = dict(concept=concept, evaluator_returncode=returncode, error='Evaluator produced no report; audit infrastructure/contract before assigning a score', log=str(log_path.relative_to(ROOT)))
    (SCORES / (concept + '.summary.json')).write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--concept', choices=CONCEPTS, action='append')
    args = parser.parse_args()
    selected = args.concept or CONCEPTS
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected)) as pool:
        list(pool.map(evaluate_when_finished, selected))
    results = []
    for concept in CONCEPTS:
        summary_path = SCORES / (concept + '.summary.json')
        if summary_path.exists():
            results.append(json.loads(summary_path.read_text()))
    (SCORES / 'summary.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
