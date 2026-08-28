import argparse
import json
import os
import resource
import signal
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant", required=True)
    parser.add_argument("--submission", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--memory-mb", type=int, default=4096)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    participant = Path(arguments.participant).resolve()
    submission = Path(arguments.submission).resolve()
    work = Path(arguments.work).resolve()
    command = arguments.command[1:] if arguments.command[:1] == ["--"] else arguments.command
    mounts = ["/usr", "/bin", "/lib", "/lib64", "/etc/alternatives", "/etc/ld.so.cache"]
    sandbox = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session"]
    for mount in mounts:
        if Path(mount).exists():
            sandbox += ["--ro-bind", mount, mount]
    sandbox += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    sandbox += ["--ro-bind", str(participant), str(participant)]
    if submission.parent != participant and participant not in submission.parents:
        sandbox += ["--ro-bind", str(submission.parent), str(submission.parent)]
    sandbox += ["--bind", str(work), str(work), "--chdir", str(work)]
    sandbox += ["--clearenv", "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin", "--setenv", "HOME", "/tmp"]
    for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"]:
        sandbox += ["--setenv", variable, str(arguments.threads)]
    sandbox += ["--setenv", "PYTHONNOUSERSITE", "1", "--setenv", "PYTHONHASHSEED", "0"]
    resource_path = work / "_process_resource.json"
    resource_format = '{"max_rss_kib":%M,"user_seconds":%U,"system_seconds":%S,"process_seconds":%e,"exit_status":%x}'
    sandbox += ["/usr/bin/time", "-q", "-f", resource_format, "-o", str(resource_path)] + command

    def limits():
        cpu_limit = int(arguments.timeout * arguments.threads)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit + 5, cpu_limit + 10))
        virtual_limit = 2 * arguments.memory_mb * 1024 ** 2
        resource.setrlimit(resource.RLIMIT_AS, (virtual_limit, virtual_limit))
        resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024 ** 2, 128 * 1024 ** 2))

    started = time.monotonic()
    process = subprocess.Popen(sandbox, preexec_fn=limits, start_new_session=True)
    timed_out = False
    try:
        status = process.wait(timeout=arguments.timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        status = 124
    usage = json.loads(resource_path.read_text()) if resource_path.exists() else {}
    maximum_resident = usage.get("max_rss_kib")
    if maximum_resident is not None and maximum_resident > arguments.memory_mb * 1024:
        status = 137
    (work / "_resource.json").write_text(json.dumps({"seconds": time.monotonic() - started, "max_rss_kib": maximum_resident,
                                                   "user_seconds": usage.get("user_seconds"), "system_seconds": usage.get("system_seconds"),
                                                   "process_seconds": usage.get("process_seconds"), "resource_source": "GNU time inside sandbox",
                                                   "returncode": status, "timed_out": timed_out, "network": "disabled", "private_tree_mounted": False}))
    return status


if __name__ == "__main__":
    sys.exit(main())
