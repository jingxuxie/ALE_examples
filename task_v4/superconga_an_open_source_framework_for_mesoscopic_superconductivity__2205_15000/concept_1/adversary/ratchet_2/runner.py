from common import ASSETS, CONCEPT, ROOT, digest, now, read_json, relative, write_json
from checking import Sandbox, checked_field, energy_gradient, lock_cpu_affinity, lower_bound, scratch_usage

import os
from pathlib import Path
import resource
import shutil
import signal
import tempfile
import time

import numpy as np


def cpu_counters():
    result = {}
    for line in Path("/proc/stat").read_text().splitlines():
        fields = line.split()
        if fields and fields[0].startswith("cpu") and fields[0][3:].isdigit():
            values = list(map(int, fields[1:9]))
            result[int(fields[0][3:])] = (sum(values), values[3] + values[4])
    return result


def utilization(before, after, core):
    total = after[core][0] - before[core][0]
    idle = after[core][1] - before[core][1]
    return (total - idle) / total if total > 0 else 0.0


def siblings(core):
    path = Path("/sys/devices/system/cpu") / ("cpu" + str(core)) / "topology/thread_siblings_list"
    result = []
    for part in path.read_text().strip().split(","):
        endpoints = list(map(int, part.split("-")))
        result.extend(range(endpoints[0], endpoints[-1] + 1))
    return result


def choose_core(policy, require_quiet):
    allowed = sorted(os.sched_getaffinity(0))
    deadline = time.monotonic() + policy["maximum_core_wait_seconds"]
    while True:
        before = cpu_counters()
        time.sleep(policy["core_sample_seconds"])
        after = cpu_counters()
        rates = {core: utilization(before, after, core) for core in after}
        selected = min(allowed, key=lambda core: (max(rates[other] for other in siblings(core)), rates[core], core))
        selected_rates = {str(other): rates[other] for other in siblings(selected)}
        if not require_quiet or max(selected_rates.values()) <= policy["low_load_pre_busy_max"]:
            return selected, selected_rates, after
        if time.monotonic() >= deadline:
            return None, selected_rates, after


def quiet_accounting(accounting, policy):
    return bool(accounting["cpu_to_wall_ratio"] >= policy["low_load_cpu_wall_min"] and accounting["sibling_busy_max"] <= policy["low_load_sibling_busy_max"] and max(accounting["pre_busy_fraction"].values()) <= policy["low_load_pre_busy_max"])


class ReplaySandbox(Sandbox):
    selected_core = None
    original_submission = None

    def limits(self):
        super().limits()
        os.sched_setaffinity(0, {self.selected_core})
        resource.setrlimit(resource.RLIMIT_CPU, (self.seconds, self.seconds))
        lock_cpu_affinity()

    def command(self, arguments):
        command = super().command(arguments)
        position = command.index("--tmpfs")
        if command[position + 1] != "/tmp":
            raise RuntimeError("unexpected trusted helper layout")
        command[position:position + 2] = ["--bind", str(self.output), "/tmp"]
        position = command.index("--chdir")
        mounts = ["--ro-bind", str(ASSETS / "cpu_monitor"), "/trusted_cpu", "--ro-bind", str(ASSETS / "participant"), str(CONCEPT / "participant"), "--cap-drop", "ALL"]
        if self.original_submission is not None:
            mounts.extend(["--ro-bind", str(self.submission), str(self.original_submission)])
        command[position:position] = mounts
        return command

    def stop(self):
        if self.process is not None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait()


def campaign_budget(policy):
    path = ROOT / "campaign.json"
    if not path.exists():
        write_json(path, {"started_at": now(), "started_unix": time.time()})
    data = read_json(path)
    count = len(list((ROOT / "runs").glob("*/*/launch.json")))
    return count < policy["maximum_total_solver_processes"] and time.time() - data["started_unix"] + policy["wall_seconds_per_case"] <= policy["maximum_campaign_wall_seconds"]


