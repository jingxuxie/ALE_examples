import json
import ctypes
import os
from pathlib import Path
import resource
import signal
import sys
import time


def cpu_usage():
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {"pid": os.getpid(), "ppid": os.getppid(),
            "self_cpu_seconds": own.ru_utime + own.ru_stime,
            "waited_children_cpu_seconds": children.ru_utime + children.ru_stime,
            "cpu_rlimit": list(resource.getrlimit(resource.RLIMIT_CPU))}


def burn_cpu(seconds):
    started = time.process_time()
    counter = 0
    while time.process_time() - started < seconds:
        for unused in range(500):
            counter += 1
    return counter


def main():
    settings = json.loads((Path(__file__).parent / "settings.json").read_text())
    if settings["mode"] == "exec" and "--execed" not in sys.argv:
        os.execv(sys.executable, [sys.executable, "-I", "-B", "-u", str(Path(__file__).resolve()), "--execed"])
    json.loads(sys.stdin.readline())
    worker_pids = []
    if settings["mode"] in ("single", "exec", "tamper"):
        if settings["mode"] == "tamper":
            denied = []
            for filename in ["/proc/1/mem"] + ["/proc/1/fd/" + str(descriptor) for descriptor in range(3, 64)]:
                try:
                    descriptor = os.open(filename, os.O_WRONLY)
                except OSError:
                    denied.append(filename)
                else:
                    os.close(descriptor)
                    raise RuntimeError("guardian_private_descriptor_accessible: " + filename)
            for filename in os.listdir("/proc/self/fd"):
                if int(filename) <= 2:
                    continue
                try:
                    target = os.readlink("/proc/self/fd/" + filename)
                except FileNotFoundError:
                    continue
                raise RuntimeError("unexpected_inherited_descriptor: " + target)
            library = ctypes.CDLL(None, use_errno=True)
            if library.ptrace(16, 1, None, None) != -1:
                raise RuntimeError("guardian_ptrace_attach_allowed")
            print(json.dumps(dict(kind="tamper_checks", denied_paths=len(denied), ptrace_errno=ctypes.get_errno())), file=sys.stderr, flush=True)
        burn_cpu(settings["seconds"])
    else:
        if settings["mode"] == "auto_reap":
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        if settings["mode"] == "no_cldwait":
            library = ctypes.CDLL(str(Path(__file__).with_name("signal_flags.so")))
            if library.no_wait_children() != 0:
                raise RuntimeError("sigaction_failed")
        read_fd, write_fd = os.pipe()
        for worker_index in range(settings["workers"]):
            child_pid = os.fork()
            if child_pid == 0:
                os.close(read_fd)
                burn_cpu(settings["seconds"])
                print(json.dumps(dict(kind="worker", worker=worker_index, **cpu_usage())), file=sys.stderr, flush=True)
                if settings["mode"] != "orphan":
                    os.write(write_fd, b"1")
                os.close(write_fd)
                os._exit(0)
            worker_pids.append(child_pid)
        os.close(write_fd)
        completed = 0
        if settings["mode"] != "orphan":
            while completed < settings["workers"]:
                received = os.read(read_fd, settings["workers"] - completed)
                if not received:
                    raise RuntimeError("worker_exited_without_completion")
                completed += len(received)
        os.close(read_fd)
        if settings["mode"] == "fork":
            for child_pid in worker_pids:
                waited_pid, status = os.waitpid(child_pid, 0)
                if waited_pid != child_pid or status != 0:
                    raise RuntimeError("worker_failed")
        elif settings["mode"] != "orphan":
            time.sleep(.02)
    print(json.dumps(dict(kind="policy", worker_pids=worker_pids, **cpu_usage())), file=sys.stderr, flush=True)
    print(json.dumps({"type": "ready"}), flush=True)
    targets = json.loads(sys.stdin.readline())["matchings"]
    print(json.dumps({"type": "final", "predictions": [.05] * len(targets)}), flush=True)
    json.loads(sys.stdin.readline())


if __name__ == "__main__":
    main()
