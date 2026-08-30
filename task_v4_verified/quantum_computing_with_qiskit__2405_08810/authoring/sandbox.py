import os
from pathlib import Path
import resource
import signal


def sandbox_command(participant_path, submission_path, entrypoint="solution.py", args=(), ready_marker=False, writable_submission=False):
    participant = Path(participant_path).resolve(strict=True)
    submission = Path(submission_path).resolve(strict=True)
    entry = Path(entrypoint)
    if entry.is_absolute() or ".." in entry.parts:
        raise ValueError("entrypoint must be relative to the submission")
    command = [
        "/usr/bin/bwrap", "--die-with-parent", "--new-session", "--unshare-all",
        "--cap-drop", "ALL", "--clearenv",
    ]
    for directory in ("/usr", "/bin", "/lib", "/lib64"):
        if Path(directory).exists():
            command.extend(["--ro-bind", directory, directory])
    command.extend(["--dir", "/etc"])
    for filename in ("/etc/ld.so.cache", "/etc/alternatives"):
        if Path(filename).exists():
            command.extend(["--ro-bind", filename, filename])
    command.extend([
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--ro-bind", str(participant), "/task",
        "--bind" if writable_submission else "--ro-bind", str(submission), "/submission",
        "--chdir", "/submission",
        "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "HOME", "/tmp",
        "--setenv", "TMPDIR", "/tmp",
        "--setenv", "PYTHONPATH", "/task/workspace:/submission",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
        "--setenv", "OPENBLAS_NUM_THREADS", "1",
        "--setenv", "OMP_NUM_THREADS", "1",
        "--setenv", "MKL_NUM_THREADS", "1",
    ])
    target = "/submission/" + str(entry)
    if ready_marker:
        wrapper = (
            "import runpy,sys; "
            "print('{\"sandbox_ready\":true}',flush=True); "
            f"sys.argv={[target, *map(str, args)]!r}; "
            f"runpy.run_path({target!r},run_name='__main__')"
        )
        command.extend(["/usr/bin/python3", "-u", "-c", wrapper])
    else:
        command.extend(["/usr/bin/python3", "-u", target, *map(str, args)])
    return command


def limits(cpu_seconds=120, memory_mb=2048):
    def apply_limits():
        available_cpus = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {available_cpus[os.getpid() % len(available_cpus)]})
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024**2, memory_mb * 1024**2))
        resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2, 32 * 1024**2))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        os.umask(0o077)
    return apply_limits


def stop_process(process):
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait()
