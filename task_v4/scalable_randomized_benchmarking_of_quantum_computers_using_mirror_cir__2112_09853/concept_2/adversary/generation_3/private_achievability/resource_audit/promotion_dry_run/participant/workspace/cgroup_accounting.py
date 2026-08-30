import os
from pathlib import Path
import time
import uuid


class EpisodeCgroup:
    def __init__(self):
        entries = Path("/proc/self/cgroup").read_text().splitlines()
        unified = [line[3:] for line in entries if line.startswith("0::")]
        if len(unified) != 1:
            raise OSError("cgroup_v2_accounting_unavailable")
        self.parent = Path("/sys/fs/cgroup") / unified[0].lstrip("/")
        if (self.parent.stat().st_uid != os.getuid() or not os.access(self.parent, os.W_OK)
                or not os.access(self.parent / "cgroup.procs", os.W_OK)):
            raise OSError("cgroup_v2_accounting_requires_writable_user_service")
        self.directory = self.parent / ("ale-mrb-episode-" + uuid.uuid4().hex)
        self.directory.mkdir()
        self.descriptors = {}
        self.result = None
        try:
            for name, flags in (("cpu.stat", os.O_RDONLY), ("cgroup.events", os.O_RDONLY), ("cgroup.kill", os.O_WRONLY)):
                self.descriptors[name] = os.open(self.directory / name, flags | os.O_CLOEXEC)
            self.before = self.read_stats("cpu.stat")
        except BaseException:
            for descriptor in self.descriptors.values():
                os.close(descriptor)
            self.directory.rmdir()
            raise

    def read_stats(self, name):
        text = os.pread(self.descriptors[name], 16384, 0).decode()
        return {key: int(value) for key, value in (line.split() for line in text.splitlines())}

    def join_self(self):
        with (self.directory / "cgroup.procs").open("w") as handle:
            handle.write(str(os.getpid()))

    def finish(self):
        if self.result is not None:
            return self.result
        assert self.directory.parent == self.parent
        assert self.directory.name.startswith("ale-mrb-episode-")
        os.write(self.descriptors["cgroup.kill"], b"1")
        deadline = time.monotonic() + 5
        while self.read_stats("cgroup.events")["populated"]:
            if time.monotonic() >= deadline:
                raise OSError("owned_episode_cgroup_did_not_empty")
            time.sleep(.005)
        after = self.read_stats("cpu.stat")
        self.result = dict(source="cgroup_v2_cpu.stat", cpu_seconds=(after["usage_usec"] - self.before["usage_usec"]) / 1e6,
                           initial_cpu_stat=self.before, final_cpu_stat=after,
                           parent_cgroup=str(self.parent), owned_episode_cgroup=str(self.directory),
                           populated_after_cleanup=0)
        for descriptor in self.descriptors.values():
            os.close(descriptor)
        self.descriptors.clear()
        descendants = [path for path in self.directory.rglob("*") if path.is_dir()]
        for directory in sorted(descendants, key=lambda path: len(path.parts), reverse=True):
            directory.rmdir()
        self.directory.rmdir()
        self.result["owned_episode_cgroup_removed"] = not self.directory.exists()
        return self.result
