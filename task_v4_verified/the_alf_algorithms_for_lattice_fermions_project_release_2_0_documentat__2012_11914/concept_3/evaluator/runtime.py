"""Fail-closed, whitelist-only Linux bubblewrap submission execution."""

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
import zipfile


WALL_SECONDS = 120.0
MEMORY_BYTES = 2 * 1024**3
SUBMISSION_BYTES = 100_000_000
OUTPUT_BYTES = 16 * 1024**2


class ExecutionError(ValueError):
    def __init__(self, reason, runtime_seconds=0.0, details=None):
        super().__init__(reason)
        self.runtime_seconds = runtime_seconds
        self.details = details or {}


def read_prediction(path):
    import numpy as np

    if path.is_symlink() or not path.is_file():
        raise ValueError("prediction output is absent or is not a regular file")
    if path.stat().st_size > OUTPUT_BYTES:
        raise ValueError("prediction archive exceeds the output size limit")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        expected = {"sample_id.npy", "spectral_mass.npy", "low_mass_quantiles.npy"}
        if len(members) != 3 or {member.filename for member in members} != expected:
            raise ValueError("prediction archive must contain exactly the three specified arrays")
        if sum(member.file_size for member in members) > OUTPUT_BYTES:
            raise ValueError("uncompressed prediction archive exceeds the output size limit")
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def snapshot_submission(source, destination):
    source = Path(source).absolute()
    if source.is_symlink() or not source.is_dir():
        raise ExecutionError("submission must be a real directory, not a symlink")
    total = 0
    count = 0
    for root, directories, filenames in os.walk(source, followlinks=False):
        for name in directories + filenames:
            path = Path(root) / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ExecutionError("submission may contain only regular files and directories")
            if stat.S_ISREG(mode):
                total += path.stat().st_size
                count += 1
        if total > SUBMISSION_BYTES or count > 10000:
            raise ExecutionError("submission exceeds 100 MB or 10000 files")
    if not (source / "solve.py").is_file():
        raise ExecutionError("submission is missing solve.py")
    shutil.copytree(source, destination)
    return total


def execute_submission(submission, input_path, public_input, wall_seconds=WALL_SECONDS):
    if not Path("/usr/bin/bwrap").is_file():
        raise ExecutionError("bubblewrap is required; no unsandboxed fallback exists")
    with tempfile.TemporaryDirectory(prefix="alf-spectral-eval-") as temporary:
        staging = Path(temporary)
        submission_bytes = snapshot_submission(submission, staging / "submission")
        shutil.copyfile(input_path, staging / "features.npz")
        (staging / "output").mkdir()
        command = [
            "/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session",
            "--cap-drop", "ALL", "--ro-bind", "/usr", "/usr",
        ]
        for library in ("/lib", "/lib64"):
            if Path(library).exists():
                command.extend(["--ro-bind", library, library])
        command.extend(["--dir", "/etc"])
        for configuration in ("/etc/alternatives", "/etc/ld.so.cache"):
            if Path(configuration).exists():
                command.extend(["--ro-bind", configuration, configuration])
        command.extend([
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--ro-bind", str(staging / "submission"), "/submission",
            "--ro-bind", str(Path(public_input).resolve()), "/public/input",
            "--ro-bind", str(staging / "features.npz"), "/input.npz",
            "--bind", str(staging / "output"), "/output",
            "--chdir", "/submission", "/usr/bin/python3", "-B",
            "/submission/solve.py", "/input.npz", "/output/predictions.npz",
        ])
        environment = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/tmp",
            "TMPDIR": "/tmp",
            "LANG": "C.UTF-8",
            "PYTHONPATH": "/public/input",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }

        def limit_resources():
            resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
            resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_BYTES, OUTPUT_BYTES))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(wall_seconds), math.ceil(wall_seconds) + 1))
            resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
            if hasattr(os, "sched_getaffinity"):
                os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

        start = time.perf_counter()
        with (staging / "stdout.log").open("wb") as stdout, (staging / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                env=environment,
                cwd=staging,
                close_fds=True,
                start_new_session=True,
                preexec_fn=limit_resources,
            )
            timed_out = False
            try:
                while True:
                    finished, status, usage = os.wait4(process.pid, os.WNOHANG)
                    if finished:
                        process.returncode = os.waitstatus_to_exitcode(status)
                        break
                    if time.perf_counter() - start > wall_seconds:
                        timed_out = True
                        os.killpg(process.pid, signal.SIGKILL)
                        _, status, usage = os.wait4(process.pid, 0)
                        process.returncode = os.waitstatus_to_exitcode(status)
                        break
                    time.sleep(0.02)
            finally:
                if process.returncode is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        elapsed = time.perf_counter() - start
        details = {
            "runtime_seconds": elapsed,
            "launcher_cpu_seconds": float(usage.ru_utime + usage.ru_stime),
            "launcher_peak_rss_bytes": int(usage.ru_maxrss * 1024),
            "submission_bytes": submission_bytes,
            "runtime_source": "evaluator monotonic clock; authoritative wall time includes worker lifetime",
            "resource_diagnostic_scope": "wait4 launcher usage only; not aggregate worker CPU/RSS; RLIMIT_AS is enforced per process",
            "isolation": "bubblewrap whitelist, all namespaces, sanitized environment, one CPU",
        }
        if timed_out:
            raise ExecutionError("submission exceeded wall-time limit", elapsed, details)
        if process.returncode != 0:
            diagnostic = (staging / "stderr.log").read_bytes()[:2000].decode("utf-8", errors="replace")
            raise ExecutionError(f"sandboxed submission exited {process.returncode}: {diagnostic}", elapsed, details)
        try:
            prediction = read_prediction(staging / "output/predictions.npz")
        except Exception as error:
            raise ExecutionError(f"malformed prediction: {error}", elapsed, details) from error
        return prediction, details
