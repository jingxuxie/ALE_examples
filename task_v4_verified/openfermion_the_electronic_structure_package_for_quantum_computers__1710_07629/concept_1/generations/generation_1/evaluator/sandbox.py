"""Exec-only Linux sandbox; import this module only in the trusted parent.

The payload cannot create processes or threads. This keeps CPU/address-space
limits aggregate and makes supervisor death kill the entire payload. No unsafe
fallback is attempted. Landlock restricts file contents, not pathname metadata.
"""

import ctypes
import errno
import fcntl
import json
import os
from pathlib import Path
import resource
import signal
import stat
import sys


USER_SITE = Path("/home/xuandong/.local/lib/python3.10/site-packages")
SYSTEM_ROOTS = (Path("/usr"), Path("/lib"), Path("/lib64"), Path("/bin"))
SAFE_PATH = "/usr/bin:/bin:/usr/local/bin"
PACKAGE_ROOTS = (Path("/usr/lib/python3/dist-packages"),
                 Path("/usr/local/lib/python3.10/dist-packages"),
                 Path("/usr/local/lib/python3.10/site-packages"), USER_SITE)


def _within(path, roots):
    return any(path == root or root in path.parents for root in roots)


def _directory(value, name):
    path = Path(value).resolve(strict=True)
    if not path.is_dir():
        raise ValueError(f"{name} must be an existing directory")
    return path


def sandbox_command(command, env, participant, submission, scratch,
                    cpu_seconds=180, memory_mb=2048):
    """Return argv/env for Popen with pipe stdin/stdout/stderr and close_fds=True.

    Call Popen directly from this process. cwd=submission and
    start_new_session=True are supported. PYTHONPATH and a participant-contained
    QAOA_ASSET_DIR are retained from env; PYTHONPATH entries must lie inside the
    explicit read allowlist. Sources are
    not copied or made writable. Use TMPDIR for all output/build artifacts.
    """
    if sys.platform != "linux" or os.uname().machine != "x86_64":
        raise RuntimeError("sandbox requires Linux x86_64 with Landlock/seccomp")
    if isinstance(command, (str, bytes)) or not command:
        raise ValueError("command must be a nonempty argv sequence")
    command = [os.fspath(argument) for argument in command]
    if any(not isinstance(argument, str) or "\0" in argument for argument in command):
        raise ValueError("command arguments must be strings without NUL")
    if Path(command[0]).name in ("python", "python3", "python3.10"):
        command.insert(1, "-S")
    for value, name in ((cpu_seconds, "cpu_seconds"), (memory_mb, "memory_mb")):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    participant = _directory(participant, "participant")
    submission = _directory(submission, "submission")
    scratch = _directory(scratch, "scratch")
    inputs = [participant, submission]
    runtime = list(dict.fromkeys(path.resolve() for path in SYSTEM_ROOTS if path.exists()))
    if USER_SITE.is_dir():
        runtime.append(USER_SITE.resolve())
    readonly = inputs + runtime
    if _within(scratch, readonly) or any(_within(path, [scratch]) for path in readonly):
        raise ValueError("scratch must not overlap any read-only tree")
    if _within(Path(__file__).resolve(), inputs):
        raise ValueError("participant/submission must not expose the private launcher")
    if scratch.stat().st_uid != os.getuid():
        raise ValueError("scratch must belong to the evaluator user")
    os.chmod(scratch, 0o700)
    pythonpath = []
    for entry in env.get("PYTHONPATH", "").split(os.pathsep):
        if not entry:
            continue
        path = Path(entry)
        if not path.is_absolute():
            path = submission / path
        path = path.resolve(strict=True)
        if not _within(path, readonly):
            raise ValueError(f"PYTHONPATH entry outside read allowlist: {path}")
        pythonpath.append(str(path))
    pythonpath.extend(str(path.resolve()) for path in (submission,) + PACKAGE_ROOTS
                      if path.is_dir())
    clean_env = {
        "PATH": SAFE_PATH,
        "HOME": str(scratch), "TMPDIR": str(scratch), "TMP": str(scratch),
        "TEMP": str(scratch), "XDG_CACHE_HOME": str(scratch),
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC",
        "PYTHONPATH": os.pathsep.join(dict.fromkeys(pythonpath)),
        "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1", "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1",
        "BLIS_NUM_THREADS": "1",
    }
    if "QAOA_ASSET_DIR" in env:
        assets = _directory(env["QAOA_ASSET_DIR"], "QAOA_ASSET_DIR")
        if not _within(assets, [participant]):
            raise ValueError("QAOA_ASSET_DIR must be inside participant")
        clean_env["QAOA_ASSET_DIR"] = str(assets)
    config = dict(command=command, readonly=[str(path) for path in readonly],
                  submission=str(submission), scratch=str(scratch),
                  cpu_seconds=cpu_seconds, memory_mb=memory_mb,
                  parent_pid=os.getpid())
    argv = ["/usr/bin/python3", "-I", "-B", "-S", str(Path(__file__).resolve()),
            "--launch", json.dumps(config, separators=(",", ":"))]
    return argv, clean_env


