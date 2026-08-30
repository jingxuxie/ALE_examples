from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np


AREA = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tuning = [json.loads((AREA / (label + ".json")).read_text()) for label in ("tuning_1", "tuning_2")]
    confirmation = [json.loads((AREA / (label + ".json")).read_text()) for label in ("confirmation_1", "confirmation_2")]
    selection = json.loads((AREA / "official_validation_audit.json").read_text())
    official = json.loads((AREA / "official_report.json").read_text())
    best = selection["variant"]
    records = [record for report in confirmation for record in report["records"]]
    variants = sorted({record["variant"] for record in records})
    families = ("local_clusters", "distant_pairs", "anticorrelated", "spam_drift")
    shapes = ((4, 4), (4, 5), (5, 5))
    generator = np.random.default_rng(492806)
    replicates = 20000
    scores = {}
    sampled_indices = generator.integers(0, 3, size=(4, 3, replicates, 3))
    for variant in variants:
        family_scores = []
        for family_index, family in enumerate(families):
            shape_means = []
            for shape_index, shape in enumerate(shapes):
                members = sorted([record for record in records if record["variant"] == variant and
                                  record["family"] == family and tuple(record["shape"]) == shape],
                                 key=lambda record: record["replica"])
                assert len(members) == 3 and all(record["valid"] for record in members)
                errors = np.asarray([record["normalized_mse"] for record in members])
                shape_means.append(errors[sampled_indices[family_index, shape_index]].mean(axis=1))
            family_scores.append(1 / (1 + np.mean(shape_means, axis=0)))
        family_scores = np.asarray(family_scores)
        scores[variant] = {"average": family_scores.mean(axis=0), "worst": family_scores.min(axis=0)}
    bootstrap = {variant: {metric + "_percentile_95": np.quantile(values, [.025, .975]).tolist()
                           for metric, values in statistics.items()} for variant, statistics in scores.items()}
    delta = scores[best]["average"] - scores["adapted_champion"]["average"]
    tuning_seeds = json.loads((AREA / "cases_tuning.json").read_text())
    confirmation_seeds = json.loads((AREA / "cases_confirmation.json").read_text())
    assert not {row["seed_hex"] for row in tuning_seeds}.intersection(row["seed_hex"] for row in confirmation_seeds)
    evidence = ["tuning_1.json", "tuning_2.json", "confirmation_1.json", "confirmation_2.json",
                "cases_tuning.json", "cases_confirmation.json", "official_selection.json",
                "official_validation_audit.json", "official_report.json", "policy.py", "search.py", "variants.json"]
    report = {
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "write_scope": "adversary/generation_2/private_achievability only",
        "current_fresh_attempt_files_accessed": False,
        "frozen_participant_evaluator_status_modified": False,
        "best_policy": "adversary/generation_2/private_achievability/policies/" + best + "/policy.py",
        "submission_directory": "adversary/generation_2/private_achievability/policies/" + best,
        "required_files": ["policy.py", "champion_policy.py", "settings.json"],
        "budget": 12000,
        "unchanged_targets": {"average": .5, "worst": 1 / 2.5625},
        "official_result": {key: official[key] for key in ("valid", "passed", "reason", "average_family_score",
                                                           "worst_family_score", "families", "resources", "isolation", "manifest_sha256")},
        "official_runtime": selection["relocation"],
        "official_source_and_candidate_unchanged": selection["source_and_candidate_unchanged"],
        "confirmation_results": [summary for result in confirmation for summary in result["summaries"]],
        "training_results": [summary for result in tuning for summary in result["summaries"]],
        "unique_training_episodes": len(tuning_seeds),
        "unique_confirmation_episodes": len(confirmation_seeds),
        "training_runs": sum(len(result["records"]) for result in tuning),
        "confirmation_runs": len(records),
        "training_invalid_runs": sum(not record["valid"] for result in tuning for record in result["records"]),
        "confirmation_invalid_runs": sum(not record["valid"] for record in records),
        "bootstrap": bootstrap,
        "paired_average_improvement_over_adapted_champion_percentile_95": np.quantile(delta, [.025, .975]).tolist(),
        "bootstrap_method": "20,000 paired episode-cluster resamples, stratified by family and graph shape; three independent seed replicas per stratum. Resample episodes, not 96 correlated predictions. Fixed analysis RNG seed 492806. Small-stratum empirical intervals are descriptive and do not account for candidate selection.",
        "frozen_suite_prior_reference": {"weak_baseline_average": .15064972875807964,
                                         "weak_baseline_worst": .11934104676360673,
                                         "adapted_champion_average": .42611969461271254,
                                         "adapted_champion_worst": .38577205241744034,
                                         "source": "Previously completed frozen generation-two baseline and allocation-adapted champion validations; neither was rerun or modified here."},
        "scientific_changes": [
            "Regularize bounded base-error and SPAM parameters using disclosed prior moments.",
            "Retain weak nonnegative interaction coefficients rather than hard support thresholding and unrestricted debiasing.",
            "Jointly refit rates and nuisance SPAM with the exact binomial likelihood and a weaker sparsity penalty.",
            "Use fewer isolated controls, varied dense native matchings, and measurement depths adapted after an intermediate fit."
        ],
        "negative_result": "Dense Gaussian-prior ridge alone stayed near 0.4; sparse shrinkage and likelihood calibration mattered more than simply changing the shot count.",
        "policy_privacy": "Candidate imports only its archived champion helper, NumPy/SciPy and standard library; reads only local settings and JSON stdin. No generator, seed, hidden parameter, target-oracle or evaluator hooks in the submission.",
        "attainability_claim": "The fixed generation-two benchmark is attained under unchanged official scoring and bwrap limits." if official["passed"] else "No passing fixed-benchmark claim: report the measured official failure honestly.",
        "evidence_sha256": {name: digest(AREA / name) for name in evidence},
    }
    (AREA / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"best_policy": report["best_policy"], "official": report["official_result"],
                      "holdout_intervals": bootstrap[best], "paired_improvement_95": report["paired_average_improvement_over_adapted_champion_percentile_95"]}, indent=2))


if __name__ == "__main__":
    main()
