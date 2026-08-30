import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parent
BINARY = Path('/home/xuandong/.local/bin/codex').resolve()
REPOSITORY = ROOT.parents[3]


def snapshot(process_id):
    records = []
    pending = [process_id]
    seen = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        process_path = Path('/proc') / str(current)
        record = {'pid': current}
        try:
            status = process_path.joinpath('status').read_text()
            for line in status.splitlines():
                key, _, value = line.partition(':')
                if key in ('Name', 'State', 'PPid', 'TracerPid', 'NSpid', 'Seccomp', 'NoNewPrivs'):
                    record[key] = value.strip()
            for field in ('wchan', 'syscall', 'stack'):
                try:
                    record[field] = process_path.joinpath(field).read_text().strip()
                except OSError as error:
                    record[field] = type(error).__name__
            for thread_path in process_path.joinpath('task').iterdir():
                children = thread_path.joinpath('children').read_text().split()
                pending.extend(int(child) for child in children)
        except OSError as error:
            record['error'] = type(error).__name__
        records.append(record)
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('probes', nargs='+')
    arguments = parser.parse_args()
    home = ROOT / 'clean_home'
    temporary = ROOT / 'tmp'
    for directory in (home / 'packages', home / 'tmp' / 'arg0', temporary, ROOT / 'task', ROOT / 'output', ROOT / 'mount_target'):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    configuration = home / 'config.toml'
    if not configuration.exists():
        configuration.write_text('model = "ultima-alpha"\n')
    environment = {
        'PATH': '/home/xuandong/.local/bin:/usr/local/bin:/usr/bin:/bin',
        'HOME': str(home),
        'CODEX_HOME': str(home),
        'TMPDIR': str(temporary),
        'LANG': 'C.UTF-8',
    }
    probes = {
        'echo': ['/bin/echo', 'INFRA_ECHO_OK'],
        'codex_version': [str(BINARY), '--version'],
        'codex_help': [str(BINARY), '--help'],
        'sandbox_help': [str(BINARY), 'sandbox', 'linux', '--help'],
        'runner_help': [str(REPOSITORY / 'run_allowlisted_codex.sh'), '--model', 'ultima-alpha', '--task-read-only', str(ROOT / 'task'), str(ROOT / 'output'), '--help'],
        'bwrap': ['/usr/bin/bwrap', '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64', '--symlink', 'usr/bin', '/bin', '--unshare-net', '--', '/bin/echo', 'INFRA_BWRAP_OK'],
        'unshare_user': ['/usr/bin/unshare', '--user', '--map-root-user', '/bin/echo', 'INFRA_USERNS_OK'],
        'strace': ['/usr/bin/strace', '-o', str(ROOT / 'strace_echo.trace'), '/bin/echo', 'INFRA_STRACE_OK'],
    }
    probes['bwrap_trace'] = ['/usr/bin/strace', '-f', '-s', '160', '-o', str(ROOT / 'bwrap.trace')] + probes['bwrap']
    probes['sandbox_cli_help'] = [str(BINARY), 'help', 'sandbox', 'linux']
    probes['sandbox_help_correct'] = [str(BINARY), 'sandbox', '--help']
    probes['features'] = [str(BINARY), 'features', 'list']
    probes['unshare_mount'] = ['/usr/bin/unshare', '--user', '--map-root-user', '--mount', '--propagation', 'private', '/bin/echo', 'INFRA_MOUNTNS_OK']
    probes['private_tmpfs'] = ['/usr/bin/unshare', '--user', '--map-root-user', '--mount', '--propagation', 'private', '/bin/mount', '-n', '-t', 'tmpfs', '-o', 'nosuid,nodev', 'tmpfs', str(ROOT / 'mount_target')]
    probes['private_root'] = ['/usr/bin/unshare', '--user', '--map-root-user', '--mount', '--propagation', 'private', '--pid', '--fork', 'python3', str(ROOT / 'private_root_probe.py'), os.readlink('/proc/self/ns/mnt')]
    allowlist = {':minimal': 'read', str(ROOT / 'task'): 'read', str(ROOT / 'output'): 'write', str(home / 'packages'): 'read', str(home / 'tmp' / 'arg0'): 'read', str(BINARY): 'read'}
    permissions = 'permissions.benchmark.filesystem={' + ','.join(json.dumps(path) + '=' + json.dumps(access) for path, access in allowlist.items()) + '}'
    probes['legacy_allowlist_echo'] = [str(BINARY), '--model', 'ultima-alpha', '-c', permissions, '-c', 'default_permissions="benchmark"', '-c', 'approval_policy="never"', '-c', 'web_search="disabled"', '-c', 'features.use_legacy_landlock=true', 'sandbox', '-P', 'benchmark', '-C', str(ROOT / 'task'), '--', '/bin/echo', 'INFRA_LEGACY_ALLOWLIST_OK']
    for name in arguments.probes:
        command = probes[name]
        started = time.monotonic()
        record = {'name': name, 'command': command, 'model_run': False}
        with (ROOT / (name + '.stdout')).open('wb') as stdout, (ROOT / (name + '.stderr')).open('wb') as stderr:
            process = subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True)
            record['pid'] = process.pid
            try:
                process.wait(timeout=60 if name == 'private_root' else 4)
                record['timeout'] = False
            except subprocess.TimeoutExpired:
                record['timeout'] = True
                record['before_cleanup'] = snapshot(process.pid)
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    record['unreaped'] = True
            record['returncode'] = process.poll()
        record['elapsed_seconds'] = round(time.monotonic() - started, 3)
        for stream in ('stdout', 'stderr'):
            data = (ROOT / (name + '.' + stream)).read_bytes()
            record[stream + '_bytes'] = len(data)
            record[stream + '_preview'] = data[:2500].decode(errors='replace')
        (ROOT / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
