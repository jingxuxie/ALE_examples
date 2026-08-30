import json
import os
import resource
import signal
import subprocess
import sys
import threading
import time

import bdg


def burn(seconds):
    start = time.process_time()
    value = 3
    while time.process_time() - start < seconds:
        value = (value * 48271) % 2147483647


def usage():
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime


def fork_work(seconds):
    child = os.fork()
    if child == 0:
        burn(seconds)
        os._exit(0)
    return child


def main(mode):
    json.loads(sys.stdin.readline())
    evidence = {"mode": mode, "rlimit_cpu": list(resource.getrlimit(resource.RLIMIT_CPU)),
                "affinity_count": len(os.sched_getaffinity(0))}
    if mode == "control":
        pass
    elif mode == "busy":
        burn(20)
    elif mode == "forked":
        children = [fork_work(0.30) for index in range(5)]
        for child in children:
            os.waitpid(child, 0)
    elif mode == "rapid":
        for index in range(40):
            os.waitpid(fork_work(0.006), 0)
    elif mode == "orphan":
        child = os.fork()
        if child == 0:
            grandchild = os.fork()
            if grandchild == 0:
                burn(0.30)
                print(json.dumps({"orphan_cpu": usage()}), file=sys.stderr, flush=True)
                os._exit(0)
            burn(0.03)
            os._exit(0)
        os.waitpid(child, 0)
    elif mode == "threaded":
        def worker():
            os.waitpid(fork_work(0.30), 0)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
    elif mode == "numpy":
        import numpy as np

        matrix = np.random.default_rng(84).normal(size=(180, 180))
        start = time.process_time()
        operations = 0
        while time.process_time() - start < 0.40:
            np.linalg.eigh(matrix + matrix.T)
            operations += 1
        evidence["numpy_eigendecompositions"] = operations
    elif mode == "sleep":
        time.sleep(20)
    elif mode == "restrictions":
        try:
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        except PermissionError:
            evidence["sigchld_autoreap_denied"] = True
        try:
            os.sched_setaffinity(0, os.sched_getaffinity(0))
        except PermissionError:
            evidence["affinity_change_denied"] = True
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (91, 91))
        except (ValueError, PermissionError):
            evidence["cpu_hard_limit_increase_denied"] = True
        os.waitpid(fork_work(0.02), 0)
    elif mode == "compile":
        with open("/tmp/probe.c", "w") as destination:
            destination.write("int main(void) { return 0; }\n")
        subprocess.run(["/usr/bin/cc", "/tmp/probe.c", "-o", "/output/probe"],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["/output/probe"], check=True)
        evidence["compiled_in_writable_scratch"] = True
    else:
        raise ValueError("unknown resource fixture")
    evidence["client_accounted_cpu"] = usage()
    print(json.dumps(evidence), file=sys.stderr, flush=True)
    print(json.dumps({"type": "final", "estimate": bdg.draw_scene(71, "dispersed")}), flush=True)
