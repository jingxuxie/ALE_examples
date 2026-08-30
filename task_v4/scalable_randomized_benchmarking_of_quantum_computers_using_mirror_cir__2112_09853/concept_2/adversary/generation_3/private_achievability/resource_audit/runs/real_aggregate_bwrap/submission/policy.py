import json
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
    json.loads(sys.stdin.readline())
    settings = json.loads((Path(__file__).parent / "settings.json").read_text())
    worker_pids = []
    if settings["mode"] == "single":
        burn_cpu(settings["seconds"])
    else:
        if settings["mode"] == "auto_reap":
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        read_fd, write_fd = os.pipe()
        for worker_index in range(settings["workers"]):
            child_pid = os.fork()
            if child_pid == 0:
                os.close(read_fd)
                burn_cpu(settings["seconds"])
                print(json.dumps(dict(kind="worker", worker=worker_index, **cpu_usage())), file=sys.stderr, flush=True)
                os.write(write_fd, b"1")
                os.close(write_fd)
                os._exit(0)
            worker_pids.append(child_pid)
        os.close(write_fd)
        completed = 0
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
        else:
            time.sleep(.02)
    print(json.dumps(dict(kind="policy", worker_pids=worker_pids, **cpu_usage())), file=sys.stderr, flush=True)
    print(json.dumps({"type": "ready"}), flush=True)
    targets = json.loads(sys.stdin.readline())["matchings"]
    print(json.dumps({"type": "final", "predictions": [.05] * len(targets)}), flush=True)
    json.loads(sys.stdin.readline())


if __name__ == "__main__":
    main()
