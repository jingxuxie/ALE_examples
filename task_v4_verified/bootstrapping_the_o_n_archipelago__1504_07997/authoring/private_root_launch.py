"""Launch the original allowlisted runner inside an isolated private root.

Invoke through unshare --user --map-root-user --mount --propagation private
--pid --fork. Capture --parent-mount-namespace before entering unshare, or
provide the same token in ALE_PARENT_MNT_NS. Resource limits are inherited.
"""

import argparse
import ctypes
import errno
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile


SYSTEM_DIRECTORIES = ('usr', 'bin', 'sbin', 'lib', 'lib64')
SYSTEM_CONFIGURATION = (
    'ld.so.cache', 'nsswitch.conf', 'hosts', 'resolv.conf', 'passwd', 'group',
    'localtime', 'os-release', 'gai.conf', 'ssl/certs', 'ssl/openssl.cnf',
)
DEVICES = ('full', 'null', 'zero', 'random', 'urandom', 'tty')


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--participant', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--runtime-home', required=True, type=Path)
    parser.add_argument('--runner', required=True, type=Path)
    parser.add_argument('--prompt-file', required=True, type=Path)
    parser.add_argument('--parent-mount-namespace', default=os.environ.get('ALE_PARENT_MNT_NS'))
    return parser.parse_args()


def require_namespaces(parent_namespace):
    if not parent_namespace or not re.fullmatch(r'mnt:\[\d+\]', parent_namespace):
        raise ValueError('Capture --parent-mount-namespace or ALE_PARENT_MNT_NS before unshare')
    if os.readlink('/proc/self/ns/mnt') == parent_namespace:
        raise RuntimeError('Refusing to modify the caller mount namespace')
    if os.getpid() != 1 or os.geteuid() != 0:
        raise RuntimeError('Requires PID 1 in fresh user, mount, and PID namespaces')
    for filename in ('uid_map', 'gid_map'):
        mappings = Path('/proc/self', filename).read_text().splitlines()
        if len(mappings) != 1:
            raise RuntimeError('Requires a single-user namespace mapping')
        inside, _outside, count = map(int, mappings[0].split())
        if inside != 0 or count != 1:
            raise RuntimeError('Requires --user --map-root-user')
    if os.uname().machine != 'x86_64':
        raise RuntimeError('This validated pivot_root implementation requires x86_64')


def validate_arguments(arguments):
    for name in ('participant', 'output', 'runtime_home'):
        directory = getattr(arguments, name).resolve(strict=True)
        if not directory.is_dir() or directory == Path('/'):
            raise ValueError(name + ' must be a specific existing directory')
        setattr(arguments, name, directory)
    directories = (arguments.participant, arguments.output, arguments.runtime_home)
    for position, directory in enumerate(directories):
        for other in directories[position + 1:]:
            if directory.is_relative_to(other) or other.is_relative_to(directory):
                raise ValueError('Participant, output, and runtime home must be disjoint')
    if any(arguments.output.iterdir()):
        raise ValueError('Output must initially be empty')
    arguments.runner = arguments.runner.resolve(strict=True)
    expected_runner = Path(__file__).resolve().parents[3] / 'run_allowlisted_codex.sh'
    if arguments.runner != expected_runner.resolve(strict=True):
        raise ValueError('--runner must name this repository original run_allowlisted_codex.sh')
    if not arguments.runner.is_file() or not os.access(arguments.runner, os.X_OK):
        raise ValueError('Original runner must be an executable file')
    for directory in directories:
        if arguments.runner.is_relative_to(directory):
            raise ValueError('The original runner must be outside participant, output, and runtime home')
    for relative in ('packages', 'packages/bin', 'tmp/arg0'):
        runtime_directory = arguments.runtime_home / relative
        if not runtime_directory.is_dir() or runtime_directory.resolve(strict=True) != runtime_directory:
            raise ValueError('Runtime allowlisted directories must be real directories, not symlinks')
    configuration = arguments.runtime_home / 'config.toml'
    if not configuration.is_file() or configuration.is_symlink():
        raise ValueError('Runtime home must contain its own config.toml')
    for filename in ('auth.json', 'model_catalog.json'):
        runtime_file = arguments.runtime_home / filename
        if runtime_file.is_symlink():
            raise ValueError('Runtime authentication/catalog files must not be symlinks')
    binary = (arguments.runtime_home / 'packages/bin/codex').resolve(strict=True)
    if not binary.is_relative_to(arguments.runtime_home / 'packages') or not os.access(binary, os.X_OK):
        raise ValueError('Use the native executable inside runtime-home/packages/bin')
    with binary.open('rb') as executable:
        if executable.read(4) != b'\x7fELF':
            raise ValueError('The runtime codex executable must be a native ELF binary')
    arguments.prompt_file = arguments.prompt_file.resolve(strict=True)
    if not arguments.prompt_file.is_file():
        raise ValueError('Prompt file must be a regular file')
    sources = list(directories) + [arguments.runner]
    sources.extend(Path('/' + name).resolve() for name in SYSTEM_DIRECTORIES)
    sources.extend(Path('/etc', name).resolve() for name in SYSTEM_CONFIGURATION)
    sources.extend(Path('/dev', name).resolve() for name in DEVICES)
    for source in sources:
        if arguments.prompt_file == source or arguments.prompt_file.is_relative_to(source):
            raise ValueError('Private prompt file must not be inside any mounted source')
    try:
        prompt = arguments.prompt_file.read_text(encoding='utf-8')
    except UnicodeError:
        raise ValueError('Prompt file must contain UTF-8 text') from None
    if not prompt.strip() or '\0' in prompt:
        raise ValueError('Prompt must be nonempty text without NUL characters')
    return prompt


