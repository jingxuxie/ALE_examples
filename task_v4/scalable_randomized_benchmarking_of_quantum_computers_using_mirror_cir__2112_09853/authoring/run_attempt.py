import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import tempfile
import time


def fingerprint(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--concept', type=Path, required=True)
    parser.add_argument('--version', default='v_1')
    parser.add_argument('--limit', type=int, default=3600)
    arguments = parser.parse_args()
    concept = arguments.concept.resolve()
    participant = concept / 'participant'
    output = concept / 'attempts' / arguments.version
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise SystemExit('Fresh attempt output must be empty; refusing to reuse it.')
    audit = concept / 'attempts' / (arguments.version + '_audit')
    audit.mkdir(parents=True, exist_ok=False)
    runner = Path('/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh')
    prompt = (
        f'Read TASK.md and solve the participant task. You have at most {arguments.limit} seconds. '
        f'Only this participant directory and your initially empty output directory {output} are available. '
        f'Write your final submission and any work files under {output}; the participant assets are read-only. '
        'Do not use network access, outside files, prior submissions, or other agents. '
        'Investigate and validate independently, and leave the runnable submission requested by TASK.md. '
        'You may use the full allotted time; there is no requirement to stop early.'
    )
    command = [str(runner), '--model', 'ultima-alpha', '--effort', 'high',
               '--task-read-only', str(participant), str(output), prompt]
    before = fingerprint(participant)
    metadata = {
        'model': 'ultima-alpha', 'reasoning_effort': 'high', 'limit_seconds': arguments.limit,
        'participant': str(participant), 'output': str(output), 'output_initially_empty': True,
        'command': command, 'runner_sha256': hashlib.sha256(runner.read_bytes()).hexdigest(),
        'participant_before': before, 'started_unix': time.time(),
        'allowlist': {'participant': 'read', 'output': 'write', 'network': 'disabled'},
    }
    (audit / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    source_home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))).resolve()
    runtime_parent = concept.parent / 'authoring' / 'ephemeral_runtime'
    runtime_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    runtime = tempfile.TemporaryDirectory(prefix='mrb-fresh-', dir=runtime_parent)
    private_home = Path(runtime.name)
    for filename in ('config.toml', 'auth.json', 'models-ultima-alpha.json'):
        source = source_home / filename
        if source.exists():
            shutil.copy2(source, private_home / filename)
            os.chmod(private_home / filename, 0o600)
    (private_home / 'packages').symlink_to(source_home / 'packages', target_is_directory=True)
    (private_home / 'tmp' / 'arg0').mkdir(parents=True)
    environment = os.environ.copy()
    environment.update(CODEX_HOME=str(private_home), TOKIO_WORKER_THREADS='4', RAYON_NUM_THREADS='4')
    metadata['isolated_runtime_home'] = True
    metadata['no_history_or_memory_copied'] = True
    metadata['runtime_credentials_removed_after_attempt'] = True
    (audit / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    started = time.monotonic()
    with (audit / 'session.log').open('wb') as stream:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True, env=environment)
        timed_out = False
        try:
            return_code = process.wait(timeout=arguments.limit)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                return_code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                return_code = process.wait()
    runtime.cleanup()
    metadata.update({
        'elapsed_seconds': time.monotonic() - started,
        'return_code': return_code, 'timed_out': timed_out, 'finished_unix': time.time(),
        'participant_unchanged': before == fingerprint(participant),
        'submission_sha256': fingerprint(output),
    })
    (audit / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({key: metadata[key] for key in ['model', 'elapsed_seconds', 'return_code',
                                                   'timed_out', 'participant_unchanged']}), flush=True)


if __name__ == '__main__':
    main()
