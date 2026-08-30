import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    deadline = time.monotonic() + 1200
    while not (ROOT / "completion.json").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("numerical supervisor did not finalize within the bounded gate")
        time.sleep(2)
    completion = json.loads((ROOT / "completion.json").read_text())
    plan = json.loads((ROOT / "plan.json").read_text())
    implementation = json.loads((ROOT / "implementation_validation.json").read_text())
    assert implementation["passed"]
    assert completion["all_workers_stopped"]
    assert completion["worker_return_codes"] == [0, 0, 0]
    assert all(digest(CONCEPT / path) == expected for path, expected in plan["sources"].items())
    assert all(digest(CONCEPT / path) == expected for path, expected in plan["frozen_snapshot"].items())
    results = [json.loads(path.read_text()) for path in sorted(ROOT.glob("L*/result.json"))]
    accepted = [result for result in results if result["accepted"]]
    excluded = [result for result in results if not result["accepted"]]
    labels = []
    cases = []
    new_failures = []
    for result in results:
        sites = result["case"]["sites"]
        case = {
            "sites": sites,
            "parameters": result["case"],
            "accepted": result["accepted"],
            "source": f"L{sites}/result.json",
            "source_sha256": digest(ROOT / f"L{sites}/result.json"),
            "computed_retained_counts": [item["diagnostic"]["count"] for item in result["history"]],
            "reason": result.get("reason"),
            "elapsed_seconds": result["elapsed_seconds"],
            "bounded_stop": result.get("bounded_stop"),
        }
        if result["accepted"]:
            label = {
                "case": result["case"],
                "label": result["label"],
                "ground_energy": result["ground_energy"],
                "absolute_sector_energies": result["absolute_sector_energies"],
                "certificate": f"L{sites}/result.json",
                "certificate_sha256": case["source_sha256"],
                "truth_extrapolated": False,
                "uncertainty_is_rigorous_tail_bound": False,
            }
            labels.append(label)
            checks = [result["history"][-1], result["doubled_onsite_cutoff"], result["independent_basis"]]
            case.update({
                "targets": result["label"]["targets"],
                "ground_energy": result["ground_energy"],
                "absolute_sector_energies": result["absolute_sector_energies"],
                "retained_local_states": result["retained_local_states"],
                "maximum_last_two_retained_cutoff_log_change": max(max(row) for row in result["last_two_cutoff_log_changes"]),
                "maximum_doubled_Fock_cutoff_log_change": max(result["doubled_cutoff_log_change"]),
                "maximum_independent_basis_log_change": max(result["independent_basis_log_change"]),
                "maximum_state_residual_dimensionless": max(value for record in checks for row in record["diagnostic"]["residuals_dimensionless"] for value in row),
                "maximum_residual_roundoff_gap_ratio": max(value for record in checks for value in record["residual_roundoff_gap_ratio"]),
                "controls": [{
                    "retained_local_states": item["diagnostic"]["count"],
                    "targets": item["prediction"]["targets"],
                    "absolute_log_errors": item["absolute_log_errors"],
                    "mean_log_error": item["mean_log_error"],
                    "p95_log_error": item["p95_log_error"],
                    "maximum_log_error": item["max_log_error"],
                    "single_case_thresholds_pass": item["single_case_thresholds_pass"],
                    "cpu_seconds": item["cpu_seconds"],
                    "wall_seconds": item["seconds"],
                    "full_batch_resource_claim": False,
                } for item in result["controls"]],
                "independent_full_Fock_crosschecks": result.get("independent_full_Fock_crosschecks", []),
            })
            for control in case["controls"]:
                if control["retained_local_states"] >= 6 and not control["single_case_thresholds_pass"]:
                    new_failures.append({"sites": sites, **control})
        else:
            case.update({
                "excluded_from_labels_and_scored_failure_evidence": True,
                "last_untrusted_diagnostic_targets": result["history"][-1]["prediction"]["targets"] if result["history"] else None,
                "last_computed_cutoff_changes": result.get("last_two_cutoff_log_changes"),
                "unconverged_values_are_not_truth": True,
            })
        cases.append(case)
    reason = "No admissible scalability ratchet is established by this bounded gate."
    if excluded:
        reason += " Uncertified lengths remain excluded from all truth and failure claims."
    if not new_failures:
        reason += " The certified pilots show the already-known four-state truncation failures, but no new failure of the reviewed six/eight-state source-native controls."
    else:
        reason += " New certified accuracy failures are recorded as candidates, not a frozen or demonstrated-hard target."
    reason += " A complete independently certified corpus and actual full-batch efficient-control measurements remain missing; isolated timings are not extrapolated."
    report = {
        "status": "complete",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "concept_3/adversary/long_chain_truth_gate only; C untouched",
        "ratchet_admitted": False,
        "freeze_ready": False,
        "hardness_claim": False,
        "verdict": reason,
        "original_D_result_unchanged": "360 original-domain certified cases pass; original champion remains legitimate and solved",
        "certified_sites": [item["case"]["sites"] for item in accepted],
        "excluded_sites": [item["case"]["sites"] for item in excluded],
        "new_certified_six_or_eight_state_control_failures": new_failures,
        "cases": cases,
        "implementation_validation": implementation,
        "numerical_admission": plan["admission"],
        "truth_scope": "Direct, parity-resolved Ritz labels with empirical retained-basis, doubled onsite Fock cutoff, independent oscillator frequency and residual checks. Not rigorous continuum/infinite-space bounds.",
        "controls_scope": "Reviewed byte-identical matrix-free source-native adaptation; not the unchanged length-specific champion. Unsupported v1 schemas are never scored as physics failures. CPU seconds are measured inside each computation; process peak RSS is not treated as isolated control RSS.",
        "timing_scope": "No 72-case CPU or wall estimate is inferred from single-case probes. No failure of all direct, sparse, adaptive, or MPS solvers is asserted.",
        "required_before_any_future_freeze": [
            "Certify the intended full parameter/length distribution, excluding all unconverged cases by public performance-independent rules.",
            "Measure the actual complete batch using efficient adaptive, matrix-free/sparse, and suitable tensor controls under the unchanged resource rules.",
            "Show a genuine measured failure not reducible to unsupported input shape, a deliberately small fixed local basis, or single-case timing extrapolation.",
        ],
        "all_private_numerical_workers_stopped": True,
        "fresh_agents_launched": 0,
        "public_or_evaluator_or_status_changes": False,
        "prior_sources_frozen_files_and_champion_unchanged": True,
        "source_hashes": plan["sources"],
        "artifacts": ["plan.json", "completion.json", "certified_cases.json", "implementation_validation.json", "truth_gate.py", "direct_control.py", "finalize.py"],
    }
    write_json(ROOT / "certified_cases.json", {"cases": labels, "excluded_lengths": report["excluded_sites"], "direct_labels_only": True})
    write_json(ROOT / "FINAL_REPORT.json", report)
    lines = [
        "# D long-chain truth gate: final findings", "", reason, "",
        "No public/evaluator/status changes, no fresh agents, no new frozen target, and no C work. Original D remains solved on its original 360-case domain.", "",
        "## Strengthened private labels", "",
        "| Sites | Certified | Retained states | Odd gap | Even gap | Odd-sector spacing |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for case in cases:
        if case["accepted"]:
            targets = case["targets"]
            lines.append(f"| {case['sites']} | yes | {case['retained_local_states']} | {targets['odd_gap']:.12g} | {targets['even_gap']:.12g} | {targets['odd_spacing']:.12g} |")
        else:
            lines.append(f"| {case['sites']} | **no; excluded** | — | not a label | not a label | not a label |")
    lines.extend(["", "Each accepted label has two successive retained-basis convergence checks, onsite Fock doubling 80→160, an independent frequency 2.0→2.34, four parity-resolved residuals, and the original gap-floor/roundoff tests. Absolute even/odd energies and the ground energy are retained in JSON. The certificates remain empirical, not rigorous infinite-space tail bounds.", "", "The independently assembled full-Fock implementation agrees with a complete rotated local basis at L2 to about 1e-15. L4 additionally has direct full-Fock cutoff-24/32 cross-check records. See `implementation_validation.json` and `L4/result.json`.", "", "## Measured source-native controls", "", "| Sites | Retained states | Mean log error | Maximum log error | CPU seconds | Single-case thresholds |", "|---|---:|---:|---:|---:|---|"])
    for case in cases:
        for control in case.get("controls", []):
            lines.append(f"| {case['sites']} | {control['retained_local_states']} | {control['mean_log_error']:.9g} | {control['maximum_log_error']:.9g} | {control['cpu_seconds']:.4f} | {'pass' if control['single_case_thresholds_pass'] else 'FAIL'} |")
    lines.extend(["", "The four-state failures are actual inaccurate parity splittings, not shape errors or timing artifacts. They do not by themselves establish useful hardness: the six/eight-state controls must be judged separately. These are source-native adapted controls, not an accusation that the original L2/L3-specific champion fails a contract it was never given.", "", "Single-case CPU measurements are not extrapolated into a 72-case resource verdict. A small fixed basis failing is not evidence that all direct solvers, adaptive bases, sparse methods, or tensor methods fail.", "", "## Evidence and limits", ""])
    for case in cases:
        lines.append(f"- L{case['sites']}: `L{case['sites']}/result.json`; {case['reason']}. Computed retained counts: {case['computed_retained_counts']}.")
    lines.extend(["- `certified_cases.json` contains only accepted labels; unresolved L6 diagnostic estimates must never become targets.", "- `FINAL_REPORT.json` contains full certificate maxima, source hashes, control predictions/errors, measured CPU times, and the admission decision.", "- `completion.json` confirms all bounded numerical workers stopped and original public/evaluator/champion files remain unchanged.", "", "## Primary local sources", "", "- `../champion_1_search/FINAL_REPORT.json`, `FINDINGS.md`, and `target_proposal.json`: prior evidence, exclusions, and unmet freeze gates.", "- `../champion_1_search/direct_control.py`: reviewed open-chain dressed-onsite matrix-free source; `direct_control.py` is a byte-identical copy.", "- `../champion_1_search/extension_teacher.py` and `../../evaluator/hidden/teacher.py`: numerical admission rules and correctly projected oscillator operators.", "- `../../champions/generation_1/predict.py`: original winning source, reviewed but not blamed for unsupported longer-chain schemas.", "- `../champion_1_search/private/extension_seeds.json`: the three fixed pre-existing pilot parameter sets; no new performance-conditioned sampling.", ""])
    (ROOT / "FINDINGS.md").write_text("\n".join(lines))
    print(json.dumps({"ratchet_admitted": False, "certified_sites": report["certified_sites"], "excluded_sites": report["excluded_sites"], "new_six_or_eight_state_failures": len(new_failures), "all_workers_stopped": True, "artifacts": ["FINAL_REPORT.json", "FINDINGS.md", "certified_cases.json"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