class _Ruleset(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _PathRule(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int)]


class _Comparison(ctypes.Structure):
    _fields_ = [("argument", ctypes.c_uint), ("operation", ctypes.c_uint),
                ("datum_a", ctypes.c_uint64), ("datum_b", ctypes.c_uint64)]


def _checked(result, operation):
    if result < 0:
        error = ctypes.get_errno()
        raise OSError(error, f"{operation}: {os.strerror(error)}")
    return result


def _prctl(libc, option, value):
    _checked(libc.prctl(option, ctypes.c_ulong(value), 0, 0, 0), "prctl")


def _parent_death(libc, parent_pid):
    _prctl(libc, 1, signal.SIGKILL)
    if os.getppid() != parent_pid:
        raise RuntimeError("trusted parent exited before sandbox setup")


def _landlock(libc, readonly, scratch):
    abi = _checked(libc.syscall(444, 0, 0, 1), "Landlock ABI query")
    if abi < 1:
        raise RuntimeError("Landlock is unavailable")
    handled = (1 << 13) - 1
    if abi >= 2:
        handled |= 1 << 13
    if abi >= 3:
        handled |= 1 << 14
    attributes = _Ruleset(handled)
    ruleset = _checked(libc.syscall(444, ctypes.byref(attributes),
                                  ctypes.sizeof(attributes), 0), "Landlock create")
    try:
        read_rights = (1 << 0) | (1 << 2) | (1 << 3)
        scratch_rights = handled & ~((1 << 6) | (1 << 9) | (1 << 10) | (1 << 11))
        rules = [(path, read_rights) for path in readonly]
        rules.extend([(scratch, scratch_rights), ("/dev/null", (1 << 1) | (1 << 2)),
                      ("/dev/urandom", 1 << 2), ("/dev/random", 1 << 2)])
        for path, rights in rules:
            descriptor = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = _PathRule(rights, descriptor)
                _checked(libc.syscall(445, ruleset, 1, ctypes.byref(rule), 0),
                         "Landlock add path")
            finally:
                os.close(descriptor)
        _checked(libc.syscall(446, ruleset, 0), "Landlock restrict")
    finally:
        os.close(ruleset)


