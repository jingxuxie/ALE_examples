import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_01"
LAUNCHER = Path("/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh")


def manifest(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v_01")
    parser.add_argument("--attempt", default="fresh_01")
    arguments = parser.parse_args()
    participant = CONCEPT / "participant" / arguments.version
    attempt = CONCEPT / "attempts" / arguments.version / arguments.attempt
    output = attempt / "output"
    output.mkdir(parents=True, exist_ok=False)
    hashes = manifest(participant)
    prompt = (
        f"Solve the research release task in {participant}/TASK.md autonomously. "
        f"The participant directory {participant} is read-only task material. "
        f"Write all your work and final deliverables in {output}. "
        "You have up to one hour. Run experiments, inspect evidence, revise, and produce the requested executable handoff. "
        "Do not ask the user for input or approval. Do not access the web, other task versions, sibling directories, "
        "reference solutions, or graders. Do not spawn additional agents or other Codex sessions. "
        "Only the supplied participant files, your output directory, and installed system tools are available. "
        "Start by confirming the scientific Python imports and reading TASK.md; then carry out the task."
    )
    command = [str(LAUNCHER), "--model", "ultima-alpha", "--effort", "high", str(participant), str(output), prompt]
    metadata = {"model": "ultima-alpha", "reasoning_effort": "high", "limit_seconds": 3600,
                "participant": str(participant), "output_allowlist": str(output),
                "launcher": str(LAUNCHER), "prompt": prompt, "participant_hashes_before": hashes,
                "start_time_unix": time.time(), "status": "running"}
    (attempt / "runtime.json").write_text(json.dumps(metadata, indent=2))
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    started = time.monotonic()
    with (attempt / "transcript.txt").open("w") as transcript:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=transcript, stderr=subprocess.STDOUT,
                                   start_new_session=True, env=environment)
        metadata["pid"] = process.pid
        (attempt / "runtime.json").write_text(json.dumps(metadata, indent=2))
        try:
            returncode = process.wait(timeout=3600)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
    metadata.update({"returncode": returncode, "timed_out": timed_out, "runtime_seconds": time.monotonic() - started,
                     "end_time_unix": time.time(), "status": "finished", "participant_hashes_after": manifest(participant)})
    metadata["participant_unchanged"] = hashes == metadata["participant_hashes_after"]
    (attempt / "runtime.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps({key: value for key, value in metadata.items() if key not in ("prompt", "participant_hashes_before", "participant_hashes_after")}, indent=2))


if __name__ == "__main__":
    main()
