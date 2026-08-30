import json
import os
from pathlib import Path
import sys
import threading
import time


def burn(seconds, thread=False):
    clock = time.thread_time if thread else time.process_time
    started = clock()
    while clock() - started < seconds:
        pass


json.loads(sys.stdin.readline())
mode = json.loads(Path(__file__).with_name("settings.json").read_text())["mode"]
details = {"mode": mode}
if mode == "cgroup_tamper":
    forbidden = ["/sys/fs/cgroup", "/run/user/2020/bus", "/run/dbus/system_bus_socket", "/proc/1/root/sys/fs/cgroup"]
    assert all(not Path(path).exists() for path in forbidden)
    descriptors = []
    for name in os.listdir("/proc/self/fd"):
        if int(name) <= 2:
            continue
        try:
            target = os.readlink("/proc/self/fd/" + name)
        except FileNotFoundError:
            continue
        descriptors.append(target)
    assert not descriptors, descriptors
    details.update(forbidden_paths_absent=forbidden, extra_inherited_descriptors=descriptors,
                   namespace_cgroup=Path("/proc/self/cgroup").read_text())
elif mode == "orphan_burn":
    read_fd, write_fd = os.pipe()
    for worker_index in range(2):
        child_pid = os.fork()
        if child_pid == 0:
            os.close(read_fd)
            os.setsid()
            burn(.75)
            os.write(write_fd, b"1")
            os.close(write_fd)
            time.sleep(30)
            os._exit(0)
    os.close(write_fd)
    completed = 0
    while completed < 2:
        completed += len(os.read(read_fd, 2 - completed))
    os.close(read_fd)
    details["unjoined_detached_workers_completed_cpu_seconds"] = 1.5
elif mode == "threads":
    workers = [threading.Thread(target=burn, args=(.5, True)) for unused in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    details["completed_thread_cpu_seconds"] = 1.
else:
    raise ValueError(mode)
os.write(2, (json.dumps(details) + "\n").encode())
print(json.dumps({"type": "ready"}), flush=True)
targets = json.loads(sys.stdin.readline())["matchings"]
print(json.dumps({"type": "final", "predictions": [.05] * len(targets)}), flush=True)
json.loads(sys.stdin.readline())
