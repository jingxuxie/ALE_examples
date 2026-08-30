import argparse
import json
import math
from pathlib import Path

from sandbox import run_submission


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lengths", type=int, nargs="+", default=[10, 12, 14])
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    bank = [json.loads(line) for line in (root / "concept_1/adversary/broad_prediction_bank.jsonl").read_text().splitlines()]
    reports = []
    for length in arguments.lengths:
        selected = [record for record in bank if record["L"] == length]
        families = sorted({record["family"] for record in selected})
        cases = [record for family in families for record in [entry for entry in selected if entry["family"] == family][:80]]
        inputs = {"cases": [{key: record[key] for key in ("id", "L", "fields")} for record in cases]}
        try:
            payload, resources = run_submission(arguments.submission, inputs, timeout=3,
                                                 startup_timeout=60, streaming=True, memory_mb=2048,
                                                 participant=root / "concept_1/participant")
            predictions = {record["id"]: float(record["f"]) for record in payload["predictions"]}
            assert len(predictions) == len(cases)
            assert all(math.isfinite(value) and 0 <= value <= 1 for value in predictions.values())
            errors = [(predictions[record["id"]] - record["f"]) ** 2 for record in cases]
            overall = math.sqrt(sum(errors) / len(errors))
            family_errors = {family: math.sqrt(sum(error for record, error in zip(cases, errors) if record["family"] == family) / 80)
                             for family in families}
            result = {"L": length, "overall_rmse": overall, "worst_family_rmse": max(family_errors.values()),
                      "families": family_errors, "resources": resources,
                      "meets_initial_numeric_targets": overall <= 0.035 and max(family_errors.values()) <= 0.05,
                      "within_original_length_contract": length in (10, 12)}
        except Exception as error:
            result = {"L": length, "error": str(error), "meets_initial_numeric_targets": False,
                      "within_original_length_contract": length in (10, 12)}
        reports.append(result)
        print(json.dumps(result), flush=True)
    arguments.output.write_text(json.dumps({"submission": str(arguments.submission), "records_per_length": 320,
                                            "purpose": "Private stress, not original scoring", "reports": reports}, indent=2) + "\n")


if __name__ == "__main__":
    main()
