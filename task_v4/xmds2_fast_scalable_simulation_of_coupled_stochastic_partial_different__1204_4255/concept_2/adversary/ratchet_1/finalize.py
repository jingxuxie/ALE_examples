import ast
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(__file__).resolve().parent
STAGE = ROOT / "generations/generation_2"


def install(files):
    sections = ["*** Begin Patch"]
    for path, content in files.items():
        sections.append("*** Add File: " + str(path.relative_to(ROOT)))
        sections.extend("+" + line for line in content.splitlines())
    sections.append("*** End Patch")
    subprocess.run(["apply_patch"], input="\n".join(sections) + "\n", text=True, cwd=ROOT, check=True)


def encoded(value):
    return json.dumps(value, indent=2, allow_nan=False) + "\n"


def functions(source):
    return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


def main():
    baseline = json.loads((STAGE / "attempts/baseline.evaluation.json").read_text())
    assert baseline["valid"] and not baseline["passed"]
    assert baseline["expected_family_members"] == 37
    assert baseline["evaluated_family_members"] >= 1
    assert any(not member["passed"] for member in baseline["family"])
    assert len(baseline["certificate_screen"]) == 37
    assert all(member["reference"]["resolved"] for member in baseline["family"])
    screening = json.loads((AUDIT / "screening.json").read_text())
    verified = json.loads((AUDIT / "verified_failures.json").read_text())
    assert len(screening["records"]) == 284 and len(verified) == 12
    assert all(record["assessment"]["reference"]["resolved"] for record in verified)
    numerical = json.loads((STAGE / "adversary/validity_controls.json").read_text())
    contract = json.loads((STAGE / "adversary/contract_controls.json").read_text())
    assert numerical["passed"] and contract["passed"]
    root_manifest = json.loads((ROOT / "evaluator/hidden/freeze_manifest.json").read_text())
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected for path, expected in root_manifest["sha256"].items())
    original_protocol = json.loads((ROOT / "participant/input/protocol.json").read_text())
    protocol = json.loads((STAGE / "participant/input/protocol.json").read_text())
    for name in ("parameter_bounds", "equation", "initial_condition", "method_under_test", "observation_fractions", "scored_observation_indices", "observable", "limits", "diagnostics"):
        assert protocol[name] == original_protocol[name], name
    for name, value in original_protocol["reference"].items():
        assert protocol["reference"][name] == value, name
    assert protocol["target"]["minimum_conservative_density_gap"] == original_protocol["target"]["minimum_conservative_density_gap"]
    original_functions = functions((ROOT / "evaluator/hidden/search_api.py").read_text())
    staged_functions = functions((STAGE / "evaluator/hidden/search_api.py").read_text())
    for name in ("parse_submission", "reference", "assess_member"):
        assert original_functions[name] == staged_functions[name], name
    assert (STAGE / "evaluator/hidden/simulator.py").read_bytes() == (ROOT / "evaluator/hidden/simulator.py").read_bytes()
    summary = {
        "generation": 2, "original_generation_solved": True,
        "original_verified_fresh_passes": 2, "organizer_dispatch_errors_counted_as_failures": False,
        "champion_source": "attempts/v_1/submission.json",
        "champion_selection": "Both official scores tie at 1; v_1 has the larger minimum conservative density gap.",
        "perturbation_screen_evaluations": len(screening["records"]),
        "screening_wall_seconds": screening["runtime_seconds"],
        "screening_reference_is_certified": False,
        "selected_point_full_reference_evaluations": len(verified),
        "selected_points_all_reference_resolved": True,
        "optimized_generation_2_candidates": 0,
        "fresh_generation_2_agents": 0,
        "design": {"calibration_half_width": 0.02, "shape_half_width": 0.01, "phase_half_width": 0.03, "legacy": 5, "corners": 32, "ungraded_interior_audit_points": 16, "total": 37},
        "draft_budget_calibration": json.loads((AUDIT / "draft_53_budget_failure.json").read_text()),
        "second_draft_budget_calibration": json.loads((AUDIT / "draft_37_budget_failure.json").read_text()),
        "scalar_accuracy_and_diagnostic_targets_unchanged": True,
        "numerical_kernel_unchanged": True,
        "full_reference_algorithm_unchanged": True,
        "root_frozen_assets_unchanged": True,
        "clusters": [],
        "certified_selected_points": [],
        "champion_new_evaluation": {
            "valid": baseline["valid"], "passed": baseline["passed"],
            "core_score": baseline["core_score"], "worst_family_score": baseline["worst_family_score"],
            "group_scores": baseline["group_scores"],
            "reason": baseline["reason"], "complete_assessment": baseline["complete_assessment"],
            "evaluated_members": baseline["evaluated_family_members"],
            "skipped_members": baseline["skipped_members"],
            "observed_continuous_score": baseline["observed_continuous_score"],
            "runtime_seconds": baseline["runtime_seconds"], "resource": baseline["resource"],
            "maximum_certificate_screen_all_members": max(member["certificate"] for member in baseline["certificate_screen"].values()),
            "maximum_tail_screen_all_members": max(member["tail_mass"] for member in baseline["certificate_screen"].values()),
            "minimum_observed_conservative_gap": min(member["conservative_density_gap"] for member in baseline["family"]),
            "maximum_field_uncertainty": max(member["reference"]["field_uncertainty"] for member in baseline["family"]),
            "maximum_observable_uncertainty": max(member["reference"]["observable_uncertainty"] for member in baseline["family"]),
            "failed_members": [{"name": member["name"], "certificate": member["certificate"], "tail_mass": member["tail_mass"], "conservative_gap": member["conservative_density_gap"]} for member in baseline["family"] if not member["passed"]],
        },
        "controls": {"numerical_and_invalid_input": len(numerical["checks"]), "generation_2_contract": len(contract["checks"]), "all_passed": True},
        "solvability": "unknown; not inferred from either old champion failing; no optimization for a new private solution was attempted",
    }
    for artifact in ("v_1", "v_2"):
        for radius in (0.01, 0.02, 0.03):
            for kind in ("axis", "corner", "interior"):
                selected = [record for record in screening["records"] if record["artifact"] == artifact and record["radius"] == radius and record["kind"] == kind]
                if not selected:
                    continue
                summary["clusters"].append({
                    "artifact": artifact, "calibration_radius": radius, "kind": kind, "count": len(selected),
                    "failures": {reason: sum(reason in record.get("failures", []) for record in selected) for reason in ("density_gap", "certificate", "tail")},
                    "failed_coordinates": [{"point_index": record["point_index"], "coordinates": record["coordinates"], "failures": record["failures"]} for record in selected if record.get("failures")],
                })
    for record in verified:
        report = record["assessment"]
        summary["certified_selected_points"].append({
            "artifact": record["artifact"], "radius": record["radius"], "selection": record["selection"],
            "coordinates": record["coordinates"], "point_index": record["point_index"],
            "passed": report["passed"], "conservative_gap": report["conservative_density_gap"],
            "certificate": report["certificate"], "tail_mass": report["tail_mass"],
            "field_uncertainty": report["reference"]["field_uncertainty"],
            "observable_uncertainty": report["reference"]["observable_uncertainty"],
        })
    assert protocol["resources"]["evaluation_wall_seconds"] == 660
    assert protocol["resources"]["evaluation_cpu_seconds"] == 400
    status = json.loads((STAGE / "status.json").read_text())
    status.update(build_status="ready_for_main_review", target_frozen=True, freeze_manifest="evaluator/hidden/freeze_manifest.json", decision_reference_validation_complete=True, complete_family_reference_assessment=baseline["complete_assessment"], baseline_new_score=baseline["core_score"], baseline_new_valid=True, baseline_new_passed=False, baseline_evaluation="attempts/baseline.evaluation.json", controls_passed=True, solvability="unknown; no private optimized generation-2 solution searched", root_initial_assets_unchanged=True)
    source_provenance = json.loads((ROOT / "provenance.json").read_text())
    source_provenance.update(generation=2, source_native_details="provenance.md", ratchet_evidence="evaluator/hidden/ratchet_evidence.json", original_model_and_reference_unchanged=True)
    rationale = '''# Generation-2 ratchet rationale

Both initial fresh trials were officially valid and passed. The missing-witness dispatcher errors were organizer errors, not empirical failures. v_1 is the archived champion because its minimum conservative gap, 0.3456619662, exceeds v_2's 0.3256300230 while both official scores are 1. The supplied baseline is exactly that verified v_1 artifact.

## Controlled audit, not arbitrary threshold inflation

The audit ran 284 inexpensive perturbation evaluations: for each of two champions, 32 full corners plus ten single-axis controls at calibration radii 1%, 2%, and 3%, followed by 16 predetermined interior points at 2%. It then ran twelve selected-point evaluations with the complete temporal, spatial and independent-DOP853 reference checks. The cheap screening values are not presented as certified gaps. No generation-2 optimization or fresh-agent trial was performed.

At the selected 2% radius, **all ten single-axis controls pass screening for both champions**. In screening, joint corners produce four distinct failing v_1 cases (three certificate failures and one tail failure), and five v_2 density-gap failures. The predetermined interior points all pass screening. These are candidate interaction effects missed by the earlier sparse correlated family, not merely a parameter already failing under one-at-a-time perturbation. The selected extrema and the final decisive v_1 rejection case are independently validated; screening counts for other corners are not claimed as fully certified failure counts.

For v_1, the fully checked largest-certificate corner has certificate 0.00012016375897741838 despite conservative density gap 0.40554970469230894 and a resolved reference. For v_2, the fully checked smallest-gap corner has conservative density gap 0.2788777734888223 while its certificate remains 0.000024207567015017774. Thus one champion loses the required temporal agreement; the other retains temporal agreement but no longer meets the prescribed substantial-error margin. Neither event is a malformed input, unresolved reference, resource timeout or an evaluator bug. A gap below 0.3 does not imply the numerical prediction is actually accurate.

Observed clusters support a concrete failure mechanism: v_1 certificate failures occur with increased nonlinear strength and an independently combined shape imbalance, most strongly when duration also increases. v_2 gap failures occur when nonlinear strength and duration both decrease, often with reduced first-component modulation. These are empirical sensitivity observations, not a proof of a unique physical mechanism. The original strength/time pairs nearly preserve their product: 1.01*0.99=0.9999. Independent 2% calibration corners permit products 0.9604 and 1.0404, while independent shape/phase signs remove the old locking of three preparation errors.

The 2% design is selected instead of the harsher 3% design: it already separates all passing axial controls from failing joint corners. No accuracy threshold, conservation tolerance, spectral-tail limit, parameter range, integrator, time output, observable or reference accuracy has been tightened. The gap target remains 0.30 and certificate limit 1e-4. The new public family retains all five old members and adds all 32 corners, with no severity-based corner selection. All sixteen predetermined interior points remain audit evidence, not grading members. This is a finite set, not a certificate for the whole continuous box.

## Validated resource and numerical contract

A 53-member draft including the interior audit points timed out at 420 wall seconds under concurrent host load, consuming 345.45 CPU seconds. That draft timeout is retained as a resource-calibration error, NOT a scientific champion failure or fresh-agent outcome. To fit the budget, the final design omits only auxiliary interior grading points while retaining the entire 32-corner Cartesian set and all five legacy members.

A second, 37-member full-sweep draft also hit 420 wall seconds under increased contention, using 257.15 CPU seconds. This is likewise a budget-calibration error, not a scientific failure. The final resource contract therefore allows 660 wall seconds while keeping the CPU cap at 400 seconds. Both timed-out draft records remain in the audit.

The final evaluator first computes the exact fixed-lattice certificate and diagnostics for all 37 members. It prioritizes the worst diagnostic guard factor, then performs all four reference solves for each visited member. A reference-validated threshold failure proves the all-members requirement false, so it stops with an **exact binary zero**. Any potential pass still requires all 37 members to receive complete, resolved reference checks. Unvisited members are explicit and are not claimed to have converged. An unresolved visited reference gives valid=false, never a trustworthy pass.

Binary scoring changes feedback, not the mathematical acceptance set: the minimum of 37 binary member indicators is already zero when one fully checked indicator is zero. The previous continuous score is retained as an observed diagnostic only, never misrepresented as the minimum over unvisited members. The staged baseline's actual cheap-sweep and decisive full-reference result are in `attempts/baseline.evaluation.json`; its runtime, memory and uncertainty are summarized in `evaluator/hidden/ratchet_evidence.json`. No successful generation-2 witness is known, so a full passing sweep's wall time is not claimed as measured.

The frozen simulator is byte-identical to generation 1. AST comparisons verify that input parsing, the four-solve reference function and single-member assessment are unchanged. Twenty-three numerical/malformed-input controls and eleven generation-2 contract controls pass. A last-member synthetic failure is not skipped, an unresolved-reference synthetic case fails closed, and a first-member trustworthy failure returns an exact zero with the unvisited set explicit. Public and hidden kernels/protocol match byte-for-byte.

Generation-2 solvability remains unknown. This is permitted, not evidence of impossibility. No private optimized solution is supplied. Empirical status is `pending_tournament`; main handles review, publication and any fresh trials.
'''
    provenance_text = '# Source and ratchet provenance\n\nThe model, fourth-order interaction-picture Fourier-Galerkin simulator, and temporal/spatial/DOP853 reference checks are unchanged from generation 1. Source paper: `https://arxiv.org/abs/1204.4255v2`. Official repository: `https://github.com/GrahamDennis/xpdeint`. Documentation: `https://xmds.sourceforge.net/reference_elements.html#error-check`. Source file fingerprints and tested dependency versions are recorded in `provenance.json`.\n\nThe source-native connection remains the full-step/half-step comparison in `xpdeint/Features/ErrorCheck.tmpl`, exact linear interaction-picture dynamics, and the documentation distinction between an error estimate and proof. The stochastic-specific upstream warning is not misrepresented as a deterministic-NLSE bug claim. This is an independently written challenge workflow, not a patched or executed XMDS implementation.\n\nGeneration 2 changes only the public finite robustness design, supplies the previous verified champion as baseline, adds guard-only screening and expands the explicit evaluation budget. The complete audit rationale and numerical evidence are in `RATCHET.md` and `evaluator/hidden/ratchet_evidence.json`. No source URLs or publication claims are needed in participant instructions.\n'
    files = {
        AUDIT / "summary.json": encoded(summary), AUDIT / "RATIONALE.md": rationale,
        STAGE / "RATCHET.md": rationale, STAGE / "status.json": encoded(status),
        STAGE / "provenance.json": encoded(source_provenance), STAGE / "provenance.md": provenance_text,
        STAGE / "participant/input/protocol.json": encoded(protocol), STAGE / "evaluator/hidden/protocol.json": encoded(protocol),
        STAGE / "evaluator/hidden/ratchet_evidence.json": encoded(summary),
        ROOT / "champions/generation_1/protocol.json": (ROOT / "participant/input/protocol.json").read_text(),
        ROOT / "champions/generation_1/freeze_manifest.json": (ROOT / "evaluator/hidden/freeze_manifest.json").read_text(),
    }
    install(files)
    paths = sorted(path for directory in (STAGE / "participant", STAGE / "evaluator") for path in directory.rglob("*") if path.is_file() and path.suffix in (".py", ".md", ".json") and path.name != "freeze_manifest.json")
    manifest = {"frozen_on": "2026-08-28", "generation": 2, "protocol_id": protocol["protocol_id"], "sha256": {str(path.relative_to(STAGE)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
    install({STAGE / "evaluator/hidden/freeze_manifest.json": encoded(manifest)})
    for first, second in (("participant/input/protocol.json", "evaluator/hidden/protocol.json"), ("participant/workspace/simulator.py", "evaluator/hidden/simulator.py"), ("participant/workspace/search_api.py", "evaluator/hidden/search_api.py")):
        assert (STAGE / first).read_bytes() == (STAGE / second).read_bytes()
    inventory = sorted(str(path.relative_to(ROOT)) for directory in (AUDIT, ROOT / "champions/generation_1", STAGE) for path in directory.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    inventory.append("adversary/ratchet_1/CHANGED_FILES.txt")
    install({AUDIT / "CHANGED_FILES.txt": "\n".join(sorted(set(inventory))) + "\n"})
    print(encoded({"ready": True, "status": status["status"], "summary": summary["champion_new_evaluation"], "controls": summary["controls"], "root_initial_assets_unchanged": True}))


if __name__ == "__main__":
    main()
