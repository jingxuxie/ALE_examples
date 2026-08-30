"""Private-root process supervisor; never import submitted Python in the host."""

import argparse
import ctypes
import errno
import json
import math
import os
from pathlib import Path
import resource
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time


AUTHORING = Path(__file__).resolve().parent
SYSTEM_DIRS = ('usr', 'bin', 'sbin', 'lib', 'lib64')
SYSTEM_CONFIG = ('ld.so.cache', 'nsswitch.conf', 'hosts', 'resolv.conf',
                 'passwd', 'group', 'localtime', 'os-release', 'gai.conf',
                 'ssl/certs', 'ssl/openssl.cnf', 'alternatives')


def private_directory(prefix):
    parent = AUTHORING / '.isolation'
    parent.mkdir(mode=0o700, exist_ok=True)
    metadata = parent.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        raise RuntimeError('Isolation staging must be an owned mode-0700 directory')
    return tempfile.TemporaryDirectory(prefix=prefix, dir=parent)


def validate_tree(directory):
    directory = Path(directory).absolute()
    if directory.resolve(strict=True) != directory or not directory.is_dir():
        raise ValueError('Expected a real directory without symlink components: ' + str(directory))
    for parent, directories, files in os.walk(directory, followlinks=False):
        for name in directories + files:
            metadata = (Path(parent) / name).lstat()
            if not (stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode)):
                raise ValueError('Symlinks and special files are forbidden in mounted data')
            if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink != 1:
                raise ValueError('Hard-linked files are forbidden in mounted data')
    return directory


def mount(*arguments):
    arguments = list(map(str, arguments))
    source = filesystem = options = None
    if arguments[0] == '--make-rprivate':
        target = arguments[1]
        flags = (1 << 18) | (1 << 14)
    elif arguments[0] == '--bind':
        source, target = arguments[1:]
        flags = 4096
    elif arguments[0] == '-t':
        filesystem, option_text, source, target = arguments[1], arguments[3], arguments[4], arguments[5]
        flags = 0
    elif arguments[0] == '-o':
        option_text, target = arguments[1:]
        flags = 32 | (os.statvfs(target).f_flag & 14)
    else:
        raise ValueError('Unsupported internal mount operation')
    if arguments[0] in ('-t', '-o'):
        values = {'ro': 1, 'nosuid': 2, 'nodev': 4, 'noexec': 8, 'bind': 4096, 'remount': 32}
        data = []
        for option in option_text.split(','):
            if option in values:
                flags |= values[option]
            else:
                data.append(option)
        options = ','.join(data) or None
    library = ctypes.CDLL(None, use_errno=True)
    library.mount.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
                              ctypes.c_ulong, ctypes.c_char_p]
    encode = lambda value: os.fsencode(value) if value is not None else None
    if library.mount(encode(source), encode(target), encode(filesystem), flags, encode(options)):
        raise OSError(ctypes.get_errno(), 'mount failed: ' + target)


def bind(root, source, destination=None, readonly=True):
    source = Path(source)
    destination = Path(destination) if destination else source
    if not destination.is_absolute() or '..' in destination.parts:
        raise ValueError('Invalid mount destination')
    target = root / destination.relative_to('/')
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        target.mkdir(exist_ok=True)
    else:
        target.touch(exist_ok=True)
    mount('--bind', source, target)
    if readonly:
        mount('-o', 'remount,bind,ro,nosuid,nodev', target)


