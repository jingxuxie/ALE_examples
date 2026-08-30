import ast
import hashlib
import json
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(__file__).resolve().parent
STAGE = ROOT / "generations/generation_3"


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serialized(value):
    return json.dumps(value, indent=2, allow_nan=False) + "\n"


def apply_files(files):
    patch = ["*** Begin Patch"]
    for path, content in files.items():
        if path.exists():
            patch.extend(["*** Update File: " + str(path), "@@"])
            patch.extend("-" + line for line in path.read_text().splitlines())
        else:
            patch.append("*** Add File: " + str(path))
        patch.extend("+" + line for line in content.splitlines())
    patch.append("*** End Patch")
    subprocess.run(["apply_patch"], input="\n".join(patch) + "\n", text=True, check=True)


def main():
    protocol = load(STAGE / "participant/input/protocol.json")
    positive = load(STAGE / "adversary/resource_positive_calibration.json")
    negative = load(STAGE / "adversary/resource_calibration.json")
    baseline = load(STAGE / "attempts/baseline.evaluation.json")
    contracts = load(STAGE / "adversary/contract_controls.json")
    controls = load(STAGE / "adversary/validity_controls.json")
    anchor = load(AUDIT / "anchor_validation.json")
    cluster = load(AUDIT / "cluster_validation.json")
    assert positive["valid"] and positive["passed"] and positive["core_score"] == positive["worst_family_score"] == 1.0
    assert positive["complete_assessment"] and positive["evaluated_family_members"] == 69 and not positive["skipped_members"]
    assert all(item["passed"] and item["reference"]["resolved"] for item in positive["family"])
    assert positive["runtime_seconds"] < 0.8 * 1500 and positive["resource"]["cpu_seconds"] < 0.8 * 900
    assert negative["valid"] and not negative["passed"] and negative["complete_assessment"] and negative["evaluated_family_members"] == 69
    assert baseline["valid"] and not baseline["passed"] and baseline["reason"] == "certified_family_threshold_failure"
    assert baseline["family"][0]["name"] == "joint6_57" and baseline["family"][0]["reference"]["resolved"]
    assert contracts["passed"] and len(contracts["checks"]) == 17
    assert controls["passed"] and len(controls["checks"]) == 23
    assert anchor["extra_reference_checks_fit_recorded_uncertainty"] and anchor["nearby_failures_resolved"]
    assert cluster["all_failures_resolved"] and len(cluster["full_reference_failures"]) == 3
    assert digest(STAGE / "participant/baseline/champion.json") == digest(ROOT / "champions/generation_2/submission.json")
    for relative in ("participant/workspace/simulator.py", "evaluator/hidden/simulator.py"):
        assert digest(STAGE / relative) == digest(ROOT / relative)
    source_tree = ast.parse((ROOT / "participant/workspace/search_api.py").read_text())
    staged_tree = ast.parse((STAGE / "participant/workspace/search_api.py").read_text())
    for name in ("reference", "assess_member", "parse_submission", "family", "certificate_screen"):
        source = next(node for node in source_tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        staged = next(node for node in staged_tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        assert ast.dump(source) == ast.dump(staged), name
    snapshot = load(STAGE / "adversary/root_readonly_snapshot.json")
    changed_root = [name for name, expected in snapshot.items() if not (ROOT / name).exists() or digest(ROOT / name) != expected]
    assert not changed_root, changed_root
    prepared = load(AUDIT / "preparation_screening.json")["records"]
    preparation_checks = load(AUDIT / "preparation_verified.json")
    assert len(prepared) == 330 and len(preparation_checks) == 25
    audits = []
    for artifact in ("v_3", "v_4"):
        records = load(AUDIT / (artifact + ".dispersion_screening.json"))["records"]
        checked = load(AUDIT / (artifact + ".dispersion_verified.json"))
        audits.append({"artifact": artifact, "design": "six-factor full corners plus axis controls, dispersion +/-0.5% and +/-1%", "screens": len(records), "screen_failures": sum(bool(item["failures"]) for item in records), "full_reference_checks": len(checked), "resolved_failures": sum(not item["assessment"]["passed"] and item["assessment"]["reference"]["resolved"] for item in checked)})
    same_box = load(AUDIT / "v_4.screening.json")["records"]
    same_box_checks = load(AUDIT / "v_4.verified.json")
    audits.insert(0, {"artifact": "v_4", "design": "existing five-dimensional box: calibration grid, face centers and seeded interior points", "screens": len(same_box), "full_reference_checks": len(same_box_checks), "resolved_failures": sum(not item["assessment"]["passed"] and item["assessment"]["reference"]["resolved"] for item in same_box_checks)})
    groups = []
    for variable, width in sorted({(item["variable"], item["width"]) for item in prepared}):
        selected = [item for item in prepared if item["variable"] == variable and item["width"] == width]
        groups.append({"variable": variable, "width": width, "screens": len(selected), "failure_counts": {name: sum(name in item["failures"] for item in selected) for name in ("gap", "certificate", "tail")}, "canonical_fraction_failures": sum(bool(item["failures"]) and item["canonical_fraction"] for item in selected)})
    summary = {
        "generation": 3, "empirical_status": "pending_tournament", "fresh_runs": 0,
        "selected_champion": load(ROOT / "champions/generation_2/selection.json"),
        "earlier_audits": audits, "preparation_audit": groups,
        "total_screen_evaluations": len(same_box) + sum(item["screens"] for item in audits[1:]) + len(prepared),
        "screen_count_scope": "970 parameter/member evaluations, not 970 independent or unique physical points; some axis controls repeat.",
        "initial_full_reference_assessments": len(same_box_checks) + sum(item["full_reference_checks"] for item in audits[1:]) + len(preparation_checks),
        "extra_cluster_assessments": sum(not item["reused_audit_assessment"] for item in cluster["full_reference_failures"]),
        "extra_nearby_assessments": len(anchor["nearby_factor_checks"]),
        "failure_cluster": cluster,
        "anchor_validation": anchor,
        "public_design": protocol["uncertainty_design"],
        "family_members": 69,
        "root_cause": "The old five-factor robustness does not extend to independent population preparation. All three failures have increased population, nonlinearity, duration and first-shape amplitude; their second-shape and phase signs differ. The target's step-halving certificate exceeds its unchanged 1e-4 limit, although low-density gaps remain large and reference convergence remains trustworthy. Matched five-factor and population-only controls pass. This is a genuine new joint condition, not an old evaluator error or a claim of an XMDS2 bug.",
        "selection_caution": "The selected canonical anchor exceeds the certificate limit by 2.78%, less than the initially preferred 5% margin. It is nonetheless reproducible, survives +/-1% changes to the new uncertainty width, and lies in a three-case fully resolved cluster. The stronger 7.82% complementary-parity failure is deliberately NOT added to grading. No thresholds, signs or parity were changed to catch it.",
        "baseline": {name: baseline[name] for name in ("valid", "passed", "core_score", "reason", "runtime_seconds", "resource", "submission_sha256")},
        "positive_full_family_calibration": {name: positive[name] for name in ("valid", "passed", "core_score", "complete_assessment", "evaluated_family_members", "runtime_seconds", "resource", "submission_sha256")},
        "positive_margins": {"minimum_gap": min(item["conservative_density_gap"] for item in positive["family"]), "maximum_certificate": max(item["certificate"] for item in positive["family"]), "maximum_tail": max(item["tail_mass"] for item in positive["family"]), "maximum_reference_field_uncertainty": max(item["reference"]["field_uncertainty"] for item in positive["family"]), "maximum_reference_observable_uncertainty": max(item["reference"]["observable_uncertainty"] for item in positive["family"])},
        "negative_full_family_calibration": {name: negative[name] for name in ("valid", "passed", "complete_assessment", "evaluated_family_members", "runtime_seconds", "resource")},
        "private_proposals": {"count": 2, "fully_verified_passes": 1, "fully_verified_failures": 1, "scope": "Privileged resource calibration only, not fresh-agent empirical trials; neither private proposal is included in participant."},
        "controls": {"contract_checks": 17, "schema_filetype_and_numerical_controls": 23, "all_passed": True},
        "root_untouched": {"hashed_files": len(snapshot), "changed_files": changed_root},
        "outer_watchdog_recommendation_seconds": 1650,
    }
    assert summary["total_screen_evaluations"] == 970 and summary["initial_full_reference_assessments"] == 54
    files = {AUDIT / "experiment_summary.json": serialized(summary), STAGE / "adversary/experiment_summary.json": serialized(summary)}
    evidence = load(STAGE / "evaluator/hidden/ratchet_evidence.json")
    evidence.update(full_failure_cluster=cluster, extra_anchor_validation=anchor, search_counts={"screen_evaluations": 970, "initial_full_reference_assessments": 54, "extra_cluster_assessments": 2, "nearby_assessments": 2}, root_cause=summary["root_cause"], selection_caution=summary["selection_caution"])
    files[STAGE / "evaluator/hidden/ratchet_evidence.json"] = serialized(evidence)
    status = load(STAGE / "status.json")
    status.update(sealed=True, known_generation_3_passing_witness=True, known_witness_scope="privileged_resource_calibration_only", evaluation_wall_seconds=1500, evaluation_cpu_seconds=900, family_members=69, note="Final generation-three staged package; pending tournament. Root publication, official attempts and status remain untouched. No fresh agents launched by this worker.")
    files[STAGE / "status.json"] = serialized(status)
    files[STAGE / "champions/README.md"] = "# No fresh generation-three champion\n\nNo generation-three fresh agents have run. A private resource-calibration witness passes all 69 cases, but is not a tournament champion and is not included in the participant baseline. Empirical status remains pending_tournament.\n"
    provenance = load(STAGE / "provenance.json")
    provenance["generation_3"]["validation"] = {"screen_evaluations": 970, "full_reference_checks_before_resource_runs": 58, "extra_reference": "320 modes/8192 RK4IP steps and 256-mode DOP853 at rtol=2e-12", "controls_passed": 40, "positive_complete_members": 69, "positive_wall_seconds": positive["runtime_seconds"], "positive_cpu_seconds": positive["resource"]["cpu_seconds"], "empirical_status": "pending_tournament"}
    files[STAGE / "provenance.json"] = serialized(provenance)
    narrative = """# Final generation-three ratchet evidence

The strongest official generation-two champion is v3: its minimum normalized gap/certificate/tail/conservation margin is 7.66%, versus 1.26% for v4. Both old official evaluations pass; none of the earlier missing-filename dispatcher errors is treated as an empirical failure.

The private audit has 970 parameter/member screen evaluations and 54 selected full reference assessments. Existing-box and modest dispersion/cross/coupling audits found no failure. Population preparation +/-0.01 yields three clustered certificate failures among 64 six-factor corners; two lie in the preregistered parity-plus half-fraction. All three were fully reference-validated, plus two nearby anchor perturbations. The new factor alone and the matching old five-factor member pass. This is a new joint physical condition, not an old grader mistake.

Generation three retains the 37 old cases and adds the fixed 32-case six-factor parity-plus design. The sixth factor is population +/-0.01 absolute; the original independent g/T calibrations remain +/-2%, shapes +/-0.01 and relative phase +/-0.03 radians. Every five-factor projection is complete; all 64 six-factor combinations and the continuous box are not claimed. Equations, initial support, parameter bounds and every numerical threshold remain unchanged.

The archived baseline validly fails joint6_57 with certificate 0.00010278175852802913, gap 0.4436681035742342, tail 0.0174252599060819. Reference field/observable uncertainty is 5.75947e-5/1.12661e-5. Extra 320-mode/8192-step and tighter independent checks fit those uncertainty estimates; nearby width factors 0.99 and 1.01 also fail with resolved references. The selected violation is modest (2.78%); the stronger complementary-parity case is recorded but not cherry-picked into grading.

All 17 contract and 23 validity/numerical controls pass. Baseline rejection takes 32.7 seconds. A real 69-member passing calibration takes 507.7 wall / 454.3 CPU seconds and 62 MiB; a separate failing exhaustive traversal also resolves all 69 in 570.4 wall / 465.2 CPU seconds. The frozen evaluator budget is 1500 wall / 900 CPU seconds, 1536 MiB, one thread. Use an outer scoring watchdog of at least 1650 seconds. The two private calibration proposals produced one full pass and one tail failure; neither is supplied in participant.

No fresh generation-three agents were launched. Status remains pending_tournament. Only root promotion and fresh trials remain for the main organizer. The exact source-native connection and URL provenance are in the staged provenance files.
"""
    files[AUDIT / "README.md"] = narrative
    files[STAGE / "adversary/README.md"] = narrative
    files[STAGE / "READY.md"] = """# Ready for main promotion

This self-contained staged package is sealed before any fresh generation-three trial. It is the final allowed generation. Do not expose private adversary or evaluator material to participants.

From this directory:

```
/usr/bin/python3 -B participant/baseline/search.py --output attempts/baseline.json
/usr/bin/python3 -B evaluator/evaluate.py --submission attempts/baseline.json --output attempts/baseline.evaluation.json
/usr/bin/python3 -B evaluator/test_contract.py
/usr/bin/python3 -B adversary/test_controls.py
```

Baseline copies the old official champion and should yield valid=true, passed=false, scores zero, reason certified_family_threshold_failure. A fresh submission uses the same evaluator command with its own JSON path. Internal wall/CPU limits are 1500/900 seconds; set the outer watchdog to at least 1650 seconds. --exhaustive optionally disables threshold pruning but never changes the score or reference requirements.

Exact target: all 69 explicit members, all three late observations t/T=0.75,0.875,1, conservative density gap >=0.30, certificate <=1e-4, tail <=0.02, mass drift <=2e-5 and energy drift <=2e-4; all unchanged full reference checks must resolve. Generation-three status is pending_tournament; no fresh launches by the generator.
"""
    apply_files(files)
    manifest = {"frozen_on": datetime.now(timezone.utc).isoformat(), "generation": 3, "protocol_id": protocol["protocol_id"], "frozen_before_fresh_trials": True, "sha256": {}}
    for folder in (STAGE / "participant", STAGE / "evaluator"):
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.name != "freeze_manifest.json" and "__pycache__" not in path.parts:
                manifest["sha256"][str(path.relative_to(STAGE))] = digest(path)
    manifest["resource_calibration"] = summary["positive_full_family_calibration"]
    freeze_path = STAGE / "evaluator/hidden/freeze_manifest.json"
    inventory_path = AUDIT / "CHANGED_FILES.txt"
    paths = {str(freeze_path.relative_to(ROOT)), str(inventory_path.relative_to(ROOT))}
    for folder in (AUDIT, ROOT / "champions/generation_2", STAGE):
        for path in folder.rglob("*"):
            if not path.is_dir():
                paths.add(str(path.relative_to(ROOT)))
    apply_files({freeze_path: serialized(manifest), inventory_path: "\n".join(sorted(paths)) + "\n"})
    print(serialized({"sealed": True, "generation": 3, "status": "pending_tournament", "changed_paths": len(paths), "frozen_files": len(manifest["sha256"]), "family_members": 69, "positive_resource": positive["resource"], "positive_runtime_seconds": positive["runtime_seconds"], "baseline_valid_failure": True, "root_unchanged": True}))


if __name__ == "__main__":
    main()
