import json
import math

from generator import validate
from sweep import HERE, save, verify


def main():
    records = []
    for name in ("screening.jsonl", "focused_screening.jsonl"):
        path = HERE / name
        if path.exists():
            records.extend(json.loads(line) for line in path.read_text().splitlines())
    for record in records:
        validate(record["input"])
    selected_ids = {"six_scenario_boundary_04", "six_scenario_boundary_12", "crossing_pole_models_05",
                    "antagonistic_scales_02", "dense_log_ladder_03", "pole_count_transition_00"}
    selected = []
    for record in records:
        if record["id"] not in selected_ids:
            continue
        for name in ("baseline", "champion"):
            record[name + "_verification"] = verify(record["input"], record[name])
        if all(record[name + "_verification"]["verified"] for name in ("baseline", "champion")):
            baseline = record["baseline_verification"]["enclosure"]
            champion = record["champion_verification"]["enclosure"]
            record["champion_over_baseline_lower"] = math.exp(min(700, champion["log_lower"] - baseline["log_upper"]))
            record["champion_over_baseline_upper"] = math.exp(min(700, champion["log_upper"] - baseline["log_lower"]))
            record["certified_regression"] = record["champion_over_baseline_lower"] > 1.005
        save(HERE / "cases" / (record["id"] + ".json"), record["input"])
        save(HERE / "outcomes" / (record["id"] + ".json"), record)
        selected.append({"id": record["id"], "family": record["family"],
                         "baseline_cpu_seconds": record["baseline"]["solve_cpu_seconds"],
                         "champion_cpu_seconds": record["champion"]["solve_cpu_seconds"],
                         "baseline": record["baseline_verification"], "champion": record["champion_verification"],
                         "ratio_lower": record.get("champion_over_baseline_lower"),
                         "ratio_upper": record.get("champion_over_baseline_upper"),
                         "certified_regression": record.get("certified_regression", False)})
        print(record["id"], "enclosed ratio", record.get("champion_over_baseline_lower"),
              record.get("champion_over_baseline_upper"), flush=True)
    outcomes = [json.loads(path.read_text()) for path in (HERE / "outcomes").glob("*.json")]
    regressions = [record["id"] for record in outcomes if record.get("certified_regression")]
    valid_pairs = [record for record in outcomes if all(record.get(name + "_verification", {}).get("verified") for name in ("baseline", "champion"))]
    summary = {"kind": "privileged_generation_only_stress_search", "screened_cases": len(records),
               "schema_validated_cases": len(records), "families": sorted({record["family"] for record in records}),
               "invalid_champion_outputs": [record["id"] for record in records if not record["champion"]["valid_output"]],
               "fully_enclosed_case_pairs": len(valid_pairs), "verified_regressions": regressions,
               "champion_max_imported_solve_cpu_seconds": max(record["champion"]["solve_cpu_seconds"] for record in records),
               "champion_internal_budget_hits": [record["id"] for record in records if record["champion"]["solve_cpu_seconds"] >= 5.8],
               "selected_case_results": selected,
               "strongest_coherent_stress_family": "six_scenario_boundary",
               "provisional_generation2_diagnostic_cases": ["six_scenario_boundary_04", "six_scenario_boundary_12"],
               "ratchet_recommendation": "No failure-based ratchet justified unless verified_regressions is nonempty. Selected cases are diagnostics, not demonstrated numerical failures.",
               "grading_caveat": "Direct imported-function search; main must grade selected full programs in the corrected sandbox supervisor.",
               "numerical_caveat": "Oracle enclosure objects are saved verbatim; these are checked floating-point bounds, not exact-rational certificates.",
               "thresholds_modified": False, "hardness_claim": None}
    save(HERE / "final_summary.json", summary)
    audit = json.loads((HERE / "peak_audit.json").read_text())
    broad = json.loads((HERE / "summary.json").read_text())
    focused = json.loads((HERE / "focused_summary.json").read_text())
    unresolved = [record["id"] for record in outcomes if any(
        "unresolved" in record.get(name + "_verification", {}).get("error", "") for name in ("baseline", "champion"))]
    handoff = {"classification_recommendation": "solved_no_justified_ratchet",
               "basis": "Main-audited generation-1 fresh pass; bounded private sweep found no genuine numerical regression.",
               "main_reported_fresh_scores": {"core_score": 1.533655280672833,
                                               "worst_family_score": 1.2076232776972333,
                                               "resource_score": 0.90332959375},
               "screened_cases": len(records), "scientific_families": len(summary["families"]),
               "schema_validated_cases": len(records), "oracle_confirmed_case_pairs": len(valid_pairs),
               "oracle_confirmed_enclosures": 2 * len(valid_pairs), "triage_only_cases": len(records) - len(valid_pairs),
               "genuine_numerical_failures": regressions, "oracle_unresolved_cases": unresolved,
               "invalid_outputs": summary["invalid_champion_outputs"],
               "peak_audit_cases": audit["examined"], "significant_peak_underestimates": audit["significant_underestimates"],
               "maximum_imported_solve_cpu_seconds": summary["champion_max_imported_solve_cpu_seconds"],
               "broad_plus_focused_search_wall_seconds": broad["elapsed_wall_seconds"] + focused["wall_seconds"],
               "root_cause_status": "Suspected missed-peak mechanism not reproduced; timer-limited refinement retained better-than-baseline nodes.",
               "strongest_stress_family": "six_scenario_boundary",
               "optional_isolated_audit_cases": [item["id"] for item in selected if item["family"] == "six_scenario_boundary"],
               "proposed_generation2_cases": [], "generation2_recommendation": "Do not launch a failure-based ratchet from this evidence.",
               "thresholds_changed": False, "authoritative_new_isolated_runs": 0,
               "caveat": "147 cases are triage-only; a finite unsuccessful sweep is not a universal optimality guarantee. Imported timings exclude executable startup.",
               "hashes": broad["hashes"]}
    save(HERE / "handoff.json", handoff)
    manifest = sorted(str(path.relative_to(HERE)) for path in HERE.rglob("*") if path.is_file() and path.name != "changed_paths.txt")
    manifest.append("changed_paths.txt")
    (HERE / "changed_paths.txt").write_text("\n".join("adversary/champion_search/" + name for name in sorted(manifest)) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "selected_case_results"}, indent=2))


if __name__ == "__main__":
    main()
