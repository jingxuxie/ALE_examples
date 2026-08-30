import os
from pathlib import Path
import threading

from sandbox import Sandbox


class ObservedSandbox(Sandbox):
    latest = None

    def start(self, arguments, **kwargs):
        process = super().start(arguments, **kwargs)
        self.cpu_by_pid = {}
        self.affinity_counts = {}
        self.finished_observation = threading.Event()
        self.root_pid = process.pid
        self.clock_ticks = os.sysconf("SC_CLK_TCK")
        self.latest_snapshot = {}
        self.observer = threading.Thread(target=self.observe, daemon=True)
        self.observer.start()
        ObservedSandbox.latest = self
        return process

    def sample(self):
        pending = [self.root_pid]
        visited = set()
        while pending:
            pid = pending.pop()
            if pid in visited:
                continue
            visited.add(pid)
            try:
                base = Path("/proc") / str(pid)
                stat = (base / "stat").read_text().rsplit(")", 1)[1].split()
                cpu = (int(stat[11]) + int(stat[12])) / self.clock_ticks
                self.cpu_by_pid[pid] = max(cpu, self.cpu_by_pid.get(pid, 0.0))
                self.affinity_counts[pid] = len(os.sched_getaffinity(pid))
                pending.extend(int(value) for value in (base / "task" / str(pid) / "children").read_text().split())
            except (OSError, ValueError, IndexError):
                continue

    def observe(self):
        while not self.finished_observation.wait(0.03):
            self.sample()
        self.sample()

    def close(self):
        super().close()
        if hasattr(self, "observer"):
            self.finished_observation.set()
            self.observer.join(timeout=2)

    def measurement(self):
        return {"observed_cpu_seconds_lower_bound": sum(self.cpu_by_pid.values()),
                "observed_cpu_by_pid": self.cpu_by_pid, "affinity_cpu_counts": self.affinity_counts,
                "cpu_sampling_interval_seconds": 0.03,
                "cpu_measurement_caveat": "Kernel process-tree sampling lower bound; up to one sampling interval per process may be missed at exit. Trusted os.times field captures only bwrap overhead on this host."}
