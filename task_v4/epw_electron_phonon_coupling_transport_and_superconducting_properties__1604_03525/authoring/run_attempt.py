import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def digest_tree(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob('*')) if path.is_file() and '__pycache__' not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--concept', type=Path, required=True)
    parser.add_argument('--generation', type=int, default=1)
    parser.add_argument('--attempt')
    args = parser.parse_args()
    concept = args.concept.resolve()
    participant = concept / 'participant'
    attempt_name = args.attempt or f'v_{args.generation}'
    if Path(attempt_name).name != attempt_name:
        raise ValueError('attempt name must be a basename')
    output = concept / 'attempts' / attempt_name
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError('fresh output directory must initially be empty')
    prefix = concept / 'attempts' / attempt_name
    prompt = (f'Independently solve TASK.md using only the participant directory. Write the requested submission '
              f'in {output}. The participant directory is read-only; copy anything you need to modify into your output. '
              'You have at most 3600 seconds to investigate, run local experiments, and produce your best working submission. '
              'Do not ask for clarification. Do not delegate or launch other agent sessions. Do not seek hidden evaluator '
              'files, other submissions, research artifacts, network access, or broader permissions. '
              'Only saved files in the output directory are evaluated.')
    command = ['/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh', '--model', 'ultima-alpha',
               '--effort', 'high', '--task-read-only', str(participant), str(output), prompt]
    metadata = {'model': 'ultima-alpha', 'effort': 'high', 'generation': args.generation,
                'attempt': attempt_name,
                'time_limit_seconds': 3600, 'initial_output_empty': True, 'command': command,
                'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'participant_before': digest_tree(participant), 'evaluator_before': digest_tree(concept / 'evaluator'),
                'isolation': 'runner allowlist: participant read-only and empty output writable; ephemeral; network disabled'}
    run_path = Path(str(prefix) + '.run.json')
    run_path.write_text(json.dumps(metadata, indent=2) + '\n')
    Path(str(prefix) + '.prompt.txt').write_text(prompt + '\n')
    start = time.monotonic()
    timed_out = False
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    with Path(str(prefix) + '.log').open('wb') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   env=environment, start_new_session=True)
        try:
            returncode = process.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait(timeout=10)
    metadata.update(elapsed_seconds=time.monotonic() - start, returncode=returncode, timed_out=timed_out,
                    finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    participant_after=digest_tree(participant), evaluator_after=digest_tree(concept / 'evaluator'))
    metadata['participant_unchanged'] = metadata['participant_before'] == metadata['participant_after']
    metadata['evaluator_unchanged'] = metadata['evaluator_before'] == metadata['evaluator_after']
    run_path.write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({key: value for key, value in metadata.items() if not isinstance(value, dict)}), flush=True)


if __name__ == '__main__':
    main()
