import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import subprocess
import time


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def digest_tree(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def run_one(concept, stage, limit):
    pilot = ROOT / "pilots" / concept
    participant = pilot / "participant" if stage == "screening" else pilot / stage / "participant"
    attempt = pilot / "attempt" if stage == "screening" else pilot / stage / "attempt"
    attempt.mkdir(parents=True, exist_ok=True)
    if any(attempt.iterdir()):
        raise RuntimeError("fresh attempt directory is not empty: " + str(attempt))
    logs = ROOT / "authoring" / "runs" / concept / stage
    logs.mkdir(parents=True, exist_ok=True)
    prompt = ("Solve the mission in TASK.md autonomously. Your only task inputs are in this participant directory. "
              "Write the completed submission, including solver.py and any supporting files, into " + str(attempt) +
              ". Do not modify the read-only participant tree. You have up to one hour. "
              "The callable entry point and scientific contract are in TASK.md and input/. "
              "Prioritize a working core numerical solution and test it locally. Do not search for private evaluation files.")
    command = ["timeout", "--signal=TERM", "--kill-after=30s", str(limit) + "s", "bash", str(RUNNER),
               "--model", "ultima-alpha", "--effort", "high", "--task-read-only",
               str(participant), str(attempt), prompt]
    metadata = {"concept": concept, "stage": stage, "model": "ultima-alpha", "time_limit_seconds": limit,
                "runner": str(RUNNER), "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
                "participant": str(participant), "attempt": str(attempt), "command": command,
                "participant_sha256_before": digest_tree(participant), "start_unix": time.time()}
    (logs / "launch.json").write_text(json.dumps(metadata, indent=2))
    environment = os.environ.copy()
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
    with (logs / "agent.log").open("w") as stream:
        process = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, env=environment)
    metadata.update({"exit_code": process.returncode, "elapsed_seconds": time.time() - metadata["start_unix"],
                     "timed_out": process.returncode in (124, 137), "participant_sha256_after": digest_tree(participant),
                     "submission_sha256": digest_tree(attempt)})
    metadata["participant_unchanged"] = metadata["participant_sha256_before"] == metadata["participant_sha256_after"]
    (logs / "result.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps({key: metadata[key] for key in ("concept", "stage", "exit_code", "elapsed_seconds", "timed_out")}), flush=True)
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concepts", nargs="+")
    parser.add_argument("--stage", default="screening")
    parser.add_argument("--limit", type=int, default=3600)
    arguments = parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(arguments.concepts)) as executor:
        results = list(executor.map(lambda concept: run_one(concept, arguments.stage, arguments.limit), arguments.concepts))
    print(json.dumps({"completed": len(results)}), flush=True)


if __name__ == "__main__":
    main()