def mount(*arguments):
    subprocess.run(['/bin/mount', '-n', *arguments], check=True, stdin=subprocess.DEVNULL)


def bind(root, source, readonly=True):
    source = Path(source)
    target = root / source.relative_to('/')
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        target.mkdir(exist_ok=True)
    else:
        target.touch(exist_ok=True)
    mount('--bind', str(source), str(target))
    if readonly:
        mount('-o', 'remount,bind,ro', str(target))


def build_root(arguments):
    parent = Path(__file__).resolve().parent / '.private_roots'
    parent.mkdir(mode=0o700, exist_ok=True)
    metadata = parent.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
        raise RuntimeError('Private root staging parent must be an owned mode-0700 directory')
    root = Path(tempfile.mkdtemp(prefix='launch_', dir=parent))
    mount('--make-rprivate', '/')
    mount('-t', 'tmpfs', '-o', 'nosuid,nodev,mode=0700', 'tmpfs', str(root))
    for name in SYSTEM_DIRECTORIES:
        source = Path('/') / name
        if source.is_symlink():
            (root / name).symlink_to(os.readlink(source))
        elif source.exists():
            bind(root, source)
    for name in SYSTEM_CONFIGURATION:
        source = Path('/etc') / name
        if source.exists():
            bind(root, source)
    for name in ('tmp', 'proc', 'dev', 'dev/shm'):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / 'tmp').chmod(0o1777)
    mount('-t', 'proc', '-o', 'nosuid,nodev,noexec', 'proc', str(root / 'proc'))
    for name in DEVICES:
        bind(root, '/dev/' + name, readonly=False)
    (root / 'dev/fd').symlink_to('/proc/self/fd')
    for name, descriptor in (('stdin', 0), ('stdout', 1), ('stderr', 2)):
        (root / 'dev' / name).symlink_to('/proc/self/fd/' + str(descriptor))
    bind(root, arguments.runner)
    bind(root, arguments.runtime_home, readonly=False)
    bind(root, arguments.participant)
    bind(root, arguments.output, readonly=False)
    return root


def enter_root(root):
    (root / 'oldroot').mkdir()
    os.chdir(root)
    library = ctypes.CDLL(None, use_errno=True)
    if library.syscall(ctypes.c_long(155), ctypes.c_char_p(b'.'), ctypes.c_char_p(b'oldroot')) != 0:
        raise OSError(ctypes.get_errno(), 'pivot_root failed')
    os.chdir('/')
    if library.umount2(ctypes.c_char_p(b'/oldroot'), ctypes.c_int(2)) != 0:
        raise OSError(ctypes.get_errno(), 'detaching the old root failed')
    os.rmdir('/oldroot')
    for descriptor in os.listdir('/proc/self/fd'):
        descriptor_number = int(descriptor)
        if descriptor_number > 2:
            try:
                os.close(descriptor_number)
            except OSError as error:
                if error.errno != errno.EBADF:
                    raise
    standard_input = os.open('/dev/null', os.O_RDONLY)
    os.dup2(standard_input, 0)
    if standard_input != 0:
        os.close(standard_input)


def controller_environment(runtime_home):
    retained = (
        'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_ORG_ID', 'OPENAI_PROJECT_ID',
        'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_ENDPOINT', 'TZ',
        'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
        'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy',
        'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS',
    )
    environment = {name: os.environ[name] for name in retained if name in os.environ}
    environment.update({
        'PATH': str(runtime_home / 'packages/bin') + ':/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin',
        'HOME': str(runtime_home),
        'CODEX_HOME': str(runtime_home),
        'TMPDIR': '/tmp',
        'LANG': 'C.UTF-8',
    })
    return environment


def main():
    arguments = parse_arguments()
    require_namespaces(arguments.parent_mount_namespace)
    prompt = validate_arguments(arguments)
    environment = controller_environment(arguments.runtime_home)
    command = [str(arguments.runner), '--model', 'ultima-alpha', '--effort', 'high',
               '--task-read-only', str(arguments.participant), str(arguments.output), prompt]
    root = build_root(arguments)
    enter_root(root)
    os.chdir(arguments.participant)
    print('private-root: isolated root ready; executing unchanged allowlisted runner (ultima-alpha)', file=sys.stderr, flush=True)
    os.execve(arguments.runner, command, environment)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print('private-root: ' + str(error), file=sys.stderr, flush=True)
        raise SystemExit(2)
