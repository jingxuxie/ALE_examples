import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


PILOT = Path(__file__).resolve().parents[2]
REFERENCE = PILOT / "private/reference"
specification = importlib.util.spec_from_file_location("pilot02_evaluator", PILOT / "private/evaluator.py")
evaluator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(evaluator)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_continuity():
    tolerance = 2e-8
    weak_error = 0.3
    errors = [0.0, tolerance / 100, tolerance / 10, tolerance, weak_error, 2 * weak_error, 1e12, 2e12]
    qualities = [evaluator.component_quality(error, weak_error, tolerance) for error in errors]
    assert qualities[0] == 1.0
    assert all(left > right > 0 for left, right in zip(qualities, qualities[1:]))
    assert evaluator.component_quality(None, weak_error, tolerance) == 0.0
    return {"errors": errors, "qualities": qualities, "strictly_decreasing": True,
            "sub_tolerance_sensitivity": True, "below_weak_sensitivity": True,
            "no_large_error_cap": True, "invalid_component_quality": 0.0}


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def main():
    output = REFERENCE / "post_audit"
    output.mkdir(exist_ok=True)
    legacy_paths = [REFERENCE / "validation.json"] + [REFERENCE / f"weak_{split}.json" for split in ["test", "challenge", "confirmation"]]
    legacy_hashes = {str(path.relative_to(PILOT)): digest(path) for path in legacy_paths}
    manifest_path = REFERENCE / "manifest.json"
    manifest_digest = digest(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    legacy_validation = json.loads((REFERENCE / "validation.json").read_text())
    audit = {
        "reason": "User-required non-saturating score correction before any participant output inspection or grading",
        "version": evaluator.SCORING_VERSION,
        "method": "Stored official reference and pre-build weak arrays only; no participant execution, attempt access, or live logs",
        "continuity_checks": check_continuity(),
        "legacy_report_sha256": legacy_hashes,
        "unchanged_manifest_sha256": manifest_digest,
        "unchanged_weights": evaluator.WEIGHTS,
        "splits": {},
    }
    all_weak_cases = []
    for split, records in manifest["splits"].items():
        started = time.monotonic()
        reference_cases, weak_cases = [], []
        previous_cases = {case["name"]: case for case in legacy_validation["splits"][split]["cases"]}
        for record in records:
            reference_path = PILOT / record["reference"]
            weak_path = PILOT / record["weak_reference"]
            expected = evaluator.load_npz(reference_path)
            weak = evaluator.load_npz(weak_path)
            reference_result = evaluator.score_arrays(expected, expected, weak)
            weak_result = evaluator.score_arrays(weak, expected, weak)
            previous_errors = previous_cases[record["name"]]["errors"]
            independent_result = evaluator.score_from_errors(previous_errors, reference_result["weak_errors"])
            assert reference_result["score"] == 1.0 and independent_result["score"] > 0.9
            assert not reference_result["issues"] and not weak_result["issues"]
            missing = dict(expected)
            missing.pop("berry_raw")
            missing_result = evaluator.score_arrays(missing, expected, weak)
            assert missing_result["component_quality"]["berry_raw"] == 0.0
            assert 0 < missing_result["score"] < reference_result["score"]
            nonfinite = dict(expected)
            nonfinite["berry_raw"] = expected["berry_raw"].copy()
            nonfinite["berry_raw"].flat[0] = np.nan
            nonfinite_result = evaluator.score_arrays(nonfinite, expected, weak)
            assert nonfinite_result["component_quality"]["berry_raw"] == 0.0
            details = {"name": record["name"], "family": record["material"],
                       "runtime": {"seconds": 0.0, "mode": "stored-array rescore; no submission execution"},
                       "reference_sha256": digest(reference_path), "weak_sha256": digest(weak_path)}
            reference_result.update(details)
            reference_result["legacy_independent_reexecution_rescore"] = independent_result
            reference_result["invalid_component_checks"] = {"missing_raw_berry_score": missing_result["score"],
                                                           "nonfinite_raw_berry_score": nonfinite_result["score"]}
            weak_result.update(details)
            reference_cases.append(reference_result)
            weak_cases.append(weak_result)
            print(split, record["name"], "reference", reference_result["score"], "weak", weak_result["score"], flush=True)
        elapsed = time.monotonic() - started
        reference_report = evaluator.summarize(reference_cases, split, elapsed)
        weak_report = evaluator.summarize(weak_cases, split, elapsed)
        for label, report in [("reference", reference_report), ("weak", weak_report)]:
            report["evaluation_mode"] = "post-audit stored-array rescore; not a live participant grade"
            write_json(output / f"{label}_{split}.json", report)
        audit["splits"][split] = {
            "reference_core_score": reference_report["core_score"],
            "reference_worst_family_score": reference_report["worst_family_score"],
            "weak_core_score": weak_report["core_score"],
            "weak_worst_family_score": weak_report["worst_family_score"],
            "weak_family_scores": weak_report["family_scores"],
            "independent_reexecution_min_score": min(case["legacy_independent_reexecution_rescore"]["score"] for case in reference_cases),
        }
        all_weak_cases.extend(weak_cases)
    assert digest(manifest_path) == manifest_digest
    assert all(digest(PILOT / relative) == expected_digest for relative, expected_digest in legacy_hashes.items())
    pooled = evaluator.summarize(all_weak_cases, "pooled", 0.0)
    audit["weak_pooled_case_mean"] = float(np.mean([case["score"] for case in all_weak_cases]))
    audit["weak_pooled_family_balanced_mean"] = pooled["core_score"]
    audit["legacy_reports_preserved"] = True
    audit["cases_weights_and_public_mission_unchanged"] = True
    write_json(output / "audit_summary.json", audit)
    print(json.dumps(audit["splits"], indent=2))
    print("WEAK CASE MEAN", audit["weak_pooled_case_mean"], "FAMILY-BALANCED", audit["weak_pooled_family_balanced_mean"])


if __name__ == "__main__":
    main()
