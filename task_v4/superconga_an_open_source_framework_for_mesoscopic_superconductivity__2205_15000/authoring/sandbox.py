import os
import resource
import signal
import subprocess
import tempfile
from pathlib import Path


class Sandbox:
    def __init__(self, participant, submission, input_dir=None, seconds=120, memory_gib=4):
        self.participant = Path(participant).resolve()
        self.submission = Path(submission).resolve()
        self.input_dir = Path(input_dir).resolve() if input_dir else None
        self.seconds = int(seconds)
        self.memory_gib = int(memory_gib)
        self.temporary = tempfile.TemporaryDirectory(prefix="superconga-eval-")
        self.output = Path(self.temporary.name)
        self.process = None

    def command(self, arguments):
        command = ["bwrap", "--die-with-parent", "--new-session", "--unshare-pid",
                   "--unshare-net", "--unshare-ipc", "--unshare-uts"]
        for directory in ("/usr", "/lib", "/lib64", "/bin", "/etc/alternatives"):
            if Path(directory).exists():
                command.extend(["--ro-bind", directory, directory])
        command.extend(["--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
                        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"])
        for source, destination in ((self.participant, "/participant"),
                                    (self.submission, "/submission"),
                                    (self.participant, str(self.participant)),
                                    (self.submission, str(self.submission))):
            command.extend(["--ro-bind", str(source), str(destination)])
        if self.input_dir:
            command.extend(["--ro-bind", str(self.input_dir), "/input"])
        command.extend(["--bind", str(self.output), "/output", "--chdir", "/submission",
                        "--clearenv", "--setenv", "PATH", "/usr/bin:/bin",
                        "--setenv", "HOME", "/tmp", "--setenv", "LANG", "C.UTF-8",
                        "--setenv", "PYTHONPATH", "/participant/workspace:/participant",
                        "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
                        "--setenv", "OPENBLAS_NUM_THREADS", "1",
                        "--setenv", "OMP_NUM_THREADS", "1",
                        "--setenv", "MKL_NUM_THREADS", "1",
                        "--setenv", "NUMEXPR_NUM_THREADS", "1"])
        return command + list(arguments)

    def limits(self):
        available = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {available[os.getpid() % len(available)]})
        resource.setrlimit(resource.RLIMIT_CPU, (self.seconds + 3, self.seconds + 5))
        memory = self.memory_gib * 1024 ** 3
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 ** 2, 64 * 1024 ** 2))
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))

    def start(self, arguments, **kwargs):
        self.process = subprocess.Popen(self.command(arguments), preexec_fn=self.limits,
                                        start_new_session=True,
                                        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, **kwargs)
        return self.process

    def run(self, arguments):
        process = self.start(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = process.communicate(timeout=self.seconds)
            return {"returncode": process.returncode, "stdout": stdout,
                    "stderr": stderr, "timed_out": False}
        except subprocess.TimeoutExpired:
            self.stop()
            stdout, stderr = process.communicate()
            return {"returncode": process.returncode, "stdout": stdout,
                    "stderr": stderr, "timed_out": True}

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait()

    def close(self):
        self.stop()
        self.temporary.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        self.close()
