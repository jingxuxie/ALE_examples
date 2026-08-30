"""Fresh ultima-alpha/xhigh sessions; the original allowlisted runner is unchanged."""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

from isolation import AUTHORING, private_directory, run_isolated, validate_tree


TASK_ROOT = AUTHORING.parent
RUNNER = Path('/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh')
RUNNER_SHA256 = '06f4693741de6587283d2cf78d91895e5a74c1230c9960b5457f8cc536cf0394'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fresh_runtime(destination, source_home=None, *, audit=False):
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    source = Path(source_home or os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))).resolve(strict=True)
    config = tomllib.loads((source / 'config.toml').read_text())
    if any(name in config for name in ('model_provider', 'model_providers')):
        raise ValueError('Custom providers require review; provider configuration is not inherited')
    destination.mkdir(mode=0o700)
    binary = Path(shutil.which('codex')).resolve(strict=True)
    with binary.open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            raise ValueError('Codex must resolve to a native ELF executable')
    packages = destination / 'packages/bin'
    packages.mkdir(parents=True)
    for name in ('codex', 'codex-code-mode-host'):
        native = binary.parent / name
        if native.is_file():
            shutil.copyfile(native, packages / name)
            (packages / name).chmod(0o500)
    for name in ('codex-linux-sandbox', 'apply_patch'):
        (packages / name).symlink_to('codex')
    (destination / 'tmp/arg0').mkdir(parents=True)
    lines = ['model = "ultima-alpha"', 'model_reasoning_effort = "xhigh"',
             'web_search = "disabled"', 'approval_policy = "never"',
             '[features]', 'shell_snapshot = false',
             '[shell_environment_policy]', 'inherit = "none"',
             '[shell_environment_policy.set]',
             'PATH = ' + json.dumps(str(packages) + ':/usr/bin:/bin'),
             'LANG = "C.UTF-8"', 'PYTHONNOUSERSITE = "1"',
             'OPENBLAS_NUM_THREADS = "1"', 'OMP_NUM_THREADS = "1"', 'MKL_NUM_THREADS = "1"']
    if config.get('model_catalog_json'):
        catalog = Path(config['model_catalog_json']).expanduser()
        if not catalog.is_absolute():
            catalog = source / catalog
        shutil.copyfile(catalog, destination / 'model_catalog.json')
        lines.insert(0, 'model_catalog_json = ' + json.dumps(str(destination / 'model_catalog.json')))
    if not audit and (source / 'auth.json').is_file():
        shutil.copyfile(source / 'auth.json', destination / 'auth.json')
        (destination / 'auth.json').chmod(0o600)
    if audit:
        (destination / 'auth.json').write_text('{"audit_canary":"not-a-credential"}\n')
        (destination / 'auth.json').chmod(0o600)
    (destination / 'config.toml').write_text('\n'.join(lines) + '\n')
    (destination / 'config.toml').chmod(0o600)


