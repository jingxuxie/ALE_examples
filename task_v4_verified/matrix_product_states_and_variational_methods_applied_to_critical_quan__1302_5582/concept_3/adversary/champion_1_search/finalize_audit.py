import sys

sys.dont_write_bytecode = True

import hashlib
import json
from pathlib import Path
import time

from benchlib import CONCEPT, SIDECAR, participant_unchanged, read, write


def ready():
    paths = [SIDECAR / "round_1_report.json", SIDECAR / "extension_results.json",
             SIDECAR / "private/extension_generation_complete.json"]
    if not all(path.exists() for path in paths):
        return False
    original = read(paths[0])
    extension = read(paths[1])
    return (extension.get("complete", False) and all(
        result["timing"].get("solver_profile_available", False) for result in original["batches"].values()))


def main():
    deadline = time.monotonic() + 3600
    while not ready():
        if time.monotonic() > deadline:
            raise RuntimeError("Audit computations incomplete; no final success report written")
        time.sleep(3)
    original = read(SIDECAR / "round_1_report.json")
    extension = read(SIDECAR / "extension_results.json")
    generation = read(SIDECAR / "private/generation_summary.json")
    audit = read(SIDECAR / "audit.json")
    invariance = read(SIDECAR / "invariance.json")
    source_hash = hashlib.sha256((CONCEPT / "attempts/v_1/predict.py").read_bytes()).hexdigest()
    assert source_hash == audit["source_sha256"]
    assert original["cases"] == 360 and invariance["passed"]
    assert participant_unchanged()
    assert generation["max_cutoff_log_change"] <= 2e-5 and generation["max_basis_log_change"] <= 2e-5
    native = read(SIDECAR / "private/native_fock_crosscheck.json")
    assert native["max_log_error"] <= 2e-5
    timings = [entry["timing"] for entry in original["batches"].values()]
    failures = []
    successful_controls = []
    for result in extension["runs"]:
        if "timing" not in result:
            continue
        record = {"sites": result["sites"], "inhomogeneous": result["inhomogeneous"],
                  "retained_local_states": result["retained_local_states"],
                  "status": result["timing"]["status"],
                  "returncode": result["timing"]["returncode"],
                  "wall_timeout": result["timing"]["wall_timeout"],
                  "cpu_seconds": result["timing"]["cpu_seconds"],
                  "max_rss_mib": result["timing"]["max_rss_mib"],
                  "wall_seconds": result["timing"]["wall_seconds"]}
        if "metrics" in result:
            record.update({"primary_success_on_single_case": result["metrics"]["primary_success"],
                           "max_log_error": result["metrics"]["max_log_error"],
                           "mean_log_error": result["metrics"]["mean_log_error"]})
        if result["timing"]["status"] != "ok" or not result.get("metrics", {}).get("primary_success", False):
            failures.append(record)
        else:
            successful_controls.append(record)
    references = [read(path) for path in sorted((SIDECAR / "private/extensions").glob("*.json"))]
    reference_summaries = []
    for record in references:
        certificate = record["certificate"]
        summary = {"sites": record["case"]["sites"], "accepted": certificate["accepted"]}
        if not certificate["accepted"]:
            summary["reason"] = certificate["reason"]
            summary["largest_computed_retained_dimension"] = certificate["history"][-1]["diagnostic"]["count"]
            summary["excluded_from_scored_evidence"] = True
        if certificate["accepted"]:
            summary.update({"retained_local_states": certificate["history"][-1]["diagnostic"]["count"],
                            "targets": certificate["label"]["targets"],
                            "max_cutoff_log_change": max(max(change) for change in certificate["last_two_cutoff_log_changes"]),
                            "max_basis_log_change": max(certificate["basis_log_change"]),
                            "max_residual_roundoff_gap_ratio": max(certificate["history"][-1]["residual_roundoff_gap_ratio"])})
        reference_summaries.append(summary)
    report = {
        "status": "complete", "date": "2026-08-28", "write_scope": "champion_1_search only",
        "original_target": {
            "verdict": "legitimate solved direct-simulation task; no fair original-domain ratchet found",
            "leakage_or_scoring_loophole_observed": False,
            "source_sha256": source_hash, "fresh_cases": 360,
            "original_domain_primary_failures": original["original_domain_primary_failures"],
            "pooled_score": original["pooled_metrics"]["score"],
            "mean_log_error": original["pooled_metrics"]["mean_log_error"],
            "worst_family_mean_log_error": original["pooled_metrics"]["worst_family_mean_log_error"],
            "max_log_error": original["pooled_metrics"]["max_log_error"],
            "score_bootstrap_95_percent": original["pooled_metrics"]["bootstrap_95_percent"]["score"],
            "batch_cpu_seconds_range": [min(item["cpu_seconds"] for item in timings), max(item["cpu_seconds"] for item in timings)],
            "batch_wall_seconds_range": [min(item["wall_seconds"] for item in timings), max(item["wall_seconds"] for item in timings)],
            "max_rss_mib": max(item["max_rss_mib"] for item in timings),
            "invariance_probe_passed": invariance["passed"],
            "teacher": generation,
            "source_of_success": "80-state onsite solves compressed to 16 local eigenstates; 128/2048-state parity blocks; physical inputs fully specify the Hamiltonian"
        },
        "new_generation_only": {
            "references": reference_summaries,
            "independent_full_fock_L4_crosscheck_max_log_error": native["max_log_error"],
            "empirical_control_failures": failures,
            "passing_single_case_controls": successful_controls,
            "interpretation": "These failures concern explicit new physics/dimensions and generic controls, not retroactive failure of original v1. Smaller-basis controls remain viable wherever they pass.",
            "proposal": "target_proposal.json",
            "ready_to_freeze_new_generation": False,
            "achievability": "unknown; requires full new certified corpus and independent 72-case direct-control tests"
        },
        "limitations": [
            "Fresh original-domain audit covers 360 cases, not all continuous parameters; zero observed failures is not a proof of universal exactness.",
            "Pooled audit metrics combine IID and edge-enriched cohorts, not an unbiased estimate of the original IID population score.",
            "Changed-basis/cutoff numerical certificates are empirical, not rigorous infinite-Hilbert tail bounds.",
            "Only three longer-chain pilot cases are examined; no population-level performance or hardness claim follows.",
            "wait4 launcher-only accounting was corrected; only trusted-bootstrap self-rusage values are used in final resource conclusions.",
            "The generic matrix-free control is not an optimized MPS or adaptive sparse solver; its resource failures do not exclude faster implementations."
        ],
        "participant_unchanged": True, "original_target_changed": False,
        "search_rounds": 3, "agent_launches": 0, "hardness_claimed": False
    }
    write(SIDECAR / "FINAL_REPORT.json", report)
    original_summary = report["original_target"]
    paragraphs = [
        "# Champion 1 audit: final findings",
        "",
        "Original D v1 is legitimately solved. No leakage or scoring loophole was observed; the solver reconstructs the Hamiltonian from public parameters and uses an efficient dressed onsite basis.",
        "",
        "Fresh original-domain results: 360 independently seeded certified cases, five balanced 72-case batches (three IID, two edge-enriched). All original primary thresholds pass. Pooled score %.12f; worst cell log-gap error %.4g." % (original_summary["pooled_score"], original_summary["max_log_error"]),
        "",
        "Per-batch solver CPU %.3f–%.3f s; wall %.3f–%.3f s; maximum solver RSS %.1f MiB. CPU/RSS are measured in the trusted bootstrap, not inferred from bubblewrap's launcher." % tuple(original_summary["batch_cpu_seconds_range"] + original_summary["batch_wall_seconds_range"] + [original_summary["max_rss_mib"]]),
        "",
        "Emptying training data, deleting all low-cutoff spectra, relabelling IDs/families and reversing input order leaves the numerical predictions identical. Only source-identical predict.py is staged; fresh labels, certificates and host paths are excluded.",
        "",
        "New-generation pilots and measured control failures are recorded in FINAL_REPORT.json and extension_results.json. Unsupported v1 length/schema errors are not counted as scientific failures. Each accepted pilot has direct computed labels and cutoff/basis checks; an L4 case also has an independent full-Fock cross-check.",
        "",
        "Concrete proposal: inhomogeneous parity-preserving L4/L6 chains, fully public physical parameters and low Fock cutoffs 4/6, original score tolerances and 30-CPU-second budget. See target_proposal.json. This is NOT a retroactive ratchet and is NOT ready to freeze: a complete new certified corpus and full-batch adaptive/sparse/MPS control tests are still required. Achievability is unknown.",
        "",
        "No original participant assets or original evaluator files were modified. No fresh agents were launched. No hardness claim is made."
    ]
    (SIDECAR / "FINDINGS.md").write_text("\n".join(paragraphs) + "\n")
    files = [{"path": str(path.relative_to(SIDECAR)), "bytes": path.stat().st_size,
              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
             for path in sorted(SIDECAR.rglob("*")) if path.is_file() and "runs" not in path.relative_to(SIDECAR).parts
             and "__pycache__" not in path.parts and path.name not in ("MANIFEST.json", "final_summary.log")]
    write(SIDECAR / "MANIFEST.json", {"files": files, "scope": "champion_1_search only",
                                    "excludes": ["self manifest", "self stdout final_summary.log", "runtime scratch and bytecode"]})
    print(json.dumps({"original": original_summary, "new_generation_references": reference_summaries,
                      "new_generation_control_failures": failures, "passing_single_case_controls": successful_controls,
                      "participant_unchanged": True, "ready_to_freeze_new_generation": False}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
