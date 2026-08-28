import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = Path('/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='v_01')
    parser.add_argument('--round', default='round_01')
    args = parser.parse_args()
    participant = (ROOT / 'concept_01/participant' / args.version).resolve()
    attempt = (ROOT / 'concept_01/attempts' / args.version).resolve()
    screening = ROOT / 'concept_01/screening' / args.round
    screening.mkdir(parents=True, exist_ok=True)
    if any(attempt.iterdir()):
        raise RuntimeError('A fresh attempt directory must be empty.')
    prompt = (
        f'Solve the professional research task in {participant}/TASK.md. '
        f'You may read only {participant}/TASK.md, {participant}/input/, '
        f'and {participant}/workspace/, and your own output directory {attempt}. '
        f'Write all final deliverables directly into {attempt}, including run.sh and workspace/. '
        'Treat the supplied task and inputs as read-only; copy implementation files into your output before changing them. '
        'The supplied workspace/runtime contains the offline dependencies and need not be copied; use ALE_RUNTIME as documented. '
        'Do not read other directories, use the network, seek hidden evaluators or references, '
        'or spawn other agents. Work autonomously, run experiments, and complete the task without asking questions. '
        'Your session has a maximum of 3600 seconds. This is a completely fresh task attempt.'
    )
    command = [str(LAUNCHER), '--model', 'ultima-alpha', '--effort', 'high',
               str(participant), str(attempt), prompt]
    record = {'model': 'ultima-alpha', 'effort': 'high', 'time_limit_seconds': 3600,
              'participant': str(participant), 'output': str(attempt),
              'launcher': str(LAUNCHER), 'fresh_session': True, 'prompt': prompt,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    (screening / 'launch.json').write_text(json.dumps(record, indent=2))
    start = time.monotonic()
    timed_out = False
    with (screening / 'transcript.log').open('w') as transcript:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=transcript, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return_code = process.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                return_code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                return_code = process.wait()
    record.update(runtime_seconds=time.monotonic() - start, return_code=return_code, timed_out=timed_out,
                  completed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    (screening / 'runtime.json').write_text(json.dumps(record, indent=2))
    print(json.dumps({key: record[key] for key in ['model', 'runtime_seconds', 'return_code', 'timed_out']}, indent=2))


if __name__ == '__main__':
    main()
