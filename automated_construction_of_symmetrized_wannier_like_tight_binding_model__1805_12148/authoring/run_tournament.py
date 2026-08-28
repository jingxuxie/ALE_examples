import argparse
import concurrent.futures
import datetime
import json
import os
import pathlib
import signal
import subprocess
import time


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / 'run_allowlisted_codex.sh'


def run_attempt(concept, phase, limit):
    pilot = ROOT / 'pilots' / concept
    participant = pilot / 'participant' if phase == 'initial' else pilot / phase / 'participant'
    attempt = pilot / 'attempt' if phase == 'initial' else pilot / phase / 'attempt'
    attempt.mkdir(parents=True, exist_ok=True)
    if any(attempt.iterdir()):
        raise RuntimeError('Fresh attempt directory is not empty: ' + str(attempt))
    if not (participant / 'TASK.md').exists():
        raise RuntimeError('Missing participant task: ' + str(participant))
    evidence = ROOT / 'authoring/tournament' / phase
    evidence.mkdir(parents=True, exist_ok=True)
    log_path = evidence / (concept + '.log')
    prompt = f'Read TASK.md and the supplied workspace/input artifacts. Solve the scientific programming task completely. Put your executable solve.py and any required local modules in {attempt.resolve()}. You have up to one hour. The participant tree is read-only; use your attempt directory for implementation and experiments. Do not use external sources or dependencies beyond the visible environment. Validate what you can and describe unresolved scientific limitations honestly. Do not stop at a plan or a placeholder.'
    command = [str(RUNNER.resolve()), '--model', 'ultima-alpha', '--effort', 'high', '--task-read-only', str(participant.resolve()), str(attempt.resolve()), prompt]
    started = time.monotonic()
    record = {'concept': concept, 'phase': phase, 'model': 'ultima-alpha', 'effort': 'high', 'limit_seconds': limit, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'participant': str(participant.resolve()), 'attempt': str(attempt.resolve()), 'command': command, 'isolation': 'allowlisted runner: participant read-only, fresh attempt writable, web disabled, approval never'}
    status_path = evidence / (concept + '.json')
    status_path.write_text(json.dumps(record, indent=2))
    environment = os.environ.copy()
    environment.update({'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'})
    with log_path.open('w') as output:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, env=environment, start_new_session=True)
        try:
            returncode = process.wait(timeout=limit)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
    record.update({'returncode': returncode, 'timed_out': timed_out, 'elapsed_seconds': time.monotonic() - started, 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'has_solve_py': (attempt / 'solve.py').exists()})
    status_path.write_text(json.dumps(record, indent=2))
    print(json.dumps({key: record[key] for key in ['concept', 'phase', 'returncode', 'elapsed_seconds', 'has_solve_py']}), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--concepts', nargs='+', required=True)
    parser.add_argument('--phase', default='initial')
    parser.add_argument('--limit', type=int, default=3600)
    arguments = parser.parse_args()
    if arguments.limit > 3600:
        parser.error('The user-specified pilot limit is one hour.')
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(arguments.concepts)) as executor:
        futures = [executor.submit(run_attempt, concept, arguments.phase, arguments.limit) for concept in arguments.concepts]
        records = [future.result() for future in futures]
    output = ROOT / 'authoring/tournament' / arguments.phase / 'runs.json'
    output.write_text(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
