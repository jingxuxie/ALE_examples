import os
import resource
import shutil
import signal
import subprocess
import time
from pathlib import Path


class SubmissionFailure(ValueError):
    pass


def stage_submission(source, destination):
    source = Path(source).resolve()
    total = 0
    count = 0
    for path in source.rglob("*"):
        if path.is_symlink():
            raise SubmissionFailure("submission contains a symlink")
        if not path.is_file() and not path.is_dir():
            raise SubmissionFailure("submission contains a special file")
        if path.is_file():
            total += path.stat().st_size
            count += 1
    if total > 128 * 1024 * 1024 or count > 4096:
        raise SubmissionFailure("submission exceeds 128 MiB or 4096 files")
    if not (source / "solve.py").is_file():
        raise SubmissionFailure("missing solve.py")
    shutil.copytree(source, destination)


def run_isolated(submission, input_directory, scratch, timeout=60):
    scratch = Path(scratch)
    staged = scratch / "submission"
    staged_input = scratch / "input"
    writable = scratch / "output"
    stage_submission(submission, staged)
    shutil.copytree(input_directory, staged_input)
    writable.mkdir()
    command = ["/usr/bin/bwrap", "--die-with-parent", "--new-session", "--unshare-all",
               "--cap-drop", "ALL", "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
               "--ro-bind", "/lib64", "/lib64", "--ro-bind", "/etc/alternatives", "/etc/alternatives",
               "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache", "--proc", "/proc", "--dev", "/dev",
               "--tmpfs", "/tmp", "--ro-bind", str(staged), "/submission",
               "--ro-bind", str(staged_input), "/input", "--bind", str(writable), "/output",
               "--chdir", "/submission", "/usr/bin/python3", "-B", "/submission/solve.py",
               "--input", "/input", "--output", "/output/answer.json"]
    environment = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "TMPDIR": "/tmp",
                   "LANG": "C.UTF-8", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1",
                   "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "OMP_THREAD_LIMIT": "1",
                   "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
        resource.setrlimit(resource.RLIMIT_CPU, (int(timeout) + 1, int(timeout) + 2))
        resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 ** 2, 16 * 1024 ** 2))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        allowed = os.sched_getaffinity(0)
        os.sched_setaffinity(0, {min(allowed)})

    started = time.monotonic()
    with (scratch / "stdout.txt").open("wb") as stdout, (scratch / "stderr.txt").open("wb") as stderr:
        process = subprocess.Popen(command, env=environment, stdout=stdout, stderr=stderr,
                                   preexec_fn=limits, start_new_session=True)
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise SubmissionFailure("timeout after {} seconds".format(timeout))
    elapsed = time.monotonic() - started
    if process.returncode:
        diagnostic = (scratch / "stderr.txt").read_text(errors="replace")[-1200:]
        if "bwrap:" in diagnostic:
            raise RuntimeError("evaluator isolation unavailable; run evaluator outside outer sandbox: " + diagnostic)
        raise SubmissionFailure("submission exit {}: {}".format(process.returncode, diagnostic))
    output = writable / "answer.json"
    if not output.is_file() or output.is_symlink() or output.stat().st_size > 8 * 1024 ** 2:
        raise SubmissionFailure("missing, nonregular, or oversized output")
    return output.read_text(), elapsed
