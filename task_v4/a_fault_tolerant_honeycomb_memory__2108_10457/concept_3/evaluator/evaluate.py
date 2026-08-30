import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

from scoring import score_predictions

ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / "evaluator" / "hidden"
PARTICIPANT = ROOT / "participant"
SANDBOX = ROOT.parent / "authoring" / "sandbox.py"


def check_frozen():
    for name in ["prediction_frozen.json", "frozen.json"]:
        frozen = json.loads((ROOT / "evaluator" / name).read_text())
        for relative, expected in frozen["sha256"].items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
                raise ValueError("frozen artifact mismatch: " + relative)
        if "sandbox_sha256" in frozen and hashlib.sha256(SANDBOX.read_bytes()).hexdigest() != frozen["sandbox_sha256"]:
            raise ValueError("shared sandbox changed since freeze")


def verify_submission(source, protocol):
    source = Path(source).resolve(strict=True)
    protected = [ROOT / "evaluator", ROOT.parent / "authoring"]
    if any(source == path or source in path.parents or path in source.parents for path in protected):
        raise ValueError("submission overlaps protected author/evaluator files")
    if not source.is_dir() or not (source / "solve.py").is_file():
        raise ValueError("submission must contain solve.py")
    total = 0
    entries = 0
    for directory, folders, files in os.walk(source, followlinks=False):
        for name in folders + files:
            information = (Path(directory) / name).lstat()
            entries += 1
            if not stat.S_ISREG(information.st_mode) and not stat.S_ISDIR(information.st_mode):
                raise ValueError("submission links/special files forbidden")
            if stat.S_ISREG(information.st_mode):
                if information.st_nlink != 1:
                    raise ValueError("submission hard links forbidden")
                total += information.st_size
            if total > protocol["submission_bytes_max"] or entries > 10000:
                raise ValueError("submission too large")
    return source


def load_predictions(path, expected_ids, protocol):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        information = os.fstat(stream.fileno())
        if not stat.S_ISREG(information.st_mode) or information.st_size > protocol["output_bytes_max"]:
            raise ValueError("invalid output file type or size")
        content = stream.read(protocol["output_bytes_max"] + 1)
    reader = csv.reader(io.StringIO(content.decode("utf-8"), newline=""), strict=True)
    if next(reader, None) != ["query_id", "p_failure"]:
        raise ValueError("output header must be query_id,p_failure")
    predictions = {}
    for row in reader:
        if len(row) != 2 or row[0] not in expected_ids or row[0] in predictions:
            raise ValueError("unknown, duplicate, or malformed query row")
        probability = float(row[1])
        if not math.isfinite(probability) or not protocol["probability_min"] <= probability <= protocol["probability_max"]:
            raise ValueError("invalid probability")
        predictions[row[0]] = probability
    if set(predictions) != set(expected_ids):
        raise ValueError("missing predictions")
    return predictions


def evaluate(submission):
    check_frozen()
    protocol = json.loads((ROOT / "evaluator" / "protocol.json").read_text())
    submission = verify_submission(submission, protocol)
    with (PARTICIPANT / "input" / "queries.csv").open(newline="") as stream:
        expected_ids = {row["query_id"] for row in csv.DictReader(stream)}
    with tempfile.TemporaryDirectory(prefix="honeycomb_prediction_") as temporary:
        temporary = Path(temporary)
        clean_submission = temporary / "submission"
        shutil.copytree(submission, clean_submission)
        scratch = temporary / "scratch"
        scratch.mkdir()
        output = scratch / "predictions.csv"
        command = [sys.executable, str(SANDBOX), "--submission", str(clean_submission),
                   "--participant", str(PARTICIPANT), "--scratch", str(scratch),
                   "--seconds", str(protocol["seconds"]), "--memory-mib", str(protocol["memory_mib"]),
                   "--", str(PARTICIPANT / "input" / "train.csv"),
                   str(PARTICIPANT / "input" / "queries.csv"), str(output)]
        started = time.monotonic()
        with (scratch / "stdout").open("wb") as stdout, (scratch / "stderr").open("wb") as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                process.wait(timeout=protocol["seconds"])
            except subprocess.TimeoutExpired:
                raise ValueError("submission time limit exceeded")
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
        elapsed = time.monotonic() - started
        if process.returncode != 0:
            raise ValueError("submission failed: " + (scratch / "stderr").read_text(errors="replace")[-2000:])
        predictions = load_predictions(output, expected_ids, protocol)
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
    labels = json.loads((HIDDEN / "labels.json").read_text())
    result = score_predictions(predictions, labels, protocol)
    runtime_score = max(0.0, 1 - elapsed / protocol["seconds"])
    result.update({"seconds": elapsed, "runtime_seconds": elapsed, "runtime_score": runtime_score,
                   "resource_score": runtime_score, "passed": result["success"],
                   "reason": "fixed worst-family accuracy target met" if result["success"] else "worst-family score below fixed 0.5 target",
                   "prediction_sha256": digest})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission_path", nargs="?")
    parser.add_argument("--submission")
    parser.add_argument("--output")
    arguments = parser.parse_args()
    try:
        result = evaluate(arguments.submission or arguments.submission_path or PARTICIPANT / "baseline")
    except Exception as error:
        reason = type(error).__name__ + ": " + str(error)
        result = {"valid": False, "success": False, "passed": False, "score": 0.0,
                  "core_score": 0.0, "worst_family_score": 0.0, "runtime_seconds": None,
                  "runtime_score": 0.0, "resource_score": 0.0, "reason": reason, "error": reason}
    rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(rendered)
    print(rendered, end="")
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
