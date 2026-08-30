import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

import tomli

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def digest_tree(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"participant assets may not contain symlinks: {path}")
        if path.is_file() and "__pycache__" not in path.parts:
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def clean_runtime(destination):
    source = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    config = tomli.loads((source / "config.toml").read_text())
    if config.get("model_provider") or config.get("model_providers"):
        raise ValueError("custom providers require explicit configuration review")
    destination.mkdir(parents=True, exist_ok=False)
    catalog = destination / "models.json"
    shutil.copy2(config["model_catalog_json"], catalog)
    shutil.copy2(source / "auth.json", destination / "auth.json")
    os.chmod(destination / "auth.json", 0o600)
    (destination / "packages").symlink_to((source / "packages").resolve(), target_is_directory=True)
    (destination / "tmp" / "arg0").mkdir(parents=True)
    settings = [
        'model = "ultima-alpha"',
        'model_reasoning_effort = "xhigh"',
        f'model_catalog_json = {json.dumps(str(catalog))}',
        'web_search = "disabled"',
        'approval_policy = "never"',
        '[history]',
        'persistence = "none"',
        '[features]',
        'memories = false',
    ]
    (destination / "config.toml").write_text("\n".join(settings) + "\n")
    return destination


def run(concept_number, generation, limit_seconds):
    concept = ROOT / f"concept_{concept_number}"
    participant = (concept / "participant").resolve()
    output = (concept / "attempts" / f"v_{generation}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("fresh submission directory must be initially empty")
    logs = concept / "adversary" / "tournament" / f"v_{generation}"
    logs.mkdir(parents=True, exist_ok=False)
    runtimes = ROOT / "authoring" / "runtimes"
    runtimes.mkdir(parents=True, exist_ok=True)
    runtime = clean_runtime(Path(tempfile.mkdtemp(prefix="fresh_", dir=runtimes)) / "home")
    hashes = digest_tree(participant)
    (logs / "participant_sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    prompt = (
        "Read TASK.md and solve the participant task. "
        f"Your only scientific assets are in {participant}. "
        f"Write the required submission to the initially empty directory {output}. "
        "Participant assets are read-only; create scratch files only in the output directory. "
        f"You have a maximum of {limit_seconds} seconds wall time. "
        "Do not use the network, request broader access, access sibling directories, or delegate to other agents. "
        "Use non-login shell commands (login=false) to avoid startup files outside the allowlist. "
        "Produce the executable or design artifact required by TASK.md before finishing."
    )
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "xhigh", "--task-read-only", str(participant), str(output), prompt]
    environment = dict(os.environ)
    environment["CODEX_HOME"] = str(runtime)
    for name in ("CODEX_THREAD_ID", "CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "CODEX_PERMISSION_PROFILE", "CODEX_SANDBOX_NETWORK_DISABLED"):
        environment.pop(name, None)
    record = {"concept": concept_number, "generation": generation, "model": "ultima-alpha", "effort": "xhigh", "limit_seconds": limit_seconds, "participant": str(participant), "output": str(output), "command": command, "started_at_unix": time.time(), "initial_output_empty": True, "fresh_runtime": True, "task_read_only": True, "runtime": str(runtime)}
    record_path = logs / "run.json"
    started = time.monotonic()
    with (logs / "stdout.log").open("w") as stdout, (logs / "stderr.log").open("w") as stderr:
        process = subprocess.Popen(command, cwd=participant, env=environment, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True)
        record["pid"] = process.pid
        record_path.write_text(json.dumps(record, indent=2) + "\n")
        try:
            returncode = process.wait(timeout=limit_seconds)
            record["timed_out"] = False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
            record["timed_out"] = True
    record.update({"returncode": returncode, "elapsed_seconds": time.monotonic() - started, "ended_at_unix": time.time(), "participant_unchanged": hashes == digest_tree(participant), "submission_files": digest_tree(output)})
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    (runtime / "auth.json").unlink(missing_ok=True)
    print(json.dumps(record, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=int, choices=[1, 2, 3])
    parser.add_argument("--generation", type=int, default=1, choices=[1, 2, 3, 4])
    arguments = parser.parse_args()
    run(arguments.concept, arguments.generation, 3600)


if __name__ == "__main__":
    main()
