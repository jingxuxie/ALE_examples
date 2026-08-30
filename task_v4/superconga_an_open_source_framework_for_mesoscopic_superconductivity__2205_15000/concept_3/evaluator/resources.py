import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "authoring"))

from sandbox import Sandbox

TICKS = os.sysconf("SC_CLK_TCK")
SAMPLE_INTERVAL = 0.01
REVISION = "checker-repair-2-tree-cpu"


class ResourceError(Exception):
    pass


class ReapedProcess:
    def __init__(self, process):
        self.raw = process
        self.pid = process.pid
        self.stdin = process.stdin
        self.stdout = process.stdout
        self.stderr = process.stderr
        self.usage = None

    @property
    def returncode(self):
        return self.raw.returncode

    def poll(self):
        if self.returncode is None:
            try:
                child, status, usage = os.wait4(self.pid, os.WNOHANG)
            except ChildProcessError as error:
                raise ResourceError("sandbox was reaped outside CPU accounting") from error
            if child:
                self.raw.returncode = os.waitstatus_to_exitcode(status)
                self.usage = usage
        return self.returncode

    def wait(self, timeout=None):
        deadline = None if timeout is None else time.monotonic() + timeout
        while self.poll() is None:
            if deadline is not None and time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(self.raw.args, timeout)
            time.sleep(0.002)
        return self.returncode


def process_stat(pid):
    try:
        text = Path("/proc", str(pid), "stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    except OSError as error:
        raise ResourceError("unavailable kernel CPU accounting") from error
    fields = text[text.rfind(")") + 2:].split()
    if len(fields) < 22:
        raise ResourceError("invalid kernel CPU accounting")
    return {"pid": pid, "start": int(fields[19]), "state": fields[0],
            "ticks": sum(int(fields[index]) for index in (11, 12, 13, 14))}


def tree_snapshot(root):
    pending = [root]
    nodes = {}
    while pending:
        pid = pending.pop()
        if pid in nodes:
            continue
        node = process_stat(pid)
        if node is None:
            continue
        nodes[pid] = node
        try:
            for thread in Path("/proc", str(pid), "task").iterdir():
                try:
                    pending.extend(int(child) for child in (thread / "children").read_text().split())
                except (FileNotFoundError, ProcessLookupError):
                    continue
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError as error:
            raise ResourceError("unavailable kernel process tree") from error
        if len(nodes) > 4096:
            raise ResourceError("sandbox process tree exceeds accounting capacity")
    return nodes


def signal_node(node, action):
    try:
        descriptor = os.pidfd_open(node["pid"])
    except ProcessLookupError:
        return False
    try:
        current = process_stat(node["pid"])
        if current is None or current["start"] != node["start"]:
            return False
        try:
            signal.pidfd_send_signal(descriptor, action)
            return True
        except ProcessLookupError:
            return False
    finally:
        os.close(descriptor)


class ResourceSandbox(Sandbox):
    def command(self, arguments):
        guard = Path(__file__).resolve().with_name("resource_guard.py")
        return super().command([]) + ["--as-pid-1", "--ro-bind", str(guard),
                                      "/__ldos_resource_guard.py", "--", "/usr/bin/python3",
                                      "/__ldos_resource_guard.py"] + list(arguments)

    def limits(self):
        self.seconds = max(1, math.ceil(self.seconds))
        super().limits()
        resource.setrlimit(resource.RLIMIT_CPU, (self.seconds, self.seconds))

    def start(self, arguments, **kwargs):
        raw = subprocess.Popen(self.command(arguments), preexec_fn=self.limits,
                               start_new_session=True,
                               env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, **kwargs)
        self.process = ReapedProcess(raw)
        return self.process

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            try:
                nodes = tree_snapshot(self.process.pid)
                for node in reversed(list(nodes.values())):
                    signal_node(node, signal.SIGKILL)
            finally:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.process.wait(timeout=5)


class CpuTreeMonitor:
    def __init__(self, process, cpu_seconds):
        self.process = process
        self.limit = float(cpu_seconds)
        self.next_sample = 0.0
        self.last_sample = 0.0
        self.peak_sample = 0.0
        self.confirmed_cpu = 0.0
        self.samples = 0
        self.max_processes = 0
        self.limit_exceeded = False

    def check(self, force=False):
        if self.process.poll() is not None:
            if self.final_cpu() > self.limit:
                self.limit_exceeded = True
                raise ResourceError("CPU time limit (complete sandbox tree)")
            return
        now = time.monotonic()
        if not force and now < self.next_sample:
            return
        self.next_sample = now + SAMPLE_INTERVAL
        nodes = tree_snapshot(self.process.pid)
        self.samples += 1
        self.max_processes = max(self.max_processes, len(nodes))
        total = sum(node["ticks"] for node in nodes.values()) / TICKS
        self.last_sample = total
        self.peak_sample = max(self.peak_sample, total)
        if total >= self.limit:
            confirmed = self.quiescent_cpu()
            self.confirmed_cpu = max(self.confirmed_cpu, confirmed)
            if confirmed >= self.limit:
                self.limit_exceeded = True
                raise ResourceError("CPU time limit (complete sandbox tree)")

    def quiescent_cpu(self):
        stopped = {}
        try:
            for attempt in range(12):
                nodes = tree_snapshot(self.process.pid)
                for pid, node in nodes.items():
                    if (pid, node["start"]) not in stopped:
                        if signal_node(node, signal.SIGSTOP):
                            stopped[(pid, node["start"])] = node
                time.sleep(0.002)
                settled = tree_snapshot(self.process.pid)
                if settled and all(node["state"] in ("T", "t", "Z", "X") for node in settled.values()):
                    return sum(node["ticks"] for node in settled.values()) / TICKS
                if not settled and self.process.poll() is not None:
                    return self.final_cpu()
            raise ResourceError("cannot obtain consistent sandbox CPU snapshot")
        finally:
            for node in reversed(list(stopped.values())):
                signal_node(node, signal.SIGCONT)

    def final_cpu(self):
        if self.process.usage is None:
            raise ResourceError("sandbox final CPU accounting unavailable")
        return self.process.usage.ru_utime + self.process.usage.ru_stime

    def report(self, clean_exit):
        final_cpu = self.final_cpu()
        complete = bool(clean_exit and self.process.returncode == 0)
        charged = final_cpu if complete else max(final_cpu, self.confirmed_cpu, self.last_sample)
        return {"method": "namespace_reaper_wait4_and_proc_tree_v2",
                "cpu_seconds": charged, "complete": complete,
                "final_wait4_cpu_seconds": final_cpu,
                "last_tree_cpu_seconds": self.last_sample,
                "peak_tree_cpu_seconds": self.peak_sample,
                "confirmed_tree_cpu_seconds": self.confirmed_cpu,
                "samples": self.samples, "max_live_processes": self.max_processes,
                "sample_interval_seconds": SAMPLE_INTERVAL, "kernel_tick_seconds": 1 / TICKS,
                "cpu_limit_seconds": self.limit, "cpu_limit_exceeded": self.limit_exceeded,
                "rlimit_cpu_soft_hard": [max(1, math.ceil(self.limit))] * 2}
