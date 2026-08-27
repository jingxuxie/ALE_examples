import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
CONCEPT = ROOT / 'concept_01'
PARTICIPANT = CONCEPT / 'participant' / 'v_01'
OUTPUT = CONCEPT / 'attempts' / 'v_01'
SCREEN = CONCEPT / 'screening' / 'v_01'


def snapshot():
    return {str(path.relative_to(PARTICIPANT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(PARTICIPANT.rglob('*')) if path.is_file() and '__pycache__' not in path.parts}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    SCREEN.mkdir(parents=True, exist_ok=True)
    if any(OUTPUT.iterdir()):
        raise RuntimeError('A fresh attempt requires an empty output directory')
    before = snapshot()
    (SCREEN / 'participant_sha256.json').write_text(json.dumps(before, indent=2))
    prompt = (f'Solve the professional research task in {PARTICIPANT}/TASK.md. '
              f'You have at most one hour. Read only this current participant directory and your own '
              f'output directory {OUTPUT}; do not inspect parent directories, sibling tasks, hidden '
              f'evaluators, references, papers or other sessions. System runtime libraries are allowed. '
              f'Treat the participant files as read-only. Copy the workspace into {OUTPUT}/workspace '
              f'and perform all edits and experiments under {OUTPUT}. Deliver a self-contained '
              f'{OUTPUT}/run.sh plus the requested experimental artifacts. Run, diagnose, revise and '
              f'validate autonomously. Do not ask the user to perform any step. Do not launch other agents. '
              f'The provided mathematical contract is complete. Do not use web search or network access.')
    command = ['/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh', '--model', 'ultima-alpha',
               '--effort', 'xhigh', str(PARTICIPANT), str(OUTPUT), prompt]
    record = {'model': 'ultima-alpha', 'reasoning_effort': 'xhigh', 'time_limit_seconds': 3600,
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'participant': str(PARTICIPANT), 'output': str(OUTPUT), 'command': command[:-1],
              'prompt': prompt, 'new_session': True}
    (SCREEN / 'launch.json').write_text(json.dumps(record, indent=2))
    started = time.monotonic()
    timed_out = False
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    environment['OPENBLAS_NUM_THREADS'] = '1'
    environment['OMP_NUM_THREADS'] = '1'
    with (SCREEN / 'transcript.log').open('w') as transcript:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=transcript, stderr=subprocess.STDOUT,
                                   env=environment, start_new_session=True)
        try:
            returncode = process.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
    record.update({'runtime_seconds': time.monotonic() - started, 'returncode': returncode,
                   'timed_out': timed_out, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'participant_unchanged': before == snapshot()})
    (SCREEN / 'runtime.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
