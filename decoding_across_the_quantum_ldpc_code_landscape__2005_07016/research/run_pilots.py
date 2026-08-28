import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / 'run_allowlisted_codex.sh'


def snapshot(folder):
    hashes = {}
    for directory, directories, filenames in os.walk(folder):
        directories[:] = [name for name in directories if name not in {'.git', '.codex', '.agents', '__pycache__'}]
        for filename in sorted(filenames):
            path = Path(directory) / filename
            try:
                if path.is_file():
                    hashes[str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
            except FileNotFoundError:
                continue
    return hashes


def run_one(pilot, phase):
    participant = pilot / 'participant'
    attempt = pilot / 'attempt'
    if snapshot(attempt):
        raise RuntimeError(f'Fresh attempt must be empty: {attempt}')
    if not (participant / 'TASK.md').exists():
        raise RuntimeError(f'Missing mission: {participant}')
    log_directory = ROOT / 'research/runs' / phase
    log_directory.mkdir(parents=True, exist_ok=True)
    name = pilot.name
    before = snapshot(participant)
    prompt = f'''Solve the mission in TASK.md completely and autonomously. Your submission directory is {attempt}. Put solve.py and all necessary authored files there; it is initially empty. Use the participant input schema and validate the core algorithm, not just file formatting. You have a maximum of one hour. No user questions, network downloads, or external task/answer access. Only this participant tree and the submission directory are allowed. Do not change the supplied participant files. Finish with a concise factual summary of what you implemented and tested. The evaluator invokes python solve.py --input CASE --output ANSWER, with the exact formats in the task. Do not create a goal that extends beyond this one-hour run.'''
    command = ['timeout', '--signal=TERM', '--kill-after=30s', '3600s', str(RUNNER), '--model', 'ultima-alpha', '--effort', 'high', '--task-read-only', str(participant), str(attempt), prompt]
    metadata = dict(concept=name, phase=phase, model_requested='ultima-alpha', time_limit_seconds=3600, participant=str(participant), attempt=str(attempt), participant_sha256_before=before, started_unix=time.time(), runner=str(RUNNER), runner_sha256=hashlib.sha256(RUNNER.read_bytes()).hexdigest(), argv=command[:-1], prompt=prompt)
    (log_directory / (name + '.metadata.json')).write_text(json.dumps(metadata, indent=2))
    started = time.monotonic()
    with (log_directory / (name + '.log')).open('w') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        metadata['pid'] = process.pid
        (log_directory / (name + '.metadata.json')).write_text(json.dumps(metadata, indent=2))
        metadata['returncode'] = process.wait()
    metadata['elapsed_seconds'] = time.monotonic() - started
    metadata['finished_unix'] = time.time()
    metadata['participant_sha256_after'] = snapshot(participant)
    metadata['participant_unchanged'] = metadata['participant_sha256_after'] == before
    metadata['submission_sha256'] = snapshot(attempt)
    metadata['submitted_solver'] = (attempt / 'solve.py').exists()
    (log_directory / (name + '.metadata.json')).write_text(json.dumps(metadata, indent=2))
    print(json.dumps({key: metadata[key] for key in ['concept', 'phase', 'returncode', 'elapsed_seconds', 'participant_unchanged', 'submitted_solver']}), flush=True)
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', required=True)
    parser.add_argument('pilots', nargs='+')
    arguments = parser.parse_args()
    pilots = [Path(path).resolve() for path in arguments.pilots]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(pilots)) as pool:
        futures = [pool.submit(run_one, pilot, arguments.phase) for pilot in pilots]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == '__main__':
    main()
