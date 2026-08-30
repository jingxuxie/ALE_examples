import argparse
import json
import os
import resource
import signal
import subprocess
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent


def command(directory, mode, device=None):
    arguments = ["bwrap", "--die-with-parent", "--unshare-all", "--new-session",
                 "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
                 "--ro-bind", "/lib64", "/lib64", "--proc", "/proc", "--dev", "/dev",
                 "--dir", "/etc", "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
                 "--ro-bind", "/etc/alternatives", "/etc/alternatives",
                 "--dir", "/work", "--ro-bind", str(HERE / "solver"), "/work/solver",
                 "--ro-bind", str(directory / "input"), "/input",
                 "--bind", str(directory / "output"), "/output",
                 "--bind", str(directory / "tmp"), "/tmp", "--chdir", "/output",
                 "--clearenv", "--setenv", "PATH", "/usr/bin", "--setenv", "HOME", "/tmp",
                 "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--setenv", "PYTHONNOUSERSITE", "1",
                 "--setenv", "OPENBLAS_NUM_THREADS", "1", "--setenv", "OMP_NUM_THREADS", "2",
                 "--setenv", "MKL_NUM_THREADS", "1", "/usr/bin/python3", "/work/solver/entry.py", mode]
    if device is not None:
        arguments += ["--device", str(device)]
    return arguments


def restrictions(cpus):
    def apply():
        os.setsid()
        os.sched_setaffinity(0, cpus)
        resource.setrlimit(resource.RLIMIT_AS, (8 * 1024 ** 3, 8 * 1024 ** 3))
    return apply


def launch(directory, mode, device, cpus):
    label = f"fit_device_{device}" if mode == "fit" else mode
    log = (directory / (label + ".log")).open("w")
    invocation = command(directory, mode, device)
    process = subprocess.Popen(invocation, stdout=log, stderr=subprocess.STDOUT, preexec_fn=restrictions(cpus))
    return {"process": process, "log": log, "started": time.monotonic(), "mode": mode,
            "device": device, "invocation": invocation, "cpus": cpus}


def execute(campaigns, maximum_campaigns, first_cpu, timeout):
    queued = list(campaigns)
    active = {}
    summaries = []
    started = time.monotonic()
    while queued or active:
        occupied_slots = {record["slot"] for record in active.values()}
        for slot in range(maximum_campaigns):
            if not queued or slot in occupied_slots:
                continue
            campaign = queued.pop(0)
            directory = HERE / "campaigns" / f"campaign_{campaign:02d}"
            cpus = list(range(first_cpu + slot * 8, first_cpu + (slot + 1) * 8))
            assert (directory / "metadata.json").is_file()
            assert not any((directory / "output").iterdir()), "Each trial must start with empty output"
            probe = subprocess.run(command(directory, "probe"), capture_output=True, text=True,
                                   preexec_fn=restrictions(cpus))
            if probe.returncode:
                (directory / "isolation_error.log").write_text(probe.stdout + probe.stderr)
                raise RuntimeError("Isolation startup failed: " + probe.stderr)
            (directory / "isolation_probe.json").write_text(probe.stdout)
            evidence = json.loads(probe.stdout)
            assert evidence["output_files"] == [] and not evidence["host_repository_visible"] and not evidence["private_directory_visible"]
            jobs = [launch(directory, "fit", device, cpus[2 * device:2 * device + 2]) for device in range(4)]
            active[campaign] = {"slot": slot, "directory": directory, "jobs": jobs,
                                "started": time.monotonic(), "cpus": cpus, "completed": []}
            print("STARTED", campaign, "CPUS", cpus, flush=True)
        for campaign, record in list(active.items()):
            for job in list(record["jobs"]):
                returncode = job["process"].poll()
                if returncode is None and time.monotonic() - job["started"] > timeout:
                    os.killpg(job["process"].pid, signal.SIGTERM)
                    job["process"].wait(timeout=10)
                    returncode = job["process"].returncode
                    job["censored_timeout"] = True
                if returncode is None:
                    continue
                job["log"].close()
                completed = {key: value for key, value in job.items() if key not in {"process", "log", "started"}}
                completed.update(returncode=returncode, elapsed_seconds=time.monotonic() - job["started"])
                record["completed"].append(completed)
                record["jobs"].remove(job)
                print("FINISHED", campaign, job["mode"], job["device"], returncode, completed["elapsed_seconds"], flush=True)
            if record["jobs"]:
                continue
            if all(job["returncode"] == 0 for job in record["completed"]) and not any(job["mode"] == "predict" for job in record["completed"]):
                record["jobs"] = [launch(record["directory"], "predict", None, record["cpus"])]
                continue
            summary = {"campaign": campaign, "elapsed_seconds": time.monotonic() - record["started"],
                       "jobs": record["completed"], "completed_prediction": (record["directory"] / "output" / "predictions.json").exists(),
                       "sandbox": "bubblewrap minimal OS libraries, read-only solver/input, initially empty output, no private artifacts, unshared network",
                       "cpu_affinity": record["cpus"], "address_space_gib_per_process": 8}
            (record["directory"] / "execution.json").write_text(json.dumps(summary, indent=2) + "\n")
            summaries.append(summary)
            del active[campaign]
        time.sleep(0.25)
    output = HERE / ("execution_batch_" + "_".join(str(campaign) for campaign in campaigns) + ".json")
    output.write_text(json.dumps({"total_elapsed_seconds": time.monotonic() - started, "trials": summaries}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaigns", type=int, nargs="+", required=True)
    parser.add_argument("--parallel-campaigns", type=int, default=2)
    parser.add_argument("--first-cpu", type=int, default=320)
    parser.add_argument("--timeout", type=float, default=900)
    arguments = parser.parse_args()
    execute(arguments.campaigns, arguments.parallel_campaigns, arguments.first_cpu, arguments.timeout)


if __name__ == "__main__":
    main()
