import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import tomli


ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path('/srv/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh')


def tree_hash(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob('*')) if path.is_file() and '__pycache__' not in path.parts}


def clean_home():
    original = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    configuration = tomli.loads((original / 'config.toml').read_text())
    runtime_root = ROOT / 'authoring' / 'runtime_homes'
    runtime_root.mkdir(exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix='fresh-', dir=runtime_root))
    destination.chmod(0o700)
    provider = configuration.get('model_provider')
    lines = ['model = "ultima-alpha"', 'model_reasoning_effort = "high"',
             'web_search = "disabled"', 'approval_policy = "never"',
             '[permissions.benchmark.network]', 'enabled = false']
    if provider:
        lines.insert(2, 'model_provider = ' + json.dumps(provider))
        for name, fields in configuration.get('model_providers', {}).items():
            if name != provider:
                continue
            lines.append('[model_providers.' + json.dumps(name) + ']')
            for key, value in fields.items():
                if isinstance(value, (str, int, float, bool)):
                    lines.append(key + ' = ' + json.dumps(value))
                elif isinstance(value, dict):
                    lines.append(key + ' = { ' + ', '.join(json.dumps(entry) + ' = ' + json.dumps(content)
                                                          for entry, content in value.items()) + ' }')
    (destination / 'config.toml').write_text('\n'.join(lines) + '\n')
    if (original / 'auth.json').is_file():
        shutil.copy2(original / 'auth.json', destination / 'auth.json')
        (destination / 'auth.json').chmod(0o600)
    (destination / 'packages').symlink_to(original / 'packages', target_is_directory=True)
    (destination / 'tmp').mkdir()
    (destination / 'tmp' / 'arg0').mkdir()
    return destination


def launch(participant, output, evidence, seconds, prompt):
    participant = participant.resolve()
    output = output.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=False)
    frozen = tree_hash(participant)
    home = clean_home()
    start = time.time()
    deadline = datetime.datetime.fromtimestamp(start + seconds, datetime.timezone.utc).isoformat()
    timed_prompt = prompt.format(output=output) + ' The external wall-clock deadline, including startup time, is ' + deadline + '.'
    command = ['/usr/bin/bash', str(RUNNER), '--model', 'ultima-alpha', '--effort', 'high',
               '--task-read-only', str(participant), str(output), timed_prompt]
    environment = os.environ.copy()
    environment['CODEX_HOME'] = str(home)
    environment['HOME'] = str(home)
    for variable in ('CODEX_PERMISSION_PROFILE', 'CODEX_SANDBOX_NETWORK_DISABLED'):
        environment.pop(variable, None)
    metadata = {'model': 'ultima-alpha', 'reasoning_effort': 'high', 'limit_seconds': seconds,
                'participant': str(participant), 'output': str(output), 'command': command,
                'participant_hashes_before': frozen, 'start_epoch': start,
                'clean_startup': True, 'task_read_only': True, 'network_enabled': False,
                'generation_artifacts_allowlisted': False, 'initial_output_empty': True, 'deadline_utc': deadline}
    (evidence / 'launch.json').write_text(json.dumps(metadata, indent=2))
    try:
        with (evidence / 'stdout.txt').open('wb') as stdout, (evidence / 'session.log').open('wb') as stderr:
            process = subprocess.Popen(command, env=environment, stdin=subprocess.DEVNULL, stdout=stdout,
                                       stderr=stderr, start_new_session=True, close_fds=True)
            timed_out = False
            try:
                return_code = process.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                return_code = 124
        metadata.update({'end_epoch': time.time(), 'elapsed_seconds': time.time() - start,
                         'return_code': return_code, 'timed_out': timed_out,
                         'participant_hashes_after': tree_hash(participant),
                         'submission_hashes': tree_hash(output)})
        metadata['participant_unchanged'] = frozen == metadata['participant_hashes_after']
        (evidence / 'launch.json').write_text(json.dumps(metadata, indent=2))
        print(json.dumps({key: metadata[key] for key in ('model', 'return_code', 'elapsed_seconds',
                                                       'timed_out', 'participant_unchanged')}))
    finally:
        shutil.rmtree(home)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--concept', type=int)
    parser.add_argument('--generation', type=int, default=1)
    parser.add_argument('--probe', action='store_true')
    options = parser.parse_args()
    if options.probe:
        base = ROOT / 'authoring' / 'isolation_probe'
        if (base / 'output').exists():
            suffix = str(int(time.time()))
            (base / 'output').rename(base / ('output_failed_' + suffix))
            if (base / 'evidence').exists():
                (base / 'evidence').rename(base / ('evidence_failed_' + suffix))
        launch(base / 'participant', base / 'output', base / 'evidence', 300,
               'Run the supplied check.py with /usr/bin/python3. Save its JSON report to {output}/probe.json. '
               'Do not solve any scientific task. Do not change permissions or use alternative tools to read denied files.')
    else:
        probe = json.loads((ROOT / 'authoring' / 'isolation_probe' / 'output' / 'probe.json').read_text())
        if not probe.get('passed'):
            raise RuntimeError('Isolation preflight has not passed')
        base = ROOT / ('concept_' + str(options.concept))
        generation = 'v_' + str(options.generation)
        launch(base / 'participant', base / 'attempts' / generation, base / 'attempts' / (generation + '_evidence'), 3600,
               'Solve TASK.md autonomously using only the supplied participant assets. You have up to 3600 seconds '
               'and four CPU threads. No network, external packages, private evaluators, prior attempts, or generation '
               'sources are available. Write all scratch work and the required final artifact(s) to {output}. '
               'The participant directory is read-only. Inspect the task, build and test your best submission, '
               'and do not stop at a plan. This is a fresh independent attempt; do not spawn or delegate to other agents.')


if __name__ == '__main__':
    main()
