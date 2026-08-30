import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"
APPROVED_RUNNER_DIGESTS = {
    "9625e083fce46db66609c63bca91b7177bd6165ac79e2efbfb02c8cc5aa43da3",
    "06f4693741de6587283d2cf78d91895e5a74c1230c9960b5457f8cc536cf0394",
}


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts and not path.is_symlink()}


def fresh_runtime():
    original = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    parent = ROOT / "authoring/runtimes"
    parent.mkdir(parents=True, exist_ok=True)
    runtime = Path(tempfile.mkdtemp(prefix="fresh_", dir=parent))
    selected = []
    section = ""
    allowed = {"model_provider", "preferred_auth_method", "forced_login_method", "cli_auth_credentials_store"}
    for line in (original / "config.toml").read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            section = stripped
        if section.startswith("[model_providers.") or section == "[model_providers]":
            selected.append(line)
        elif not section and re.match(r"[a-zA-Z_]+\s*=", stripped):
            if stripped.split("=", 1)[0].strip() in allowed:
                selected.append(line)
    (runtime / "config.toml").write_text("\n".join(selected) + "\n[permissions.benchmark.network]\nenabled = false\n")
    (runtime / "config.toml").chmod(0o600)
    if (original / "auth.json").exists():
        shutil.copy2(original / "auth.json", runtime / "auth.json")
        (runtime / "auth.json").chmod(0o600)
    (runtime / "packages").mkdir()
    (runtime / "tmp/arg0").mkdir(parents=True)
    return runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--attempt", default="v_1")
    parser.add_argument("--seconds", type=int, default=3600)
    parser.add_argument("--freeze-only", action="store_true")
    parser.add_argument("--cores", type=int)
    parser.add_argument("--address-space-gib", type=int)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        raise ValueError("attempt limit must not exceed one hour")
    concept = ROOT / args.concept
    participant = (concept / "participant").resolve()
    freeze_file = concept / "freeze_manifest.json"
    if args.freeze_only:
        if freeze_file.exists():
            raise ValueError("generation already frozen")
        if any(path.is_symlink() for path in participant.rglob("*")):
            raise ValueError("participant symlinks are forbidden")
        freeze_file.write_text(json.dumps(dict(frozen_at=datetime.now(timezone.utc).isoformat(),
            participant_sha256=hashes(participant), evaluator_sha256=hashes(concept / "evaluator")), indent=2) + "\n")
        print(str(freeze_file))
        return
    frozen = json.loads(freeze_file.read_text())
    runner_bytes = RUNNER.read_bytes()
    runner_digest = hashlib.sha256(runner_bytes).hexdigest()
    if runner_digest not in APPROVED_RUNNER_DIGESTS:
        raise ValueError("shared runner changed; audit its permissions before another attempt")
    snapshots = ROOT / "authoring/runner_snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    (snapshots / (runner_digest + ".sh")).write_bytes(runner_bytes)
    if hashes(participant) != frozen["participant_sha256"] or hashes(concept / "evaluator") != frozen["evaluator_sha256"]:
        raise ValueError("assets changed after generation freeze")
    output = (concept / "attempts" / args.attempt).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("fresh agent requires an empty output directory")
    runtime = fresh_runtime()
    environment = dict(os.environ, CODEX_HOME=str(runtime), OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
                       MKL_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    prompt = (
        f"Read TASK.md and solve the task autonomously. Write the complete required submission to {output}. "
        f"You have at most {args.seconds} seconds. Participant assets are read-only; use your output directory for all work. "
        "Decide your own investigation, implementation, and validation. Do not stop at a plan or placeholder. "
        "Only participant assets, system software, and your initially empty output directory are available. "
        "Networking, external repositories, private evaluators, generation artifacts, and other submissions are unavailable. "
        "Work independently without spawning agents. Use login=false for shell commands."
    )
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only",
               str(participant), str(output), prompt]
    available_cores = sorted(os.sched_getaffinity(0))
    offset = int(hashlib.sha256(args.concept.encode()).hexdigest()[:8], 16) % len(available_cores)
    selected_cores = [available_cores[(offset + index) % len(available_cores)]
                      for index in range(min(args.cores or len(available_cores), len(available_cores)))]

    def set_resources():
        if args.cores:
            os.sched_setaffinity(0, selected_cores)
        if args.address_space_gib:
            ceiling = args.address_space_gib * 1024 ** 3
            resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))

    started = time.monotonic()
    record_path = concept / "attempts" / (args.attempt + ".run.json")
    record = dict(model="ultima-alpha", effort="high", limit_seconds=args.seconds,
                  started_at=datetime.now(timezone.utc).isoformat(), runner=str(RUNNER),
                  runner_sha256=runner_digest, participant=str(participant),
                  output=str(output), initial_output_empty=True, task_read_only=True, ephemeral=True,
                  fresh_runtime=True, web_search="disabled", command_network_enabled=False,
                  private_artifacts_available=False, participant_sha256=frozen["participant_sha256"],
                  evaluator_sha256=frozen["evaluator_sha256"], prompt=prompt, status="running")
    record.update(cpu_affinity=selected_cores if args.cores else None,
                  per_process_address_space_gib=args.address_space_gib)
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    try:
        with (concept / "attempts" / (args.attempt + ".log")).open("w") as log:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                       env=environment, start_new_session=True, preexec_fn=set_resources)
            record["agent_pid"] = process.pid
            record_path.write_text(json.dumps(record, indent=2) + "\n")
            try:
                process.wait(timeout=args.seconds)
                record["timed_out"] = False
            except subprocess.TimeoutExpired:
                record["timed_out"] = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        record.update(status="finished", returncode=process.returncode, elapsed_seconds=time.monotonic() - started,
                      runner_sha256_at_finish=hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
                      finished_at=datetime.now(timezone.utc).isoformat(), submission_sha256=hashes(output),
                      participant_unchanged=hashes(participant) == frozen["participant_sha256"],
                      evaluator_unchanged=hashes(concept / "evaluator") == frozen["evaluator_sha256"])
        record_path.write_text(json.dumps(record, indent=2) + "\n")
    finally:
        for filename in ("auth.json", "config.toml"):
            credential = runtime / filename
            if credential.exists():
                credential.unlink()
    print(json.dumps({key: value for key, value in record.items() if key not in
                      ("participant_sha256", "evaluator_sha256", "submission_sha256", "prompt")}))


if __name__ == "__main__":
    main()
