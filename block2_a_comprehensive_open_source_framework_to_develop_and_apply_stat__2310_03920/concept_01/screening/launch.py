import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    participant = (ROOT / 'participant/v_01').resolve()
    attempt = (ROOT / 'attempts/v_01').resolve()
    assert not any(attempt.iterdir()), 'Fresh attempt directory must be empty'
    manifest = {}
    for path in participant.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            manifest[str(path.relative_to(participant))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (ROOT / 'screening/participant_v01_manifest.json').write_text(json.dumps(manifest, indent=2))
    prompt = f'''Read TASK.md in your current directory and complete its research task autonomously.
Your writable output directory is {attempt}. Put run.sh, workspace, the actual experiments, and all requested evidence there.
You have a one-hour session budget. Use the available time for scientific diagnosis, experiments and revision, not just a proposed plan.
Only read files in {participant} and your output directory, apart from the system runtime necessary to execute commands.
Do not read parent/sibling directories, other tasks, private references, evaluators or external sources. Do not use the internet.
The task assets are read-only; copy any code you need to modify into your output workspace. The bundled runtime need not be copied.
Initialize the numerical environment with the provided workspace/env.sh. Do not ask the user to run commands or select a method.
Finish by leaving a reproducible executable and an honest report, including unresolved limitations if any.'''
    command = ['timeout', '--signal=TERM', '--kill-after=15s', '3600',
               '/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh', '--model', 'ultima-alpha',
               '--effort', 'xhigh', '--task-read-only', str(participant), str(attempt), prompt]
    metadata = {'model': 'ultima-alpha', 'effort': 'xhigh', 'session_limit_seconds': 3600,
                'participant': str(participant), 'output': str(attempt), 'prompt': prompt,
                'launcher': command[4], 'fresh_session': True, 'participant_read_only': True, 'web_search': 'disabled'}
    (ROOT / 'screening/launch_v01.json').write_text(json.dumps(metadata, indent=2))
    started = time.monotonic()
    with (ROOT / 'screening/transcript_v01.txt').open('w') as handle:
        result = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT)
    metadata.update(runtime_seconds=time.monotonic() - started, returncode=result.returncode)
    (ROOT / 'screening/launch_v01.json').write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2), flush=True)


if __name__ == '__main__':
    main()