def evaluator_restrictions():
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(38, 1, 0, 0, 0) or library.prctl(28, 15, 0, 0, 0):
        raise OSError(ctypes.get_errno(), 'no_new_privs/securebits')
    for capability in range(64):
        if library.prctl(24, capability, 0, 0, 0) and ctypes.get_errno() != errno.EINVAL:
            raise OSError(ctypes.get_errno(), 'capability bounding set')
    header = (ctypes.c_uint32 * 2)(0x20080522, 0)
    capabilities = (ctypes.c_uint32 * 6)()
    if library.capset(ctypes.byref(header), ctypes.byref(capabilities)):
        raise OSError(ctypes.get_errno(), 'capset')
    seccomp = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    seccomp.seccomp_init.argtypes = [ctypes.c_uint32]
    seccomp.seccomp_init.restype = ctypes.c_void_p
    seccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    seccomp.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    seccomp.seccomp_load.argtypes = [ctypes.c_void_p]
    seccomp.seccomp_release.argtypes = [ctypes.c_void_p]
    context = seccomp.seccomp_init(0x7FFF0000)
    if not context:
        raise RuntimeError('seccomp unavailable; refusing unsafe fallback')
    denied = ('socket', 'socketpair', 'connect', 'bind', 'listen', 'accept', 'accept4',
              'ptrace', 'process_vm_readv', 'process_vm_writev', 'pidfd_getfd',
              'mount', 'umount2', 'pivot_root', 'unshare', 'setns', 'chroot',
              'fsopen', 'fsmount', 'fspick', 'fsconfig', 'open_tree', 'move_mount',
              'mount_setattr', 'open_by_handle_at', 'name_to_handle_at', 'bpf',
              'perf_event_open', 'io_uring_setup', 'userfaultfd', 'keyctl', 'add_key',
              'request_key', 'reboot', 'kexec_load', 'init_module', 'finit_module',
              'delete_module', 'sched_setaffinity')
    try:
        for name in denied + ('clone3',):
            number = seccomp.seccomp_syscall_resolve_name(name.encode())
            error = errno.ENOSYS if name == 'clone3' else errno.EPERM
            if number >= 0 and seccomp.seccomp_rule_add(context, 0x00050000 | error, number, 0):
                raise RuntimeError('Cannot enforce syscall restriction: ' + name)
        if seccomp.seccomp_load(context):
            raise RuntimeError('Cannot load seccomp; refusing unsafe fallback')
    finally:
        seccomp.seccomp_release(context)


def child(specification, parent_namespaces):
    def trace(stage):
        if specification.get('trace_setup'):
            print('isolation-stage: ' + stage, file=sys.stderr, flush=True)

    trace('validate namespaces')
    if os.uname().machine != 'x86_64' or os.getpid() != 1 or os.geteuid() != 0:
        raise RuntimeError('Requires x86_64 and PID 1 in a fresh mapped-root namespace')
    for name, previous in parent_namespaces.items():
        if os.readlink('/proc/self/ns/' + name) == previous:
            raise RuntimeError('Refusing inherited namespace: ' + name)
    for name in ('uid_map', 'gid_map'):
        mappings = Path('/proc/self', name).read_text().splitlines()
        if len(mappings) != 1 or list(map(int, mappings[0].split()))[::2] != [0, 1]:
            raise RuntimeError('Requires --user --map-root-user')
    root = Path(specification['root'])
    root.mkdir(mode=0o700)
    mount('--make-rprivate', '/')
    mount('-t', 'tmpfs', '-o', 'nosuid,nodev,mode=0755', 'tmpfs', root)
    os.chdir(root)
    root = Path('.')
    trace('system directories')
    for name in SYSTEM_DIRS:
        source = Path('/') / name
        if source.is_symlink():
            (root / name).symlink_to(os.readlink(source))
        elif source.exists():
            bind(root, source)
    trace('system configuration')
    for name in SYSTEM_CONFIG:
        trace('configuration ' + name)
        source = Path('/etc') / name
        if source.exists():
            bind(root, source)
    for name in ('proc', 'dev', 'dev/shm', 'tmp'):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / 'tmp').chmod(0o1777)
    mount('-t', 'proc', '-o', 'nosuid,nodev,noexec', 'proc', root / 'proc')
    devices = ('null', 'zero', 'full', 'random', 'urandom')
    if not specification.get('evaluation'):
        devices += ('tty',)
    for name in devices:
        bind(root, '/dev/' + name, readonly=False)
    (root / 'dev/fd').symlink_to('/proc/self/fd')
    for name, descriptor in (('stdin', 0), ('stdout', 1), ('stderr', 2)):
        (root / 'dev' / name).symlink_to('/proc/self/fd/' + str(descriptor))
    trace('data mounts')
    for entry in specification['mounts']:
        bind(root, entry['source'], entry['target'], entry['readonly'])
    (root / 'oldroot').mkdir()
    os.chdir(root)
    library = ctypes.CDLL(None, use_errno=True)
    if library.syscall(ctypes.c_long(155), ctypes.c_char_p(b'.'), ctypes.c_char_p(b'oldroot')):
        raise OSError(ctypes.get_errno(), 'pivot_root')
    os.chdir('/')
    if library.umount2(ctypes.c_char_p(b'/oldroot'), ctypes.c_int(2)):
        raise OSError(ctypes.get_errno(), 'detach old root')
    os.rmdir('/oldroot')
    trace('detached old root')
    ready_descriptor = specification.get('ready_fd')
    for descriptor in os.listdir('/proc/self/fd'):
        number = int(descriptor)
        if number > 2 and number != ready_descriptor:
            try:
                os.close(number)
            except OSError as error:
                if error.errno != errno.EBADF:
                    raise
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if specification.get('evaluation'):
        trace('evaluation limits')
        memory = specification['memory_mb'] * 1024**2
        setup_usage = resource.getrusage(resource.RUSAGE_SELF)
        seconds = math.ceil(specification['timeout'] + setup_usage.ru_utime + setup_usage.ru_stime)
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        mount('-o', 'remount,ro,nosuid,nodev', '/')
        evaluator_restrictions()
    trace('exec')
    os.chdir(specification['cwd'])
    if ready_descriptor is not None:
        os.write(ready_descriptor, (str(time.monotonic_ns()) + '\n').encode())
        os.close(ready_descriptor)
    os.execvpe(specification['command'][0], specification['command'], dict(os.environ))


