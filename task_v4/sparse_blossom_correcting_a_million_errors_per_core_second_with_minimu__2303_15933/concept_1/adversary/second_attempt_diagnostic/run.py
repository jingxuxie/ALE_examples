import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

SIDE = Path(__file__).resolve().parent
ROOT = SIDE.parents[1]
GENERATION = ROOT / "generations/generation_2"
SUBMISSION = GENERATION / "attempts/v_2_frozen_submission/submission.py"
sys.dont_write_bytecode = True
os.environ.update(PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
    MPLCONFIGDIR=str(SIDE / "cache"), TMPDIR=str(SIDE / "tmp"))
(SIDE / "tmp").mkdir(exist_ok=True)


def save(name, value):
    (SIDE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_evaluator():
    specification = importlib.util.spec_from_file_location("unchanged_evaluator", GENERATION / "evaluator/evaluate.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def inventory(directory):
    return {path.relative_to(directory).as_posix(): digest(path) for path in sorted(directory.rglob("*")) if path.is_file()}


def integrity():
    module = load_evaluator()
    frozen = module.verify_freeze()
    protected = {}
    for relative in ["participant", "evaluator"]:
        protected.update({relative + "/" + name: value for name, value in inventory(GENERATION / relative).items()})
    for relative in ["status.json", "participant/input/target.json"]:
        protected[relative] = digest(GENERATION / relative)
    snapshots = {name: inventory(GENERATION / "attempts" / (name + "_frozen_submission")) for name in ["v_1", "v_2"]}
    audit = json.loads((GENERATION / "attempts/v_2_evaluation_audit.json").read_text())
    expected = audit["frozen_submission_sha256"]
    if snapshots["v_2"] != expected:
        raise RuntimeError("Frozen v2 snapshot differs from the official pre-evaluation audit")
    return dict(utc=datetime.now(timezone.utc).isoformat(), freeze_sha256=digest(GENERATION / "evaluator/hidden/frozen.json"),
        protected=protected, snapshots=snapshots, audit_identity_matches=True, original_limits=frozen["limits"])


def proc_snapshot(pid):
    base = Path("/proc") / str(pid)
    try:
        raw = (base / "stat").read_text()
        fields = raw[raw.rfind(")") + 2:].split()
        ticks = os.sysconf("SC_CLK_TCK")
        usage = dict(pid=pid, state=fields[0], parent_pid=int(fields[1]), threads=int(fields[17]),
            proc_cpu_seconds=(int(fields[11]) + int(fields[12])) / ticks,
            command=(base / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace"))
        try:
            usage["scheduled_cpu_seconds"] = int((base / "schedstat").read_text().split()[0]) / 1e9
        except (OSError, ValueError, IndexError):
            pass
        usage["cpu_limit"] = next((line for line in (base / "limits").read_text().splitlines() if line.startswith("Max cpu time")), None)
        usage["memory_status"] = [line for line in (base / "status").read_text().splitlines() if line.startswith(("VmRSS:", "VmHWM:", "NSpid:"))]
        children = [int(value) for value in (base / "task" / str(pid) / "children").read_text().split()]
        return usage, children
    except (OSError, ValueError, IndexError, ProcessLookupError):
        return None, []


def monitor_tree(root_pid):
    pending, records, visited = [root_pid], [], set()
    while pending:
        pid = pending.pop()
        if pid in visited:
            continue
        visited.add(pid)
        record, children = proc_snapshot(pid)
        if record:
            records.append(record)
        pending.extend(children)
    return records


def host_snapshot():
    result = dict(uname=list(os.uname()), utc=datetime.now(timezone.utc).isoformat())
    for path in [Path("/proc/self/cgroup"), Path("/sys/fs/cgroup/memory.events"), Path("/proc/loadavg")]:
        try:
            result[str(path)] = path.read_text()
        except OSError as error:
            result[str(path)] = type(error).__name__
    return result


def run_monitored(name, command, deadline):
    if (SIDE / (name + ".json")).exists():
        raise RuntimeError("Refusing to repeat or overwrite an evaluation")
    started = time.monotonic()
    with (SIDE / (name + ".log")).open("wb") as log, (SIDE / (name + "_processes.jsonl")).open("w") as process_log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            env=os.environ.copy(), start_new_session=True)
        killed_by_driver = False
        while process.poll() is None:
            completed = [path.name for path in (SIDE / "tmp").glob("logical-decoder-*/out/*.npz")]
            process_log.write(json.dumps(dict(elapsed_seconds=time.monotonic() - started,
                processes=monitor_tree(process.pid), completed_artifacts=completed)) + "\n")
            process_log.flush()
            if time.monotonic() >= deadline:
                killed_by_driver = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(1)
        returncode = process.wait()
    result = dict(command=command, returncode=returncode, wall_seconds=time.monotonic() - started,
        driver_watchdog=killed_by_driver, external_monitor_only=True)
    save(name + "_launcher.json", result)
    return result


def relaxed_worker():
    module = load_evaluator()
    original = module.verify_freeze()
    original_verifier = module.verify_freeze
    original_isolated = module.run_isolated

    def diagnostic_freeze():
        frozen = copy.deepcopy(original_verifier())
        frozen["limits"]["cpu_seconds"] = 180
        return frozen

    def capture_isolated(command, log_path, wall_limit):
        execution = original_isolated(command, log_path, wall_limit)
        workspace = log_path.parent
        output = SIDE / "relaxed_worker_outputs"
        output.mkdir(exist_ok=True)
        for path in (workspace / "out").iterdir():
            if path.is_file() and not path.is_symlink():
                shutil.copy2(path, output / path.name)
        shutil.copy2(workspace / "request/request.json", SIDE / "relaxed_request.json")
        save("relaxed_isolation_command.json", dict(command=command, execution=execution))
        return execution

    module.verify_freeze = diagnostic_freeze
    module.run_isolated = capture_isolated
    evaluated = module.evaluate(SUBMISSION, "both")
    comparison = None
    if evaluated.get("valid"):
        comparison = dict(evaluated["gates"])
        comparison["runtime"] = evaluated["execution"]["cpu_seconds"] <= original["limits"]["cpu_seconds"] and not evaluated["execution"]["watchdog_timeout"]
    report = dict(kind="NONQUALIFYING_RELAXED_CPU_DIAGNOSTIC", nonqualifying_diagnostic=True,
        valid=evaluated.get("valid", False), passed=False,
        reason="The CPU ceiling was relaxed in memory; this is not an official qualifying score",
        original_cpu_seconds=original["limits"]["cpu_seconds"], original_worker_cpu_rlimit=original["limits"]["cpu_seconds"] + 1,
        diagnostic_cpu_seconds=180, diagnostic_worker_cpu_rlimit=181, source_unchanged=True, mandatory_isolation_unchanged=True,
        original_numeric_gate_comparison=comparison, original_numeric_gates_all_met=all(comparison.values()) if comparison else None,
        evaluation=evaluated)
    save("relaxed_diagnostic.json", report)
    print(json.dumps(report, indent=2), flush=True)


def main():
    if "--relaxed-worker" in sys.argv:
        relaxed_worker()
        return
    if (SIDE / "integrity_before.json").exists():
        raise RuntimeError("This diagnostic is single-use; no extra official replay")
    before = integrity()
    save("integrity_before.json", before)
    save("host_before.json", host_snapshot())
    shutil.copy2(GENERATION / "attempts/v_2_result.json", SIDE / "initial_official_result.json")
    shutil.copy2(SUBMISSION.parent / "finalvalid.log", SIDE / "frozen_development_finalvalid.log")
    deadline = time.monotonic() + 1000
    command = ["/usr/bin/python3", str(GENERATION / "evaluator/evaluate.py"), "--submission", str(SUBMISSION),
        "--split", "both", "--report", str(SIDE / "official_replay.json")]
    official = run_monitored("official_replay", command, deadline)
    print("Official replay completed: " + json.dumps(official), flush=True)
    if official["driver_watchdog"]:
        raise RuntimeError("Bounded driver watchdog stopped replay; no resource conclusion is justified")
    diagnostic = run_monitored("relaxed_diagnostic", ["/usr/bin/python3", str(Path(__file__).resolve()), "--relaxed-worker"], deadline)
    print("Relaxed diagnostic completed: " + json.dumps(diagnostic), flush=True)
    after = integrity()
    save("integrity_after.json", after)
    save("host_after.json", host_snapshot())
    replay = json.loads((SIDE / "official_replay.json").read_text())
    relaxed_path = SIDE / "relaxed_diagnostic.json"
    relaxed = json.loads(relaxed_path.read_text()) if relaxed_path.exists() else None
    summary = dict(official_replay_count=1, relaxed_run_count=1, unchanged_protected_tree=before["protected"] == after["protected"],
        unchanged_v1_snapshot=before["snapshots"]["v_1"] == after["snapshots"]["v_1"],
        unchanged_v2_snapshot=before["snapshots"]["v_2"] == after["snapshots"]["v_2"],
        freeze_sha256=before["freeze_sha256"], official_replay=replay, relaxed_diagnostic=relaxed,
        driver_watchdog=diagnostic["driver_watchdog"], no_candidate_optimization=True, no_fresh_agents_launched=True,
        interpretation="A SIGKILL return code alone does not identify its sender. A completed relaxed run supplies quality and CPU evidence but cannot qualify under changed enforcement. Compare its measured CPU with the original 132-second numerical gate.")
    save("summary.json", summary)
    print(json.dumps(dict(unchanged=summary["unchanged_protected_tree"] and summary["unchanged_v2_snapshot"],
        replay_valid=replay.get("valid"), replay_passed=replay.get("passed"), relaxed_valid=relaxed.get("valid") if relaxed else None)), flush=True)


if __name__ == "__main__":
    main()
