import argparse
import ctypes
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

try:
    import tomllib
except ImportError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def inventory(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def descendants(parent):
    result = []
    try:
        children = Path(f"/proc/{parent}/task/{parent}/children").read_text().split()
    except (FileNotFoundError, ProcessLookupError):
        return result
    for child in children:
        result.extend(descendants(int(child)))
        result.append(int(child))
    return result


def terminate_descendants():
    terminated = set()
    for pending_signal in (signal.SIGTERM, signal.SIGKILL):
        for child in descendants(os.getpid()):
            try:
                os.kill(child, pending_signal)
                terminated.add(child)
            except ProcessLookupError:
                pass
        time.sleep(1)
    return sorted(terminated)


def runtime_home():
    original = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).resolve()
    config = tomllib.loads((original / "config.toml").read_text())
    if config.get("model_providers"):
        raise RuntimeError("Provider overrides require explicit sanitization")
    runtime = Path(tempfile.mkdtemp(prefix=".runtime-", dir=ROOT / "research"))
    runtime.chmod(0o700)
    (runtime / "packages").symlink_to(original / "packages", target_is_directory=True)
    (runtime / "tmp" / "arg0").mkdir(parents=True)
    if (original / "auth.json").exists():
        (runtime / "auth.json").symlink_to(original / "auth.json")
    settings = ['model = "ultima-alpha"', 'model_reasoning_effort = "high"', 'web_search = "disabled"']
    for key in ("model_catalog_json", "model_provider", "chatgpt_base_url"):
        if key in config:
            settings.append(f"{key} = {json.dumps(config[key])}")
    settings.extend(["[features]", "shell_snapshot = false"])
    (runtime / "config.toml").write_text("\n".join(settings) + "\n")
    return runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--limit", type=int, default=3600)
    parser.add_argument("--preflight", action="store_true")
    arguments = parser.parse_args()
    if not 1 <= arguments.limit <= 3600:
        raise ValueError("Attempt limit must be at most one hour")
    concept = (ROOT / arguments.concept).resolve()
    participant = concept / "participant"
    output = concept / "attempts" / f"v_{arguments.attempt}"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=True)
    lock = output.with_suffix(".lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    metadata = output.with_suffix(".metadata.json")
    if list(output.iterdir()) or metadata.exists():
        raise RuntimeError("Fresh attempts require an empty output and no earlier metadata")
    runtime = runtime_home()
    started_utc = datetime.datetime.now(datetime.timezone.utc)
    deadline = started_utc + datetime.timedelta(seconds=arguments.limit)
    prompt = (
        f"Read TASK.md in {participant} and solve the professional task autonomously. "
        f"Write your complete final submission and all scratch work into {output}. "
        "Participant assets are read-only. Only these assets, your initially empty "
        "writable output directory, and standard runtime tools are available. "
        "Hidden evaluators, generators, private data, other attempts and the network "
        "are unavailable. Follow the stated executable/artifact interface. "
        "Decide your own investigation and approach; produce the requested artifact, "
        "not just a proposal. You may use the full wall-clock allowance to test and improve. "
        f"The limit is {arguments.limit} seconds, with an absolute UTC deadline of "
        f"{deadline.isoformat()}. Startup and tools count toward this limit."
    )
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only",
               str(participant), str(output), prompt]
    environment = dict(os.environ, CODEX_HOME=str(runtime), OPENBLAS_NUM_THREADS="1",
                       OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1",
                       PYTHONDONTWRITEBYTECODE="1", TASK_DEADLINE_UTC=deadline.isoformat())
    if ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError("Cannot install child deadline supervisor")
    record = {"model": "ultima-alpha", "effort": "high", "limit_seconds": arguments.limit,
              "generation": arguments.generation, "attempt": arguments.attempt,
              "preflight_only": arguments.preflight, "fresh": True, "output_empty_at_launch": True,
              "participant_read_only": True, "runner": str(RUNNER), "command": command,
              "participant": str(participant), "output": str(output),
              "started_utc": started_utc.isoformat(), "deadline_utc": deadline.isoformat(),
              "participant_hashes_before": inventory(participant),
              "evaluator_hashes_before": inventory(concept / "evaluator"),
              "status_at_launch": json.loads((concept / "status.json").read_text()),
              "runtime": str(runtime), "private_artifacts_mounted": False}
    metadata.write_text(json.dumps(record, indent=2) + "\n")
    started = time.monotonic()
    with output.with_suffix(".transcript.txt").open("w") as transcript:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=transcript,
                                 stderr=subprocess.STDOUT, env=environment, start_new_session=True)
        record["pid"] = child.pid
        metadata.write_text(json.dumps(record, indent=2) + "\n")
        try:
            returncode = child.wait(timeout=arguments.limit)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            terminate_descendants()
            returncode = child.wait(timeout=20)
    record.update({"returncode": returncode, "timed_out": timed_out,
                   "elapsed_seconds": time.monotonic() - started,
                   "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "background_descendants_terminated": terminate_descendants(),
                   "participant_hashes_after": inventory(participant),
                   "evaluator_hashes_after": inventory(concept / "evaluator"),
                   "submission_hashes": inventory(output)})
    record["participant_unchanged"] = record["participant_hashes_before"] == record["participant_hashes_after"]
    record["evaluator_unchanged"] = record["evaluator_hashes_before"] == record["evaluator_hashes_after"]
    metadata.write_text(json.dumps(record, indent=2) + "\n")
    if (runtime / "auth.json").is_symlink():
        (runtime / "auth.json").unlink()
    print(json.dumps({key: record[key] for key in ("model", "generation", "attempt", "returncode",
                      "timed_out", "elapsed_seconds", "participant_unchanged", "evaluator_unchanged")}, indent=2))


if __name__ == "__main__":
    main()
