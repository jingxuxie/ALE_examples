import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / 'run_allowlisted_codex.sh'


def digest_tree(directory):
    manifest = {}
    for path in sorted(directory.rglob('*')):
        if not path.is_file() or 'vendor' in path.parts or '__pycache__' in path.parts:
            continue
        manifest[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--round', required=True)
    parser.add_argument('--concepts', nargs='+', required=True)
    parser.add_argument('--limit', type=int, default=3600)
    arguments = parser.parse_args()
    runs = []
    destination = ROOT / 'authoring' / 'runs' / arguments.round
    destination.mkdir(parents=True, exist_ok=True)
    for concept in arguments.concepts:
        base = ROOT / 'pilots' / concept
        if arguments.round != 'initial':
            base = base / arguments.round
        assert (base / 'participant' / 'TASK.md').is_file(), base
        assert (base / 'private' / 'evaluator.py').is_file(), base
        assert (base / 'participant' / 'workspace' / 'vendor').is_dir(), base
        assert (base / 'attempt').is_dir() and not list((base / 'attempt').iterdir()), base
    for concept in arguments.concepts:
        base = ROOT / 'pilots' / concept
        if arguments.round != 'initial':
            base = base / arguments.round
        participant = base / 'participant'
        attempt = base / 'attempt'
        assert (participant / 'TASK.md').exists(), participant
        assert (base / 'private' / 'evaluator.py').exists(), base
        assert attempt.is_dir() and not list(attempt.iterdir()), f'Attempt must be empty: {attempt}'
        prompt = (
            'Complete the mission in TASK.md. Read the input contract and supplied workspace. '
            f'Write your self-contained submission and all scratch/build files only into {attempt}. '
            'The participant directory is read-only. There are no private references or prior attempts '
            'available to you. Do not seek external files or use network access. '
            f'Numerical dependencies are installed in {participant}/workspace/vendor; set '
            f'PYTHONPATH={participant}/workspace/vendor when running Python if needed. '
            'These dependencies remain available during evaluation; do not copy vendor into your submission. '
            'You may copy the public baseline into your output directory and improve it. '
            'Implement and test a real solution rather than just describing one. '
            'Finish with a short summary of the implementation and any remaining scientific limitations. '
            'You have up to one hour; the evaluator execution limit is separately specified by the task.'
        )
        command = [str(RUNNER), '--model', 'ultima-alpha', '--effort', 'high', '--task-read-only',
                   str(participant), str(attempt), prompt]
        log = open(destination / (concept + '.log'), 'w')
        environment = os.environ.copy()
        environment.update(PYTHONPATH=str(participant / 'workspace' / 'vendor'), PYTHONNOUSERSITE='1',
            OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', NUMBA_NUM_THREADS='1',
            NUMBA_CACHE_DIR=str(attempt / '.numba_cache'))
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
            env=environment, start_new_session=True)
        record = dict(concept=concept, round=arguments.round, model='ultima-alpha', effort='high',
            participant=str(participant), attempt=str(attempt), pid=process.pid,
            started_utc=datetime.now(timezone.utc).isoformat(), time_limit_seconds=arguments.limit,
            runner_sha256=hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
            participant_sha256=digest_tree(participant), prompt=prompt, status='running')
        path = destination / (concept + '.json')
        path.write_text(json.dumps(record, indent=2))
        runs.append((process, log, record, path, time.monotonic()))
        print('STARTED', concept, process.pid, flush=True)
    pending = list(runs)
    while pending:
        for run in pending[:]:
            process, log, record, path, started = run
            expired = time.monotonic() - started > arguments.limit
            if process.poll() is None and expired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            if process.poll() is not None:
                log.close()
                record.update(status='timeout' if expired else 'completed', returncode=process.returncode,
                    elapsed_seconds=time.monotonic() - started,
                    finished_utc=datetime.now(timezone.utc).isoformat(),
                    final_participant_sha256=digest_tree(Path(record['participant'])),
                    submission_sha256=digest_tree(Path(record['attempt'])))
                path.write_text(json.dumps(record, indent=2))
                print('FINISHED', record['concept'], record['status'], process.returncode, flush=True)
                pending.remove(run)
        if pending:
            time.sleep(5)


if __name__ == '__main__':
    main()
