import argparse
import concurrent.futures
import hashlib
import json
import math
import pathlib
import sys

import numpy as np

BASE = pathlib.Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
sys.path.insert(0, str(ROOT / "authoring"))
from isolated_eval import run_solver


def score_result(prediction, reference):
    floors = {"parameters": 0.04, "density": 0.001, "violation": 0.00002, "correlation": 0.0001}
    scores = {}
    errors = {}
    for name in floors:
        expected = np.asarray(reference[name], dtype=float)
        actual = np.asarray(prediction.get(name, []), dtype=float)
        if actual.shape != expected.shape or not np.all(np.isfinite(actual)):
            scores[name] = 0.0
            errors[name] = "nonfinite or incorrect shape"
            continue
        weak = np.array([0.1, 0.1, 0.0]) if name == "parameters" else np.zeros_like(expected)
        scale = max(floors[name], float(np.sqrt(np.mean((weak - expected) ** 2))))
        error = float(np.sqrt(np.mean((actual - expected) ** 2)))
        scores[name] = math.exp(-math.log(10) * error / scale)
        errors[name] = {"rmse": error, "weak_scale": scale}
    return scores, errors


def evaluate_record(record, submission, participant, execution_dir=None):
    execution = run_solver(submission, participant or BASE / "participant", record["case"], timeout=3600, memory_gib=6, startup_grace=30)
    if execution["ok"]:
        try:
            scores, errors = score_result(execution["result"], record["reference"])
        except (ValueError, TypeError, AttributeError, OverflowError) as error:
            scores = {name: 0.0 for name in ["parameters", "density", "violation", "correlation"]}
            errors = {"output": str(error)}
    else:
        scores = {name: 0.0 for name in ["parameters", "density", "violation", "correlation"]}
        errors = {"execution": execution.get("error")}
    if execution_dir is not None:
        destination = pathlib.Path(execution_dir)
        destination.mkdir(parents=True, exist_ok=True)
        case_digest = hashlib.sha256(json.dumps(record["case"], sort_keys=True).encode()).hexdigest()
        payload = {"id": record["id"], "case_sha256": case_digest, "execution": execution}
        (destination / (record["id"] + ".json")).write_text(json.dumps(payload, indent=2, allow_nan=False))
    execution.pop("result", None)
    row = {"id": record["id"], "family": record["family"], "score": float(np.prod(list(scores.values())) ** 0.25),
           "components": scores, "errors": errors, "execution": execution}
    print(json.dumps({"id": row["id"], "score": row["score"], "seconds": execution["seconds"]}), flush=True)
    return row


def evaluate(submission, split, participant=None, workers=1, execution_dir=None):
    records = [json.loads(path.read_text()) for path in sorted((BASE / "private" / "challenge_pool" / split).glob("*.json"))]
    if not records:
        raise RuntimeError("no frozen reference records for " + split)
    expected_count = {"screening": 6, "challenge": 9, "confirmation": 6}.get(split)
    if expected_count is not None and len(records) != expected_count:
        raise RuntimeError("reference precomputation is incomplete for " + split)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        rows = list(executor.map(lambda record: evaluate_record(record, submission, participant, execution_dir), records))
    return summarize(rows, split)


def summarize(rows, split):
    families = {family: float(np.mean([row["score"] for row in rows if row["family"] == family])) for family in sorted({row["family"] for row in rows})}
    components = {name: float(np.mean([row["components"][name] for row in rows])) for name in rows[0]["components"]}
    result = {"mean_core": float(np.mean([row["score"] for row in rows])), "worst_family": min(families.values()),
              "family_scores": families, "component_scores": components, "cases": rows,
              "total_seconds": sum(row["execution"]["seconds"] for row in rows), "split": split}
    result["score"] = result["mean_core"]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--split", default="screening")
    parser.add_argument("--output", required=True)
    parser.add_argument("--participant")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--execution-dir")
    arguments = parser.parse_args()
    if not 1 <= arguments.workers <= 16:
        parser.error("workers must be between 1 and 16; parallel use requires a reentrant submission")
    result = evaluate(arguments.submission, arguments.split, arguments.participant, arguments.workers, arguments.execution_dir)
    pathlib.Path(arguments.output).write_text(json.dumps(result, indent=2))
    print(json.dumps({key: result[key] for key in ("mean_core", "worst_family", "component_scores")}), flush=True)


if __name__ == "__main__":
    main()
