from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


AREA = Path(__file__).resolve().parent


def stats(directory, filename):
    return {name: int(value) for name, value in
            (line.split() for line in (directory / filename).read_text().splitlines())}


def current_cgroup():
    line = next(line for line in Path("/proc/self/cgroup").read_text().splitlines() if line.startswith("0::"))
    return Path("/sys/fs/cgroup") / line[3:].lstrip("/")


def main():
    parent = current_cgroup()
    assert "user@" + str(os.getuid()) + ".service" in str(parent)
    assert parent.name.startswith("ale-e3-resource-probe-") and parent.name.endswith(".service")
    report = dict(started_utc=datetime.now(timezone.utc).isoformat(), uid=os.getuid(),
                  parent_cgroup=str(parent), parent_procs_writable=os.access(parent / "cgroup.procs", os.W_OK),
                  parent_subtree_control=(parent / "cgroup.subtree_control").read_text().strip())
    job = parent / ("owned-probe-" + uuid.uuid4().hex)
    job.mkdir()
    report["job_cgroup"] = str(job)
    try:
        def join():
            with (job / "cgroup.procs").open("w") as handle:
                handle.write(str(os.getpid()))

        before = stats(job, "cpu.stat")
        program = "import json,time,pathlib\nstarted=time.process_time()\nwhile time.process_time()-started<.5: pass\nprint(json.dumps({'cgroup':pathlib.Path('/proc/self/cgroup').read_text(),'self_cpu':time.process_time()}))\n"
        result = subprocess.run([sys.executable, "-I", "-B", "-c", program], preexec_fn=join,
                                check=True, capture_output=True, text=True, timeout=10)
        report["child"] = json.loads(result.stdout)
        report["initial_cpu_stat"] = before
        report["final_cpu_stat"] = stats(job, "cpu.stat")
        report["cpu_seconds"] = (report["final_cpu_stat"]["usage_usec"] - before["usage_usec"]) / 1e6
        assert str(job).removeprefix("/sys/fs/cgroup") in report["child"]["cgroup"]
        assert report["cpu_seconds"] >= .5
        assert current_cgroup() == parent
        report["service_parent_outside_job"] = True
        report["passed"] = True
    except BaseException as exception:
        report.update(passed=False, error=repr(exception))
        raise
    finally:
        assert job.parent == parent and current_cgroup() == parent
        report["events_before_cleanup"] = stats(job, "cgroup.events")
        (job / "cgroup.kill").write_text("1")
        deadline = time.monotonic() + 5
        while stats(job, "cgroup.events")["populated"]:
            if time.monotonic() >= deadline:
                raise RuntimeError("owned_cgroup_not_empty")
            time.sleep(.01)
        report["cpu_stat_after_cleanup"] = stats(job, "cpu.stat")
        job.rmdir()
        report["owned_job_removed"] = not job.exists()
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        (AREA / "service_probe_report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
