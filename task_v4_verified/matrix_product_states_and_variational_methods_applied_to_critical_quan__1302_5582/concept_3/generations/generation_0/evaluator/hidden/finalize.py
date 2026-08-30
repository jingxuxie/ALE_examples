import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import hashlib
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
import evaluate


def read(relative):
    return evaluate.load_json(ROOT / relative)


def write(relative, payload):
    (ROOT / relative).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def main():
    evaluate.verify_integrity()
    validation = read("attempts/baseline_validation.json")
    hidden = read("attempts/baseline_hidden.json")
    tests = read("attempts/validation_report.json")
    teacher_summary = read("evaluator/hidden/teacher_summary.json")
    certificates = read("evaluator/hidden/certificates.json")["certificates"]
    assert validation["status"] == hidden["status"] == "ok"
    assert tests["status"] == "passed" and tests["check_count"] >= 80
    teacher_summary["max_final_cutoff_log_change"] = max(
        max(certificate["last_two_cutoff_log_changes"][-1]) for certificate in certificates)
    teacher_summary["max_teacher_sector_dimension"] = max(
        certificate["history"][-1]["sector_dimension"] for certificate in certificates)
    teacher_summary["max_orthogonality_error"] = max(
        certificate["history"][-1]["orthogonality_max"] for certificate in certificates)
    teacher_summary["odd_gap_decades"] = float(np.log10(
        teacher_summary["target_ranges"]["odd_gap"][1] / teacher_summary["target_ranges"]["odd_gap"][0]))
    report = {
        "build_date": "2026-08-28",
        "target_contract_sha256": teacher_summary["contract_sha256"],
        "teacher": teacher_summary,
        "baseline_validation": validation,
        "baseline_hidden": hidden,
        "raw_low_cutoff_hidden": read("attempts/raw_low_cutoff_hidden.json"),
        "validation": {"status": tests["status"], "check_count": tests["check_count"]},
        "uncertainty": {
            "teacher": "Empirical cutoff/frequency agreement and finite-matrix residuals, not a rigorous infinite-cutoff tail bound.",
            "prediction": "Stratified case bootstrap with 12 hidden cases per family; finite-sample, descriptive intervals only.",
            "difficulty": "Only a fixed builder baseline was evaluated. Better interpolation, extrapolation or direct solvers are not ruled out."
        },
        "asymmetric_privilege": {
            "release_only": "participant/",
            "solver_visible": ["submission read-only", "public participant input assets read-only",
                               "current low-cutoff batch read-only", "fresh output and scratch", "system runtime"],
            "solver_excluded": ["hidden labels", "teacher spectra and certificates", "private seeds",
                                "scorer", "adversary", "host repository"]
        },
        "agent_launches": 0,
        "tested_participants": 0,
        "hardness_claimed": False
    }
    write("attempts/build_report.json", report)
    status = {
        "concept": "concept_3", "mode": "D_hidden_prediction", "status": "hard_open_candidate",
        "build_ready": True, "target_frozen": True,
        "target_frozen_before_generation_and_baseline": True,
        "target_contract_sha256": teacher_summary["contract_sha256"],
        "certified_counts": teacher_summary["counts"],
        "cutoff_counts": teacher_summary["label_cutoffs"],
        "teacher_max_cutoff_log_change": teacher_summary["max_cutoff_log_change"],
        "teacher_max_final_cutoff_log_change": teacher_summary["max_final_cutoff_log_change"],
        "teacher_max_basis_log_change": teacher_summary["max_basis_log_change"],
        "teacher_max_state_residual": teacher_summary["max_state_residual"],
        "teacher_max_residual_roundoff_gap_ratio": teacher_summary["max_residual_roundoff_gap_ratio"],
        "teacher_truth_extrapolated": False, "certification_is_rigorous_tail_bound": False,
        "baseline": {"validation_score": validation["score"], "hidden_score": hidden["score"],
                     "hidden_mean_log_error": hidden["mean_log_error"],
                     "hidden_worst_family_mean_log_error": hidden["worst_family_mean_log_error"],
                     "hidden_p95_log_error": hidden["p95_log_error"],
                     "hidden_score_bootstrap_95_percent": hidden["bootstrap_95_percent"]["score"],
                     "primary_success": hidden["primary_success"]},
        "validation": {"status": "passed", "check_count": tests["check_count"]},
        "participant_agent_launches": 0, "tested_participants": 0,
        "champion": None, "hardness_claimed": False,
        "report": "attempts/build_report.json", "changed_files": "MANIFEST.json", "pending": []
    }
    write("status.json", status)
    files = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or "__pycache__" in relative.parts or ".runs" in relative.parts or path.name == "MANIFEST.json":
            continue
        files.append({"path": str(relative), "bytes": path.stat().st_size,
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "participant_visible": relative.parts[0] == "participant"})
    write("MANIFEST.json", {"scope": "concept_3 only", "files": files,
                           "file_count": len(files), "total_bytes": sum(record["bytes"] for record in files),
                           "excludes": ["MANIFEST.json itself", "Python bytecode caches", "empty runtime scratch"]})
    print(json.dumps({"build_ready": True, "status": status["status"], "files": len(files),
                      "teacher": teacher_summary, "raw_low_cutoff_score": report["raw_low_cutoff_hidden"]["score"]},
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