def run_case(reference, case_path, stage, policy, source_manifest, require_quiet=False):
    destination = ROOT / "runs" / stage / reference["case_id"]
    record_path = destination / "record.json"
    input_hash = digest(case_path)
    source_hash = digest(ROOT / "source_manifest.json")
    if record_path.exists():
        record = read_json(record_path)
        if record["input_sha256"] != input_hash or record["source_manifest_sha256"] != source_hash:
            raise ValueError("attempted resume with changed source or input")
        return record
    destination.mkdir(parents=True, exist_ok=True)
    record = {"case_id": reference["case_id"], "family": reference["family"], "stage": stage, "valid": False, "input_sha256": input_hash, "source_manifest_sha256": source_hash}
    if not campaign_budget(policy):
        record.update({"status": "budget_exhausted", "reason": "bounded campaign limit reached"})
        write_json(record_path, record)
        return record
    selected, before_load, counters = choose_core(policy, require_quiet)
    if selected is None:
        record.update({"status": "load_deferred", "reason": "no sufficiently quiet physical core within bounded wait", "pre_busy_fraction": before_load})
        write_json(record_path, record)
        return record
    if (destination / "launch.json").exists():
        record.update({"status": "interrupted_previous_run", "reason": "a prior launch has no trustworthy final record; not rerun silently"})
        write_json(record_path, record)
        return record
    write_json(destination / "launch.json", {"at": now(), "selected_cpu": selected, "input_sha256": input_hash, "source_manifest_sha256": source_hash})
    case = read_json(case_path)
    reason = None
    with tempfile.TemporaryDirectory(prefix="replay-public-", dir=ROOT / "scratch") as temporary:
        public_input = Path(temporary)
        shutil.copyfile(case_path, public_input / "case.json")
        with ReplaySandbox(ASSETS / "participant", ROOT / "submission", input_dir=public_input, seconds=policy["wall_seconds_per_case"], memory_gib=2) as sandbox:
            sandbox.selected_core = selected
            sandbox.original_submission = source_manifest["original_submission"]
            log_path = destination / "trusted_accounting.json"
            with log_path.open("wb") as log:
                started = time.monotonic()
                process = sandbox.start(["/usr/bin/python3", "/trusted_cpu/run.py"], stdout=log, stderr=log)
                while True:
                    waited, status, usage = os.wait4(process.pid, os.WNOHANG)
                    if waited:
                        process.returncode = os.waitstatus_to_exitcode(status)
                        break
                    if time.monotonic() - started > policy["wall_seconds_per_case"]:
                        reason = "wall deadline exceeded"
                    try:
                        if scratch_usage(sandbox.output) + log_path.stat().st_size > policy["scratch_mib"] * 1024**2:
                            reason = "scratch/log limit exceeded"
                    except ValueError as error:
                        reason = str(error)
                    if reason:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        waited, status, usage = os.wait4(process.pid, 0)
                        process.returncode = os.waitstatus_to_exitcode(status)
                        break
                    time.sleep(0.025)
                elapsed = time.monotonic() - started
                sandbox.stop()
            payload = {}
            if process.returncode == 0 and reason is None:
                try:
                    payload = read_json(log_path)
                    if payload["schema_version"] != 1 or payload["returncode"] != 0:
                        raise ValueError("incorrect accounting protocol")
                except Exception as error:
                    reason = "invalid trusted accounting: " + str(error)[:160]
            outer_cpu = usage.ru_utime + usage.ru_stime
            cpu_seconds = payload.get("cpu_seconds", 0) + payload.get("monitor_cpu_seconds", 0) + outer_cpu
            after = cpu_counters()
            sibling_load = [utilization(counters, after, other) for other in siblings(selected) if other != selected]
            accounting = {"wall_seconds": elapsed, "cpu_seconds": cpu_seconds, "cpu_to_wall_ratio": cpu_seconds / elapsed, "selected_cpu": selected, "pre_busy_fraction": before_load, "sibling_busy_max": max(sibling_load, default=0), "outer_bubblewrap_cpu_seconds": outer_cpu, "maximum_rss_kib": payload.get("maximum_rss_kib"), "affinity_locked": True, "trusted_monitor_sha256": digest(ASSETS / "cpu_monitor/run.py"), "returncode": process.returncode}
            record["resource_accounting"] = accounting
            record["low_load_validated"] = quiet_accounting(accounting, policy)
            if (sandbox.output / "solver.log").exists():
                shutil.copyfile(sandbox.output / "solver.log", destination / "solver.log")
            if process.returncode != 0:
                reason = reason or "nonzero process exit"
            if elapsed > policy["wall_seconds_per_case"] or cpu_seconds > policy["cpu_seconds_per_case"]:
                reason = "trusted resource deadline exceeded"
            try:
                if scratch_usage(sandbox.output) + log_path.stat().st_size > policy["scratch_mib"] * 1024**2:
                    reason = "scratch/log limit exceeded"
                if reason is None:
                    field = checked_field(sandbox.output / "result.npz", case, policy["result_max_bytes"])
                    energy, unused, rms = energy_gradient(case, field)
                    np.savez_compressed(destination / "field.npz", psi=field)
                    initial = np.asarray(case["initial_real"]) + 1j * np.asarray(case["initial_imag"])
                    initial_energy, unused, unused_rms = energy_gradient(case, initial)
                    if rms > policy["stationarity_rms_max"]:
                        reason = "output not stationary"
                    elif energy < lower_bound(case) - 1e-8:
                        reason = "energy below rigorous onsite lower bound"
                    elif energy > initial_energy + policy["regression_relative_tolerance"] * max(1, abs(initial_energy)):
                        reason = "quality regression against supplied feasible initial field"
                    record.update({"checked_energy": energy, "gradient_rms": rms, "field_path": relative(destination / "field.npz"), "remaining_gap": energy - reference["witness_energy"], "provided_initial_energy": initial_energy})
            except Exception as error:
                reason = "invalid result: " + str(error)[:200]
    record.update({"valid": reason is None, "status": "valid" if reason is None else "invalid", "reason": reason or "ok"})
    write_json(record_path, record)
    print(stage, reference["case_id"], record["status"], record.get("remaining_gap"), "low_load", record["low_load_validated"], flush=True)
    return record
