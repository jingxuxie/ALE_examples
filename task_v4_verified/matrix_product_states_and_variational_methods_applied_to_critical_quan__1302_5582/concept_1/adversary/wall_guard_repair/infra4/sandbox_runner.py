"""Fail-closed bwrap runner. No participant module is imported by the host."""

import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import stat
import subprocess
import tempfile
import time


class SandboxUnavailable(RuntimeError):
    pass


def sandbox_command(submission, participant, scratch, request, output, public_source=None):
    executable = Path("/usr/bin/bwrap")
    if not executable.is_file():
        raise SandboxUnavailable("/usr/bin/bwrap is required; no unsandboxed fallback")
    command = [str(executable), "--die-with-parent", "--new-session", "--unshare-all",
               "--cap-drop", "ALL", "--clearenv"]
    for directory in ("/usr", "/bin", "/lib", "/lib64"):
        if Path(directory).exists():
            command += ["--ro-bind", directory, directory]
    if Path("/etc/ld.so.cache").exists():
        command += ["--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache"]
    if Path("/etc/alternatives").exists():
        command += ["--ro-bind", "/etc/alternatives", "/etc/alternatives"]
    public_source = participant if public_source is None else public_source
    command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                "--ro-bind", str(submission), "/submission",
                "--ro-bind", str(public_source), "/public",
                "--ro-bind", str(public_source), str(participant),
                "--ro-bind", str(public_source.parent / "worker.py"), "/worker.py",
                "--bind", str(scratch), "/work", "--chdir", "/submission"]
    environment = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "TMPDIR": "/tmp",
                   "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
                   "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                   "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
                   "VECLIB_MAXIMUM_THREADS": "1", "BLIS_NUM_THREADS": "1"}
    for name, value in environment.items():
        command += ["--setenv", name, value]
    bootstrap = (public_source.parent / "worker.py").read_text()
    command += ["/usr/bin/python", "-I", "-B", "-c", bootstrap]
    return command


def run_submission(submission, participant, scratch, request):
    scratch = Path(scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    submission = Path(submission).resolve()
    participant = Path(participant).resolve()
    for source in (submission, participant):
        if any(path.is_symlink() for path in source.rglob("*")):
            raise ValueError("linked staged assets are not allowed")
    with tempfile.TemporaryDirectory(prefix="phi4-mps-", dir="/tmp") as directory:
        local = Path(directory)
        shutil.copytree(submission, local / "submission", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(participant, local / "public", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copyfile(Path(__file__).with_name("worker.py"), local / "worker.py")
        local_scratch = local / "work"
        local_scratch.mkdir()
        result = run_local(local / "submission", participant, local_scratch, request, local / "public")
        for name in ("stdout.log", "stderr.log", "request.json", "resource.json", "state.npz"):
            source = local_scratch / name
            if not source.exists() and not source.is_symlink():
                continue
            metadata = source.lstat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                result.update(process_valid=False, error="output artifacts must be regular non-linked files")
                continue
            shutil.copyfile(source, scratch / name)
        result["state_path"] = str(scratch / "state.npz")
        result["staging"] = "public assets and submission copied to local /tmp before timed execution"
        return result


def run_local(submission, participant, scratch, request, public_source):
    request_path = scratch / "request.json"
    request_path.write_text(json.dumps(request, allow_nan=False))
    command = sandbox_command(submission, participant, scratch, "request.json", "state.npz", public_source)
    cpu_limit = float(request["budget_seconds"])
    wall_limit = float(request["wall_seconds"])

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(cpu_limit) + 1, math.ceil(cpu_limit) + 2))
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 ** 2, 16 * 1024 ** 2))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    start = time.monotonic()
    outer_timed_out = False
    with (scratch / "stdout.log").open("wb") as stdout, (scratch / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                   preexec_fn=limits, start_new_session=True, close_fds=True)
        try:
            process.wait(timeout=120.0 + wall_limit)
        except subprocess.TimeoutExpired:
            outer_timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    outer_wall = time.monotonic() - start
    wall = outer_wall
    timed_out = outer_timed_out
    cpu = 0.0
    resource_path = scratch / "resource.json"
    accounted = False
    if resource_path.exists() and not resource_path.is_symlink():
        metadata = resource_path.lstat()
        if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1 and metadata.st_size < 4096:
            try:
                accounting = json.loads(resource_path.read_text())
                cpu = float(accounting["cpu_seconds"])
                wall = float(accounting["worker_wall_seconds"])
                worker_timed_out = accounting["worker_timed_out"]
                child_exitcode = accounting["worker_exitcode"]
                expected_exitcode = child_exitcode if child_exitcode >= 0 else 128 - child_exitcode
                accounted = (math.isfinite(cpu) and cpu >= 0 and math.isfinite(wall) and wall >= 0
                             and isinstance(worker_timed_out, bool)
                             and isinstance(child_exitcode, int) and process.returncode == expected_exitcode
                             and accounting["accounting"] == "protected supervisor wait4 on direct solver child")
                timed_out = outer_timed_out or worker_timed_out
            except (ValueError, TypeError, KeyError, OSError):
                accounted = False
    if outer_timed_out and not accounted:
        raise SandboxUnavailable("outer safety watchdog expired without protected solver accounting; inconclusive, not a solver score")
    error_path = scratch / "stderr.log"
    error_metadata = error_path.lstat()
    if not stat.S_ISREG(error_metadata.st_mode) or error_metadata.st_nlink != 1:
        return {"process_valid": False, "returncode": process.returncode, "cpu_seconds": cpu,
                "wall_seconds": wall, "timed_out": timed_out,
                "error": "stderr must be a regular non-linked file", "state_path": str(scratch / "state.npz")}
    error = error_path.read_text(errors="replace")[-3000:]
    if process.returncode != 0 and ("bwrap:" in error or "bubblewrap" in error):
        raise SandboxUnavailable(error.strip())
    valid = process.returncode == 0 and not timed_out and accounted and cpu <= cpu_limit and wall <= wall_limit
    if not valid and not error:
        error = ("protected solver wall limit exceeded" if timed_out or wall > wall_limit else
                 "solver CPU limit exceeded" if accounted and cpu > cpu_limit else
                 "solver failed or protected resource accounting unavailable")
    return {"process_valid": valid, "returncode": process.returncode,
            "cpu_seconds": cpu, "cpu_accounted": accounted, "wall_seconds": wall, "timed_out": timed_out,
            "outer_wall_seconds": outer_wall, "outer_timed_out": outer_timed_out,
            "wall_accounting": "protected supervisor elapsed time on direct solver child",
            "error": error if not valid else "", "state_path": str(scratch / "state.npz")}
