import math
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import time

from oracle import InvalidResult, strict_json


ROOT = Path(__file__).resolve().parents[1]
CPU_SECONDS = 8.0
WALL_SECONDS = 180.0
MEMORY_BYTES = 1024 * 1024 * 1024
OUTPUT_BYTES = 65536


def sandbox_command(bundle, scratch, entrypoint, cpu_seconds):
    if shutil.which("bwrap") is None:
        raise InvalidResult("infrastructure: bubblewrap is required; no unrestricted fallback")
    command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--cap-drop", "ALL"]
    for directory in ("/usr", "/bin", "/lib", "/lib64"):
        if Path(directory).exists():
            command += ["--ro-bind", directory, directory]
    for path in ("/etc/ld.so.cache", "/etc/alternatives"):
        if Path(path).exists():
            command += ["--ro-bind", path, path]
    command += ["--ro-bind", str(bundle), "/submission", "--bind", str(scratch), "/work",
                "--ro-bind", str(ROOT / "evaluator" / "supervisor.py"), "/runtime/supervisor.py",
                "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--chdir", "/work",
                "--clearenv", "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp",
                "--setenv", "OPENBLAS_NUM_THREADS", "1", "--setenv", "OMP_NUM_THREADS", "1",
                "--setenv", "MKL_NUM_THREADS", "1", "--setenv", "NUMEXPR_NUM_THREADS", "1",
                "--setenv", "PYTHONHASHSEED", "0", "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
                "/usr/bin/python3", "-I", "/runtime/supervisor.py", entrypoint, str(cpu_seconds)]
    return command


def run_solution(solution, input_text, wall_seconds=WALL_SECONDS, cpu_seconds=CPU_SECONDS):
    solution = Path(solution).resolve()
    if not solution.is_file() or solution.suffix != ".py":
        raise InvalidResult("solution must be a Python file")
    bundle = solution.parent
    for private in (ROOT / "evaluator", ROOT / "adversary", ROOT / "attempts", ROOT / "champions"):
        if private == bundle or bundle in private.parents:
            raise InvalidResult("submission directory would expose private evaluator assets")
    runs = ROOT / "adversary" / ".runs"
    runs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="case_", dir=runs) as directory:
        scratch = Path(directory) / "work"
        control = Path(directory) / "control"
        scratch.mkdir()
        control.mkdir(mode=0o700)
        (scratch / "input.json").write_text(input_text, encoding="utf-8")
        command = sandbox_command(bundle, scratch, solution.name, cpu_seconds)
        started = time.monotonic()
        with (control / "resources.json").open("wb") as stdout, (control / "supervisor.stderr").open("wb") as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
            usage = None
            timed_out = False
            while usage is None:
                waited, status, result = os.wait4(process.pid, os.WNOHANG)
                if waited:
                    usage = result
                    process.returncode = os.waitstatus_to_exitcode(status)
                    break
                if time.monotonic() - started > wall_seconds:
                    timed_out = True
                    os.killpg(process.pid, signal.SIGKILL)
                    _, status, usage = os.wait4(process.pid, 0)
                    process.returncode = os.waitstatus_to_exitcode(status)
                    break
                time.sleep(0.02)
        elapsed = time.monotonic() - started
        if timed_out:
            raise InvalidResult("wall watchdog exceeded (180s default; not the scored resource)")
        if process.returncode != 0:
            detail = (control / "supervisor.stderr").read_text(errors="replace")[-1600:]
            raise InvalidResult("sandboxed execution failed: " + str(process.returncode) + "; " + detail)
        diagnostics = strict_json((control / "resources.json").read_text())
        diagnostics["wall_seconds"] = elapsed
        diagnostics["accounting"] = "protected direct-parent wait4"
        cpu = diagnostics["cpu_seconds"]
        if diagnostics["returncode"] != 0:
            detail = (scratch / "solution.stderr").read_text(errors="replace")[-1600:]
            raise InvalidResult("candidate failed: " + str(diagnostics["returncode"]) + "; " + detail)
        if cpu > cpu_seconds:
            raise InvalidResult("CPU budget exceeded")
        output_path = scratch / "output.json"
        try:
            metadata = output_path.lstat()
        except FileNotFoundError as error:
            raise InvalidResult("missing output") from error
        if not stat.S_ISREG(metadata.st_mode) or output_path.resolve().parent != scratch.resolve():
            raise InvalidResult("output must be a regular file contained in scratch")
        descriptor = os.open(output_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_size > OUTPUT_BYTES:
                raise InvalidResult("nonregular or oversized output")
            content = handle.read(OUTPUT_BYTES + 1)
        if len(content) > OUTPUT_BYTES:
            raise InvalidResult("oversized output")
        output = strict_json(content.decode("utf-8"))
        return output, diagnostics
