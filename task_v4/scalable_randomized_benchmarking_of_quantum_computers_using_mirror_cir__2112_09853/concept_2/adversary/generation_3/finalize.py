from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from promote import edit_files


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def digest(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def main():
    status = load("status.json")
    assert status["current_generation"] == 3 and status["remaining_ratchets"] == 0
    assert not status["participant_ready_for_main_runner"] and not status["current_generation_fresh_attempts"]
    manifest = load("evaluator/hidden/manifest.json")
    for relative, expected in manifest["files"].items():
        assert digest(relative) == expected, relative
    baseline = load("evaluator/hidden/generation_3_baseline_report.json")
    selfcheck = load("evaluator/hidden/generation_3_selfcheck_report.json")
    assert baseline["valid"] and baseline["isolation"] == "bwrap" and len(baseline["episodes"]) == 12
    assert baseline["manifest_sha256"] == status["manifest_sha256"]
    assert all(record["shots_used"] <= 2000 for record in baseline["episodes"])
    assert selfcheck["passed"] and selfcheck["self_checks_passed"] == 56 and selfcheck["isolation"] == "bwrap"
    assert digest("participant/workspace/model.py") == digest("evaluator/hidden/model.py")
    assert digest("participant/workspace/transport.py") == digest("evaluator/hidden/transport.py")
    assert load("participant/input/limits.json")["shots_budget"] == 2000
    broad = load("adversary/generation_3/broad.json")
    confirmation = load("adversary/generation_3/confirmation.json")
    assert len(broad["records"]) == 120 and all(record["valid"] for record in broad["records"])
    assert len(confirmation["records"]) == 36 and all(record["valid"] for record in confirmation["records"])
    selected = [record for record in confirmation["records"] if record["budget"] == 2000]
    summary = next(row for row in confirmation["summaries"] if row["budget"] == 2000)
    neighbor = next(row for row in confirmation["summaries"] if row["budget"] == 6000)
    assert not summary["quality_target_met"] and neighbor["certified_isolated_pass"]
    families = ("local_clusters", "distant_pairs", "anticorrelated", "spam_drift")
    diagnostics = {}
    for family in families:
        rows = [record["diagnostics"] for record in selected if record["family"] == family]
        diagnostics[family] = {field: float(np.mean([row[field] for row in rows]))
                               for field in ("support_recall", "support_precision", "supported_pairs_unobserved",
                                             "base_rmse", "depth_zero_shots", "max_adjacent_spam_change",
                                             "mean_true_support_posterior_inclusion",
                                             "known_support_spam_prior_moment_fisher_proxy")}
    generator = np.random.default_rng(20260828)
    bootstrap_family_scores = []
    for family in families:
        shape_means = []
        for shape in ((4, 4), (4, 5), (5, 5)):
            errors = np.array([record["normalized_mse"] for record in selected
                               if record["family"] == family and tuple(record["shape"]) == shape])
            assert len(errors) == 2
            indices = generator.integers(0, 2, size=(20000, 2))
            shape_means.append(errors[indices].mean(axis=1))
        bootstrap_family_scores.append(1 / (1 + np.mean(shape_means, axis=0)))
    bootstrap_family_scores = np.asarray(bootstrap_family_scores)
    benchmark = load("evaluator/hidden/benchmark.json")
    seed_sets = {"g3_hidden": {row["seed_hex"] for row in benchmark["episodes"]},
                 "g2_hidden": {row["seed_hex"] for row in load("adversary/generation_2_snapshot/evaluator/hidden/benchmark.json")["episodes"]},
                 "g1_hidden": {row["seed_hex"] for row in load("adversary/generation_1_snapshot/evaluator/hidden/benchmark.json")["episodes"]},
                 "exploration": {row["seed_hex"] for row in load("adversary/generation_3/cases_exploration.json")},
                 "confirmation": {row["seed_hex"] for row in load("adversary/generation_3/cases_confirmation.json")}}
    labels = list(seed_sets)
    for index, label in enumerate(labels):
        assert not seed_sets[label].intersection(set().union(*(seed_sets[other] for other in labels[index + 1:])))
    public_files = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted((ROOT / "participant").rglob("*"))
                    if path.is_file() and not {"__pycache__", ".git"}.intersection(path.parts)}
    tree_hash = hashlib.sha256(json.dumps(public_files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    sampler_hash = digest("champions/generation_2/sampler.so")
    assert digest("adversary/generation_3/policies/proportional/sampler.so") == sampler_hash
    assert digest("adversary/generation_3/policies/adaptive/sampler.so") == sampler_hash
    evidence = ["adversary/generation_3/broad.json", "adversary/generation_3/confirmation.json",
                "adversary/generation_3/cases_exploration.json", "adversary/generation_3/cases_confirmation.json",
                "adversary/generation_3/policy.py", "adversary/generation_3/sweep.py",
                "champions/generation_2/policy.py", "champions/generation_2/sampler.cpp",
                "evaluator/hidden/generation_3_baseline_report.json", "evaluator/hidden/generation_3_selfcheck_report.json",
                "evaluator/hidden/benchmark.json", "evaluator/hidden/manifest.json"]
    ready = datetime.now(timezone.utc).isoformat()
    audit = {
        "generation": 3, "final_generation": True, "ratchets_used": 2, "ratchets_remaining": 0,
        "selected_budget": 2000, "frozen_utc": benchmark["frozen_utc"], "ready_utc": ready,
        "quality_targets": status["target"], "full_sampler_unchanged_sha256": sampler_hash,
        "sampler_chains_rescaled": False,
        "adaptation": "Actual archived G2 Bayesian policy and compiled sampler. Allocation counts follow declared budget; the adaptive-design context uses that budget rather than 12,000. The sampler, 600/250/3 interim and 1500/500/4 final schedule, and original CPU/wall safeguards are unchanged. Two allocation variants were screened; no L1 policy is used.",
        "selection": "3,000 shots is near the current champion's quality frontier; 2,000 produces substantial valid quality failure. Do not use the more severe 1,500/1,000 settings. All physical priors and quality/runtime limits stay fixed.",
        "broad_results": broad["summaries"], "independent_confirmation": summary,
        "neighboring_isolated_pass_not_selected_budget_proof": neighbor,
        "root_diagnostics": diagnostics,
        "root_cause_interpretation": "Support recall falls to about one quarter, with fewer than one supported pair unobserved on average. Anticorrelated heterogeneity and SPAM drift are hardest. This points mainly to unresolved sparse support and nuisance coupling, not invalid budgets. The champion uses approximate independent inclusion priors and a Fourier drift approximation; exploiting disclosed joint priors and improving active design remain genuine open routes, not changes to hidden physics.",
        "noise_diagnostics": {"known_support_spam_prior_moment_proxy_mean": float(np.mean([record["diagnostics"]["known_support_spam_prior_moment_fisher_proxy"] for record in selected])),
                              "unregularized_fisher_identifiable_cases": summary["oracle_proxy_identifiable_episodes"],
                              "cases": 24,
                              "caveat": "Unregularized local information is rank deficient in some cases. Adding Gaussian prior-moment precision with true support and SPAM yields an optimistic local diagnostic, not a rigorous risk bound, posterior computation, or achievability certificate. No passing 2,000-shot policy is claimed."},
        "confirmation_bootstrap": {"average_percentile_95": np.quantile(bootstrap_family_scores.mean(axis=0), [.025, .975]).tolist(),
                                   "worst_percentile_95": np.quantile(bootstrap_family_scores.min(axis=0), [.025, .975]).tolist(),
                                   "method": "20,000 episode-cluster resamples stratified by family and graph shape; two seed replicas per stratum, fixed analysis RNG 20260828. Descriptive small-stratum intervals, not resampling correlated targets."},
        "seed_sets_disjoint": True, "seed_counts": {label: len(values) for label, values in seed_sets.items()},
        "baseline": {key: baseline[key] for key in ("valid", "passed", "average_family_score", "worst_family_score", "isolation")},
        "baseline_repair": "Standalone pure-Python weak policy calibrates a budget-feasible subset of single edges; unmeasured edges use the measured mean. No champion inference, native library, or private data enters participant assets.",
        "self_checks_passed": 56,
        "validation": "Physics normalization, zero/nonzero noise, budget and phase enforcement, malformed messages, symlinks/hardlinks/path traversal, hidden paths/parent proc, isolated NumPy/SciPy/BLAS/LAPACK, and 12 valid partial-baseline episodes pass.",
        "resource_contract": "60 aggregate child CPU seconds plus 0.25 accounting tolerance; 90-second episode wall deadline including teardown; 1536 MiB address-space limit per process, not aggregate memory. At most four independent calibration workers.",
        "evidence_sha256": {relative: digest(relative) for relative in evidence},
        "participant_files_sha256": public_files, "participant_tree_sha256": tree_hash,
        "tree_hash_format": "SHA256 of compact sorted-key JSON path-to-SHA256 map; __pycache__ and .git excluded.",
        "archives_untouched": ["attempts", "champions/generation_1", "champions/generation_2", "adversary/generation_1_snapshot", "adversary/generation_2_snapshot"],
        "fresh_agents_launched_by_author": 0,
    }
    edit_files({"adversary/generation_3/frontier_audit.json": json.dumps(audit, indent=2) + "\n"})
    status.update(status="generation_3_frozen_ready", participant_ready_for_main_runner=True,
                  ready_utc=ready, package_frozen=True, author_build_complete=True,
                  baseline_core_score=baseline["core_score"], baseline_worst_family_score=baseline["worst_family_score"],
                  baseline_valid=True, baseline_passed=baseline["passed"], baseline_isolation="bwrap",
                  self_checks_passed=56, participant_tree_sha256=tree_hash,
                  private_audit_sha256=digest("adversary/generation_3/frontier_audit.json"))
    edit_files({"status.json": json.dumps(status, indent=2) + "\n"})
    print(json.dumps({"status": status["status"], "generation": 3, "budget": 2000,
                      "manifest_sha256": status["manifest_sha256"], "baseline_average": baseline["core_score"],
                      "baseline_worst": baseline["worst_family_score"], "champion_average": summary["average_score"],
                      "champion_worst": summary["worst_family_score"], "confirmation_bootstrap": audit["confirmation_bootstrap"]}))


if __name__ == "__main__":
    main()
