import ctypes
import os
from pathlib import Path
import platform
import resource


class Ruleset(ctypes.Structure):
    _fields_ = [('handled_access_fs', ctypes.c_uint64)]


class PathRule(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]


def restrict_solver(read_directory, work_directory, seconds=120, gibibytes=3):
    if platform.machine() not in ('x86_64', 'aarch64'):
        raise RuntimeError('Unsupported Landlock syscall architecture')
    library = ctypes.CDLL(None, use_errno=True)
    abi = library.syscall(444, 0, 0, 1)
    if abi < 1:
        raise RuntimeError('Landlock is required; refusing unsandboxed evaluation')
    handled = (1 << 13) - 1
    attributes = Ruleset(handled)
    descriptor = library.syscall(444, ctypes.byref(attributes), ctypes.sizeof(attributes), 0)
    if descriptor < 0:
        raise OSError(ctypes.get_errno(), 'landlock_create_ruleset')
    readable = (1 << 0) | (1 << 2) | (1 << 3)
    runtime = ['/usr', '/lib', '/lib64', '/bin', '/etc/ld.so.cache', '/etc/localtime',
               '/dev/urandom', '/dev/random', '/proc/cpuinfo', '/proc/meminfo']
    rules = [(entry, readable) for entry in runtime]
    rules.extend([(str(read_directory), readable), (str(work_directory), handled),
                  ('/dev/null', (1 << 1) | (1 << 2))])
    for entry, allowed in rules:
        path = Path(entry)
        if not path.exists():
            continue
        if not path.is_dir():
            allowed &= (1 << 0) | (1 << 1) | (1 << 2)
        parent = os.open(str(path), os.O_PATH | os.O_CLOEXEC)
        rule = PathRule(allowed, parent)
        status = library.syscall(445, descriptor, 1, ctypes.byref(rule), 0)
        os.close(parent)
        if status:
            raise OSError(ctypes.get_errno(), f'landlock_add_rule: {entry}')
    if library.prctl(38, 1, 0, 0, 0):
        raise OSError(ctypes.get_errno(), 'PR_SET_NO_NEW_PRIVS')
    if library.syscall(446, descriptor, 0):
        raise OSError(ctypes.get_errno(), 'landlock_restrict_self')
    os.close(descriptor)
    resource.setrlimit(resource.RLIMIT_AS, (gibibytes * 1024**3, gibibytes * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds + 5))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
