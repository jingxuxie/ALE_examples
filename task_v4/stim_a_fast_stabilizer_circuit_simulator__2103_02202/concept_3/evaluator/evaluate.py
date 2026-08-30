import argparse
import json
import os
from pathlib import Path
import resource
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from checker import MAX_BYTES, Invalid, check, load, rejection


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (10, 11))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def worker(descriptor):
    started = time.monotonic()
    try:
        instance = json.loads((ROOT / "hidden" / "instance.json").read_text())
    except (ValueError, OSError):
        return rejection("Trusted instance unavailable", "infrastructure")
    size = 0
    try:
        with os.fdopen(descriptor, "rb") as source:
            raw = source.read(MAX_BYTES + 1)
        size = len(raw)
        artifact = load(raw)
        del raw
        result = check(artifact, instance)
    except MemoryError:
        result = rejection("Evaluation memory limit exceeded", "resource")
    except (ValueError, UnicodeError, OSError, RecursionError, TypeError, KeyError) as error:
        result = rejection(str(error)[:300])
    usage = resource.getrusage(resource.RUSAGE_SELF)
    result["resources"] = dict(artifact_bytes=size, wall_seconds=time.monotonic() - started,
                               cpu_seconds=usage.ru_utime + usage.ru_stime, peak_rss_kib=usage.ru_maxrss)
    return result


def evaluate(submission):
    descriptor = None
    started = time.monotonic()
    try:
        path = Path(submission).absolute()
        if path.is_symlink():
            raise Invalid("Submission symlinks are forbidden")
        if path.is_dir():
            path = path / "circuit.json"
        if path.name != "circuit.json":
            raise Invalid("Artifact must be named circuit.json")
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        finally:
            os.close(directory)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise Invalid("Artifact must be a regular file")
        if info.st_size > MAX_BYTES:
            raise Invalid("Artifact exceeds 64 MiB")
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker-fd", str(descriptor)],
            cwd=ROOT, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            pass_fds=(descriptor,), capture_output=True, timeout=15, preexec_fn=limits)
        if completed.returncode:
            return rejection("Worker terminated or exceeded resource limits", "resource")
        try:
            result = json.loads(completed.stdout)
        except ValueError:
            return rejection("Invalid trusted worker report", "infrastructure")
        result.setdefault("resources", {})["total_wall_seconds"] = time.monotonic() - started
        return result
    except subprocess.TimeoutExpired:
        return rejection("Evaluation wall limit exceeded", "resource")
    except (OSError, ValueError) as error:
        return rejection(str(error)[:300])
    except subprocess.SubprocessError:
        return rejection("Worker launch failed", "infrastructure")
    finally:
        if descriptor is not None:
            os.close(descriptor)


def main():
    parser = argparse.ArgumentParser(description="Evaluate static JSON only; submitted code is never executed.")
    parser.add_argument("--submission")
    parser.add_argument("--report")
    parser.add_argument("--worker-fd", type=int, help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    if arguments.worker_fd is None and not arguments.submission:
        parser.error("--submission is required")
    result = worker(arguments.worker_fd) if arguments.worker_fd is not None else evaluate(arguments.submission)
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        Path(arguments.report).write_text(text)
    print(text, end="")
    return 2 if result.get("error_kind") == "infrastructure" else 0


if __name__ == "__main__":
    raise SystemExit(main())
