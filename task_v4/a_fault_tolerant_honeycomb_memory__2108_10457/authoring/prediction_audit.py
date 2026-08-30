import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_3"
sys.path.insert(0, str(CONCEPT / "evaluator"))

from evaluate import check_frozen, evaluate, load_predictions, verify_submission
from scoring import likelihood_interval, score_predictions


def csv_text(rows, header=("query_id", "p_failure")):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue()


def main():
    check_frozen()
    protocol = json.loads((CONCEPT / "evaluator" / "protocol.json").read_text())
    labels_path = CONCEPT / "evaluator" / "hidden" / "labels.json"
    original_hash = hashlib.sha256(labels_path.read_bytes()).hexdigest()
    labels = json.loads(labels_path.read_text())
    identifiers = {row["query_id"] for row in labels}
    ordered = sorted(identifiers)
    valid_rows = [[identifier, "0.5"] for identifier in ordered]
    checks = []

    def passed(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    with (CONCEPT / "participant" / "input" / "train.csv").open(newline="") as stream:
        training = list(csv.DictReader(stream))
    with (CONCEPT / "participant" / "input" / "queries.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        query_fields = reader.fieldnames
        queries = list(reader)
    passed("private counts absent from query schema", not {"num_shots", "num_correct", "total_processing_seconds"}.intersection(query_fields))
    passed("exact 780/612/80 split", len(training) == 780 and len(queries) == 692 and sum(row["stress"] == "joint" for row in labels) == 80)
    block_fields = ["data_width", "data_height", "rounds", "noise", "circuit_style", "code_distance", "num_qubits"]
    train_blocks = {tuple(row[field] for field in block_fields) for row in training}
    query_blocks = {tuple(row[field] for field in block_fields) for row in queries}
    passed("decoder/observable configuration blocks disjoint", not train_blocks.intersection(query_blocks))
    passed("opaque unique query IDs", len(identifiers) == len(queries) == len(labels))

    with tempfile.TemporaryDirectory(prefix="prediction_audit_") as temporary:
        temporary = Path(temporary)
        output = temporary / "predictions.csv"
        output.write_text(csv_text(list(reversed(valid_rows))))
        passed("arbitrary valid output order", len(load_predictions(output, identifiers, protocol)) == 692)
        invalid = {
            "missing row": csv_text(valid_rows[:-1]),
            "duplicate row": csv_text(valid_rows + valid_rows[:1]),
            "unknown ID": csv_text([["not-a-query", "0.5"]] + valid_rows[1:]),
            "wrong header": csv_text(valid_rows, ("id", "prediction")),
            "extra column": csv_text([[ordered[0], "0.5", "extra"]] + valid_rows[1:]),
            "empty output": "",
            "oversized output": "x" * (protocol["output_bytes_max"] + 1),
        }
        for value in ["nan", "inf", "-inf", "0", "-0.1", "1", "1.1", "True"]:
            invalid["invalid probability " + value] = csv_text([[ordered[0], value]] + valid_rows[1:])
        for name, content in invalid.items():
            output.write_text(content)
            try:
                load_predictions(output, identifiers, protocol)
            except (ValueError, OSError, UnicodeError, csv.Error):
                checks.append("reject " + name)
            else:
                raise AssertionError("accepted " + name)
        target = temporary / "real.csv"
        target.write_text(csv_text(valid_rows))
        linked = temporary / "linked.csv"
        linked.symlink_to(target)
        fifo = temporary / "fifo.csv"
        os.mkfifo(fifo)
        for name, path in [("symlink output", linked), ("FIFO output", fifo)]:
            try:
                load_predictions(path, identifiers, protocol)
            except (ValueError, OSError):
                checks.append("reject " + name)
            else:
                raise AssertionError("accepted " + name)
        bad_submission = temporary / "bad_submission"
        bad_submission.mkdir()
        (bad_submission / "solve.py").symlink_to(CONCEPT / "participant" / "baseline" / "solve.py")
        try:
            verify_submission(bad_submission, protocol)
        except ValueError:
            checks.append("reject linked submission")
        else:
            raise AssertionError("linked submission accepted")

    lower, upper = likelihood_interval(100000000, 0, protocol["likelihood_ratio"])
    passed("zero-event exact upper likelihood bound", lower == 0 and math.isclose(upper, -math.expm1(-math.log(1000) / 100000000)))
    lower, upper = likelihood_interval(1000, 10, protocol["likelihood_ratio"])
    for endpoint in [lower, upper]:
        regret = 10 * math.log(0.01 / endpoint) + 990 * (math.log1p(-0.01) - math.log1p(-endpoint))
        passed("nonzero likelihood endpoint", math.isclose(regret, math.log(1000), rel_tol=1e-8))
    oracle = {row["query_id"]: min(max((row["num_shots"] - row["num_correct"]) / row["num_shots"], protocol["probability_min"]), protocol["probability_max"]) for row in labels}
    oracle_result = score_predictions(oracle, labels, protocol)
    passed("count-likelihood optimum scores one (grader control, not a solver)", oracle_result["score"] == 1.0)
    shifted = {identifier: oracle[ordered[(index + 137) % len(ordered)]] for index, identifier in enumerate(ordered)}
    passed("misaligned labels fail target", not score_predictions(shifted, labels, protocol)["success"])

    integrations = {}
    for mode in ["isolation", "tiny", "nan"]:
        destination = CONCEPT / "adversary" / mode
        destination.mkdir(exist_ok=True)
        shutil.copyfile(CONCEPT / "adversary" / "probe" / "solve.py", destination / "solve.py")
        (destination / "mode.txt").write_text(mode + "\n")
        if mode == "nan":
            try:
                evaluate(destination)
            except ValueError as error:
                passed("sandbox rejects NaN output", "invalid probability" in str(error))
                integrations[mode] = {"rejected": True, "error": str(error)}
            else:
                raise AssertionError("NaN output accepted")
        else:
            result = evaluate(destination)
            integrations[mode] = result
            passed("sandbox " + mode + " valid and below target", result["valid"] and not result["success"])

    baseline = json.loads((CONCEPT / "attempts" / "baseline.json").read_text())
    repeat = evaluate(CONCEPT / "participant" / "baseline")
    passed("baseline repeat predictions deterministic", baseline["prediction_sha256"] == repeat["prediction_sha256"])
    passed("baseline repeat score deterministic", baseline["score"] == repeat["score"])
    passed("hidden counts unchanged by attempts", hashlib.sha256(labels_path.read_bytes()).hexdigest() == original_hash)
    check_frozen()
    checks.append("all frozen hashes unchanged")
    report = {"passed": True, "checks": checks, "check_count": len(checks), "integration_results": integrations,
              "baseline_repeat": repeat, "fresh_agent_launched": False,
              "oracle_note": "In-process grader sanity check only; no oracle submission or label-bearing prediction file was created."}
    (CONCEPT / "adversary" / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    status = json.loads((CONCEPT / "status.json").read_text())
    status.update({"state": "ready_for_fresh_run", "baseline": baseline,
                   "adversary": {"passed": True, "checks": len(checks), "report": "adversary/results.json"},
                   "updated_utc": datetime.now(timezone.utc).isoformat(),
                   "fresh_agent_launched": False, "champion": None,
                   "achievability": "Baseline below target; no independent train-only passing champion tested. Threshold unchanged.",
                   "baseline_source_sha256": hashlib.sha256((CONCEPT / "participant" / "baseline" / "solve.py").read_bytes()).hexdigest()})
    (CONCEPT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"passed": True, "checks": len(checks), "baseline_score": baseline["score"],
                      "constant_half_score": integrations["isolation"]["score"], "tiny_score": integrations["tiny"]["score"]}))


if __name__ == "__main__":
    main()
