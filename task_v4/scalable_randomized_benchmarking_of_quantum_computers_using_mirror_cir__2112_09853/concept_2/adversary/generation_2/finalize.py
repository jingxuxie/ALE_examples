import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def digest(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def save_json(relative, value):
    path = ROOT / relative
    content = json.dumps(value, indent=2) + "\n"
    if path.exists():
        patch = "*** Begin Patch\n*** Update File: " + relative + "\n@@\n"
        patch += "".join("-" + line + "\n" for line in path.read_text().splitlines())
    else:
        patch = "*** Begin Patch\n*** Add File: " + relative + "\n"
    patch += "".join("+" + line + "\n" for line in content.splitlines())
    subprocess.run(["apply_patch", patch + "*** End Patch\n"], cwd=ROOT, check=True)


def main():
    status = load("status.json")
    assert status["current_generation"] == 2
    assert not status["current_generation_fresh_attempts"]
    assert not status["participant_ready_for_main_runner"]
    manifest = load("evaluator/hidden/manifest.json")
    for relative, expected in manifest["files"].items():
        assert digest(relative) == expected, relative
    baseline_path = "evaluator/hidden/generation_2_baseline_report.json"
    champion_path = "evaluator/hidden/generation_2_adapted_champion_report.json"
    selfcheck_path = "evaluator/hidden/generation_2_selfcheck_report.json"
    baseline = load(baseline_path)
    champion = load(champion_path)
    selfcheck = load(selfcheck_path)
    for report in (baseline, champion):
        assert report["valid"] and report["isolation"] == "bwrap"
        assert not report["passed"] and report["reason"] == "accuracy_target_not_met"
        assert len(report["episodes"]) == 12
        assert all(record["shots_used"] <= 12000 for record in report["episodes"])
        assert report["manifest_sha256"] == digest("evaluator/hidden/manifest.json")
    assert selfcheck["passed"] and selfcheck["self_checks_passed"] == 56
    assert selfcheck["isolation"] == "bwrap"
    assert digest("participant/workspace/model.py") == digest("evaluator/hidden/model.py")
    assert digest("participant/workspace/transport.py") == digest("evaluator/hidden/transport.py")
    assert load("participant/input/limits.json")["shots_budget"] == 12000
    benchmark = load("evaluator/hidden/benchmark.json")
    assert benchmark["fixed_before_fresh_attempts"] and benchmark["generation"] == 2
    broad = load("adversary/generation_2/broad_audit.json")
    confirmation = load("adversary/generation_2/confirm_12000_bwrap.json")
    neighbor = load("adversary/generation_2/confirm_24000_bwrap.json")
    assert len(broad["records"]) == 252 and all(record["valid"] for record in broad["records"])
    assert confirmation["summaries"][0]["valid"] and not confirmation["summaries"][0]["quality_target_met"]
    assert neighbor["summaries"][0]["certified_isolated_pass"]
    seeds = {"generation_2_hidden": {row["seed_hex"] for row in benchmark["episodes"]}}
    for label in ("exploration", "confirmation", "holdout"):
        relative = "adversary/generation_2/cases_" + label + ".json"
        if (ROOT / relative).exists():
            seeds[label] = {row["seed_hex"] for row in load(relative)}
    old_cases = load("adversary/generation_1_snapshot/evaluator/hidden/benchmark.json")
    seeds["generation_1_hidden"] = {row["seed_hex"] for row in old_cases["episodes"]}
    labels = list(seeds)
    for index, label in enumerate(labels):
        assert not seeds[label].intersection(set().union(*(seeds[other] for other in labels[index + 1:])))
    public_default_seeds = {2026 + 1009 * family_index + 53 * shape_index
                            for family_index in range(4) for shape_index in range(3)}
    assert all(int(seed, 16) not in public_default_seeds for group in seeds.values() for seed in group)
    family_diagnostics = {}
    for family in confirmation["summaries"][0]["families"]:
        records = [record["diagnostics"] for record in confirmation["records"] if record["family"] == family]
        family_diagnostics[family] = {
            field: sum(record[field] for record in records) / len(records)
            for field in ("support_recall", "support_precision", "supported_pairs_unobserved",
                          "base_rmse", "depth_zero_shots", "max_adjacent_spam_change",
                          "oracle_local_fisher_normalized_mse")}
    public_files = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted((ROOT / "participant").rglob("*"))
                    if path.is_file() and not {"__pycache__", ".git"}.intersection(path.parts)}
    tree_hash = hashlib.sha256(json.dumps(public_files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    evidence_paths = [baseline_path, champion_path, selfcheck_path,
                      "adversary/generation_2/broad_audit.json",
                      "adversary/generation_2/confirm_12000_bwrap.json",
                      "adversary/generation_2/confirm_24000_bwrap.json",
                      "adversary/generation_2/cases_exploration.json",
                      "adversary/generation_2/cases_confirmation.json",
                      "adversary/generation_2/champion_policy.py",
                      "adversary/generation_2/budget_policy.py",
                      "evaluator/hidden/benchmark.json", "evaluator/hidden/manifest.json"]
    ready_utc = datetime.now(timezone.utc).isoformat()
    audit = {
        "generation": 2, "selected_budget": 12000, "ready_utc": ready_utc,
        "frozen_utc": benchmark["frozen_utc"], "quality_targets": status["target"],
        "selection": "Keep 12,000 shots: the valid allocation-adapted champion fails average accuracy substantially across independent cases; 24,000 shots passes under isolation. Avoid 8,000 or less because optimistic shot-noise and estimability diagnostics become tighter.",
        "adaptation": "Only shot allocation, context count, control thinning and midpoint refit timing change. Original champion inference and matching design are retained; no hidden parameter or target access is added to the policy.",
        "exploration": broad["summaries"],
        "independent_isolated_confirmation": confirmation["summaries"][0],
        "neighboring_isolated_pass_not_same_budget_achievability": neighbor["summaries"][0],
        "frozen_suite_adapted_champion": {key: champion[key] for key in ("valid", "passed", "average_family_score", "worst_family_score", "families", "resources")},
        "root_diagnostics": family_diagnostics,
        "diagnostic_interpretation": "All supported pairs were queried in the independent 12-case confirmation, yet mean support recall is only 0.319. Limited-signal support selection and coupled base/SPAM inference, rather than absent pair coverage or invalid budgets, dominate. Local clusters and SPAM drift score lowest in that confirmation; this is observational, not a causal ablation.",
        "fisher_caveat": "Known true support and SPAM give an optimistic local Fisher normalized-MSE proxy of 0.3687 at 12,000 shots. This is not a certified achievable score, global Bayesian bound, or proof with unknown nuisance parameters. Generation two remains hard open.",
        "additional_holdout": {"report": "adversary/generation_2/confirm_12000_holdout_bwrap.json", "cases": 36, "strategy": "coverage_thin", "role": "Post-selection independent confirmation only; no resulting target or budget changes."},
        "seed_counts": {label: len(group) for label, group in seeds.items()},
        "seed_sets_disjoint": True, "public_default_seeds_disjoint": True,
        "validation": {"self_checks_passed": 56, "baseline_valid_episodes": 12,
                       "baseline_average_score": baseline["average_family_score"],
                       "baseline_worst_family_score": baseline["worst_family_score"],
                       "public_private_model_and_transport_match": True,
                       "cpu_accounting": "Independent worker processes, at most four, with per-episode aggregate child CPU enforcement.",
                       "memory_contract": "1536 MiB address space per process, not aggregate memory or a process-count bound."},
        "evidence_sha256": {relative: digest(relative) for relative in evidence_paths},
        "participant_files_sha256": public_files,
        "participant_tree_sha256": tree_hash,
        "tree_hash_format": "SHA256 of compact sorted-key JSON mapping relative file paths to SHA256, excluding __pycache__ and .git.",
        "immutable_archives": ["adversary/generation_1_snapshot", "champions/generation_1", "attempts/v_1"],
        "fresh_agents_launched_by_author": 0,
    }
    save_json("adversary/generation_2/frontier_audit.json", audit)
    status["generation_history"][0]["baseline_average_score"] = status["baseline_core_score"]
    status["generation_history"][0]["baseline_worst_family_score"] = status["baseline_worst_family_score"]
    status["generation_history"][0]["public_baseline_core_score"] = status.pop("public_baseline_core_score", None)
    status.update(status="generation_2_frozen_ready", participant_ready_for_main_runner=True,
                  package_frozen=True, ready_utc=ready_utc, self_checks_passed=56,
                  baseline_core_score=baseline["core_score"], baseline_worst_family_score=baseline["worst_family_score"],
                  baseline_valid=True, baseline_passed=False, baseline_isolation="bwrap",
                  participant_tree_sha256=tree_hash, champion_generation=1,
                  current_generation_champion=None, additional_holdout_report=audit["additional_holdout"]["report"],
                  adapted_champion_frozen_suite_report=champion_path,
                  private_audit_sha256=digest("adversary/generation_2/frontier_audit.json"))
    save_json("status.json", status)
    print(json.dumps({"status": status["status"], "current_generation": status["current_generation"],
                      "manifest_sha256": status["manifest_sha256"], "participant_tree_sha256": tree_hash,
                      "baseline_average": baseline["core_score"], "baseline_worst": baseline["worst_family_score"],
                      "adapted_champion_average": champion["core_score"], "adapted_champion_worst": champion["worst_family_score"]}))


if __name__ == "__main__":
    main()
