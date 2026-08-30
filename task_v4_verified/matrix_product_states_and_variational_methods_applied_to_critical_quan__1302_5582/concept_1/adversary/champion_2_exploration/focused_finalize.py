import json
from pathlib import Path
import time

from harness import ROOT, sha256, write_json
from focused_summary import summarize


def main():
    started = time.process_time()
    summary = summarize(True)
    plan = json.loads((ROOT / "tranche_2/PLAN.json").read_text())
    families = {entry["case_id"]: entry["family"] for entry in plan["initial_configurations"]}
    assert len(summary["cases"]) == 12
    candidates = []
    validations = []
    for entry in summary["cases"]:
        request_path = ROOT / "requests" / (entry["case_id"] + ".json")
        request = json.loads(request_path.read_text())
        assert request["n_sites"] == 64 and request["local_dim"] == 14
        assert 12 <= request["bond_cap"] <= 24
        for name, lower, upper in (("omega", 0.55, 1.85), ("mass2", -0.20, 0.03),
                                   ("lambda4", 0.05, 0.30), ("coupling", 0.05, 1.50),
                                   ("field", -0.004, 0.004)):
            assert len(request[name]) == 64 - int(name == "coupling")
            assert all(lower <= value <= upper for value in request[name])
        if request["sector"] != "any":
            assert not any(request["field"])
        baseline = entry["records"]["v4_40"]
        assert baseline["resource_observation_valid"]
        validations.append({"case_id": entry["case_id"], "in_domain": True,
                            "baseline_valid_within_observed_limits": True,
                            "request_sha256": sha256(request_path)})
        if not entry.get("above_screen"):
            continue
        repeated = entry["records"]["repeat_v4_40"]
        teacher = entry["records"]["teacher_80"]
        alternative = entry["records"]["v3_40"]
        assert repeated["resource_observation_valid"]
        assert abs(repeated["energy"] - baseline["energy"]) < 1e-10
        assert abs(teacher["energy"] - alternative["energy"]) < 1e-9
        allocation_path = ROOT / "runs" / entry["case_id"] / "allocation_diagnostics.json"
        allocation = json.loads(allocation_path.read_text())
        candidates.append({
            **entry, "family": families[entry["case_id"]],
            "request": str(request_path.relative_to(ROOT)), "request_sha256": sha256(request_path),
            "repeat_confirmed": True, "independent_teacher_confirmed": True,
            "teacher_seed": "v3_40; independently implemented corrected two-site/one-site refinement",
            "different_charge_allocation_cuts": allocation["comparisons"]["v3_40"]["different_charge_allocation_cuts"],
            "reference_is_attainable_same_cap_not_exact": True,
            "full_future_6_and_40_second_target_tested": False,
        })
    candidates.sort(key=lambda entry: entry["v4_energy_gap"], reverse=True)
    evidence = {
        "initial_configurations": 12, "screen_total_energy": 6.4e-6,
        "confirmed_screen_positive": candidates,
        "negative_control_case_ids": [entry["case_id"] for entry in summary["cases"] if not entry.get("above_screen")],
        "formal_admission": False, "formal_generation_started": False,
        "decision": "Four confirmed follow-up gaps, one marginal; not eight robust cases. Three stronger follow-ups plus the original allocation case can contribute to a separately justified combined suite.",
        "limitation": "V3 already attains all four lower branches in cold 40-second runs; full future short/long quality gates and a combined portfolio are untested.",
    }
    write_json(ROOT / "tranche_2/CANDIDATE_EVIDENCE.json", evidence)
    origins = json.loads((ROOT / "SOURCE_ORIGINS.json").read_text())
    assert all(sha256(ROOT / name) == record["snapshot_sha256"] for name, record in origins.items())
    parent_cpu = 0.0
    accounting = {}
    for name in ("BATCH_ACCOUNTING.json", "CONFIRM_ACCOUNTING.json", "FIELD_REFINE_ACCOUNTING.json"):
        record = json.loads((ROOT / "tranche_2" / name).read_text())
        accounting[name] = record
        parent_cpu += record["parent_cpu_seconds"]
    initialization = json.loads((ROOT / "tranche_2/FIELD_INIT_ACCOUNTING.json").read_text())
    audit_cpu = time.process_time() - started
    accounted = summary["recorded_cpu_seconds"] + parent_cpu + initialization["inprocess_cpu_seconds"] + audit_cpu
    assert accounted + 60 < 1200
    audit = {
        "completed_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "validations": validations, "source_snapshots_unchanged": True,
        "recorded_wait4_child_cpu_seconds": summary["recorded_cpu_seconds"],
        "recorded_coordinator_cpu_seconds": parent_cpu,
        "projected_initializer_cpu_seconds": initialization["inprocess_cpu_seconds"],
        "final_remeasurement_cpu_seconds": audit_cpu,
        "accounted_cpu_seconds": accounted, "additional_ad_hoc_analysis_reserve_seconds": 60,
        "accounted_plus_reserve_seconds": accounted + 60, "authorized_cpu_limit_seconds": 1200,
        "all_numerical_children_completed": True, "out_of_domain_probes": 0,
        "main_scaling_search_inspected": False, "frozen_assets_modified": False,
        "formal_evaluator_invocations": 0, "accounting": accounting,
    }
    write_json(ROOT / "tranche_2/AUDIT.json", audit)
    lines = ["# Focused tranche: measured decision evidence", "",
             "Twelve in-domain N64/d14 configurations; six odd, four even, two nonzero-field unrestricted.",
             "Every baseline and repeated v4 output is physically valid and within its observed 40-second CPU/120-second wall limits.",
             "These are private source-native measurements, not frozen evaluator grades.", "",
             "## Confirmed same-cap gaps", "",
             "| Case | Sector / cap | V4 energy | Attainable reference | Gap | Screen multiple |", 
             "|---|---|---:|---:|---:|---:|"]
    for entry in candidates:
        baseline = entry["records"]["v4_40"]["energy"]
        reference = entry["records"][entry["attainable_reference"]]["energy"]
        lines.append(f"| `{entry['case_id']}` | {entry['sector']} / {entry['bond_cap']} | {baseline:.14f} | {reference:.14f} | {entry['v4_energy_gap']:.10g} | {entry['screen_multiple']:.6f} |")
    lines += ["", "The screen remains exactly 6.4e-6; it has not been relaxed. The three-soft-region case is only 1.20 times screen and is marginal for selection.",
              "Every listed gap survives a fresh v4 repeat and independent corrected-teacher refinement of the v3 seed. References are attainable same-bond MPS energies, never exact energies.",
              "", "## Root cause and limits", "",
              "The differing virtual-charge cuts are 4/5/61 (quartic interfaces), 9 (edge islands), 3/61 (dimerized), and 3/61 (three soft regions). The initial tranche's controlled reallocation rescue proves the mechanism in the original disordered case; these follow-up charge differences are measured associations.",
              "The even random-block control instead favors v4 despite identical charge counts, so not every v3/v4 difference is a charge-count effect.",
              "Both field controls show no screened gap against the retained alternatives. The extra parity-projected initializer is refined with the original nonzero field and unrestricted sector; its final energy 45.458604537035605 is higher than v4's 45.45857413246858, so it is not a failure reference.",
              "", "## Selection assessment", "",
              "This tranche does not establish an eight-case robust hard G2 suite. Three stronger follow-ups plus the original 4.32-times-screen case could supply four in-domain allocation cases if another independently verified frontier warrants a combined suite. The fourth follow-up should not be presented as a large-margin case.",
              "V3 already attains the lower branches in valid cold long-budget runs. Allocation-only G2 may be inexpensive to repair; neither a combined portfolio nor the full future 6/40-second target has been tested here.",
              "An unrestricted zero-field fixed-cap parity tradeoff was identified as a future hypothesis, not run: an even exact ground state does not imply an even best capped MPS. No thirteenth configuration or out-of-domain control was launched, and main's scaling search was not inspected.",
              "", "## Provenance and compute", "",
              f"Recorded child + coordinator + initialization + final-measurement CPU: {accounted:.3f} seconds; including a 60-second ad-hoc-analysis allowance: {accounted + 60:.3f} / 1200 seconds. Per-child wall/CPU, requests, NPZ states, source hashes, and negative controls are retained.",
              "`CANDIDATE_EVIDENCE.json` contains requests, reference paths, hashes, timing records, and charge-allocation differences. `SUMMARY.json` preserves all twelve comparisons; `AUDIT.json` records domain and source checks. No public, evaluator, calibration, attempt, status, target, or generation asset was edited.", ""]
    (ROOT / "tranche_2/REPORT.md").write_text("\n".join(lines))
    selected_paths = list((ROOT / "tranche_2").rglob("*")) + list(ROOT.glob("focused_*.py"))
    selected_paths += list((ROOT / "requests").glob("f2_*.json"))
    for directory in (ROOT / "runs").glob("f2_*"):
        selected_paths += list(directory.rglob("*"))
    selected_paths += [ROOT / "SOURCE_HASHES.json", ROOT / "SOURCE_ORIGINS.json", ROOT / "harness.py", ROOT / "teacher.py"]
    manifest = {str(path.relative_to(ROOT)): {"sha256": sha256(path), "bytes": path.stat().st_size}
                for path in sorted(set(selected_paths)) if path.is_file()
                and path != ROOT / "tranche_2/ARTIFACT_MANIFEST.json"
                and path != ROOT / "tranche_2/finalize.log"}
    write_json(ROOT / "tranche_2/ARTIFACT_MANIFEST.json", manifest)
    print(json.dumps({"confirmed_cases": [entry["case_id"] for entry in candidates],
                      "accounted_cpu_seconds": accounted, "with_analysis_reserve": accounted + 60,
                      "manifest_files": len(manifest)}), flush=True)


if __name__ == "__main__":
    main()