def controller_environment(runtime, *, audit=False):
    names = ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_ORG_ID', 'OPENAI_PROJECT_ID',
             'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
             'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')
    environment = {} if audit else {name: os.environ[name] for name in names if name in os.environ}
    environment.update(PATH=str(runtime / 'packages/bin') + ':/usr/bin:/bin',
                       HOME=str(runtime), CODEX_HOME=str(runtime), LANG='C.UTF-8',
                       TMPDIR='/tmp', PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    return environment


def generation_spec(participant, output, runtime, prompt):
    if digest(RUNNER) != RUNNER_SHA256:
        raise RuntimeError('Original allowlisted runner changed; refusing to launch')
    mounts = [{'source': str(path), 'target': str(path), 'readonly': readonly}
              for path, readonly in ((RUNNER, True), (runtime, False),
                                     (runtime / 'packages', True), (participant, True), (output, False))]
    return {'mounts': mounts, 'cwd': str(participant),
            'command': [str(RUNNER), '--model', 'ultima-alpha', '--effort', 'xhigh',
                        '--task-read-only', str(participant), str(output), prompt]}


def sandbox_command(participant, output, runtime, command):
    """Audit the unchanged runner's permission profile without calling a model."""
    paths = {':minimal': 'read', str(participant): 'read', str(output): 'write',
             str(runtime / 'packages'): 'read', str(runtime / 'tmp/arg0'): 'read',
             str(runtime / 'packages/bin/codex'): 'read'}
    override = 'permissions.benchmark.filesystem={' + ','.join(
        json.dumps(path) + '=' + json.dumps(access) for path, access in paths.items()) + '}'
    return [str(runtime / 'packages/bin/codex'),
            '-c', override, '-c', 'default_permissions="benchmark"',
            '-c', 'approval_policy="never"', '-c', 'web_search="disabled"',
            'sandbox', '--', *command]


def launch(participant, output, *, prompt_file=None, source_codex_home=None, limit=3600):
    participant = validate_tree(Path(participant).absolute())
    output = validate_tree(Path(output).absolute())
    if not participant.is_relative_to(TASK_ROOT) or participant.name != 'participant':
        raise ValueError('Participant must be this task\'s participant directory')
    if output.parent != participant.parent / 'attempts' or not re.fullmatch(r'v_[1-9][0-9]*', output.name):
        raise ValueError('Output must be sibling attempts/v_N (positive N)')
    if any(output.iterdir()) or not 0 < limit <= 3600:
        raise ValueError('Requires empty output and a limit of at most 3600 seconds')
    identifier = hashlib.sha256(str(output).encode()).hexdigest()
    records = AUTHORING / 'launch_records'
    records.mkdir(mode=0o700, exist_ok=True)
    with (records / (identifier + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record_path = records / (identifier + '.json')
        if record_path.exists() or any(output.iterdir()):
            raise ValueError('Attempt already launched; choose a new empty v_N')
        prompt = (Path(prompt_file).read_text() if prompt_file else
                  'Read TASK.md and solve the task autonomously. You have at most one hour. '
                  'The participant directory is read-only. Write your complete submission and '
                  f'all scratch files into {output}. Do not access other tasks, hidden data, '
                  'evaluators, previous attempts, credentials, or the external network. '
                  'Do not request escalation. Save the best complete submission you can.')
        if not prompt.strip() or '\0' in prompt:
            raise ValueError('Prompt must be nonempty text without NUL')
        record = {'model': 'ultima-alpha', 'effort': 'xhigh', 'limit_seconds': limit,
                  'participant': str(participant), 'output': str(output),
                  'participant_access': 'read-only', 'output_empty_at_start': True,
                  'runner_sha256': digest(RUNNER), 'status': 'starting',
                  'started_at': datetime.now(timezone.utc).isoformat()}
        record_path.write_text(json.dumps(record, indent=2) + '\n')
        try:
            with private_directory('session_') as directory:
                runtime = Path(directory) / 'runtime'
                fresh_runtime(runtime, source_codex_home)
                spec = generation_spec(participant, output, runtime, prompt)
                record['status'] = 'running'
                record_path.write_text(json.dumps(record, indent=2) + '\n')
                print('Fresh ultima-alpha/xhigh; record: ' + str(record_path), flush=True)
                result = run_isolated(spec, environment=controller_environment(runtime),
                                      timeout=limit, max_output_bytes=64 * 1024**2)
                for name in ('stdout', 'stderr'):
                    path = records / (identifier + '.' + name + '.log')
                    path.write_text(result.pop(name))
                    path.chmod(0o600)
                record.update(result, status='finished', runner_unchanged=digest(RUNNER) == RUNNER_SHA256)
        except BaseException:
            record['status'] = 'failed_or_interrupted'
            raise
        finally:
            record['finished_at'] = datetime.now(timezone.utc).isoformat()
            record_path.write_text(json.dumps(record, indent=2) + '\n')
        return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--participant', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prompt-file', type=Path)
    parser.add_argument('--source-codex-home', type=Path)
    parser.add_argument('--limit', type=float, default=3600)
    arguments = parser.parse_args()
    try:
        result = launch(**vars(arguments))
        print(json.dumps(result, indent=2))
        raise SystemExit(124 if result['timed_out'] else 125 if result['output_limited'] else result['returncode'])
    except (OSError, ValueError, RuntimeError) as error:
        print('launch failed: ' + str(error), file=sys.stderr)
        raise SystemExit(125)
