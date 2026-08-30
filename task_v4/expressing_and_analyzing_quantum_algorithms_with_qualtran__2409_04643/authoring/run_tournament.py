import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import tempfile
import time

import tomli

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def make_runtime():
    source = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).resolve()
    parent = ROOT / "authoring" / "infrastructure" / "runtimes"
    parent.mkdir(parents=True, exist_ok=True)
    runtime = Path(tempfile.mkdtemp(prefix="fresh_", dir=parent))
    runtime.chmod(0o700)
    configuration = tomli.loads((source / "config.toml").read_text())
    if configuration.get("model_provider") or configuration.get("model_providers"):
        raise RuntimeError("custom provider requires explicit review")
    lines = ['model = "ultima-alpha"', 'model_reasoning_effort = "xhigh"']
    if configuration.get("model_catalog_json"):
        shutil.copyfile(configuration["model_catalog_json"], runtime / "model_catalog.json")
        lines.append("model_catalog_json = " + json.dumps(str(runtime / "model_catalog.json")))
    (runtime / "config.toml").write_text("\n".join(lines) + "\n")
    if (source / "auth.json").exists():
        shutil.copyfile(source / "auth.json", runtime / "auth.json")
        (runtime / "auth.json").chmod(0o600)
    binary = Path(shutil.which("codex")).resolve()
    local_bin = runtime / "packages" / "bin"
    local_bin.mkdir(parents=True)
    for executable in binary.parent.iterdir():
        if executable.is_file():
            try:
                os.link(executable, local_bin / executable.name)
            except OSError:
                shutil.copy2(executable, local_bin / executable.name)
    (runtime / "tmp" / "arg0").mkdir(parents=True)
    return runtime


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    available = sorted(os.sched_getaffinity(0))
    offset = (os.getpid() * 4) % len(available)
    os.sched_setaffinity(0, {available[(offset + index) % len(available)] for index in range(min(4, len(available)))})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=int)
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--attempt-index", type=int)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    attempt_index = args.attempt_index or args.generation
    concept = ROOT / f"concept_{args.concept}"
    participant = (concept / "participant").resolve()
    if args.preflight:
        label = "preflight" if attempt_index == 1 else f"preflight_{attempt_index}"
        record_dir = ROOT / "authoring" / "infrastructure" / label
        output = record_dir / "output"
    else:
        freeze_path = concept / "adversary" / f"generation_{args.generation}_freeze.json"
        frozen = json.loads(freeze_path.read_text())["sha256"]
        if any(frozen.get("participant/" + name) != digest for name, digest in hashes(participant).items()):
            raise RuntimeError("participant differs from frozen assets")
        record_dir = concept / "adversary" / f"run_v_{attempt_index}"
        output = concept / "attempts" / f"v_{attempt_index}"
    record_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("fresh output must initially be empty")
    runtime = make_runtime()
    prompt = ("You are a completely fresh independent participant. Read TASK.md and the supplied local assets. "
              "Solve the task autonomously and write the required artifact to " + str(output) + ". "
              "You have up to 3600 seconds, four CPU threads and 8 GiB memory. The participant directory is "
              "read-only; write all code, experiments and scratch files in the output directory. Use only "
              "the participant assets and system dependencies. Do not seek other sessions, hidden evaluation "
              "data, authoring files, prior attempts or network access. Your task is the mission in TASK.md, "
              "not infrastructure exploration. Keep improving until the target is reached or time runs out. "
              "Submit your best artifact even if the target remains unmet. Shell startup can be slow in "
              "this isolated environment; persistent terminal sessions are supported for efficient local work.")
    prompt_file = record_dir / "prompt.txt"
    prompt_file.write_text(prompt)
    command = ["unshare", "--user", "--map-root-user", "--mount", "--propagation", "private",
               "--pid", "--fork", "python3", str(ROOT / "authoring" / "private_root_launch.py"),
               "--parent-mount-namespace", os.readlink("/proc/self/ns/mnt"),
               "--participant", str(participant), "--output", str(output.resolve()),
               "--runtime-home", str(runtime), "--runner", str(RUNNER.resolve()),
               "--prompt-file", str(prompt_file.resolve())]
    if args.preflight:
        command.append("--preflight")
    metadata = {"model": "ultima-alpha", "effort": "xhigh", "generation": args.generation,
                "attempt_index": attempt_index,
                "preflight": args.preflight, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "time_limit_seconds": 120 if args.preflight else 3600,
                "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
                "participant_sha256": hashes(participant), "initial_output_empty": True,
                "allowlisted_paths": {str(participant): "read", str(output.resolve()): "write"},
                "runtime": str(runtime), "command": command, "completed": False}
    metadata_file = record_dir / "run.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))
    environment = os.environ.copy()
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        environment[variable] = "4"
    started = time.monotonic()
    with (record_dir / "session.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   env=environment, preexec_fn=limits, start_new_session=True)
        metadata["pid"] = process.pid
        metadata_file.write_text(json.dumps(metadata, indent=2))
        timed_out = False
        try:
            returncode = process.wait(timeout=metadata["time_limit_seconds"])
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
    metadata.update({"completed": True, "timed_out": timed_out, "returncode": returncode,
                     "elapsed_seconds": time.monotonic() - started,
                     "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     "participant_unchanged": hashes(participant) == metadata["participant_sha256"],
                     "output_files": sorted(str(path.relative_to(output)) for path in output.rglob("*") if path.is_file())})
    metadata_file.write_text(json.dumps(metadata, indent=2))
    if (runtime / "auth.json").exists():
        (runtime / "auth.json").unlink()
    print(json.dumps({key: metadata[key] for key in ("model", "preflight", "completed", "returncode", "timed_out", "elapsed_seconds", "participant_unchanged", "output_files")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
