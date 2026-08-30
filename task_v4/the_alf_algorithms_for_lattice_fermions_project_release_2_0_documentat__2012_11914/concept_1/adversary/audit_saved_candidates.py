import hashlib
import importlib.util
import json
import math
from pathlib import Path
import time

import mpmath as mp


ROOT = Path(__file__).resolve().parents[1]


def main():
    specification = importlib.util.spec_from_file_location("sign_grader", ROOT / "evaluator/evaluate.py")
    grader = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(grader)
    model = json.loads((ROOT / "participant/input/model.json").read_text())
    directory = ROOT / "adversary/fresh_v3_saved_candidates"
    directory.mkdir(exist_ok=True)
    candidates = {}
    rejected = []
    for path in sorted((ROOT / "attempts/v_3").glob("*.json")):
        try:
            payload = json.loads(path.read_text())
            fields = payload["fields"]
            assert len(fields) == 16 and all(len(row) == 16 for row in fields)
            assert all(type(value) is int and value in (-1, 1) for row in fields for value in row)
        except (ValueError, TypeError, KeyError, AssertionError):
            rejected.append(path.name)
            continue
        digest = hashlib.sha256(json.dumps(fields).encode()).hexdigest()
        entry = candidates.setdefault(digest, {"fields": fields, "source_files": []})
        entry["source_files"].append(path.name)
    started = time.monotonic()
    records = []
    for digest, entry in candidates.items():
        point = model["certification_points"][0]
        lower_signs, lower_log = grader.precision_weight(entry["fields"], model, point, 65)
        upper_signs, upper_log = grader.precision_weight(entry["fields"], model, point, 95)
        with mp.workdps(95):
            discrepancy = abs(lower_log - upper_log)
            agreement = discrepancy < mp.mpf("1e-25")
        record = {
            "fields_sha256": digest,
            "source_files": entry["source_files"],
            "lower_signs": lower_signs,
            "upper_signs": upper_signs,
            "log_discrepancy": str(discrepancy),
            "precision_agreement": bool(agreement),
            "nominally_negative": math.prod(lower_signs) == math.prod(upper_signs) == -1,
            "valid_witness": False
        }
        if record["nominally_negative"] and agreement:
            artifact = directory / f"extracted_{digest}.json"
            artifact.write_text(json.dumps({"fields": entry["fields"]}) + "\n")
            record["full_evaluation"] = grader.evaluate(artifact, model)
            record["valid_witness"] = record["full_evaluation"]["passed"]
        records.append(record)
        print(json.dumps(record), flush=True)
    report = {
        "purpose": "Rule out a saved valid physical witness hidden by an interface mistake; this is a private post-attempt audit, not agent feedback.",
        "qualified_attempt": "v_3",
        "unique_valid_discrete_candidates": len(records),
        "noncandidate_files": rejected,
        "nominally_negative_candidates": sum(record["nominally_negative"] for record in records),
        "passing_saved_witnesses": sum(record["valid_witness"] for record in records),
        "all_precision_checks_agreed": all(record["precision_agreement"] for record in records),
        "runtime_seconds": time.monotonic() - started,
        "records": records
    }
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
