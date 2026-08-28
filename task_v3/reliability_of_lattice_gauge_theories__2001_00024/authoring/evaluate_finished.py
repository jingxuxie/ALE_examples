import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]


def evaluate_concept(concept, stage, splits):
    pilot = ROOT / "pilots" / concept
    version = pilot if stage == "screening" else pilot / stage
    logs = ROOT / "authoring" / "runs" / concept / stage
    deadline = time.monotonic() + 4500
    while not (logs / "result.json").exists():
        if time.monotonic() > deadline:
            raise RuntimeError("pilot did not produce termination metadata: " + concept)
        time.sleep(10)
    metadata = json.loads((logs / "result.json").read_text())
    if not metadata["participant_unchanged"]:
        raise RuntimeError("participant changed during pilot: " + concept)
    submission = pathlib.Path(metadata["attempt"])
    environment = os.environ.copy()
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
    for split in splits:
        output = logs / (split + "_evaluation.json")
        evaluator_path = version / "private" / "evaluator.py"
        command = ["python", str(evaluator_path), "--submission", str(submission),
                   "--participant", metadata["participant"], "--split", split, "--output", str(output)]
        invocation = {"concept": concept, "stage": stage, "split": split, "command": command,
                      "evaluator_sha256": hashlib.sha256(evaluator_path.read_bytes()).hexdigest(),
                      "submission_sha256": metadata["submission_sha256"], "start_unix": time.time()}
        (logs / (split + "_evaluation_invocation.json")).write_text(json.dumps(invocation, indent=2))
        with (logs / (split + "_evaluation.log")).open("w") as stream:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                                    env=environment)
        if result.returncode:
            raise RuntimeError("evaluation failed: " + concept + " " + split)
        score = json.loads(output.read_text())
        print(json.dumps({"concept": concept, "stage": stage, "split": split,
                          "mean_core": score["mean_core"], "worst_family": score["worst_family"]}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concepts", nargs="+")
    parser.add_argument("--stage", default="screening")
    parser.add_argument("--splits", nargs="+", default=["screening", "challenge"])
    arguments = parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(arguments.concepts)) as executor:
        list(executor.map(lambda concept: evaluate_concept(concept, arguments.stage, arguments.splits), arguments.concepts))


if __name__ == "__main__":
    main()
