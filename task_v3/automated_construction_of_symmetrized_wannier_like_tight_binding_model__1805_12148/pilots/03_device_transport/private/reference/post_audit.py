"""Revalidate private scoring without reading active attempts or confirmation cases."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REFERENCE = Path(__file__).resolve().parent
PRIVATE = REFERENCE.parent
sys.path.insert(0, str(PRIVATE))
from evaluator import BASELINE_ERROR_FLOOR, FLOORS, SCORING_VERSION, WEIGHTS, evaluate, numerical_errors, score_components


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_participant():
    freeze = json.loads((REFERENCE / "participant_freeze.json").read_text())
    participant = PRIVATE.parent / "participant"
    observed = {path.relative_to(participant).as_posix(): digest(path)
                for path in sorted(participant.rglob("*")) if path.is_file()}
    assert observed == freeze["files"], "Frozen participant changed"
    return freeze["participant_sha256"]


def scoring_regressions():
    baseline = {group: 1.0 for group in WEIGHTS}
    expected = {group: np.ones((2, 2)) for group in WEIGHTS}
    expected["sigma_0"] = expected.pop("sigma").astype(np.complex128)
    observed = []
    for multiplier in (0.0, 0.001, 0.1, 1.0, 10.0, 1000.0, 1000000.0):
        prediction = {key: (1 + multiplier) * value for key, value in expected.items()}
        errors, details = numerical_errors(prediction, expected)
        components = score_components(errors, details, baseline)
        observed.append({"perturbation_multiplier": multiplier, "errors": errors, "components": components})
    for group in WEIGHTS:
        values = [row["components"][group] for row in observed]
        assert values[0] == 1.0 and all(before > after > 0 for before, after in zip(values, values[1:]))
        assert observed[-1]["errors"][group] > 1000
        assert abs(values[3] - 1 / (1 + 9 * observed[3]["errors"][group])) < 1e-15
    missing_errors, missing_details = numerical_errors({}, expected)
    assert all(error == 1.0 for error in missing_errors.values())
    assert all(value == 0.0 for value in score_components(missing_errors, missing_details, baseline).values())
    invalid = {key: np.full(value.shape, np.nan) for key, value in expected.items()}
    invalid_errors, invalid_details = numerical_errors(invalid, expected)
    assert all(value == 0.0 for value in score_components(invalid_errors, invalid_details, baseline).values())
    return {"finite_error_sweep": observed, "missing_errors": missing_errors,
            "missing_and_nonfinite_scores": 0.0}


def main():
    frozen_hash = frozen_participant()
    legacy_names = ("baseline_report_test.json", "control_report_test.json", "control_report_challenge.json",
                    "validation_summary.json", "baseline_errors.json")
    legacy_hashes = {name: digest(REFERENCE / name) for name in legacy_names}
    manifests = {split: digest(PRIVATE / "challenge_pool" / split / "manifest.json")
                 for split in ("test", "challenge")}
    calibration = json.loads((REFERENCE / "baseline_errors.json").read_text())["errors"]
    assert all(error == 1.0 for family in calibration.values() for error in family.values())
    regressions = scoring_regressions()
    reports = {}
    for split in ("test", "challenge"):
        reports[split] = {}
        for label, submission in (("strong", REFERENCE / "control"), ("weak", REFERENCE / "weak_zero")):
            destination = REFERENCE / f"post_audit_{label}_{split}.json"
            report = evaluate(submission, split, destination, trusted_reference=True)
            assert report["scoring_version"] == SCORING_VERSION
            assert report["weights"] == WEIGHTS and report["normalization_floors"] == FLOORS
            assert all(row["returncode"] == 0 and not row["timed_out"] for row in report["per_case"])
            assert all(row["runtime_seconds"] < 90 and row["peak_rss_mb"] < 1024 for row in report["per_case"])
            assert all(detail["status"] == "ok" for row in report["per_case"] for detail in row["field_errors"].values())
            if label == "strong":
                assert report["core_score"] > 0.9 and report["worst_family_score"] > 0.9
            reports[split][label] = {key: report[key] for key in ("core_score", "worst_family_score", "family_scores")}
            reports[split][label]["report"] = destination.name
            reports[split][label]["maximum_runtime_seconds"] = max(row["runtime_seconds"] for row in report["per_case"])
            reports[split][label]["maximum_peak_rss_mb"] = max(row["peak_rss_mb"] for row in report["per_case"])
    assert frozen_participant() == frozen_hash
    assert all(digest(REFERENCE / name) == expected for name, expected in legacy_hashes.items())
    assert all(digest(PRIVATE / "challenge_pool" / split / "manifest.json") == expected
               for split, expected in manifests.items())
    summary = {"status": "post_audit_validated_before_freshpilot_grading", "scoring_version": SCORING_VERSION,
               "formula": "component = 1/(1+9*error/max(baseline_error,scientific_floor)); invalid groups = 0",
               "error_cap": None, "baseline_error_floor": BASELINE_ERROR_FLOOR,
               "baseline_calibration": calibration,
               "baseline_inspection": "Every missing-field anchor is dimensionless unit error 1, not MAX_ERROR or an inflated sentinel. Calibration is retained unchanged; finite zero-transport outputs are measured separately.",
               "weak_control": "Input-derived valid shapes, finite zeros for every required output; no stored answers or solver imports.",
               "reports": reports, "scoring_regressions": regressions,
               "legacy_reports_preserved_sha256": legacy_hashes,
               "unchanged_manifest_sha256": manifests, "participant_sha256": frozen_hash,
               "scope": "Private author controls only. No active attempts/logs or confirmation candidate execution. Public task and cases unchanged."}
    (REFERENCE / "post_audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"status": summary["status"], "reports": reports}, indent=2), flush=True)


if __name__ == "__main__":
    main()
