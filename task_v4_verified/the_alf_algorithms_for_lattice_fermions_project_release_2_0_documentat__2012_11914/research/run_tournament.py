import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def manifest(directory):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def attempt(concept_name, generation, seconds, participant_override=None):
    concept = ROOT / concept_name
    participant = Path(participant_override).resolve() if participant_override else concept / "participant"
    output = concept / "attempts" / f"v_{generation}"
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError(f"Fresh submission directory is not empty: {output}")
    logs = concept / "attempts" / "logs"
    logs.mkdir(exist_ok=True)
    prompt = (
        f"Read TASK.md and solve the participant task. Your writable output directory is {output}. "
        "The provided participant directory is read-only; create your solution and all scratch files "
        "in the output directory. Submit the executable or artifact required by TASK.md, not merely a plan. "
        f"You have at most {seconds} seconds of wall time. You may finish earlier if satisfied. "
        "Only the participant assets and your output are available. Do not spawn other agents."
    )
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only", str(participant), str(output), prompt]
    record = {
        "model": "ultima-alpha", "reasoning_effort": "high", "generation": generation,
        "time_limit_seconds": seconds, "participant": str(participant), "output": str(output),
        "runner": str(RUNNER), "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
        "participant_sha256": manifest(participant), "output_initially_empty": True,
        "isolation": "Provided allowlist runner; participant read-only; only output writable; web disabled; ephemeral session; no parent context.",
        "prompt": prompt, "started_unix": time.time(), "state": "running",
    }
    record_path = logs / f"v_{generation}.run.json"
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    started = time.monotonic()
    with (logs / f"v_{generation}.stdout.log").open("w") as stdout, (logs / f"v_{generation}.stderr.log").open("w") as stderr:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True)
        record["pid"] = process.pid
        record_path.write_text(json.dumps(record, indent=2) + "\n")
        timed_out = False
        try:
            return_code = process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                return_code = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                return_code = process.wait()
    record.update({"elapsed_seconds": time.monotonic() - started, "return_code": return_code,
                   "timed_out": timed_out, "state": "finished", "finished_unix": time.time(),
                   "participant_unchanged": manifest(participant) == record["participant_sha256"],
                   "submission_sha256": manifest(output)})
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"concept": concept_name, "generation": generation, "return_code": return_code,
                      "timed_out": timed_out, "elapsed_seconds": record["elapsed_seconds"]}), flush=True)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("concepts", nargs="+")
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--limit", type=int, default=3600)
    parser.add_argument("--participant", type=Path)
    arguments = parser.parse_args()
    if arguments.participant and len(arguments.concepts) != 1:
        parser.error("--participant requires exactly one concept")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(arguments.concepts)) as executor:
        results = [executor.submit(attempt, concept, arguments.generation, arguments.limit, arguments.participant) for concept in arguments.concepts]
        for result in results:
            result.result()
