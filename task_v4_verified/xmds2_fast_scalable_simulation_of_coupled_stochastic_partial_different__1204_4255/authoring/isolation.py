import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import tempfile
import time


def process_tree_memory(process_id, cpu_seen, cpu):
    pending = [process_id]
    visited = set()
    address_space_kb = 0
    resident_kb = 0
    affinity_valid = True
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        try:
            directory = Path("/proc") / str(current)
            statistics = (directory / "stat").read_text().rsplit(")", 1)[1].split()
            cpu_seen[current] = max(cpu_seen.get(current, 0), int(statistics[11]) + int(statistics[12]))
            for line in (directory / "status").read_text().splitlines():
                if line.startswith("VmSize:"):
                    address_space_kb += int(line.split()[1])
                elif line.startswith("VmRSS:"):
                    resident_kb += int(line.split()[1])
            for task in (directory / "task").iterdir():
                affinity_valid = affinity_valid and os.sched_getaffinity(int(task.name)).issubset({cpu})
                pending.extend(int(value) for value in (task / "children").read_text().split())
        except (OSError, ValueError):
            pass
    return address_space_kb, resident_kb, affinity_valid


def run_submission(submission, participant, payload, timeout=120, memory_mb=1024):
    submission = Path(submission).resolve()
    participant = Path(participant).resolve()
    command = ["bwrap", "--die-with-parent", "--new-session", "--unshare-net", "--unshare-pid", "--unshare-ipc", "--unshare-uts"]
    for path in ["/usr", "/bin", "/lib", "/lib64", "/etc/alternatives", "/etc/ld.so.cache"]:
        if Path(path).exists():
            command.extend(["--ro-bind", path, path])
    command.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--dir", "/home"])
    command.extend(["--ro-bind", str(submission), "/submission", "--ro-bind", str(participant), "/task", "--chdir", "/submission", "--clearenv"])
    for name, value in {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "PYTHONPATH": "/task/workspace:/submission", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "LANG": "C.UTF-8"}.items():
        command.extend(["--setenv", name, value])
    allowed_cpus = sorted(os.sched_getaffinity(0))
    cpu = allowed_cpus[os.getpid() % len(allowed_cpus)]
    with tempfile.TemporaryDirectory(prefix="xmds-evaluation-") as temporary:
        control = Path(temporary) / "control"
        control.mkdir()
        ready = control / "ready"
        launch = 'import os; open("/control/ready", "w").close(); os.execv("/usr/bin/python3", ["/usr/bin/python3", "-u", "-s", "/submission/solve.py"])'
        command.extend(["--bind", str(control), "/control", "/usr/bin/python3", "-I", "-c", launch])

        def limits():
            os.sched_setaffinity(0, {cpu})
            memory = memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
            resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(timeout), math.ceil(timeout) + 1))
            resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 * 1024, 64 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))

        started = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        input_path = Path(temporary) / "requests.jsonl"
        input_path.write_text(payload)
        peak_address_space_kb = 0
        peak_resident_kb = 0
        resource_violation = None
        execution_started = None
        cpu_seen = {}
        with input_path.open("r") as stdin, open(Path(temporary) / "stdout.log", "w+") as stdout, open(Path(temporary) / "stderr.log", "w+") as stderr:
            process = subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr, start_new_session=True, preexec_fn=limits)
            timed_out = False
            while process.poll() is None:
                current_time = time.monotonic()
                if execution_started is None and ready.exists():
                    execution_started = current_time
                address_space_kb, resident_kb, affinity_valid = process_tree_memory(process.pid, cpu_seen, cpu)
                peak_address_space_kb = max(peak_address_space_kb, address_space_kb)
                peak_resident_kb = max(peak_resident_kb, resident_kb)
                if address_space_kb > memory_mb * 1024:
                    resource_violation = "aggregate process-tree address-space limit"
                if not affinity_valid:
                    resource_violation = "process or thread expanded its single-CPU affinity"
                timed_out = (current_time - execution_started > timeout) if execution_started is not None else (current_time - started > 180)
                if timed_out or resource_violation:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    break
                time.sleep(0.05)
            process.wait()
            stdout.seek(0)
            stderr.seek(0)
            finished = time.monotonic()
            result = {"stdout": stdout.read(64 * 1024 * 1024), "stderr": stderr.read()[-4000:], "returncode": process.returncode, "timed_out": timed_out, "resource_violation": resource_violation, "elapsed_seconds": finished - execution_started if execution_started is not None else 0.0, "setup_seconds": (execution_started or finished) - started, "total_wall_seconds": finished - started, "launch_completed": execution_started is not None or ready.exists()}
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        result.update({"max_rss_kb": peak_resident_kb, "peak_aggregate_address_space_kb": peak_address_space_kb, "observed_cpu_seconds_lower_bound": sum(cpu_seen.values()) / os.sysconf("SC_CLK_TCK"), "launcher_user_seconds": after.ru_utime - before.ru_utime, "launcher_system_seconds": after.ru_stime - before.ru_stime, "cpu_affinity": [cpu], "memory_sampling_seconds": 0.05})
        return result
