from common import ROOT, digest, load_corpus, now, read_json, verify_files, write_json


def main():
    manifest, policy = load_corpus()
    report = read_json(ROOT / "report.json")
    validation = read_json(ROOT / "validation.json")
    source = read_json(ROOT / "source_manifest.json")
    verify_files(source["sha256"])
    verify_files(read_json(ROOT / "harness_manifest.json")["sha256"])
    if not validation["passed"]:
        raise ValueError("harness validation failed")
    roots = {record["case_id"]: record for record in read_json(ROOT / "root_cause.json")["records"]}
    counterexamples = []
    for name in ("vp03", "vp05"):
        control = read_json(ROOT / "controls" / (name + ".json"))
        reference = control["baseline"]
        repeats = control["attempts"]
        diagnostic = control["baseline_diagnostic"]
        maximum_wall = max(record["resource_accounting"]["wall_seconds"] for record in repeats)
        minimum_remaining = 55.0 - maximum_wall
        counterexamples.append({
            "case_id": name, "family": reference["family"], "baseline_energy": reference["baseline_energy"], "witness_energy": reference["witness_energy"], "gap": reference["reference_gap"],
            "case_path": reference["case_path"], "baseline_path": reference["baseline_path"], "witness_path": reference["witness_path"],
            "energy_at_65_percent_closure": reference["baseline_energy"] - 0.65 * reference["reference_gap"],
            "repeat_count": len(repeats), "repeat_energies": [record["checked_energy"] for record in repeats], "repeat_scores": [record["case_score"] for record in repeats], "all_repeats_resource_valid": all(record["valid"] for record in repeats), "strict_low_load_repeats": sum(record["low_load_validated"] for record in repeats),
            "maximum_repeat_wall_seconds": maximum_wall, "polish_gain": diagnostic["polish"]["gain"], "changed_hole_count": diagnostic["topology"]["changed_hole_count"], "changed_vortex_plaquettes": diagnostic["topology"]["changed_vortex_plaquettes"],
            "budget_independence_evidence": {"solver_declared_budget": 55.0, "largest_time_cutoff_reserve": 6.5, "minimum_remaining_budget_lower_bound": minimum_remaining, "time_cutoffs_cannot_explain_failure": minimum_remaining > 6.5, "argument": "Budget starts inside the child, later than trusted outer wall timing; locked one-core CPU is no greater than elapsed wall. Thus the solver's monotone max(wall,cpu) budget never approached any search time guard. All repeats completed normally. Initialization-only reproduction succeeds on the exact input, ruling out the projection-failure fallback. Logs report zero nonlinear candidate trials; this supports a missing bulk-vortex search mechanism rather than time starvation.", "initialization_check": roots[name], "replaces_frozen_low_load_gate": False},
            "status": "persistent_quality_counterexample_not_certified_by_strict_low_load_gate",
        })
    quality = {"at": now(), "status": "persistent_quality_gaps_with_explicit_certification_caveat", "cases": counterexamples, "core_score_on_these_frozen_repeats": 0.0, "worst_family_score_on_these_frozen_repeats": 0.0, "thresholds_if_main_later_approves": {"core_min": policy["core_min"], "worst_family_min": policy["worst_family_min"]}, "formal_generation3_proposal": False, "new_executable_achievability": "unknown; no new solver qualified", "private_witnesses_preexist_v2_source_inspection": True, "source_manifest_sha256": digest(ROOT / "source_manifest.json"), "corpus_manifest_sha256": digest(ROOT / "corpus/manifest.json")}
    write_json(ROOT / "quality_counterexamples.json", quality)
    valid = [entry for entry in report["broad_results"] if entry["record"]["valid"]]
    reached = [entry for entry in valid if entry["record"]["remaining_gap"] <= 1e-7]
    invalid = [entry["record"]["case_id"] for entry in report["broad_results"] if not entry["record"]["valid"]]
    report.update({"finalized_at": now(), "broad_valid_count": len(valid), "broad_reached_or_beat_witness_count": len(reached), "broad_infrastructure_cases": invalid, "persistent_quality_cases": [entry["case_id"] for entry in counterexamples], "quality_counterexamples": "quality_counterexamples.json", "root_cause": "root_cause.json", "validation": "validation.json", "tests_passed": validation["tests_run"], "official_A2_result_unchanged": "valid/pass core=1.0 worst=1.0", "active_solver_processes": 0, "strict_low_load_gate_satisfied": False, "formal_generation3_proposal": False, "incomplete_cpu_accounting_note": "Killed-wrapper cases have only outer Bubblewrap CPU in their raw accounting; their payload CPU is unknown. They are invalid infrastructure outcomes, never counted as hard quality counterexamples.", "scratch_caveat": "This initial campaign used shared-workspace scratch. Large startup/IO overhead and sibling contention were observed; normal local helper scratch was requested but not used without Main permission. No post-hoc gate relaxation or extra solver campaign was performed."})
    write_json(ROOT / "report.json", report)
    write_json(ROOT / "status.json", {key: value for key, value in report.items() if key not in ("broad_results", "controls", "diagnostic_broad_score")})
    lines = [
        "# A2 bounded broad replay: measured disposition", "", "**Status: resource_inconclusive under the predeclared certification policy.**",
        "Two repeatable physical quality gaps remain, so claiming `no_meaningful_ratchet` or global robustness would be inaccurate. The strict quiet-load gate was not met, so no certified generation-3 proposal is created or installed. Main's official A2 result remains valid/pass/core=1.0/worst=1.0.", "", "## Coverage and outcomes", "",
        "- Preserved 24 validated physical cases and their preexisting attained fields; selected 13 stationary starts with gaps at least 0.5 before reading v2.",
        "- Ran 21 unchanged-solver processes, sequentially: 13 broad cases, two warm-discovery runs, and six frozen-input repeats. All work is stopped; no fresh agents or live asset edits.",
        "- Broad outcomes: 10 valid; eight reach or beat witnesses; two retain stationary/topological gaps; three wrapper deadline failures (`nf04`, `nf05`, `nf06`) are infrastructure, not hard counterexamples.",
        "- 17 harness tests pass, including all 24 reference/physical-input rechecks, gradient/gauge checks, topology covariance, supplied-start equality, safe NPZ loading, result gates, and control decisions.", "", "## Persistent quality findings", "",
        "| Case | Supplied A2 baseline B | Preexisting witness W | Gap | Three frozen warm-repeat scores |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for entry in counterexamples:
        lines.append("| " + entry["case_id"] + " | %.12f | %.12f | %.12f | 0, 0, 0 |" % (entry["baseline_energy"], entry["witness_energy"], entry["gap"]))
    lines.extend([
        "", "Both cases are in the real `vortex_pinning` family. Fields are stationary, unchanged under warm replay, and improve by less than 1e-9 under tighter local polishing. Reliable topology diagnostics find 148 and 114 changed vortex plaquettes relative to the respective witnesses (plus one changed hole winding in vp03). No new witnesses, synthetic frustrations, or global-minimum assertions are used.",
        "", "## Root cause versus resource caveat", "",
        "All six scored repeats are resource-valid and finish in 10.02–20.72 seconds. The captured solver declares 55 seconds and its largest time-cutoff reserve is 6.5 seconds. Trusted outer timings bound the remaining internal budget below by at least 34.27 seconds; therefore these failures cannot be explained by hitting a search time guard. Independent initialization-only reproduction succeeds. The solver logs zero nonlinear candidate trials: its harmonic hole-sector search has no explicit bulk-vortex relocation proposal, while the private witness changes the vortex allocation. This is evidence of a representation/search limitation, not loose tolerance or a larger grid alone.",
        "", "Nevertheless the frozen *proxy* for clean-load certification requires CPU/wall >=0.95, sibling busy fraction <=0.30, and low initial core load. No repeat meets all three. We do not silently substitute the stronger fixed-work argument for that predeclared gate. Exact resource counters and all six fields are preserved; `quality_counterexamples.json` makes this distinction machine-readable.",
        "", "Three other cases exceed wrapper deadlines with shared-workspace scratch. Solver-printed energies are not trusted or counted as passing results. Payload CPU accounting is unavailable when the protected monitor is killed; raw outer Bubblewrap CPU is not a payload measurement. A local-scratch correction was requested, but no out-of-scope scratch writes or additional campaign were performed without permission.",
        "", "## Handoff", "",
        "- `report.json`, `status.json`: full measured disposition; `quality_counterexamples.json`: exact baseline/witness paths, zero scores, topology, and budget-independence argument.",
        "- `source_manifest.json`, `submission`: four-file byte-preserved finished v2 artifact; `provenance/v2_exit.json`, `v2_evaluation.json`, and `v2_audit.json`: official completion evidence.",
        "- `corpus/manifest.json`, `policy.json`: frozen 24-case preservation, 13-case selection, immutable preexisting witnesses and resource/quality gates.",
        "- `runs`, `controls`, `frozen_warm_inputs`, `diagnostics`: all per-process logs, timings, checked fields, fixed starts, and polish/topology controls.",
        "- `root_cause.json`, `root_cause.py`: successful 15-/20-dimensional sector initialization checks, not a new optimization portfolio.",
        "- `validation.json`, `physical_revalidation.json`, `test_harness.py`: 17 passing tests and 24-case physical/reference validation.",
        "", "No generation-3 executable is claimed feasible, no ground state is asserted, and no next generation is installed. Main may review the fixed-work evidence or authorize normal local ephemeral scratch for a bounded instrumentation repair before deciding on any proposal. Durable writes remain exclusively in ratchet_2.",
    ])
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n")
    files = [path for path in ROOT.rglob("*") if path.is_file() and path.name != "evidence_manifest.json" and not any(part in ("scratch", "corpus", "assets", "__pycache__") for part in path.relative_to(ROOT).parts)]
    files.append(ROOT / "corpus/manifest.json")
    write_json(ROOT / "evidence_manifest.json", {"at": now(), "sha256": {str(path.relative_to(ROOT)): digest(path) for path in sorted(files)}, "immutable_corpus_and_assets_are_transitively_hashed": True, "no_formal_generation3_proposal": True})
    print({"status": report["status"], "solver_processes": report["solver_processes_launched"], "broad_valid": len(valid), "witnesses_reached_or_beaten": len(reached), "persistent_quality_cases": report["persistent_quality_cases"], "infrastructure_cases": invalid, "tests_passed": validation["tests_run"], "evidence_files": len(files)})


if __name__ == "__main__":
    main()
