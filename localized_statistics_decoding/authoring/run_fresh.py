import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path('/home/xuandong/mnt/jingxu/ALE/tasks_v2/localized_statistics_decoding')
RUNNER = '/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='v_01')
    parser.add_argument('--attempt', default='fresh_01')
    arguments = parser.parse_args()
    participant = (ROOT / 'participant' / arguments.version).resolve()
    attempt = (ROOT / 'attempts' / arguments.version / arguments.attempt).resolve()
    prompt = (
        f'You are a fresh independent solver. Read {participant}/TASK.md and solve the task. '
        f'Your final self-contained submission must be rooted at {attempt}/solve.py; place all '
        f'other deliverables in {attempt}. Copy any starter modules you need into your output '
        'workspace before editing. Do not modify the original TASK.md or public inputs. '
        'Use the public diagnostics to run, inspect, revise, and validate your scientific solution. '
        'You have 1200 seconds. Work autonomously and do not ask the user to run commands. '
        f'Only {participant} and {attempt} are available as task/work directories. '
        'Do not search for author solutions, hidden evaluations, other tasks or prior attempts. '
        'No network or additional dependencies are needed. Finish by checking the required CLI '
        'and saving every validation and diagnostic deliverable required by TASK.md. '
        'The output directory may contain runner logs; they are not task input.'
    )
    command = [RUNNER, '--model', 'ultima-alpha', str(participant), str(attempt), prompt]
    started = time.monotonic()
    started_utc = datetime.now(timezone.utc).isoformat()
    timed_out = False
    with (attempt / 'transcript.log').open('wb') as transcript:
        process = subprocess.Popen(command, stdout=transcript, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            return_code = process.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                return_code = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                return_code = process.wait()
    metadata = {'model': 'ultima-alpha', 'time_limit_seconds': 1200,
                'started_utc': started_utc, 'finished_utc': datetime.now(timezone.utc).isoformat(),
                'elapsed_seconds': round(time.monotonic() - started, 3),
                'timed_out': timed_out, 'process_return_code': return_code,
                'allowed_task_directory': str(participant), 'allowed_output_directory': str(attempt),
                'runner': RUNNER, 'new_ephemeral_session': True}
    (attempt / 'run.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata))


if __name__ == '__main__':
    main()
