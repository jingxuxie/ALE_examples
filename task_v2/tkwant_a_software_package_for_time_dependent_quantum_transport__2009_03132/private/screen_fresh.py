import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = Path('/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh')


def manifest(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob('*')) if path.is_file() and '__pycache__' not in str(path) and '.pytest_cache' not in str(path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--concept', default='concept_01')
    parser.add_argument('--version', default='v_01')
    parser.add_argument('--attempt', default='fresh_01')
    args = parser.parse_args()
    concept = ROOT / args.concept
    participant = (concept / 'participant' / args.version).resolve()
    output = (concept / 'attempts' / args.version / args.attempt / 'output').resolve()
    record = concept / 'screening' / args.version / args.attempt
    output.mkdir(parents=True, exist_ok=False)
    record.mkdir(parents=True, exist_ok=True)
    before = manifest(participant)
    (record / 'participant_before.json').write_text(json.dumps(before, indent=2))
    prompt = (
        'You are the independent research engineer assigned the task in TASK.md. '
        'Read TASK.md and the input contract, then solve the task autonomously. '
        f'The only task directory you may read is {participant}. '
        f'The only directory where you may write your solution and experiments is {output}. '
        'Treat the participant directory as immutable; copy the active workspace into your output/workspace before edits. '
        'System-installed Python libraries and ordinary runtime binaries are available. '
        'Do not read any other project, sibling directory, paper, solution, evaluation, credential or session file. '
        'Do not use web browsing, network requests, other agents, or external services. '
        'You have up to one hour. Run your own experiments and checks without asking the user. '
        'Do not stop at a proposed method: deliver the self-contained executable, measured evidence, claims, and report. '
        'The final run.sh must be portable: grading mounts only your output as /submission, the requested cases as /cases.json, '
        'and a writable result directory as /output, plus system libraries. It must not depend on the original task path. '
        f'Place the final deliverables directly under {output}. '
        'If you cannot achieve full accuracy, still submit your best executable and report honest limitations.'
    )
    command = [str(LAUNCHER), '--model', 'ultima-alpha', str(participant), str(output), prompt]
    (record / 'launch.json').write_text(json.dumps(dict(model='ultima-alpha', time_limit_seconds=3600, command=command,
                                                     task_directory=str(participant), writable_directory=str(output),
                                                     fresh_session=True, launcher=str(LAUNCHER)), indent=2))
    started = time.time()
    with open(record / 'transcript.txt', 'w') as transcript:
        process = subprocess.Popen(command, stdout=transcript, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            returncode = process.wait(timeout=3600)
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            returncode = 124
            timed_out = True
    result = dict(model='ultima-alpha', started_unix=started, finished_unix=time.time(), runtime_seconds=time.time() - started,
                  returncode=returncode, timeout=timed_out, participant_unchanged=before == manifest(participant), output_directory=str(output))
    (record / 'runtime.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
