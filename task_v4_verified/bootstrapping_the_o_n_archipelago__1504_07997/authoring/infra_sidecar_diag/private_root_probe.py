import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
BINARY = Path('/home/xuandong/.local/bin/codex').resolve()
REPOSITORY = ROOT.parents[3]
STAGING = ROOT / 'rootfs'
HOME = ROOT / 'clean_home'
TASK = ROOT / 'task'
OUTPUT = ROOT / 'output'


def mount(*arguments):
    print('mount setup:', ' '.join(arguments), flush=True)
    subprocess.run(['/bin/mount', '-n', *arguments], check=True, stdin=subprocess.DEVNULL)


def bind(source, readonly=True):
    source = Path(source)
    target = STAGING / source.relative_to('/')
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        target.mkdir(exist_ok=True)
    else:
        target.touch(exist_ok=True)
    mount('--bind', str(source), str(target))
    if readonly:
        mount('-o', 'remount,bind,ro', str(target))


def main():
    if len(sys.argv) != 2 or os.readlink('/proc/self/ns/mnt') == sys.argv[1] or os.getuid() != 0 or os.getpid() != 1:
        raise RuntimeError('Requires a new private mount/user/PID namespace')
    STAGING.mkdir(exist_ok=True, mode=0o700)
    mount('-t', 'tmpfs', '-o', 'nosuid,nodev', 'tmpfs', str(STAGING))
    for name in ('usr', 'bin', 'sbin', 'lib', 'lib64'):
        source = Path('/') / name
        if source.is_symlink():
            (STAGING / name).symlink_to(os.readlink(source))
        elif source.exists():
            bind(source)
    for name in ('ld.so.cache', 'nsswitch.conf', 'hosts', 'resolv.conf', 'passwd', 'group', 'ssl/certs'):
        source = Path('/etc') / name
        if source.exists():
            bind(source)
    for name in ('tmp', 'proc', 'dev', 'dev/shm'):
        (STAGING / name).mkdir(parents=True, exist_ok=True)
    (STAGING / 'tmp').chmod(0o1777)
    mount('-t', 'proc', '-o', 'nosuid,nodev,noexec', 'proc', str(STAGING / 'proc'))
    for name in ('full', 'null', 'zero', 'random', 'urandom', 'tty'):
        bind('/dev/' + name, readonly=False)
    (STAGING / 'dev/fd').symlink_to('/proc/self/fd')
    for name, descriptor in (('stdin', 0), ('stdout', 1), ('stderr', 2)):
        (STAGING / 'dev' / name).symlink_to('/proc/self/fd/' + str(descriptor))
    bind(BINARY)
    bind(REPOSITORY / 'run_allowlisted_codex.sh')
    bind(HOME, readonly=False)
    bind(TASK)
    bind(OUTPUT, readonly=False)
    allowlist = {':minimal': 'read', str(TASK): 'read', str(OUTPUT): 'write', str(HOME / 'packages'): 'read', str(HOME / 'tmp/arg0'): 'read', str(BINARY): 'read'}
    permissions = 'permissions.benchmark.filesystem={' + ','.join(json.dumps(path) + '=' + json.dumps(access) for path, access in allowlist.items()) + '}'
    check = '\n'.join([
        'import errno, json, os, socket',
        'from pathlib import Path',
        'task = Path(' + repr(str(TASK)) + ')',
        'output = Path(' + repr(str(OUTPUT)) + ')',
        'results = {}',
        'results["participant_read"] = (task / "allowed.txt").read_text() == "synthetic participant\\n"',
        '(output / "write_ok.txt").write_text("synthetic output\\n")',
        'results["output_write"] = True',
        'try:',
        '    (task / "forbidden_write.txt").write_text("bad")',
        '    results["participant_write_denied"] = False',
        'except OSError:',
        '    results["participant_write_denied"] = True',
        'for name, path in ' + repr({'excluded_read_denied': str(ROOT / 'excluded.txt'), 'runtime_config_read_denied': str(HOME / 'config.toml')}) + '.items():',
        '    try:',
        '        Path(path).read_bytes()',
        '        results[name] = False',
        '    except OSError:',
        '        results[name] = True',
        'try:',
        '    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:',
        '        connection.settimeout(1)',
        '        connection.connect(("127.0.0.1", 9))',
        '    results["network_denied"] = False',
        'except OSError as error:',
        '    results["network_denied"] = error.errno in (errno.EPERM, errno.EACCES, errno.ENETUNREACH)',
        'print(json.dumps(results), flush=True)',
        'raise SystemExit(0 if all(results.values()) else 1)',
    ])
    environment = {'PATH': str(BINARY.parent) + ':/usr/local/bin:/usr/bin:/bin', 'HOME': str(HOME), 'CODEX_HOME': str(HOME), 'TMPDIR': '/tmp', 'LANG': 'C.UTF-8'}
    command = [str(BINARY), '--model', 'ultima-alpha', '-c', permissions, '-c', 'default_permissions="benchmark"', '-c', 'approval_policy="never"', '-c', 'web_search="disabled"', 'sandbox', '-P', 'benchmark', '-C', str(TASK), '--', '/usr/bin/python3', '-c', check]
    print('PRIVATE_ROOT_READY: synthetic mounts only; original runner unchanged; no model run', flush=True)
    (STAGING / 'oldroot').mkdir()
    os.chdir(STAGING)
    library = ctypes.CDLL(None, use_errno=True)
    if os.uname().machine != 'x86_64':
        raise RuntimeError('Diagnostic pivot_root syscall is x86_64-only')
    if library.syscall(ctypes.c_long(155), ctypes.c_char_p(b'.'), ctypes.c_char_p(b'oldroot')) != 0:
        raise OSError(ctypes.get_errno(), 'pivot_root failed')
    os.chdir('/')
    if library.umount2(ctypes.c_char_p(b'/oldroot'), ctypes.c_int(2)) != 0:
        raise OSError(ctypes.get_errno(), 'detach old root failed')
    os.rmdir('/oldroot')
    os.chdir(TASK)
    os.execve(BINARY, command, environment)


if __name__ == '__main__':
    main()
