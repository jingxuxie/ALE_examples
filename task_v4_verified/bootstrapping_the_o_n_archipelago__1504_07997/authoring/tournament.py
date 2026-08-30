import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time

try:
    import tomllib
except ImportError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def hashes(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            content = b"SYMLINK:" + os.fsencode(os.readlink(path))
        elif path.is_file():
            content = path.read_bytes()
        else:
            continue
        result[str(path.relative_to(directory))] = hashlib.sha256(content).hexdigest()
    return result


def clean_runtime(environment):
    original = Path(environment.get("CODEX_HOME", str(Path.home() / ".codex"))).resolve()
    parent = ROOT / "authoring/runtimes"
    parent.mkdir(exist_ok=True)
    runtime = Path(tempfile.mkdtemp(prefix="fresh_", dir=parent))
    runtime.chmod(0o700)
    configuration = tomllib.loads((original / "config.toml").read_text())
    lines = ['model = "ultima-alpha"', 'model_reasoning_effort = "high"']
    if configuration.get("model_catalog_json"):
        shutil.copyfile(configuration["model_catalog_json"], runtime / "model_catalog.json")
        lines.append("model_catalog_json = " + json.dumps(str(runtime / "model_catalog.json")))
    for key in ("model_provider", "model_providers"):
        if key in configuration:
            raise RuntimeError("custom provider requires explicit reviewed clean-runtime configuration")
    (runtime / "config.toml").write_text("\n".join(lines) + "\n")
    if (original / "auth.json").exists():
        shutil.copyfile(original / "auth.json", runtime / "auth.json")
        (runtime / "auth.json").chmod(0o600)
    binary = Path(shutil.which("codex")).resolve()
    local_bin = runtime / "packages/bin"
    local_bin.mkdir(parents=True)
    for source in binary.parent.iterdir():
        if source.is_file():
            try:
                os.link(source, local_bin / source.name)
            except OSError:
                shutil.copyfile(source, local_bin / source.name)
                shutil.copymode(source, local_bin / source.name)
    (runtime / "tmp/arg0").mkdir(parents=True)
    environment["PATH"] = str(local_bin) + os.pathsep + environment.get("PATH", "")
    environment["CODEX_HOME"] = str(runtime)
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        environment[variable] = "4"
    return runtime


def resource_limits():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    available = sorted(os.sched_getaffinity(0))
    offset = (os.getpid() * 4) % len(available)
    os.sched_setaffinity(0, {available[(offset+position) % len(available)] for position in range(4)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--attempt", default="v_1")
    parser.add_argument("--generation", type=int, default=1)
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    participant = concept / "participant"
    output = concept / "attempts" / arguments.attempt
    output.mkdir(parents=True, exist_ok=True)
    if list(output.iterdir()):
        raise RuntimeError("fresh output must be empty")
    metadata_path = output.parent / (arguments.attempt + ".metadata.json")
    if metadata_path.exists():
        raise RuntimeError("attempt already exists")
    prompt = (
        "Read TASK.md and solve the task autonomously. You have at most one hour. "
        "Only participant/ is available, read-only, plus normal installed system tools. "
        f"Your initially empty writable output directory is {output}. "
        "Put your final submission and all needed assets there. Choose your own "
        "research and solution strategy, and save the best complete submission you can. "
        "Do not access any sibling task, evaluator, hidden data, prior submissions, "
        "Codex runtime files or external network. Do not request escalation. "
        "The resource cap is four CPU threads and 4 GiB RAM. "
        "Use only your output directory for scratch files."
    )
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only",
               str(participant), str(output), prompt]
    environment = os.environ.copy()
    runtime = clean_runtime(environment)
    prompt_path = output.parent / (arguments.attempt + ".prompt.txt")
    prompt_path.write_text(prompt + "\n")
    private_launcher = ROOT / "authoring/private_root_launch.py"
    launch_command = ["/usr/bin/unshare", "--user", "--map-root-user", "--mount", "--propagation", "private",
                      "--pid", "--fork", sys.executable, str(private_launcher),
                      "--participant", str(participant), "--output", str(output),
                      "--runtime-home", str(runtime), "--runner", str(RUNNER),
                      "--prompt-file", str(prompt_path),
                      "--parent-mount-namespace", os.readlink("/proc/self/ns/mnt")]
    metadata = {
        "model": "ultima-alpha", "effort": "high", "time_limit_seconds": 3600,
        "generation": arguments.generation, "attempt": arguments.attempt,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "participant_sha256": hashes(participant), "evaluator_sha256": hashes(concept / "evaluator"),
        "status_sha256": hashlib.sha256((concept / "status.json").read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
        "output_empty_at_start": True, "participant_access": "read-only", "privileged_mounts": [],
        "runtime_home": str(runtime), "runtime_isolation": "fresh; no history, memories, skills, plugins",
        "network": "disabled", "command": command, "status": "running"
    }
    metadata["outer_isolation"] = "private user/mount/PID namespace, detached private root, fresh tmp inode"
    metadata["launch_command"] = launch_command
    metadata["launcher_sha256"] = hashlib.sha256(private_launcher.read_bytes()).hexdigest()
    metadata["evaluation_sandbox_sha256"] = hashlib.sha256((ROOT / "authoring/sandbox.py").read_bytes()).hexdigest()
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    started = time.monotonic()
    with (output.parent / (arguments.attempt + ".session.log")).open("w") as log:
        process = subprocess.Popen(launch_command, env=environment, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=resource_limits)
        metadata["pid"] = process.pid
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
        try:
            process.wait(timeout=3600)
            metadata.update(status="finished", timed_out=False)
        except subprocess.TimeoutExpired:
            metadata.update(status="time_limit", timed_out=True)
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    metadata.update(returncode=process.returncode, elapsed_seconds=time.monotonic() - started,
                    finished_at=datetime.now(timezone.utc).isoformat(), submission_sha256=hashes(output))
    metadata["participant_unchanged"] = hashes(participant) == metadata["participant_sha256"]
    metadata["evaluator_unchanged"] = hashes(concept / "evaluator") == metadata["evaluator_sha256"]
    metadata["launcher_unchanged"] = hashlib.sha256(private_launcher.read_bytes()).hexdigest() == metadata["launcher_sha256"]
    metadata["evaluation_sandbox_unchanged"] = hashlib.sha256((ROOT / "authoring/sandbox.py").read_bytes()).hexdigest() == metadata["evaluation_sandbox_sha256"]
    frozen = output.parent / (arguments.attempt + ".frozen")
    shutil.copytree(output, frozen, symlinks=True)
    metadata["frozen_sha256"] = hashes(frozen)
    metadata["frozen_matches_submission"] = metadata["frozen_sha256"] == metadata["submission_sha256"]
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    auth = runtime / "auth.json"
    if auth.exists():
        auth.unlink()
    print(json.dumps({key: value for key, value in metadata.items()
                      if not key.endswith("sha256") and key != "command"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
