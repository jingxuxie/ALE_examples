import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from evaluate import ROOT


def digest_tree(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob('*')) if path.is_file() and '__pycache__' not in str(path)
            and '.pytest_cache' not in str(path)}


def main():
    reference = json.loads((ROOT / 'screening/v_01/reference_evaluation/evaluation.json').read_text())
    checks = json.loads((ROOT / 'screening/v_01/reference_independent_checks.json').read_text())
    if reference['core_score'] < 0.98 or reference['evidence']['score'] < 0.98 or not checks['passed']:
        raise RuntimeError('Reference gate not satisfied')
    participant = ROOT / 'participant/v_01'
    allowed_output = ROOT / 'attempts/v_01'
    output = allowed_output / 'output'
    if any(allowed_output.iterdir()):
        raise RuntimeError('A new attempt requires an empty allowed output directory')
    screening = ROOT / 'screening/v_01'
    before = digest_tree(participant)
    (screening / 'participant_before.json').write_text(json.dumps(before, indent=2))
    launcher = ROOT.parents[2] / 'run_allowlisted_codex.sh'
    prompt = (
        'You are an independent research-software participant. Read TASK.md in your current directory and solve it fully. '
        'The only benchmark files you may read are this participant directory and the supplied output directory. '
        'Do not seek the paper, evaluator, reference, other tasks, other attempts, or parent directories. '
        'Copy workspace into your output before modifying it, and leave the participant files unchanged. '
        'Write your complete submission to ' + str(output) + '. '
        'You have up to one hour. Run the baseline, diagnose the physical and numerical discrepancies, '
        'repair the executable system, run controlled experiments, and produce all deliverables. '
        'Do not ask the user to run commands or select methods. Stop only when your best complete submission is ready. '
        'Do not claim successful validation without running it.'
    )
    command = [str(launcher), '--model', 'ultima-alpha', '--effort', 'high', str(participant), str(allowed_output), prompt]
    (screening / 'launch.json').write_text(json.dumps({'command': command, 'model': 'ultima-alpha',
        'time_limit_seconds': 3600, 'fresh_session': True, 'allowed_task': str(participant),
        'allowed_output': str(allowed_output), 'prompt': prompt}, indent=2))
    started_wall = time.time()
    started = time.monotonic()
    with (screening / 'transcript.txt').open('w') as transcript:
        process = subprocess.Popen(command, stdout=transcript, stderr=subprocess.STDOUT, start_new_session=True)
        timeout = False
        try:
            exitcode = process.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            timeout = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            exitcode = process.returncode
    after = digest_tree(participant)
    (screening / 'participant_after.json').write_text(json.dumps(after, indent=2))
    metadata = {'model': 'ultima-alpha', 'reasoning_effort': 'high', 'runtime_seconds': time.monotonic() - started,
                'start_unix': started_wall, 'end_unix': time.time(), 'exitcode': exitcode, 'timeout': timeout,
                'participant_unchanged': before == after, 'new_session': True,
                'output': str(output), 'transcript': str(screening / 'transcript.txt')}
    (screening / 'attempt.json').write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