def run_evaluation(specification, *, environment, timeout, max_output_bytes, setup_timeout=60):
    """Keep setup outside the solver deadline; never pass the ready FD to solve.py."""
    with private_directory('root_') as directory:
        ready_read, ready_write = os.pipe2(os.O_CLOEXEC)
        specification = dict(specification, root=str(Path(directory) / 'root'), ready_fd=ready_write)
        parent = {name: os.readlink('/proc/self/ns/' + name) for name in ('mnt', 'user', 'pid', 'net', 'ipc')}
        request = Path(directory) / 'request.json'
        request.write_text(json.dumps({'specification': specification, 'parent': parent}))
        request.chmod(0o600)
        command = ['/usr/bin/unshare', '--user', '--map-root-user', '--mount',
                   '--propagation', 'private', '--pid', '--fork', '--kill-child=KILL',
                   '--ipc', '--net', '/usr/bin/python3', '-I', str(Path(__file__).resolve()),
                   '--child', str(request)]
        started = time.monotonic()
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, env=environment, close_fds=True,
                                       pass_fds=(ready_write,), start_new_session=True)
        except BaseException:
            os.close(ready_read)
            raise
        finally:
            os.close(ready_write)
        buffers = {'stdout': bytearray(), 'stderr': bytearray()}
        ready_buffer = bytearray()
        ready_at = None
        timed_out = setup_timed_out = output_limited = False
        infrastructure_error = None
        deadline = started + setup_timeout
        selector = selectors.DefaultSelector()
        ready_stream = os.fdopen(ready_read, 'rb', buffering=0)
        for name, stream in [('ready', ready_stream), ('stdout', process.stdout), ('stderr', process.stderr)]:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        try:
            while selector.get_map() or process.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    if ready_at is None:
                        setup_timed_out = True
                        infrastructure_error = 'sandbox setup exceeded its separate deadline'
                    else:
                        timed_out = True
                    break
                for key, _events in selector.select(min(remaining, 0.1)):
                    block = os.read(key.fileobj.fileno(), 128 if key.data == 'ready' else 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data == 'ready':
                        ready_buffer.extend(block)
                        if b'\n' in ready_buffer:
                            try:
                                ready_at = int(ready_buffer.strip()) / 1_000_000_000
                            except ValueError:
                                infrastructure_error = 'invalid sandbox readiness marker'
                                break
                            if not started <= ready_at <= time.monotonic():
                                infrastructure_error = 'invalid sandbox readiness timestamp'
                                break
                            deadline = ready_at + timeout
                            selector.unregister(key.fileobj)
                            ready_stream.close()
                        elif len(ready_buffer) >= 128:
                            infrastructure_error = 'oversized sandbox readiness marker'
                            break
                        continue
                    room = max_output_bytes - sum(map(len, buffers.values()))
                    buffers[key.data].extend(block[:room])
                    if len(block) > room:
                        output_limited = True
                        break
                if output_limited or infrastructure_error:
                    break
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            selector.close()
            ready_stream.close()
            process.stdout.close()
            process.stderr.close()
        finished = time.monotonic()
        if ready_at is None and infrastructure_error is None:
            infrastructure_error = 'sandbox exited before executing submitted code'
        execution_seconds = finished - ready_at if ready_at is not None else 0.0
        return {'returncode': process.returncode, 'timed_out': timed_out,
                'setup_timed_out': setup_timed_out, 'infrastructure_error': infrastructure_error,
                'output_limited': output_limited, 'ready_received': ready_at is not None,
                'setup_seconds': (ready_at or finished) - started,
                'execution_seconds': execution_seconds, 'elapsed_seconds': execution_seconds,
                'wall_seconds': finished - started,
                **{name: bytes(value).decode('utf-8', errors='replace') for name, value in buffers.items()}}


def run_isolated(specification, *, environment, timeout, max_output_bytes=8 * 1024**2):
    """Return bounded stdout/stderr and telemetry, killing the entire PID tree."""
    if not 0 < timeout <= 3600 or max_output_bytes < 1:
        raise ValueError('Invalid execution limits')
    if specification.get('evaluation'):
        return run_evaluation(specification, environment=environment, timeout=timeout,
                              max_output_bytes=max_output_bytes)
    with private_directory('root_') as directory:
        specification = dict(specification, root=str(Path(directory) / 'root'))
        namespaces = ('mnt', 'user', 'pid', 'net', 'ipc') if specification.get('evaluation') else ('mnt', 'user', 'pid', 'ipc')
        parent = {name: os.readlink('/proc/self/ns/' + name) for name in namespaces}
        request = Path(directory) / 'request.json'
        request.write_text(json.dumps({'specification': specification, 'parent': parent}))
        request.chmod(0o600)
        command = ['/usr/bin/unshare', '--user', '--map-root-user', '--mount',
                   '--propagation', 'private', '--pid', '--fork', '--kill-child=KILL', '--ipc']
        if specification.get('evaluation'):
            command.append('--net')
        command += ['/usr/bin/python3', '-I', str(Path(__file__).resolve()), '--child', str(request)]
        started = time.monotonic()
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=environment, close_fds=True,
                                   start_new_session=True)
        buffers = {'stdout': bytearray(), 'stderr': bytearray()}
        timed_out = False
        output_limited = False
        selector = selectors.DefaultSelector()
        for name in buffers:
            stream = getattr(process, name)
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        try:
            while selector.get_map() or process.poll() is None:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    timed_out = True
                    break
                for key, _events in selector.select(min(remaining, 0.1)):
                    block = os.read(key.fileobj.fileno(), 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    room = max_output_bytes - sum(map(len, buffers.values()))
                    buffers[key.data].extend(block[:room])
                    if len(block) > room:
                        output_limited = True
                        break
                if output_limited:
                    break
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            selector.close()
            process.stdout.close()
            process.stderr.close()
        return {'returncode': process.returncode, 'timed_out': timed_out,
                'output_limited': output_limited, 'elapsed_seconds': time.monotonic() - started,
                **{name: bytes(value).decode('utf-8', errors='replace') for name, value in buffers.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', required=True, type=Path)
    arguments = parser.parse_args()
    try:
        request = json.loads(arguments.child.read_text())
        child(request['specification'], request['parent'])
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('isolation setup failed: ' + str(error), file=sys.stderr, flush=True)
        raise SystemExit(125)
