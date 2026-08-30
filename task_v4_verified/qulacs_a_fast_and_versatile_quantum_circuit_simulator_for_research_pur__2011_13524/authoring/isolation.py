import argparse
import ctypes
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time


SYSTEM_CONFIG = (
    "/etc/ld.so.cache", "/etc/alternatives", "/etc/nsswitch.conf",
    "/etc/hosts", "/etc/resolv.conf", "/etc/ssl/certs", "/etc/ssl/openssl.cnf",
    "/etc/passwd", "/etc/group", "/etc/localtime",
)


def landlock_status():
    if os.uname().machine != "x86_64":
        return {"supported": False, "reason": "ABI probe is x86_64-specific"}
    library = ctypes.CDLL(None, use_errno=True)
    version = library.syscall(444, 0, 0, 1)
    return {
        "abi": version,
        "errno": ctypes.get_errno() if version < 0 else 0,
        "equivalent_fallback_implemented": False,
        "reason": "Landlock alone is not a mount/PID/network namespace replacement; ABI < 3 cannot restrict truncation",
    }


def checked_directory(value):
    path = Path(value)
    if path.is_symlink():
        raise ValueError("An allowlisted directory cannot be a symlink")
    path = path.resolve(strict=True)
    if not path.is_dir() or path == Path("/"):
        raise ValueError("Expected a specific existing directory")
    return path


def check_tree(directory):
    for path in directory.rglob("*"):
        metadata = path.lstat()
        if path.name in {".git", ".codex", ".agents"}:
            raise ValueError(f"Agent/repository configuration is not permitted: {path}")
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"Symlinks are not permitted in the submitted tree: {path}")
        if stat.S_ISREG(metadata.st_mode):
            if metadata.st_nlink != 1:
                raise ValueError(f"Hardlinked files are not permitted: {path}")
        elif not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"Special files are not permitted: {path}")


def validate_pair(read_directory, write_directory):
    read_directory = checked_directory(read_directory)
    write_directory = checked_directory(write_directory)
    if read_directory == write_directory or read_directory in write_directory.parents or write_directory in read_directory.parents:
        raise ValueError("Read and write directories must be disjoint")
    if any(write_directory.iterdir()):
        raise ValueError("The writable directory must initially be empty")
    check_tree(read_directory)
    return read_directory, write_directory


def clean_environment():
    return {
        "PATH": "/usr/bin:/bin", "HOME": "/tmp", "TMPDIR": "/tmp",
        "SHELL": "/bin/bash", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "TERM": "dumb", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "TOKIO_WORKER_THREADS": "2", "RAYON_NUM_THREADS": "2",
    }


def bubblewrap_command(bindings, working_directory, command, network=False):
    arguments = [
        "/usr/bin/bwrap", "--unshare-user", "--unshare-pid", "--unshare-ipc",
        "--unshare-uts", "--die-with-parent", "--new-session", "--cap-drop", "ALL",
        "--ro-bind", "/usr", "/usr", "--proc", "/proc", "--dev", "/dev",
        "--tmpfs", "/tmp",
    ]
    if not network:
        arguments.append("--unshare-net")
    for name in ("bin", "sbin", "lib", "lib64", "lib32", "libx32"):
        source = Path("/") / name
        if source.is_symlink():
            arguments.extend(["--symlink", os.readlink(source), str(source)])
        elif source.exists():
            arguments.extend(["--ro-bind", str(source), str(source)])
    for name in SYSTEM_CONFIG:
        if Path(name).exists():
            arguments.extend(["--ro-bind", name, name])
    for source, destination, writable in bindings:
        arguments.extend(["--bind" if writable else "--ro-bind", str(source), str(destination)])
    arguments.extend(["--chdir", str(working_directory), "--"])
    if not network:
        arguments = ["/usr/bin/python3", "-I", str(Path(__file__).with_name("isolation_bwrap.py"))] + arguments[1:]
    return arguments + list(map(str, command))


def own_descendants():
    pending = [os.getpid()]
    descendants = set()
    while pending:
        process_id = pending.pop()
        try:
            children = Path(f"/proc/{process_id}/task/{process_id}/children").read_text().split()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        for child in map(int, children):
            if child not in descendants:
                descendants.add(child)
                pending.append(child)
    return descendants


def run_bounded(command, environment, seconds, log_path=None, input_bytes=None):
    if not 0 < seconds <= 3600:
        raise ValueError("Timeout must be positive and no greater than 3600 seconds")
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "Cannot become a child subreaper")
    started = time.monotonic()
    output = open(log_path, "xb") if log_path else None
    process = None
    timed_out = False
    try:
        process = subprocess.Popen(
            command, env=environment, cwd="/", start_new_session=True, close_fds=True,
            stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
            stdout=output, stderr=subprocess.STDOUT if output else None,
        )
        try:
            process.communicate(input=input_bytes, timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            for child in own_descendants():
                try:
                    os.kill(child, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=5)
            reap_deadline = time.monotonic() + 3
            while own_descendants() and time.monotonic() < reap_deadline:
                for child in own_descendants():
                    try:
                        os.kill(child, signal.SIGKILL)
                        os.waitpid(child, os.WNOHANG)
                    except (ChildProcessError, ProcessLookupError):
                        pass
                time.sleep(0.05)
        return {
            "returncode": 124 if timed_out else process.returncode,
            "timed_out": timed_out, "elapsed_seconds": round(time.monotonic() - started, 3),
            "limit_seconds": seconds, "remaining_owned_descendants": sorted(own_descendants()),
        }
    finally:
        if output:
            output.close()


def submission_command(submission, work, command):
    submission, work = validate_pair(submission, work)
    return bubblewrap_command(
        [(submission, submission, False), (work, work, True)], work, command, network=False,
    )


def main():
    parser = argparse.ArgumentParser(description="Fail-closed submission subprocess sandbox; never mounts evaluator or sibling outputs")
    parser.add_argument("--landlock-status", action="store_true")
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--stdin", action="store_true", help="Explicitly forward public per-case bytes from stdin, not a file descriptor")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    if arguments.landlock_status:
        print(json.dumps(landlock_status(), indent=2))
        return 0
    command = arguments.command
    if command and command[0] == "--":
        command = command[1:]
    if not arguments.submission or not arguments.work or not command:
        parser.error("--submission, --work, and a command after -- are required")
    isolated = submission_command(arguments.submission, arguments.work, command)
    input_bytes = sys.stdin.buffer.read(1048577) if arguments.stdin else None
    if input_bytes is not None and len(input_bytes) > 1048576:
        raise ValueError("Public stdin input exceeds the 1 MiB limit")
    result = run_bounded(isolated, clean_environment(), arguments.seconds, input_bytes=input_bytes)
    print(json.dumps({"submission_sandbox": result}), file=sys.stderr)
    return result["returncode"] or bool(result["remaining_owned_descendants"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"ISOLATION_REFUSED: {error}", file=sys.stderr)
        raise SystemExit(2)
