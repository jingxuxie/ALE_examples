import argparse
import collections
import csv
import json
import math
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_3"
sys.path.insert(0, str(CONCEPT / "evaluator"))
from evaluate import load_predictions, verify_submission
from scoring import likelihood_interval, row_error, score_predictions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    participant = CONCEPT / "participant"
    protocol = json.loads((CONCEPT / "evaluator/protocol.json").read_text())
    submission = verify_submission(arguments.submission, protocol)
    labels = json.loads((CONCEPT / "evaluator/hidden/labels.json").read_text())
    expected_ids = {row["query_id"] for row in labels}
    with tempfile.TemporaryDirectory(prefix="honeycomb_prediction_audit_") as temporary:
        temporary = Path(temporary)
        clean_submission = temporary / "submission"
        shutil.copytree(submission, clean_submission)
        scratch = temporary / "scratch"
        scratch.mkdir()
        prediction_path = scratch / "predictions.csv"
        command = [sys.executable, str(ROOT / "authoring/sandbox.py"),
                   "--submission", str(clean_submission), "--participant", str(participant),
                   "--scratch", str(scratch), "--seconds", str(protocol["seconds"]),
                   "--memory-mib", str(protocol["memory_mib"]), "--",
                   str(participant / "input/train.csv"), str(participant / "input/queries.csv"),
                   str(prediction_path)]
        started = time.monotonic()
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=protocol["seconds"])
        except subprocess.TimeoutExpired:
            import os
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise RuntimeError("audit submission timed out")
        if process.returncode:
            raise RuntimeError(stderr.decode(errors="replace")[-2000:])
        predictions = load_predictions(prediction_path, expected_ids, protocol)
        elapsed = time.monotonic() - started
    original = score_predictions(predictions, labels, protocol)
    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    failures = []
    for row in labels:
        probability = predictions[row["query_id"]]
        lower, upper = likelihood_interval(row["num_shots"], row["num_shots"] - row["num_correct"],
                                           protocol["likelihood_ratio"])
        error = row_error(probability, lower, upper)
        distance = str(row["code_distance"])
        key = "/".join([row["circuit_style"], row["decoder"], row["stress"], "distance=" + distance])
        cells[key][row["preserved_observable"]].append(error**2)
        if error > math.log10(2):
            failures.append({key: row[key] for key in row if key not in {"num_shots", "num_correct"}} |
                            {"shots": row["num_shots"], "errors": row["num_shots"] - row["num_correct"],
                             "prediction": probability, "likelihood_interval": [lower, upper],
                             "residual_log10_error": error})
    grouped = {}
    for key, observables in sorted(cells.items()):
        rms = math.sqrt(sum(sum(values) / len(values) for values in observables.values()) / len(observables))
        grouped[key] = {"rms_log10": rms, "score": 10**(-rms),
                        "rows": sum(len(values) for values in observables.values())}
    worst = max(value["rms_log10"] for key, value in grouped.items() if "/joint/" not in key)
    report = {"original": original, "fine_grained_worst_score": 10**(-worst),
              "fine_grained_cells": grouped, "factor_two_residual_failures": len(failures),
              "failures": sorted(failures, key=lambda row: -row["residual_log10_error"]),
              "runtime_seconds": elapsed,
              "interpretation": "Private stress audit across the same held-out scientific observations, stratified by distance. Original pass conditions are unchanged. Joint low-noise/large-size observations remain diagnostic; likelihood-support widths are respected."}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"original_worst_score": original["worst_family_score"],
                      "fine_grained_worst_score": report["fine_grained_worst_score"],
                      "factor_two_residual_failures": len(failures), "runtime_seconds": elapsed}, indent=2))


if __name__ == "__main__":
    main()