def _seccomp(library):
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    library.seccomp_load.argtypes = [ctypes.c_void_p]
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                             ctypes.c_int, ctypes.c_uint,
                                             ctypes.POINTER(_Comparison)]
    context = library.seccomp_init(0x00050000 | errno.EPERM)
    if not context:
        raise RuntimeError("seccomp_init failed")
    allow = 0x7FFF0000

    def rule(name, comparisons=(), action=allow):
        number = library.seccomp_syscall_resolve_name(name.encode("ascii"))
        if number < 0:
            raise RuntimeError(f"unknown required syscall: {name}")
        arguments = (_Comparison * len(comparisons))(*comparisons)
        result = library.seccomp_rule_add_array(context, action, number,
                                               len(comparisons), arguments)
        if result != 0:
            raise RuntimeError(f"seccomp rule {name} failed: {result}")

    try:
        for name in (
            "read write readv writev pread64 pwrite64 close close_range dup dup2 dup3 lseek "
            "fstat newfstatat stat lstat statx access faccessat faccessat2 "
            "readlink readlinkat getdents getdents64 creat "
            "mmap mprotect munmap mremap brk madvise membarrier "
            "rt_sigaction rt_sigprocmask rt_sigreturn rt_sigsuspend rt_sigtimedwait "
            "sigaltstack restart_syscall futex arch_prctl set_tid_address "
            "set_robust_list rseq getpid getppid gettid getuid geteuid getgid "
            "getegid getgroups uname sysinfo getcwd chdir fchdir "
            "execve execveat exit exit_group wait4 waitid "
            "sched_getaffinity sched_yield sched_getparam sched_getscheduler "
            "getpriority getrlimit clock_gettime clock_getres gettimeofday time "
            "nanosleep clock_nanosleep times getrusage getrandom getcpu "
            "poll ppoll select pselect6 epoll_create epoll_create1 epoll_ctl "
            "epoll_wait epoll_pwait eventfd eventfd2 pipe pipe2 "
            "fsync fdatasync sync_file_range mkdir mkdirat rmdir unlink unlinkat "
            "rename renameat renameat2 link linkat symlink symlinkat umask"
        ).split():
            rule(name)
        for name, position in (("open", 1), ("openat", 2)):
            rule(name, [_Comparison(position, 7, os.O_TRUNC, 0)])
            for access in (os.O_WRONLY, os.O_RDWR):
                rule(name, [_Comparison(position, 7, os.O_ACCMODE, access)])
        for operation in (0, 1, 2, 3, 4, 5, 6, 7, 1030):
            rule("fcntl", [_Comparison(1, 4, operation, 0)])
        rule("prlimit64", [_Comparison(2, 4, 0, 0)])
        for operation in (0x5401, 0x5450, 0x5451):
            rule("ioctl", [_Comparison(1, 4, operation, 0)])
        rule("clone3", action=0x00050000 | errno.ENOSYS)
        result = library.seccomp_load(context)
        if result != 0:
            raise RuntimeError(f"seccomp_load failed: {result}")
    finally:
        library.seccomp_release(context)


def _seal_descriptors(config):
    readable = [Path(path) for path in config["readonly"]] + [Path(config["scratch"])]
    for descriptor in range(3):
        metadata = os.fstat(descriptor)
        if stat.S_ISFIFO(metadata.st_mode):
            continue
        if stat.S_ISCHR(metadata.st_mode) and metadata.st_rdev == os.makedev(1, 3):
            continue
        if stat.S_ISREG(metadata.st_mode):
            target = Path(os.readlink(f"/proc/self/fd/{descriptor}")).resolve()
            access = fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE
            roots = readable if access == os.O_RDONLY else [Path(config["scratch"])]
            if _within(target, roots):
                continue
        raise RuntimeError(f"unsafe inherited standard descriptor: {descriptor}")
    for entry in os.listdir("/proc/self/fd"):
        descriptor = int(entry)
        if descriptor > 2:
            try:
                os.close(descriptor)
            except OSError as error:
                if error.errno != errno.EBADF:
                    raise


def _payload(config, libc, supervisor_pid):
    _parent_death(libc, supervisor_pid)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    _prctl(libc, 4, 0)
    _prctl(libc, 38, 1)
    os.umask(0o077)
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    memory = config["memory_mb"] * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (config["cpu_seconds"], config["cpu_seconds"]))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    library = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    _seal_descriptors(config)
    os.chdir(config["submission"])
    _landlock(libc, config["readonly"], config["scratch"])
    _seccomp(library)
    os.execvpe(config["command"][0], config["command"], os.environ)


def _launch(config):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    _parent_death(libc, config["parent_pid"])
    _prctl(libc, 4, 0)
    supervisor_pid = os.getpid()
    child_pid = os.fork()
    if child_pid == 0:
        try:
            _payload(config, libc, supervisor_pid)
        except BaseException as error:
            print(f"sandbox setup/exec failed: {error}", file=sys.stderr, flush=True)
            os._exit(125)

    def terminate(signum, frame):
        try:
            os.kill(child_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    _, status = os.waitpid(child_pid, 0)
    returncode = os.waitstatus_to_exitcode(status)
    return returncode if returncode >= 0 else 128 - returncode


if __name__ == "__main__":
    try:
        if len(sys.argv) != 3 or sys.argv[1] != "--launch":
            raise ValueError("use sandbox_command from the trusted evaluator")
        raise SystemExit(_launch(json.loads(sys.argv[2])))
    except Exception as error:
        print(f"sandbox refused execution: {error}", file=sys.stderr, flush=True)
        raise SystemExit(125)
