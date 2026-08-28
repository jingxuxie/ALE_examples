import argparse
import datetime
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path


def digest_tree(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='v_01')
    arguments = parser.parse_args()
    concept = Path(__file__).resolve().parent.parent
    participant = concept / 'participant' / arguments.version
    attempt = concept / 'attempts' / arguments.version
    logs = concept / 'screening' / arguments.version
    logs.mkdir(exist_ok=True)
    attempt.mkdir(exist_ok=True)
    if any(attempt.iterdir()):
        raise RuntimeError('A fresh attempt requires an empty output directory.')
    launcher = Path('/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh')
    prompt = (f'Read TASK.md and carry out the research release-audit task autonomously. '
              f'Your only task inputs are in {participant}. Write all deliverables into {attempt}. '
              'You have up to one hour. Use only these two allowlisted directories and the supplied '
              'runtime dependencies; do not access external files, network resources, or other '
              'agent sessions. Diagnose, implement, experiment, validate, and report your result. '
              'Do not ask the user to perform any work. Stop when your deliverables are complete.')
    command = [str(launcher), '--model', 'ultima-alpha', '--effort', 'xhigh',
               str(participant), str(attempt), prompt]
    metadata = {'model': 'ultima-alpha', 'reasoning_effort': 'xhigh',
                'time_limit_seconds': 3600, 'command': command,
                'start_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'participant': str(participant), 'attempt': str(attempt),
                'session_policy': 'new ephemeral session; no resume',
                'isolation': 'user-provided run_allowlisted_codex.sh minimal filesystem profile',
                'participant_sha256_before': digest_tree(participant)}
    (logs / 'launch.json').write_text(json.dumps(metadata, indent=2) + '\n')
    started = time.monotonic()
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    environment['PYTHONNOUSERSITE'] = '1'
    environment['OPENBLAS_NUM_THREADS'] = '1'
    environment['OMP_NUM_THREADS'] = '1'
    with (logs / 'transcript.txt').open('w') as transcript:
        process = subprocess.Popen(command, stdout=transcript, stderr=subprocess.STDOUT,
                                   cwd=participant, env=environment, start_new_session=True)
        try:
            returncode = process.wait(timeout=3600)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
    metadata.update(runtime_seconds=time.monotonic() - started, returncode=returncode,
                    timed_out=timed_out, finish_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    participant_sha256_after=digest_tree(participant))
    (logs / 'runtime.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({key: metadata[key] for key in ('model', 'runtime_seconds', 'returncode', 'timed_out')}))


if __name__ == '__main__':
    main()
